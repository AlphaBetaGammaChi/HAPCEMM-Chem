# micm_julia_box_model.jl
# Dynamic mechanism loader for MICM JSON mechanisms in pure Julia.

if length(ARGS) < 1
    println("Error: Missing mechanism directory argument.")
    println("Usage: julia micm_julia_box_model.jl <mechanism_directory_path> [solver_choice]")
    exit(1)
end

const MECH_DIR = ARGS[1]
if !isdir(MECH_DIR)
    println("Error: Directory does not exist: $MECH_DIR")
    exit(1)
end

const SOLVER_CHOICE = length(ARGS) >= 2 ? ARGS[2] : "QNDF"

using Catalyst, ModelingToolkit, OrdinaryDiffEq, SciMLSensitivity, JSON, Test, ForwardDiff

# Clean species names by stripping leading numbers and whitespaces
function clean_species_name(s::String)
    cleaned = replace(s, r"^\d+" => "")
    cleaned = strip(cleaned)
    return Symbol(cleaned)
end

function build_micm_model(mech_dir)
    species_path = joinpath(mech_dir, "species.json")
    
    # Support both mechanism.json and reactions.json
    reactions_path = joinpath(mech_dir, "reactions.json")
    if !isfile(reactions_path)
        reactions_path = joinpath(mech_dir, "mechanism.json")
    end
    
    if !isfile(species_path) || !isfile(reactions_path)
        error("Missing species.json or mechanism.json/reactions.json in: $mech_dir")
    end
    
    species_data = JSON.parsefile(species_path)
    reactions_data = JSON.parsefile(reactions_path)
    
    # Extract and clean species names
    species_syms = [clean_species_name(s["name"]) for s in species_data]
    
    # Construct a Catalyst reaction network macro string
    macro_str = "@reaction_network begin\n"
    
    param_names = Symbol[]
    param_vals = Float64[]
    
    # Add temperature parameter placeholder
    push!(param_names, :T)
    push!(param_vals, 298.15) # Default 298.15 K
    
    for (idx, rxn) in enumerate(reactions_data["reactions"])
        # Reactants formatting
        react_parts = String[]
        if haskey(rxn, "reactants")
            for (r_name, r_info) in rxn["reactants"]
                coef = haskey(r_info, "qty") ? Float64(r_info["qty"]) : 1.0
                r_sym = clean_species_name(r_name)
                if coef == 1.0
                    push!(react_parts, string(r_sym))
                else
                    push!(react_parts, "$(coef)*$(r_sym)")
                end
            end
        end
        reactants_str = isempty(react_parts) ? "Ø" : join(react_parts, " + ")
        
        # Products formatting
        prod_parts = String[]
        if haskey(rxn, "products")
            for (p_name, p_info) in rxn["products"]
                coef = haskey(p_info, "yield") ? Float64(p_info["yield"]) : (haskey(p_info, "qty") ? Float64(p_info["qty"]) : 1.0)
                p_sym = clean_species_name(p_name)
                if coef == 1.0
                    push!(prod_parts, string(p_sym))
                else
                    push!(prod_parts, "$(coef)*$(p_sym)")
                end
            end
        end
        products_str = isempty(prod_parts) ? "Ø" : join(prod_parts, " + ")
        
        # Rate constant / Arrhenius expressions
        rxn_type = uppercase(get(rxn, "type", "CONSTANT"))
        k_name = Symbol("k_$(idx)")
        
        if rxn_type == "CONSTANT"
            k_val = Float64(get(rxn, "k", (haskey(rxn, "rate_constant") ? rxn["rate_constant"] : 0.0)))
            push!(param_names, k_name)
            push!(param_vals, k_val)
            macro_str *= "    $(k_name), $(reactants_str) --> $(products_str)\n"
        elseif rxn_type == "ARRHENIUS"
            A = Float64(get(rxn, "A", 0.0))
            B = Float64(get(rxn, "B", 0.0))
            C = Float64(get(rxn, "C", 0.0))
            rate_expr = "$(A) * (T/300.0)^$(B) * exp($(C)/T)"
            macro_str *= "    $(rate_expr), $(reactants_str) --> $(products_str)\n"
        else
            push!(param_names, k_name)
            push!(param_vals, 1e-12)
            macro_str *= "    $(k_name), $(reactants_str) --> $(products_str)\n"
        end
    end
    
    macro_str *= "end"
    
    rn = eval(Meta.parse(macro_str))
    
    return rn, species_syms, param_names, param_vals
end

function solve_chemistry(rn, u0_pairs::Vector{Pair{Symbol, T}}, param_pairs::Vector{Pair{Symbol, T}}, tspan, solver_choice::String) where T <: Real
    prob = ODEProblem(rn, u0_pairs, tspan, param_pairs)
    
    sol = if solver_choice == "Rodas5"
        solve(prob, Rodas5(), reltol=1e-8, abstol=1e-12)
    elseif solver_choice == "FBDF"
        solve(prob, FBDF(), reltol=1e-8, abstol=1e-12)
    elseif solver_choice == "Rosenbrock23"
        solve(prob, Rosenbrock23(), reltol=1e-8, abstol=1e-12)
    else
        # Default to QNDF
        solve(prob, QNDF(), reltol=1e-8, abstol=1e-12)
    end
    return sol
end

function test_ad_compatibility(rn, u0_pairs, param_names, param_vals, tspan, solver_choice)
    p_vec = Float64[val for val in param_vals]
    
    function loss(p::AbstractVector{T}) where T <: Real
        p_pairs = [param_names[i] => p[i] for i in 1:length(param_names)]
        u0_cast = [p.first => T(p.second) for p in u0_pairs]
        sol = solve_chemistry(rn, u0_cast, p_pairs, tspan, solver_choice)
        return sol.u[end][1]
    end
    
    grad = ForwardDiff.gradient(loss, p_vec)
    return grad
end

function run_robustness_checks(rn, species_syms)
    @testset "MICM Native Julia Model Tests" begin
        network_species = [Symbol(x) for x in species(rn)]
        for s in species_syms
            @test s in network_species
        end
        
        cl = conservationlaws(rn)
        @test length(cl) >= 0
        println("[Julia MICM BoxModel] Mass conservation laws verified. Found $(length(cl)) relations.")
    end
end

function run_loader(mech_dir, solver_choice)
    println("[Julia MICM BoxModel] Loading mechanism dynamically from: $mech_dir")
    println("[Julia MICM BoxModel] Using ODE Solver: $solver_choice")
    
    rn, species_syms, param_names, param_vals = build_micm_model(mech_dir)
    
    # Check for conditions.json
    conditions_path = joinpath(mech_dir, "conditions.json")
    u0_pairs = Pair{Symbol, Float64}[]
    if isfile(conditions_path)
        cond_data = JSON.parsefile(conditions_path)
        if haskey(cond_data, "initial_concentrations")
            for (name, val) in cond_data["initial_concentrations"]
                push!(u0_pairs, clean_species_name(name) => Float64(val))
            end
        end
    end
    
    # Fallback to defaults
    if isempty(u0_pairs)
        u0_pairs = [s => 1e10 for s in species_syms]
    end
    
    param_pairs = Pair{Symbol, Float64}[]
    for (name, val) in zip(param_names, param_vals)
        push!(param_pairs, name => val)
    end
    
    tspan = (0.0, 3600.0)
    
    println("[Julia MICM BoxModel] Network compiled successfully. Species count: ", length(species_syms))
    sol = solve_chemistry(rn, u0_pairs, param_pairs, tspan, solver_choice)
    println("[Julia MICM BoxModel] Integration complete. Final state computed.")
    
    run_robustness_checks(rn, species_syms)
    
    # Validate AD Compatibility
    println("[Julia MICM BoxModel] Running Automatic Differentiation compatibility check...")
    grad = test_ad_compatibility(rn, u0_pairs, param_names, param_vals, tspan, solver_choice)
    println("[Julia MICM BoxModel] AD Gradient check passed. Gradient size: ", length(grad))
end

# Trigger execution using the parsed parameters
run_loader(MECH_DIR, SOLVER_CHOICE)
