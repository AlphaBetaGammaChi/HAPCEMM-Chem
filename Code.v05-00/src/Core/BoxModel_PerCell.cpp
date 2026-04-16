/* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */
/*                                                                  */
/*     Aircraft Plume Chemistry, Emission and Microphysics Model    */
/*                             (APCEMM)                             */
/*                                                                  */
/* BoxModel Per-Cell Chemistry Implementation                      */
/*                                                                  */
/* Two modes:                                                       */
/*   - INDEPENDENT: Each cell runs box model chemistry independently */
/*                  (simplified, no species transport)              */
/*   - COUPLED:     Species transported between cells              */
/*                  (full mode, requires transport integration)     */
/*                                                                  */
/* Author               : AlphaBetaGammaChi                         */
/* Time                 : 4/2024                                   */
/* File                 : BoxModel_PerCell.cpp                       */
/*                                                                  */
/* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */

#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <sys/stat.h>

#include "Core/BoxModel_PerCell.hpp"
#include "Core/BoxModel_PerCell_KPP.hpp"
#include "Core/Input_Mod.hpp"
#include "Core/Input.hpp"
#include "Core/SZA.hpp"
#include "KPP/KPP.hpp"
#include "KPP/KPP_Parameters.h"
#include "KPP/KPP_Global.h"
#include "Util/PhysConstant.hpp"
#include "Util/PhysFunction.hpp"

#ifdef OMP
#include <omp.h>
#endif

#ifdef NETCDF
#include <netcdf>
using namespace netCDF;
#endif

namespace BoxModel {

// ============================================================================
// Helper: Get species indices from KPP
// ============================================================================

int getNumSpecies() {
    return NVAR;
}

const char* getSpeciesName(int index) {
    if (index >= 0 && index < NVAR) {
        return SPC_NAMES[index];
    }
    return "UNKNOWN";
}

// ============================================================================
// Initialize species array with background concentrations
// ============================================================================

void initSpeciesArray(int nx, int ny, double* species, const Input& input, double airDens) {
    // Get background concentrations from Input [ppb]
    double no_ppb = input.backgNOx();
    double o3_ppb = input.backgO3();
    double co_ppb = input.backgCO();
    double ch4_ppb = input.backgCH4();
    double so2_ppb = input.backgSO2();
    
    // Convert from ppb to molec/cm3 and initialize all cells
    for (int j = 0; j < ny; j++) {
        for (int i = 0; i < nx; i++) {
            int idx = j * nx + i;  // Row-major order
            
            // Species indices from KPP_Parameters.h
            species[NVAR * idx + ind_NO]  = no_ppb * 1.0e-9 * airDens;
            species[NVAR * idx + ind_O3]  = o3_ppb * 1.0e-9 * airDens;
            species[NVAR * idx + ind_CO]  = co_ppb * 1.0e-9 * airDens;
            species[NVAR * idx + ind_CH4] = ch4_ppb * 1.0e9 * airDens;
            species[NVAR * idx + ind_NO2] = no_ppb * 0.5 * 1.0e-9 * airDens;
            species[NVAR * idx + ind_H2O] = airDens * 1.0e-4;  // Approximate
            if (so2_ppb > 0.0) {
                species[NVAR * idx + ind_SO2] = so2_ppb * 1.0e-9 * airDens;
            }
            
            // Initialize other species to zero
            for (int ispec = 0; ispec < NVAR; ispec++) {
                int specIdx = NVAR * idx + ispec;
                if (species[specIdx] == 0.0 && 
                    ispec != ind_NO && ispec != ind_O3 && ispec != ind_CO &&
                    ispec != ind_CH4 && ispec != ind_NO2 && ispec != ind_H2O && 
                    ispec != ind_SO2) {
                    species[specIdx] = 0.0;
                }
            }
        }
    }
    
    std::cout << "Initialized " << nx << "x" << ny << " grid with background species" << std::endl;
}

// ============================================================================
// Run per-cell chemistry - Simplified (INDEPENDENT) mode
// Each cell runs independently without species transport
// ============================================================================

int runPerCellChemistry(
    const OptInput& Input_Opt,
    const Input& input,
    int nx, int ny,
    double* species,
    const double* temperature,
    const double* pressure,
    const double* humidity,
    const double* aerosolSAD,
    double dt,
    PerCellMode mode) {
    
    std::cout << "\n===== Running Per-Cell Chemistry =====" << std::endl;
    std::cout << "Grid size: " << nx << " x " << ny << " = " << nx*ny << " cells" << std::endl;
    std::cout << "Chemistry timestep: " << dt << " s" << std::endl;
    std::cout << "Mode: " << (mode == PerCellMode::INDEPENDENT ? "INDEPENDENT (simplified)" : "COUPLED (full)") << std::endl;
    
    if (mode == PerCellMode::COUPLED) {
        std::cout << "WARNING: COUPLED mode not yet implemented - falling back to INDEPENDENT" << std::endl;
        mode = PerCellMode::INDEPENDENT;
    }
    
    // Get number of chemistry timesteps
    int nChemSteps = 1;  // For now, single step
    if (dt > 60.0) {  // If timestep > 1 minute, do multiple chemistry steps
        nChemSteps = static_cast<int>(dt / 60.0);
        if (nChemSteps < 1) nChemSteps = 1;
    }
    
    double chemDt = dt / nChemSteps;  // Chemistry sub-timestep
    
    // Get latitude and day of year for SZA calculation
    double latitude = input.latitude_deg();
    int emissionDOY = input.emissionDOY();
    
    // Get simulation time
    double tStart_h = input.emissionTime();
    double tEnd_h = tStart_h + input.simulationTime();
    double tStart_s = tStart_h * 3600.0;
    double tEnd_s = tEnd_h * 3600.0;
    
    std::cout << "Chemistry sub-timestep: " << chemDt << " s (" << nChemSteps << " steps)" << std::endl;
    
    // Get OpenMP thread count
    int numThreads = Input_Opt.SIMULATION_BOXMODEL_THREADS;
    if (numThreads <= 0) numThreads = 1;
    
#ifdef OMP
    std::cout << "Using " << numThreads << " OpenMP threads" << std::endl;
    omp_set_num_threads(numThreads);
#else
    std::cout << "OpenMP not enabled - running sequentially" << std::endl;
#endif
    
    // Sequential version (no OpenMP for now - will add in Step 6)
    // Each cell runs independently
    
    double* cellSpecies = new double[NVAR];
    double* rtol = new double[NVAR];
    double* atol = new double[NVAR];
    double fix[NFIX];
    
    // Set up KPP tolerances
    for (int i = 0; i < NVAR; i++) {
        rtol[i] = 1.0e-4;
        atol[i] = 1.0e6;
    }
    for (int i = 0; i < NFIX; i++) {
        fix[i] = 0.0;
    }
    
    // Loop over all cells
    for (int j = 0; j < ny; j++) {
        for (int i = 0; i < nx; i++) {
            int cellIdx = j * nx + i;
            
            // Get cell conditions
            double T = temperature[j * nx + i];
            double P = pressure[j * nx + i];
            double RH = humidity[j * nx + i];
            
            // Air density
            double airDens = P / (physConst::kB * T) * 1.0e-6;
            
            // Initialize species for this cell
            for (int ispec = 0; ispec < NVAR; ispec++) {
                cellSpecies[ispec] = species[NVAR * cellIdx + ispec];
            }
            
            // Initialize KPP state for this thread/cell
            PerCell::initThreadState(T, P, cellSpecies[ind_H2O], cellSpecies);
            
            // Loop over chemistry sub-timesteps
            for (int step = 0; step < nChemSteps; step++) {
                double t = step * chemDt;
                double nextT = (step + 1) * chemDt;
                
                // Calculate SZA for this cell and time
                SZA sun(latitude, emissionDOY);
                sun.Update(t + chemDt / 2.0);
                double cosSZA = sun.CSZA;
                
                // Update photolysis rates
                PerCell::updatePhotolysisRates(cosSZA);
                
                // Update reaction rate constants
                PerCell::updateRateConstants(T, P, airDens, cellSpecies[ind_H2O]);
                
                // Run KPP integration
                int ierr = INTEGRATE(cellSpecies, fix, t, nextT, atol, rtol, 0.0);
                
                if (ierr < 0) {
                    std::cout << "Warning: Integration failed at cell (" << i << "," << j << "), step " << step << std::endl;
                }
            }
            
            // Extract results
            PerCell::getResults(cellSpecies);
            
            // Store back to species array
            for (int ispec = 0; ispec < NVAR; ispec++) {
                species[NVAR * cellIdx + ispec] = cellSpecies[ispec];
            }
            
            // Progress output
            if ((j * nx + i) % 100 == 0) {
                std::cout << "  Processed " << (j * nx + i + 1) << " / " << nx*ny << " cells" << std::endl;
            }
        }
    }
    
    // Cleanup
    delete[] cellSpecies;
    delete[] rtol;
    delete[] atol;
    
    std::cout << "Per-cell chemistry completed!" << std::endl;
    
    return 0;
}

// ============================================================================
// Write per-cell output to NetCDF
// Follows same pattern as BoxModel.cpp writeBoxModelOutput()
// ============================================================================

#ifdef NETCDF
void writePerCellOutput(
    const std::string& outputFile,
    int nx, int ny,
    const double* species,
    double timeHours) {
    
    try {
        using namespace netCDF;
        using namespace netCDF::exceptions;
        
        NcFile ncFile(outputFile, NcFile::replace);
        
        // Create dimensions
        NcDim xDim = ncFile.addDim("x", nx);
        NcDim yDim = ncFile.addDim("y", ny);
        NcDim specDim = ncFile.addDim("species", NVAR);
        NcDim timeDim = ncFile.addDim("time", 1);
        
        // Create time variable
        NcVar timeVar = ncFile.addVar("time", ncFloat, timeDim);
        timeVar.putAtt("units", "hours since emission start");
        timeVar.putAtt("description", "Simulation time from start");
        float timeVal = static_cast<float>(timeHours);
        timeVar.putVar(&timeVal);
        
        // Create x coordinate
        NcVar xVar = ncFile.addVar("x", ncFloat, xDim);
        xVar.putAtt("units", "m");
        xVar.putAtt("description", "x-coordinate (horizontal distance from emission point)");
        
        // Create y coordinate  
        NcVar yVar = ncFile.addVar("y", ncFloat, yDim);
        yVar.putAtt("units", "m");
        yVar.putAtt("description", "y-coordinate (vertical distance from emission point)");
        
        // Create species variable [species x y x x]
        NcVar specVar = ncFile.addVar("concentrations", ncFloat,
                                       std::vector<NcDim>{specDim, yDim, xDim});
        specVar.putAtt("units", "molec/cm3");
        specVar.putAtt("description", "Species concentrations at each grid cell");
        specVar.putAtt("long_name", "Chemical species concentrations");
        
        // Add global attributes matching LAGRID format
        ncFile.putAtt("Conventions", "COARDS");
        ncFile.putAtt("Model", "APCEMM");
        ncFile.putAtt("BoxModel_Mode", "Per-cell (mode=2)");
        ncFile.putAtt("History", "Created by per-cell chemistry model");
        
        // Create 1D array for output
        std::vector<float> specData(NVAR * ny * nx);
        
        // Flatten: species varies slowest in netCDF (C order)
        for (int ispec = 0; ispec < NVAR; ispec++) {
            for (int j = 0; j < ny; j++) {
                for (int i = 0; i < nx; i++) {
                    int flatIdx = ispec * ny * nx + j * nx + i;
                    int srcIdx = NVAR * (j * nx + i) + ispec;
                    specData[flatIdx] = static_cast<float>(species[srcIdx]);
                }
            }
        }
        specVar.putVar(specData.data());
        
        // Write coordinate arrays (just indices for now)
        std::vector<float> xCoords(nx), yCoords(ny);
        for (int i = 0; i < nx; i++) xCoords[i] = static_cast<float>(i);
        for (int j = 0; j < ny; j++) yCoords[j] = static_cast<float>(j);
        xVar.putVar(xCoords.data());
        yVar.putVar(yCoords.data());
        
        std::cout << "Per-cell output written to: " << outputFile << std::endl;
        
    } catch (const std::exception& e) {
        std::cout << "Warning: Could not write NetCDF output: " << e.what() << std::endl;
    }
}
#else
void writePerCellOutput(
    const std::string& outputFile,
    int nx, int ny,
    const double* species,
    double timeHours) {
    std::cout << "NetCDF not available - skipping output" << std::endl;
}
#endif

} // namespace BoxModel