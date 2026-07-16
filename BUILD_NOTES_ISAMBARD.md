# Compilation and Architecture Notes for Isambard (ARM64)

This document outlines the modifications made to the original HAPCEMM-Chem repository to ensure successful compilation and execution on the Isambard cluster.

## A) Modifications to Original Repository

### 1. Build System Patches (CMake)
The original build system relied on "pkg-config" to find NetCDF. The following changes were applied:
*   **Root CMakeLists.txt**: Replaced "pkg_check_modules" with "find_package(netCDFCxx CONFIG REQUIRED)". This uses the modern CMake configuration provided by the locally installed libraries.
*   **Target Linkage**: Updated all library targets (Core, KPP, EPM) to link against the specific CMake target "netCDF::netcdf-cxx4" instead of raw library flags.
*   **Visibility Changes**: Changed library linkage from PRIVATE to PUBLIC in sub-directories to ensure that transitive dependencies (like NetCDF) are correctly propagated to the final APCEMM executable.

### 2. Dependency Management (vcpkg)
*   **vcpkg.json**: Added a "builtin-baseline" commit hash. This is required for "Manifest Mode" in newer versions of vcpkg to ensure reproducible dependency versions.
*   **vcpkg-configuration.json**: Disabled the external artifact registry (vcpkg-configuration.json.bak) which was causing network errors. The system now uses the built-in git registry.
*   **Bootstrap**: Compiled a local ARM64 version of the vcpkg toolset.

### 3. Environment Adjustments
*   **Compiler**: Switched to "gcc-native/13.2" (module load gcc-native/13.2) to support modern C++ features.

---

## B) File Configuration and Linkage

The project is structured into several static libraries that are linked into the final executable.

### Core Libraries
1.  **libCore.a (src/Core):**
    *   **Role**: Manages model state (aircraft, mesh, meteorology) and diagnostic output (NetCDF).
2.  **libKPP.a (src/KPP):**
    *   **Role**: Kinetic Pre-Processor. Chemical reaction solver.
3.  **libEPM.a (src/EPM):**
    *   **Role**: Exhaust Plume Model.
4.  **libAIM.a (src/AIM):**
    *   **Role**: Aerosol Interaction Module. Nucleation and coagulation.
5.  **libLAGRID.a (src/LAGRID):**
    *   **Role**: Lagrangian Grid management.
6.  **libFVM_ANDS.a (src/FVM_ANDS):**
    *   **Role**: Finite Volume Method for Advection-Diffusion-Shear.

### Executables
*   **APCEMM**: The primary binary (Orchestrator).
*   **unittest**: Catch2-based test suite.

---

## C) Evaluation: Does this make sense?

**Yes, the current architecture is standard for high-performance C++ scientific codes.**

*   **Modularization**: Splitting the code into libraries allows for independent testing.
*   **Dependency Management**: Using vcpkg ensures that the exact same versions of Boost and NetCDF are used.
*   **Static Linking**: Ensures the binary is portable across different compute nodes without needing complex library paths.

**Recommendation**: Use the "build_debug" executable if you encounter numerical stability issues in the Release build on ARM64.
