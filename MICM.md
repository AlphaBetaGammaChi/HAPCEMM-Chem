# HAPCEMM-Chem: MICM Integration & Extension Guide

This document summarizes the completed integration of the **Model-Independent Chemistry Module (MICM)** within HAPCEMM-Chem, the future extensions it enables, and how to operate the system.

---

## 1. What Was Done (Completed Work)

### A. Compiled C++ MICM Integration (`-DUSE_MICM=ON`)
*   **Local Installation**: Compiled and installed NCAR's MICM C++ library (`v3.5.0` with the `SolverConfig` JSON configuration parser) locally on Isambard under:
    `/projects/b35as/public/HAPCEMM-Chem/micm_installed/`
*   **Backend Wrapper**: Completed HAPCEMM's `MicmBackend.cpp` wrapper class. It:
    *   Loads standard MICM JSON mechanism directories at runtime.
    *   Dynamically maps HAPCEMM active and fixed species to MICM solver indices.
    *   Updates environmental variables (temperature, pressure, air density).
    *   Computes chemical forcing (RHS) and sparse/dense Jacobians, negating MICM's internal $-J$ matrices back to the positive $J$ format.
*   **Compilation**: Linked with `musica::micm` and compiled the binary successfully with `-DUSE_MICM=ON`.

### B. Pure Julia Catalyst Box Model
*   **Loader Script**: Implemented `/projects/b35as/public/HAPCEMM-Chem/scripts/micm_julia_box_model.jl` to run completely natively in Julia.
*   **Metaprogramming**: Uses `eval(Meta.parse(macro_str))` to compile Catalyst `@reaction_network` objects on the fly from JSON files.
*   **Dynamic Loader**: Added the `ARGS` command-line check at the top to support hot-swapping any mechanism directory at runtime.
*   **Stiff Solver & AD**: Integrates chemistry using the state-of-the-art `QNDF()` stiff ODE solver with strict tolerances and verifies Automatic Differentiation (AD) compatibility using `ForwardDiff.gradient`.
*   **Guardrails**: Employs `@testset` to check species alignment and computes Catalyst conservation relations to verify mass balance.

### C. Automation Scripts & Libraries
*   **KPP-to-JSON Converter (`kpp_to_micm.py`)**: A Python regex-based parser that strips comments, cleans double-precision exponents (`D` -> `e`), extracts species/coefficients, and generates valid MICM JSON files.
*   **UCX Generator (`generate_ucx.py`)**: A dependency-free Python script that directly outputs Base and Modified UCX mechanism JSON folders.
*   **Deployed Mechanisms**: Converted and verified 5 standard mechanisms:
    1.  `cri` (CRI scheme)
    2.  `mcm_full` (Full MCM scheme)
    3.  `cri_hom` (CRI-HOM scheme)
    4.  `ucx_base` (Base UCX)
    5.  `ucx_mod` (Modified UCX)

---

## 2. What Can Be Done (Future Opportunities)

### A. Isotopic Fractionation Studies
*   **What**: Trace emissions sources (e.g. Sustainable Aviation Fuel vs. fossil kerosene) or plume ages.
*   **How**: Duplicate the desired reactions in `mechanism.json`, substitute species names with their isotopologues (e.g. `"13C12CH5OH"`), and multiply the rate constant by the Kinetic Isotope Effect (KIE) factor. MICM will integrate the parallel heavy/light networks automatically.

### B. Battery Thermal Runaway Plume Chemistry
*   **What**: Model toxic gases ($\text{CO}, \text{HF}, \text{HCN}$) released during aircraft battery runaway events.
*   **How**: Write a custom `mechanism.json` containing the runaway off-gas oxidation kinetics, place it in a new folder under `mechanisms/`, and load it directly into either the C++ or Julia solver.

### C. Adjoint Plume Optimization
*   **What**: Compute sensitivities of plume metrics (like contrail optical depth) back to engine emissions rates.
*   **How**: Use the dynamic Julia loader script coupled with `SciMLSensitivity.jl` and `Enzyme.jl` to compute adjoint sensitivities of the combined chemistry-microphysics ODE system.

---

## 3. How to Run & Maintain

### A. Compiling HAPCEMM-Chem with C++ MICM
On Isambard, load the compiler, configure CMake, and build:
```bash
module load gcc-native/13.2
cd /projects/b35as/public/HAPCEMM-Chem/Code.v05-00/build
cmake .. -DUSE_MICM=ON -Dmicm_DIR=/projects/b35as/public/HAPCEMM-Chem/micm_installed/micm-3.5.0/cmake
make -j
```

### B. Running the Julia Dynamic Loader
Run the model by passing the target mechanism directory:
```bash
julia scripts/micm_julia_box_model.jl mechanisms/cri_hom
```

### C. Converting a New KPP `.eqn` File
To convert a new chemical network:
```bash
python kpp_to_micm.py path/to/mechanism.eqn mechanisms/my_new_mechanism
```
This output folder can immediately be used by both the C++ and Julia solvers.
