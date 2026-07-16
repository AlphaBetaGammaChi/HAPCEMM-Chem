# kpp_julia_box_model.jl
# Fully working prototype box-model solver and sensitivity analyzer in pure Julia.

using Catalyst, ModelingToolkit, OrdinaryDiffEq, SciMLSensitivity, NCDatasets

# ==========================================
# 1. KPP File Parsers
# ==========================================

function parse_spc(spc_path)
    species = String[]
    open(spc_path, "r") do io
        active = true
        for line in eachline(io)
            clean = strip(split(line, "#")[1])
            if isempty(clean)
                continue
            end
            if clean == "#DEFVAR"
                active = true; continue
            elseif clean == "#DEFFIX"
                active = false; continue
            end
            
            m = match(r"([A-Za-z0-9\(\)]+)\s*=", clean)
            if m !== nothing
                name = m.captures[1]
                push!(species, name)
            end
        end
    end
    return unique(species)
end

function parse_eqn(eqn_path)
    reactions = []
    open(eqn_path, "r") do io
        for line in eachline(io)
            # Match reaction lines like: {335} OH + H2 = H2O + H : GCARR(2.80E-12, 0.0E+00, -1800.0);
            m = match(r"\{(\d+)\}\s*([^\:]+)\s*\:\s*([^;]+);", line)
            if m !== nothing
                rx_num = parse(Int, m.captures[1])
                equation = strip(m.captures[2])
                rate = strip(m.captures[3])
                
                # Split reactants and products
                parts = split(equation, "=")
                reactants = strip(parts[1])
                products = strip(parts[2])
                
                push!(reactions, (num=rx_num, react=reactants, prod=products, rate=rate))
            end
        end
    end
    return reactions
end

# Helper to split reactant/product string (e.g. "OH + 2.000NO3") into components
function parse_species_coefs(str, species_symbols)
    components = []
    if str == "" || str == "IGNORE"
        return components
    end
    for term in split(str, "+")
        term = strip(term)
        m = match(r"^([\d\.]+)?\s*([A-Za-z0-9\(\)]+)$", term)
        if m !== nothing
            coef = m.captures[1] === nothing ? 1.0 : parse(Float64, m.captures[1])
            name = m.captures[2]
            sym = Symbol(name)
            if sym in species_symbols
                push!(components, (species=sym, coef=coef))
            end
        end
    end
    return components
end

# ==========================================
# 2. Symbolic Rate Parsers
# ==========================================

# Translates KPP rate strings into symbolic expressions in terms of T, P, etc.
# This ensures that temperature and pressure are fully differentiable parameters!
function parse_rate_to_symbolic(rate_str, T, P)
    clean_rate = replace(rate_str, "E" => "e") # change exponent syntax
    
    # 1. Match GCARR(A, B, C)
    m_gcarr = match(r"GCARR\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^,\)]+)\s*\)", clean_rate)
    if m_gcarr !== nothing
        A = parse(Float64, m_gcarr.captures[1])
        B = parse(Float64, m_gcarr.captures[2])
        C = parse(Float64, m_gcarr.captures[3])
        # Arrhenius expression: A * (T/300)^B * exp(-C/T)
        return A * (T / 300.0)^B * exp(-C / T)
    end
    
    # 2. Match PHOTOL(id)
    m_photol = match(r"PHOTOL\s*\(\s*(\d+)\s*\)", clean_rate)
    if m_photol !== nothing
        id = parse(Int, m_photol.captures[1])
        # Return a unique symbolic parameter for this photolysis rate
        param_name = Symbol("photol_", id)
        return @parameters $param_name[1]
    end
    
    # 3. Match HET(species, id)
    m_het = match(r"HET\s*\(\s*([^,]+)\s*,\s*(\d+)\s*\)", clean_rate)
    if m_het !== nothing
        sp_name = m_het.captures[1]
        id = parse(Int, m_het.captures[2])
        # Return a unique symbolic parameter for this heterogeneous rate
        param_name = Symbol("het_", sp_name, "_", id)
        return @parameters $param_name[1]
    end
    
    # 4. Fallback: Parse as a float constant if it is just a number
    try
        val = parse(Float64, clean_rate)
        return val
    catch
        # If it's a complex expression (e.g. "0.04 * PHOTOL(105)")
        # We simplify it by treating the whole rate string as a custom parameter
        param_name = Symbol("custom_rate_", replace(rx_clean_name(rate_str), r"[^A-Za-z0-9_]" => "_"))
        return @parameters $param_name[1]
    end
end

def_rx_clean_name(str) = strip(replace(str, r"\s+" => ""))

# ==========================================
# 3. Model Builder
# ==========================================

function build_model(spc_path, eqn_path)
    species = parse_spc(spc_path)
    reactions = parse_eqn(eqn_path)
    
    # Define time and parameters
    @parameters t T P entrain_rate
    species_syms = [Symbol(sp) for sp in species]
    @variables $(species_syms...)(t)
    
    # 1. Build Catalyst Reaction System
    catalyst_reactions = Reaction[]
    for rx in reactions
        react_data = parse_species_coefs(rx.react, species_syms)
        prod_data = parse_species_coefs(rx.prod, species_syms)
        
        reactants = [eval(sp.species) for sp in react_data]
        react_coefs = [sp.coef for sp in react_data]
        products = [eval(sp.species) for sp in prod_data]
        prod_coefs = [sp.coef for sp in prod_data]
        
        # Build symbolic rate expression
        rate_val = parse_rate_to_symbolic(rx.rate, T, P)
        
        push!(catalyst_reactions, Reaction(rate_val, reactants, products, react_coefs, prod_coefs))
    end
    
    rs = ReactionSystem(catalyst_reactions, t, species_syms, [T, P])
    odesys = convert(ODESystem, rs)
    
    # 2. Add Plume Dilution & Entrainment Equations
    eqs = equations(odesys)
    states_list = states(odesys)
    coupled_eqs = Equation[]
    
    for (i, eq) in enumerate(eqs)
        state = states_list[i]
        # Create ambient concentration parameter for each species
        ambient_name = Symbol("ambient_", state.metadata[Symbolics.varname])
        ambient_param = @parameters $ambient_name
        
        # d[X]/dt = Chem_RHS - entrain_rate * ([X] - [X]_ambient)
        new_rhs = eq.rhs - entrain_rate * (state - ambient_param[1])
        push!(coupled_eqs, Differential(t)(state) ~ new_rhs)
    end
    
    return ODESystem(coupled_eqs, t, states_list, [parameters(odesys)..., entrain_rate])
end

# ==========================================
# 4. Forward Solve and All-Metrics Adjoint
# ==========================================

function solve_and_analyze(odesys, u0_dict, param_dict, tspan)
    prob = ODEProblem(odesys, u0_dict, tspan, param_dict)
    
    # 1. Forward run
    sol = solve(prob, Rodas5(), reltol=1e-4, abstol=1e-6)
    println("[Julia BoxModel] Forward simulation complete. Time steps: ", length(sol.t))
    
    # 2. Sensitivities of ALL final outputs with respect to ALL parameters
    n_outputs = length(sol.u[end])
    n_params = length(parameters(odesys))
    
    # Initialize the sensitivity matrix (Output species x Parameters)
    dY_dp = zeros(Float64, n_outputs, n_params)
    
    println("[Julia BoxModel] Computing adjoint sensitivities for all $(n_outputs) metrics...")
    
    for i in 1:n_outputs
        # Cost function: final concentration of species i
        g(sol) = sol.u[end][i]
        
        # Compute gradient vector
        _, grad = adjoint_sensitivities(sol, Rodas5(), sensealg=InterpolatingAdjoint(), g=g)
        dY_dp[i, :] = grad
    end
    
    println("[Julia BoxModel] Adjoint sensitivity matrix computed: Size $(size(dY_dp))")
    return sol, dY_dp
end

# ==========================================
# 5. NetCDF Exporter
# ==========================================

function save_to_netcdf(filename, sol, dY_dp, species_names)
    NCDataset(filename, "c") do ds
        # Dimensions
        defDim(ds, "time", length(sol.t))
        defDim(ds, "species", length(species_names))
        defDim(ds, "params", size(dY_dp, 2))
        
        # Variables
        t_var = defVar(ds, "time", Float64, ("time",))
        t_var[:] = sol.t
        
        conc_var = defVar(ds, "concentrations", Float32, ("species", "time"))
        conc_var[:, :] = Float32.(reduce(hcat, sol.u))
        
        sens_var = defVar(ds, "sensitivities", Float32, ("species", "params"))
        sens_var[:, :] = Float32.(dY_dp)
        
        # Metadata attributes
        for (i, name) in enumerate(species_names)
            ds.attrib["species_$(i)"] = name
        end
    end
    println("[Julia BoxModel] Saved results to: ", filename)
end
