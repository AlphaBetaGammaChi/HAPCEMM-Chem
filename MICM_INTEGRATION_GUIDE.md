# Technical Guide: MICM (Music Box) Solver Integration in HAPCEMM-Chem

This guide explains how the NCAR **MICM** (Commonly referred to as the Music Box chemistry solver) integration is structured, where it is located, and how to build and execute simulations using it.

---

## 1. Overview of How It Works

The MICM integration operates on a **hybrid C++ and Julia architecture** designed to combine the high performance of NCAR's C++ MICM library with the robust differential equation solvers of Julia's scientific ecosystem (`OrdinaryDiffEq.jl`).

### Core Workflow:
1. **Mechanism Initialization (C++)**: 
   When the model runs, HAPCEMM initializes a `HAPCEMM::MicmBackend` instance. This class uses NCAR's `micm::SolverConfig` to read and parse the chemical mechanism files (`config.json`, `species.json`, and `reactions.json`) from the mechanism path.
2. **Environment & Rates Update (C++)**:
   During the Box Model chemistry loop, HAPCEMM updates ambient temperature, pressure, air density, and photolysis rates, then passes these values to the `MicmBackend` wrapper to compute current rate constants.
3. **ODE Integration (Julia)**:
   The concentrations and pre-computed rate constants are passed to Julia's `OrdinaryDiffEq.jl` via the `JuliaBridge` library interface.
   - Julia runs a stiff ODE solver (`Rodas5`) to integrate the chemistry over the timestep.
   - The Right-Hand Side (RHS) of the ODE (`micm_rhs!`) and its Jacobian (`micm_jac!`) are computed by calling back to C++ functions (`MicmFun_wrapper` and `MicmJac_wrapper` in `libhapcemm.so`) using Julia's `ccall`.
4. **Adjoint Sensitivity Analysis (Julia & Enzyme.jl)**:
   If adjoint analysis is enabled, `Enzyme.jl` performs reverse-mode automatic differentiation over the chemistry integration steps.
   - Because differentiating raw `ccall` interfaces is challenging, custom pullback rules (custom Enzyme rules) are defined for `kpp_rhs!` and `micm_rhs!`.
   - The reverse pass calls the analytical Jacobians (`MicmJac_wrapper`) from C++ to compute the gradients.
5. **Output Writing (Julia)**:
   Once the integration or adjoint pass completes, Julia uses `NCDatasets.jl` to save results directly to NetCDF format.

> [!NOTE]
> Currently, the C++ wrapper `MicmBackend.cpp` contains skeleton/stub implementations for concentration copying, rate constant calculations, RHS, and Jacobians (which return zero). This allows the codebase to compile and run the KPP solver path without compilation issues while the full MICM solver is being integrated.

---

## 2. File Locations on Isambard

All files related to the MICM integration are located within the `/projects/b35as/public/HAPCEMM-Chem/` directory:

| Component / File Role | Path on Isambard |
| :--- | :--- |
| **C++ Header** | `Code.v05-00/include/MICM/MicmBackend.hpp` |
| **C++ Implementation** | `Code.v05-00/src/MICM/MicmBackend.cpp` |
| **C++ Julia Callbacks** | `Code.v05-00/src/MICM/MicmFun_wrapper.cpp` |
| **C++ Julia Bridge Interface** | `Code.v05-00/include/Util/JuliaBridge.hpp` & `Code.v05-00/src/Util/JuliaBridge.cpp` |
| **C++ Core Integration** | `Code.v05-00/src/Core/BoxModel.cpp` (Guarded by `#ifdef USE_MICM`) |
| **Input Parsing** | `Code.v05-00/src/YamlInputReader/YamlInputReader.cpp` |
| **Julia Chemistry Module** | `Code.v05-00/julia/hapcemm_chemistry.jl` |
| **Julia Adjoint Module** | `Code.v05-00/julia/adjoint_module.jl` |
| **Julia Output Module** | `Code.v05-00/julia/output.jl` |
| **Julia Dependencies** | `Code.v05-00/julia/Project.toml` |
| **CMake Build System** | `Code.v05-00/CMakeLists.txt` (Adds `-DUSE_MICM` compiler flags and source linkages) |
| **Default Configuration** | `Code.v05-00/defaults/input.yaml` (Defines the `CHEMISTRY SOLVER SUBMENU` parameters) |
| **KPP $\rightarrow$ MICM Converter** | `scripts/kpp_to_micm.py` |
| **Pure Julia MICM Solver** | `scripts/micm_julia_box_model.jl` |

---

## 3. How to Use the MICM C++/Julia Solver (Hybrid Mode)

### Step A: Setup the Julia Environment
Instantiate the Julia packages required for the chemical solver bridge:
```bash
/lfs1i3/home/b35as/db18005.b35as/julia-1.10.4/bin/julia --project=/projects/b35as/public/HAPCEMM-Chem/Code.v05-00/julia -e 'using Pkg; Pkg.instantiate()'
```

### Step B: Build HAPCEMM with MICM Enabled
To compile with the MICM backend enabled, navigate to your build folder, load the compiler modules, and run CMake with the `-DUSE_MICM=ON` option:
```bash
# Load Compiler Module
module load gcc-native/13.2

# Navigate to build directory
cd /projects/b35as/public/HAPCEMM-Chem/Code.v05-00/build

# Configure CMake with MICM enabled
# (If MICM is installed in a custom path, specify -Dmicm_DIR=/path/to/micm/lib/cmake/micm)
cmake .. -DUSE_MICM=ON

# Compile the project
make -j
```

### Step C: Configure the Simulation (`input.yaml`)
Modify the `input.yaml` configuration file to configure and select the MICM solver:

1. **Activate the Box Model**:
   ```yaml
   SIMULATION MENU:
     BOX MODEL SUBMENU:
       Run box model (T/F): T
       netCDF filename format (string): APCEMM_BOX_CASE_*
       Box model coupling (T/F): F
   ```

2. **Select the MICM Solver**:
   Configure the solver type and provide the mechanism directory path (which must contain `config.json`, `species.json`, and `reactions.json`):
   ```yaml
     CHEMISTRY SOLVER SUBMENU:
       Chemistry solver (string): micm
       MICM mechanism path (string): /projects/b35as/public/HAPCEMM-Chem/Mechanisms/CRI-HOM_micm/
   ```

3. **(Optional) Configure Adjoint Sensitivity**:
   To compute sensitivities using Enzyme.jl:
   ```yaml
       ADJOINT SUBMENU:
         Enable adjoint (T/F): T
         Adjoint mode (string): all  # options: 'all', 'species', 'parameter'
         Adjoint target name (string): O3  # target for species/parameter mode
   ```

### Step D: Execute the Simulation
Run the compiled binary passing your configuration file:
```bash
# Ensure the shared library search path includes your build/src directory 
# so Julia's ccall can locate libhapcemm.so:
export LD_LIBRARY_PATH=/projects/b35as/public/HAPCEMM-Chem/Code.v05-00/build/src:$LD_LIBRARY_PATH

# Run HAPCEMM
./APCEMM input.yaml
```

---

## 4. Converting KPP Mechanisms to MICM JSON Format

To use your existing KPP configurations with MICM, you can use the automated conversion script `scripts/kpp_to_micm.py`. It parses your KPP `.eqn` and `.spc` files to generate the `species.json`, `reactions.json`, and `config.json` files in the output directory.

Run the converter for your specific schemes using these command lines:

### A. Default UCX Scheme
```bash
python3 /projects/b35as/public/HAPCEMM-Chem/scripts/kpp_to_micm.py \
  /projects/b35as/public/HAPCEMM-Chem/Code.v05-00/src/KPP/UCX.eqn \
  /projects/b35as/public/HAPCEMM-Chem/Mechanisms/UCX_micm/ \
  /projects/b35as/public/HAPCEMM-Chem/Code.v05-00/src/KPP/UCX.spc
```

### B. Common Representative Intermediate (CRI) Scheme
```bash
python3 /projects/b35as/public/HAPCEMM-Chem/scripts/kpp_to_micm.py \
  /projects/b35as/public/HAPCEMM-Chem/Mechanisms/cri_2-2_unix/cri_2-2_kpp_complete.eqn \
  /projects/b35as/public/HAPCEMM-Chem/Mechanisms/cri_micm/ \
  /projects/b35as/public/HAPCEMM-Chem/Mechanisms/cri_2-2_unix/cri_2-2_species_complete.tsv
```

### C. Master Chemical Mechanism (MCM) Scheme
```bash
python3 /projects/b35as/public/HAPCEMM-Chem/scripts/kpp_to_micm.py \
  /projects/b35as/public/HAPCEMM-Chem/Mechanisms/mcm_3-3-1_unix/mcm_3-3-1_kpp_complete.eqn \
  /projects/b35as/public/HAPCEMM-Chem/Mechanisms/mcm_micm/ \
  /projects/b35as/public/HAPCEMM-Chem/Mechanisms/mcm_3-3-1_unix/mcm_3-3-1_species_complete.tsv
```

### D. CRI-HOM Scheme
```bash
python3 /projects/b35as/public/HAPCEMM-Chem/scripts/kpp_to_micm.py \
  /projects/b35as/public/HAPCEMM-Chem/CRI-HOM/CRI-HOM.eqn \
  /projects/b35as/public/HAPCEMM-Chem/Mechanisms/CRI-HOM_micm/ \
  /projects/b35as/public/HAPCEMM-Chem/CRI-HOM/CRI-HOM.spc
```

---

## 5. Running the MICM Box Model in Pure Julia

If you prefer to run simulations entirely inside Julia (allowing 100% native Automatic Differentiation via `SciMLSensitivity` and bypassing the C++ wrapper compilation), you can use `scripts/micm_julia_box_model.jl`.

### Quickstart Guide:

1. **Activate Julia Environment with Catalyst**:
   Ensure Catalyst and JSON are available:
   ```bash
   /lfs1i3/home/b35as/db18005.b35as/julia-1.10.4/bin/julia -e 'using Pkg; Pkg.add(["Catalyst", "JSON", "ModelingToolkit", "OrdinaryDiffEq", "SciMLSensitivity", "NCDatasets"])'
   ```

2. **Execute the Pure Julia Runner**:
   You can write a simple wrapper script or use the REPL:
   ```julia
   # Run in Julia REPL or script
   include("/projects/b35as/public/HAPCEMM-Chem/scripts/micm_julia_box_model.jl")
   
   # Build the system from your MICM JSON folder
   odesys, species_names = build_micm_model("/projects/b35as/public/HAPCEMM-Chem/Mechanisms/CRI-HOM_micm/")
   
   # Setup initial concentrations and parameters
   u0_dict = Dict(Symbol(sp) => 1e-21 for sp in species_names)
   u0_dict[:O3] = 5.5e10  # Set custom initial values
   
   param_dict = Dict(
       :T => 220.0,
       :P => 25000.0,
       :entrain_rate => 1e-5,
       # Add any dynamic photolysis rate parameters if needed
   )
   # Initialize ambient values
   for sp in species_names
       param_dict[Symbol("ambient_", sp)] = 1e-21
   end
   
   # Run simulation and save NetCDF results
   tspan = (0.0, 3600.0)
   sol, sensitivities = solve_and_analyze_micm(odesys, u0_dict, param_dict, tspan)
   save_micm_to_netcdf("julia_micm_boxmodel.nc", sol, sensitivities, species_names)
   ```
