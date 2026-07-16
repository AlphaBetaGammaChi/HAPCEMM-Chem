# run_test.jl (FIXED)
# Includes the generated HapcemmAdjoint module instead of the missing scratch file.
# Note: This test requires libhapcemm.so to be compiled and accessible in LD_LIBRARY_PATH,
# as HapcemmChemistry uses ccall to interface with KPP and MICM backends.

# First, ensure the generated julia files exist
if !isfile("Code.v05-00/julia/adjoint_module.jl")
    println("ERROR: Code.v05-00/julia/adjoint_module.jl not found. Please run `python3 implement_plan_c_micm.py` first.")
    exit(1)
end

include("Code.v05-00/julia/adjoint_module.jl")
include("Code.v05-00/julia/output.jl")

using .HapcemmAdjoint
using .HapcemmOutput

# Define flat arrays mimicking the HAPCEMM C++ internal state
nVar = 200     # Approximate number of variable species
nReact = 300   # Approximate number of reactions
nFix = 5       # Approximate number of fixed species

u0 = fill(1e-21, nVar)
u0[1] = 55.0e-9 * 1e19 # O3 example

rconst = fill(1e-12, nReact)
FIX = fill(2.55e19, nFix)

tspan = (0.0, 3600.0)

# Run Adjoint pass for :kpp backend
println("Running Adjoint pass via Enzyme reverse mode...")
try
    # Target index 1, mode :all
    species_grad, param_grad = HapcemmAdjoint.run_adjoint_pass(u0, rconst, FIX, tspan, :kpp, :all, 1)
    
    println("Adjoint Pass Completed!")
    println("Sensitivity to initial O3 (species 1): ", species_grad[1])
    
    # Mock names for NetCDF output
    spc_names = ["Species_$i" for i in 1:nVar]
    rxn_names = ["Reaction_$i" for i in 1:nReact]
    
    # Reshape sensitivities to match time dimensions expected by write_adjoint_output
    species_sens_mat = reshape(species_grad, (nVar, 1))
    param_sens_mat = reshape(param_grad, (nReact, 1))
    
    HapcemmOutput.write_adjoint_output("julia_boxmodel_output.nc", [3600.0], species_sens_mat, param_sens_mat, spc_names, rxn_names)
catch e
    println("Error running adjoint pass. Please ensure libhapcemm.so is in LD_LIBRARY_PATH.")
    println(e)
end
