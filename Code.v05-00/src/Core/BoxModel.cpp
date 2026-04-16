/* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */
/*                                                                  */
/*     Aircraft Plume Chemistry, Emission and Microphysics Model    */
/*                             (APCEMM)                             */
/*                                                                  */
/* BoxModel Program File                                            */
/*                                                                  */
/* Author               : Thibaud M. Fritz                          */
/* File                 : BoxModel.cpp                              */
/*                                                                  */
/* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */

#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <ctime>
#include <sys/stat.h>
#include <sstream>

#ifdef OMP
#include "omp.h"
#endif

#include "Core/BoxModel.hpp"
#include "Core/Input_Mod.hpp"
#include "Core/Input.hpp"
#include "Core/Parameters.hpp"
#include "Core/SZA.hpp"
#include "KPP/KPP.hpp"
#include "KPP/KPP_Parameters.h"
#include "KPP/KPP_Global.h"
#include "Util/PhysConstant.hpp"
#include "Util/PhysFunction.hpp"

#include <netcdf>
using namespace netCDF;

namespace BoxModel {

// ============================================================================
// Global storage for final species (used for LAGRID coupling)
// ============================================================================

static LAGRIDCouplingData g_finalSpecies;  // Final species after box model integration

// ============================================================================
// Getter for final species (used by Main.cpp to pass to LAGRID)
// ============================================================================

LAGRIDCouplingData getFinalSpecies() {
    return g_finalSpecies;
}

// ============================================================================
// Time Array Building Function
// ============================================================================

std::vector<double> buildTimeArray(double tStart, double tEnd, 
                               double sunRise, double sunSet, 
                               double dt) {
    std::vector<double> timeArray;
    
    double currentTime = tStart;
    
    while (currentTime < tEnd) {
        // Add current time to array
        timeArray.push_back(currentTime);
        
        // Move to next timestep
        currentTime += dt;
        
        // Ensure we don't exceed end time
        if (currentTime > tEnd) {
            timeArray.push_back(tEnd);
            break;
        }
    }
    
    return timeArray;
}

// ============================================================================
// NetCDF Output Writing - Matching Fritz's Write_Box Format
// ============================================================================

void writeBoxModelOutput(const std::string& outputFile,
                       const std::vector<double>& timeArray,
                       const std::vector<std::vector<double> >& speciesHistory,
                       const std::vector<double>& cosSZASeries,
                       double airDens,
                       double relHumidity_i,
                       int nVar) {
    
    using namespace netCDF;
    using namespace netCDF::exceptions;
    
    try {
        // Create NetCDF file
        NcFile ncFile(outputFile, NcFile::replace);
        
        // Get number of timesteps
        size_t nTime = timeArray.size();
        
        // Create time dimension
        NcDim timeDim = ncFile.addDim("time", nTime);
        
        // Create species dimension  
        NcDim speciesDim = ncFile.addDim("species", nVar);
        
        // Create and write time variable [hours from start]
        ncFile.addVar("time", ncFloat, timeDim)
            .putVar(timeArray.data());
        
        // Create and write cosine of SZA
        NcVar cosSZAVar = ncFile.addVar("cosSZA", ncFloat, timeDim);
        cosSZAVar.putVar(cosSZASeries.data());
        cosSZAVar.putAtt("units", "dimensionless");
        cosSZAVar.putAtt("description", "Cosine of solar zenith angle");
        
        // Create and write air density
        NcVar airDensVar = ncFile.addVar("airDensity", ncFloat, timeDim);
        std::vector<double> airDensArr(nTime, airDens);
        airDensVar.putVar(airDensArr.data());
        airDensVar.putAtt("units", "molec/cm3");
        airDensVar.putAtt("description", "Air number density");
        
        // Create and write relative humidity (ice)
        NcVar relHumIVar = ncFile.addVar("relHumidity_ice", ncFloat, timeDim);
        std::vector<double> relHumIArr(nTime, relHumidity_i);
        relHumIVar.putVar(relHumIArr.data());
        relHumIVar.putAtt("units", "dimensionless");
        relHumIVar.putAtt("description", "Relative humidity with respect to ice");
        
        // Create and write species concentrations [species x time]
        NcVar specVar = ncFile.addVar("concentrations", ncFloat, 
                                    std::vector<NcDim>{speciesDim, timeDim});
        
        // Convert from molec/cm3 to ppb and write
        std::vector<float> specData(nTime * nVar);
        for (int i = 0; i < nVar; i++) {
            for (size_t j = 0; j < nTime; j++) {
                double conc_molec = speciesHistory[i][j];
                double conc_ppb = (conc_molec / airDens) * 1.0e9;
                specData[i * nTime + j] = static_cast<float>(conc_ppb);
            }
        }
        specVar.putVar(specData.data());
        specVar.putAtt("units", "ppb");
        specVar.putAtt("description", "Species concentrations in ppb");
        
        std::cout << "Box model output written to: " << outputFile << std::endl;
        
    } catch (const std::exception& e) {
        std::cout << "Warning: Could not write NetCDF output: " << e.what() << std::endl;
        std::cout << "Output data is still available in memory." << std::endl;
    }
}

// ============================================================================
// Main Box Model Function
// ============================================================================

int runBoxModel(const OptInput& Input_Opt, const Input& input, const EPMCouplingData& epmCoupling) {
    
    std::cout << "\n===== Running Box Model =====" << std::endl;
    
    // =======================================================================
    // Load Simulation Parameters
    // =======================================================================
    
    // Timestep [minutes -> seconds]
    double chemDT_min = Input_Opt.CHEMISTRY_TIMESTEP;
    double transDT_min = Input_Opt.TRANSPORT_TIMESTEP;
    
    // Use the smaller timestep
    double dt;
    if (chemDT_min <= 0.0 || transDT_min <= 0.0) {
        dt = std::max(chemDT_min, transDT_min) * 60.0;
    } else {
        dt = std::min(chemDT_min, transDT_min) * 60.0;
    }
    
    if (dt <= 0.0) {
        std::cout << "Warning: Using 1 minute default timestep" << std::endl;
        dt = 60.0;
    }
    
    // =======================================================================
    // Load Meteorological Conditions
    // =======================================================================
    
    double temperature_K = input.temperature_K();
    double pressure_Pa = input.pressure_Pa();
    double relHumidity_w = input.relHumidity_w();
    
    // Calculate relative humidity with respect to ice
    double relHumidity_i = relHumidity_w * physFunc::pSat_H2Ol(temperature_K) 
                              / physFunc::pSat_H2Os(temperature_K);
    
    // Air density [molec/cm3]
    double airDens = pressure_Pa / (physConst::kB * temperature_K) * 1.0e-6;
    
    std::cout << "Temperature: " << temperature_K << " K" << std::endl;
    std::cout << "Pressure: " << pressure_Pa << " Pa" << std::endl;
    std::cout << "Rel. Humidity (ice): " << relHumidity_i << std::endl;
    std::cout << "Air Density: " << airDens << " molec/cm3" << std::endl;
    std::cout << "Timestep: " << dt << " s" << std::endl;
    
    // =======================================================================
    // EPM Coupling: Use aerosol surface area for heterogeneous chemistry
    // =======================================================================
    
    if (epmCoupling.isValid) {
        std::cout << "\n===== EPM Coupling Data =====" << std::endl;
        std::cout << "Liquid Aerosol SAD: " << epmCoupling.LA_SAD << " m2/kg-air" << std::endl;
        std::cout << "Polar Strat. Aerosol SAD: " << epmCoupling.PA_SAD << " m2/kg-air" << std::endl;
        std::cout << "Liquid Water Content: " << epmCoupling.LA_LWC << " kg/kg-air" << std::endl;
        std::cout << "Polar Strat. Water Content: " << epmCoupling.PA_LWC << " kg/kg-air" << std::endl;
        
        // Use coupling data to compute heterogeneous reaction rates
        // This would modify KPP's RCONST array during integration
        // For now, just log that we're using it
    }
    
    // =======================================================================
    // Initialize Solar Zenith Angle
    // =======================================================================
    
    double latitude = input.latitude_deg();
    int emissionDOY = input.emissionDOY();
    
    SZA sun(latitude, emissionDOY);
    
    double sunRise_hr = sun.sunRise;
    double sunSet_hr = sun.sunSet;
    
    std::cout << "Latitude: " << latitude << " deg" << std::endl;
    std::cout << "Day of year: " << emissionDOY << std::endl;
    std::cout << "Sunrise: " << sunRise_hr << " hr" << std::endl;
    std::cout << "Sunset: " << sunSet_hr << " hr" << std::endl;
    
    // =======================================================================
    // Define Time Integration Period
    // =======================================================================
    
    double tEmission_h = input.emissionTime();
    double tSimulation_h = input.simulationTime();
    double tInitial_h = tEmission_h;
    double tFinal_h = tInitial_h + tSimulation_h;
    
    double tInitial_s = tInitial_h * 3600.0;
    double tFinal_s = tFinal_h * 3600.0;
    
    std::cout << "Emission time: " << tEmission_h << " hr" << std::endl;
    std::cout << "Simulation time: " << tSimulation_h << " hr" << std::endl;
    std::cout << "Time range: " << tInitial_s << " - " << tFinal_s << " s" << std::endl;
    
    // =======================================================================
    // Build Time Array
    // =======================================================================
    
    double sunRise_s = sunRise_hr * 3600.0;
    double sunSet_s = sunSet_hr * 3600.0;
    
    std::vector<double> timeArray = buildTimeArray(tInitial_s, tFinal_s, 
                                           sunRise_s, sunSet_s, dt);
    
    size_t nTime = timeArray.size();
    std::cout << "Number of timesteps: " << nTime << std::endl;
    
    if (nTime == 0) {
        std::cout << "Error: No timesteps generated" << std::endl;
        return -1;
    }
    
    // =======================================================================
    // Initialize KPP Species
    // =======================================================================

    // Local arrays for KPP species
    double VAR_local[NVAR];
    
    // Reset all species to zero
    for (int i = 0; i < NVAR; i++) {
        VAR_local[i] = 0.0;
    }
    
    // =======================================================================
    // Initialize Species from Background Conditions (via Input class)
    // =======================================================================
    
    // Use background concentrations from Input class [ppb]
    double no_ppb = input.backgNOx();
    double o3_ppb = input.backgO3();
    double co_ppb = input.backgCO();
    double ch4_ppb = input.backgCH4();
    double so2_ppb = input.backgSO2();
    
    // Convert from ppb to molec/cm3
    VAR_local[ind_NO] = no_ppb * 1.0e-9 * airDens;
    VAR_local[ind_O3] = o3_ppb * 1.0e-9 * airDens;
    VAR_local[ind_CO] = co_ppb * 1.0e-9 * airDens;
    VAR_local[ind_CH4] = ch4_ppb * 1.0e-9 * airDens;
    VAR_local[ind_NO2] = no_ppb * 0.5 * 1.0e-9 * airDens;
    VAR_local[ind_H2O] = airDens * relHumidity_w * 1.0e-4;
    if (so2_ppb > 0.0) {
        VAR_local[ind_SO2] = so2_ppb * 1.0e-9 * airDens;
    }
    
    std::cout << "Initial species concentrations [ppb]:" << std::endl;
    std::cout << "  NO: " << no_ppb << std::endl;
    std::cout << "  NO2: " << no_ppb * 0.5 << std::endl;
    std::cout << "  O3: " << o3_ppb << std::endl;
    std::cout << "  CO: " << co_ppb << std::endl;
    std::cout << "  CH4: " << ch4_ppb << std::endl;
    std::cout << "  SO2: " << so2_ppb << std::endl;
    
    // KPP tolerances
    double RTOL[NVAR];
    double ATOL[NVAR];
    // Fixed species array (all zero for box model)
    double FIX[NFIX];
    for (int i = 0; i < NFIX; i++) FIX[i] = 0.0;
    for (int i = 0; i < NVAR; i++) {
        RTOL[i] = 1.0e-4;
        ATOL[i] = 1.0e6;
    }
    
    // =======================================================================
    // Initialize Photolysis Rate Array
    // =======================================================================
    
    double jRate[NPHOTOL];
    for (int i = 0; i < NPHOTOL; i++) {
        jRate[i] = 0.0;
    }
    
    // =======================================================================
    // Storage for Output
    // =======================================================================
    
    std::vector<std::vector<double> > speciesHistory(NVAR, std::vector<double>(nTime));
    std::vector<double> cosSZASeries(nTime);
    
    // =======================================================================
    // Main Time Integration Loop
    // =======================================================================
    
    std::cout << "\nStarting chemistry integration..." << std::endl;
    
    for (size_t iTime = 0; iTime < nTime - 1; iTime++) {
        
        double t = timeArray[iTime];
        double nextT = timeArray[iTime + 1];
        double dT = nextT - t;
        
        // Update solar zenith angle
        sun.Update(t + dT / 2.0);
        double cosSZA = sun.CSZA;
        cosSZASeries[iTime] = cosSZA;
        
        // Reset photolysis rates
        for (int i = 0; i < NPHOTOL; i++) {
            jRate[i] = 0.0;
        }
        
        // Calculate photolysis rates during daytime
        if (cosSZA > 0.0) {
            Update_JRates(jRate, cosSZA);
        }
        
        // Update photolysis rates in KPP
        for (int i = 0; i < NPHOTOL; i++) {
            PHOTOL[i] = jRate[i];
        }
        
        // Zero reaction rates
        for (int i = 0; i < NREACT; i++) {
            RCONST[i] = 0.0;
        }
        
        // Update temperature- and pressure-dependent reaction rates
        Update_RCONST(temperature_K, pressure_Pa, airDens, VAR_local[ind_H2O]);
        
        // ===================================================================
        // Heterogeneous chemistry on background aerosols (if enabled)
        // Uses GC_SETHET from KPP_HetRates.cpp
        // ===================================================================
        if (input.chemHET()) {
            // Get geoengineering parameters from input
            double geoRadius = input.backgroundGeoengineeringRadius();  // meters
            double geoGamma = input.backgroundGeoengineeringGamma();   // accommodation coefficient
            
            // Get background aerosol surface area (simplified: use default values)
            double defaultSAD = 1.0e-6;  // m²/cm³ (very small background)
            double area[NAERO];
            double radi[NAERO];
            for (int k = 0; k < NAERO; k++) {
                area[k] = defaultSAD;
                radi[k] = 1.0e-7;  // 100 nm default radius
            }
            
            // Set geoengineering aerosol SAD
            double geoRadius_cm = geoRadius * 100.0;  // Convert m to cm
            double geoSAD = input.backgroundGeoengineeringNumber() * 4.0 * PI * geoRadius_cm * geoRadius_cm;  // cm²/cm³
            
            // Other aerosol SADs (set to zero for now)
            double naclSAD = 0.0, caco3SAD = 0.0, al2o3SAD = 0.0, dustSAD = 0.0, diamondSAD = 0.0;
            double naclRad = 1.0e-7, caco3Rad = 1.0e-7, al2o3Rad = 1.0e-7, dustRad = 1.0e-7, diamondRad = 1.0e-7;
            
            // Sticking coefficients (default values)
            double kheti_sla[11] = {0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8};
            
            // Call GC_SETHET to compute heterogeneous reaction rates
            GC_SETHET(
                temperature_K, 
                pressure_Pa / 101325.0,  // Convert Pa to atm
                airDens,
                relHumidity_w,
                0,  // STATE_PSC: not in PSC
                VAR_local.data(),
                area, radi,
                0.0,  // IWC
                kheti_sla,
                input.ADV_TROPOPAUSE_PRESSURE(),
                geoSAD,
                geoRadius,
                geoGamma,
                naclSAD, caco3SAD, al2o3SAD, dustSAD, diamondSAD,
                naclRad, caco3Rad, al2o3Rad, dustRad, diamondRad
            );
        }
        
        // Integrate chemistry
        int IERR = INTEGRATE(VAR_local, FIX, t, nextT, ATOL, RTOL, 0.0);
        
        if (IERR < 0) {
            std::cout << "Integration failed at timestep " << iTime 
                    << " (t = " << t << " s)" << std::endl;
            return IERR;
        }
        
        // Store results
        for (int i = 0; i < NVAR; i++) {
            speciesHistory[i][iTime] = VAR_local[i];
        }
        
        if (iTime % 10 == 0) {
            std::cout << "  Timestep " << iTime << "/" << nTime-1 
                    << " (t = " << t/3600.0 << " hr)" << std::endl;
        }
    }
    
    // Store final values
    for (int i = 0; i < NVAR; i++) {
        speciesHistory[i][nTime - 1] = VAR_local[i];
    }
    cosSZASeries[nTime - 1] = sun.CSZA;
    
    // =======================================================================
    // Write Output to NetCDF
    // =======================================================================
    
    std::cout << "\nWriting output to NetCDF..." << std::endl;
    
    std::string outputFile = Input_Opt.SIMULATION_BOX_FILENAME;
    writeBoxModelOutput(outputFile, timeArray, speciesHistory, cosSZASeries,
                  airDens, relHumidity_i, NVAR);
    
    // =======================================================================
    // Print Summary
    // =======================================================================
    
    std::cout << "\n===== Box Model Results =====" << std::endl;
    std::cout << "Final species concentrations:" << std::endl;
    
    for (int i = 0; i < NVAR; i++) {
        if (VAR_local[i] > 0.0) {
            double concentration_ppb = VAR_local[i] / airDens * 1.0e9;
            std::cout << "  " << SPC_NAMES[i] << ": " << concentration_ppb << " ppb" << std::endl;
        }
    }
    
    // Store final species for LAGRID coupling
    g_finalSpecies.isValid = true;
    g_finalSpecies.NO   = VAR_local[ind_NO]   / airDens * 1.0e9;
    g_finalSpecies.NO2  = VAR_local[ind_NO2]  / airDens * 1.0e9;
    g_finalSpecies.O3  = VAR_local[ind_O3]   / airDens * 1.0e9;
    g_finalSpecies.CO   = VAR_local[ind_CO]   / airDens * 1.0e9;
    g_finalSpecies.CH4  = VAR_local[ind_CH4]  / airDens * 1.0e9;
    g_finalSpecies.SO2  = VAR_local[ind_SO2]  / airDens * 1.0e9;
    g_finalSpecies.H2O  = VAR_local[ind_H2O]  / airDens * 1.0e9;
    // HNO3 index may not be in the current list - only store if available
    g_finalSpecies.HNO3 = 0.0;  // Default if not in mechanism
    
    std::cout << "\nBox model completed successfully!" << std::endl;
    
    return 0;
    
} // runBoxModel

} // namespace BoxModel