# Per-Grid-Cell Box Model (Mode=2) Documentation

## Overview

This document describes the per-grid-cell box model option (mode=2) added to APCEMM. This feature enables chemistry to run independently on each grid cell of the LAGRID plume model, allowing for spatially-varying chemical evolution based on local temperature, pressure, and humidity conditions.

---

## KNOWN LIMITATIONS

### 1. Box Model Assumptions
- **Well-mixed cell assumption**: Each grid cell is treated as a well-mixed box with no sub-grid chemistry gradients. Species are assumed uniform within each cell.
- **No species transport**: The current implementation (INDEPENDENT mode) treats each cell as completely independent - there is no transport of chemical species between cells. See COUPLED mode for future extension.

### 2. Timestep Requirements
- **Chemistry timestep must be >= transport timestep**: For stability, the chemistry timestep should be equal to or greater than the transport timestep. Using a smaller chemistry timestep than transport may lead to numerical instability.
- **Chemistry timestep in input.yaml**: Set `Chemistry timestep [min]` in the BOX MODEL SUBMENU. Default is 10 minutes.
- **Sub-timestepping**: If the chemistry timestep exceeds 60 seconds, the code automatically divides into multiple sub-timesteps of ~60 seconds each.

### 3. KPP Integration Time Scales
- **Mechanism complexity**: Integration time scales with the complexity of the chemical mechanism. Larger mechanisms (more species, reactions) require more computation per cell.
- **Convergence**: KPP integration may fail for some cells (extreme temperatures, pressures, or concentrations). Failed integrations are reported but do not stop the simulation.

### 4. Memory Requirements
- **Species array size**: Memory scales as `NVAR × nx × ny × 8 bytes` (double precision):
  - Early plume (20×20): ~48 KB
  - Mid plume (50×30): ~180 KB
  - Mature plume (100×50): ~600 KB
- **No time history stored**: Only current timestep is stored. If time history is needed for diagnostics, sample periodically to a separate output file.

---

## KNOWN RISKS

### 1. KPP Thread Safety
- **Critical**: KPP uses global arrays (VAR, RCONST, PHOTOL, FIX) that are shared across threads. The implementation uses `threadprivate` arrays to ensure thread safety.
- **Failure mode**: If threadprivate declarations fail silently or are not properly propagated, results will be incorrect (mixed species between cells).
- **Mitigation**: The code uses `#pragma omp threadprivate` directives as specified in Step 2. Test with single-threaded run first to verify correctness.

### 2. Dynamic Grid Growth
- **Performance variation**: Early timesteps are computationally cheap (small grid). Late timesteps are expensive (larger grid as contrail spreads).
- **Grid remapping**: Species are remapped to new grid after each transport timestep. Interpolation is used - new cells get weighted contributions from nearby old cells.
- **Memory allocation**: Species array is reallocated each timestep during remapping. This is handled automatically but may cause performance overhead.

### 3. Operator Splitting
- **Splitting error**: Transport and chemistry are solved separately (operator splitting), which introduces splitting error.
- **Recommended timestep ratios**: For typical simulations, use chemistry timestep = transport timestep (ratio = 1:1). Smaller ratios increase accuracy but also computation time.

### 4. Initial Conditions
- **Uniform initialization**: All cells start with the same background concentrations from input.yaml. Plume emissions are not currently added to the species array.
- **Coupling with mode=1**: If mode=1 (whole domain box model) has run with coupling enabled, the evolved species could be used as initial conditions (not yet implemented).

---

## VALIDATION REQUIREMENTS

### 1. Thread Independence
- [ ] Mode=2 with 1 thread should give same result as mode=2 with N threads
- [ ] Run same simulation with 1, 2, 4, 8 threads and compare output

### 2. Consistency with Mode=1
- [ ] Domain-averaged mode=2 output should be approximately consistent with mode=1 output
- [ ] Compare species concentrations at corresponding timesteps
- [ ] Expected differences: ~10-20% due to spatial variation in mode=2

### 3. Species Constraints
- [ ] Species should remain non-negative at all times
- [ ] Check: NO, NO2, O3, CO, CH4, SO2 should never go negative
- [ ] Mass balance: Total mass should be approximately conserved within ~1%

### 4. Scientific Validity
- [ ] Temperature-dependent chemistry: Verify higher T cells show faster chemistry
- [ ] Diurnal cycle: Verify photolysis rates change with time of day
- [ ] Humidity effects: Verify H2O affects chemistry rates

---

## PERFORMANCE NOTES

### 1. Scaling with Grid Size
- **Computational complexity**: O(nx × ny) - linear with number of cells
- **Typical runtime**: 
  - 20×20 grid (early): ~seconds per chemistry timestep
  - 50×30 grid (mid): ~10-30 seconds per timestep
  - 100×50 grid (mature): ~1-2 minutes per timestep

### 2. Scaling with Thread Count
- **Expected speedup**: Near-linear up to ~8 threads, then diminishing returns
- **Cache effects**: Better performance with contiguous memory access patterns
- **Load balancing**: Dynamic scheduling helps with irregular grids

### 3. Recommended Settings
- **Chemistry timestep**: 10 minutes (default) is good for typical 3-6 hour simulations
- **Thread count**: Match available cores, typically 4-8 for HPC
- **Output frequency**: Every 10 transport timesteps is reasonable

### 4. Memory Requirements
- **Per simulation**: ~1 MB for species array at typical grid sizes
- **Additional**: KPP threadprivate arrays add ~NVAR × NTHREADS × 8 bytes

---

## USAGE

### Input.yaml Configuration

```yaml
BOX MODEL SUBMENU:
  Run box model (T/F): F          # Old flag (ignored if mode present)
  Box model mode (int): 2          # 0=off, 1=whole domain, 2=per-cell
  Chemistry timestep [min] (double): 10.0
  OpenMP threads (int): 4
```

### Output Files
- Output format: NetCDF
- Filename pattern: `APCEMM_PERCELL_CASE_[n].nc`
- Dimensions: time, y, x, species
- Variables: species concentrations [molec/cm3]

---

## FILE STRUCTURE

```
Code.v05-00/
├── include/Core/
│   ├── BoxModel_PerCell.hpp       # Header for per-cell chemistry
│   └── BoxModel_PerCell_KPP.hpp   # Thread safety wrapper for KPP
├── src/Core/
│   ├── BoxModel_PerCell.cpp      # Per-cell chemistry implementation
│   └── BoxModel_PerCell_KPP.cpp   # KPP thread-local array implementations
└── docs/
    └── PerCellBoxModel_Notes.md  # This file
```

---

## VERSION HISTORY

- **v1.0** (4/2024): Initial implementation
  - Steps 1-7 completed
  - INDEPENDENT mode (no species transport)
  - OpenMP parallelization

---

## FUTURE EXTENSIONS

### COUPLED Mode (PerCellMode::COUPLED)
- Add species transport between cells using FVM
- More scientifically complete but significantly more complex
- Would require coupling transport and chemistry within each timestep

### Emission Plume Initialization
- Add initial species from emission, not just background
- Requires mapping emission indices to LAGRID grid

### Mode=1 Coupling
- Use evolved species from mode=1 as initial conditions for mode=2
- Enables multi-scale modeling (domain + per-cell)