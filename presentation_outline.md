# HAPCEMM-Chem: MICM Integration Presentation Outline

## 1. Introduction & Context
*   **What is HAPCEMM?** A fork of the APCEMM model (Hypothetical Aircraft Plume Chemistry, Emissions, and Microphysics Model) designed for simulating aircraft exhaust plumes, alternative fuels, and entrained species.
*   **The Goal:** Shift towards a more flexible chemistry solver by integrating NCAR's **Model-Independent Chemistry Module (MICM)** to replace the older KPP system.
*   **Why MICM?** Enables runtime JSON configuration, easing the introduction of new mechanisms (e.g., CRI, MCM, battery thermal runaway plumes) without recompiling the core C++ engine.

## 2. Technical Architecture: The Hybrid Approach
*   **C++ & Julia Interoperability:** HAPCEMM core is C++. We integrated a hybrid approach where C++ handles the MICM JSON parsing and rate constant calculations, while Julia handles the heavy lifting of ODE integration.
*   **The Julia Bridge:** A custom interface (`JuliaBridge.hpp/cpp`) passes concentrations and rate constants to Julia.
*   **Stiff Solvers:** Julia utilizes state-of-the-art stiff ODE solvers (e.g., `Rodas5` via `OrdinaryDiffEq.jl`) to integrate the complex chemical kinetics.

## 3. Key Innovations & Features
*   **Adjoint Sensitivity Analysis:** Integrated `Enzyme.jl` for reverse-mode Automatic Differentiation (AD) across the chemistry integration steps. Enables optimization of plume metrics (like contrail optical depth) with respect to engine emissions.
*   **Automated KPP-to-MICM Conversion:** Developed Python scripts (`kpp_to_micm.py`) to automatically parse legacy KPP `.eqn` and `.spc` files into MICM-compatible JSON.
*   **Pure Julia Catalyst Mode:** Created a pure-Julia pathway (`micm_julia_box_model.jl`) using `Catalyst.jl` for 100% native AD, bypassing the C++ wrapper entirely when needed.

## 4. Figures & Visualizations to Include
*   **Architecture Diagram:** Visualizing the data flow from `HAPCEMM C++ Core` $\rightarrow$ `MicmBackend` $\rightarrow$ `JuliaBridge` $\rightarrow$ `OrdinaryDiffEq.jl`.
*   **Performance Comparison:** Bar chart comparing simulation times between the legacy KPP solver and the new hybrid MICM/Julia solver.
*   **Adjoint Sensitivities:** Heatmap or line graph showing the sensitivity of an output (e.g., Ozone concentration) back to initial input parameters, demonstrating the power of the `Enzyme.jl` integration.
*   **Mechanism Workflow:** Flowchart showing the `kpp_to_micm.py` conversion from `.eqn` to `config.json`, `reactions.json`, and `species.json`.

## 5. Future Extensions
*   **Isotopic Fractionation:** Tracing sustainable aviation fuels (SAF) vs fossil fuels.
*   **Battery Thermal Runaway:** Modeling toxic gases (CO, HF, HCN) during aviation battery failures.

## 6. Conclusion
*   HAPCEMM-Chem is now a highly extensible, modern platform for atmospheric plume chemistry, powered by the flexibility of MICM and the mathematical robustness of Julia.
