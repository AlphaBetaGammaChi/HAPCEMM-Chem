/* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */
/*                                                                  */
/*     Aircraft Plume Chemistry, Emission and Microphysics Model    */
/*                             (APCEMM)                             */
/*                                                                  */
/* BoxModel Per-Cell KPP Thread Safety Implementation              */
/*                                                                  */
/* Author               : Thibaud M. Fritz                          */
/* Time                 : 4/2024                                   */
/* File                 : BoxModel_PerCell_KPP.cpp                   */
/*                                                                  */
/* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */

#include "Core/BoxModel_PerCell_KPP.hpp"
#include "KPP/KPP.hpp"
#include "Util/PhysConstant.hpp"
#include <cstring>

namespace BoxModel {
namespace PerCell {

// Define thread-local arrays (these are automatically threadprivate due to #pragma)
double VAR_thread[NVAR];
double RCONST_thread[NREACT];
double PHOTOL_thread[NPHOTOL];
double FIX_thread[NFIX];

void initThreadState(double temperature_K, double pressure_Pa, 
                     double h2o_molec, const double* initialSpecies) {
    // Initialize species from provided initial conditions
    for (int i = 0; i < NVAR; i++) {
        VAR_thread[i] = initialSpecies[i];
    }
    
    // Initialize fixed species to zero
    for (int i = 0; i < NFIX; i++) {
        FIX_thread[i] = 0.0;
    }
    
    // Initialize photolysis rates to zero
    for (int i = 0; i < NPHOTOL; i++) {
        PHOTOL_thread[i] = 0.0;
    }
    
    // Initialize reaction rates to zero
    for (int i = 0; i < NREACT; i++) {
        RCONST_thread[i] = 0.0;
    }
    
    // Set initial KPP state from arrays
    // (These global arrays are used by KPP internally)
    for (int i = 0; i < NVAR; i++) {
        VAR[i] = VAR_thread[i];
    }
    for (int i = 0; i < NFIX; i++) {
        FIX[i] = FIX_thread[i];
    }
    for (int i = 0; i < NPHOTOL; i++) {
        PHOTOL[i] = PHOTOL_thread[i];
    }
    for (int i = 0; i < NREACT; i++) {
        RCONST[i] = RCONST_thread[i];
    }
}

void getResults(double* speciesOut) {
    // Copy from thread-local to output
    for (int i = 0; i < NVAR; i++) {
        speciesOut[i] = VAR_thread[i];
    }
    
    // Also update global KPP arrays (needed for subsequent calls)
    for (int i = 0; i < NVAR; i++) {
        VAR[i] = VAR_thread[i];
    }
}

void updatePhotolysisRates(double cosSZA) {
    // Calculate photolysis rates using KPP functions
    double jRate[NPHOTOL];
    for (int i = 0; i < NPHOTOL; i++) {
        jRate[i] = 0.0;
    }
    
    // Only calculate during daytime
    if (cosSZA > 0.0) {
        Update_JRates(jRate, cosSZA);
    }
    
    // Store in thread-local array
    for (int i = 0; i < NPHOTOL; i++) {
        PHOTOL_thread[i] = jRate[i];
        PHOTOL[i] = jRate[i];  // Also update global for KPP
    }
}

void updateRateConstants(double temperature_K, double pressure_Pa, 
                         double airDens, double h2o_molec) {
    // Use KPP function to update temperature/pressure dependent rates
    Update_RCONST(temperature_K, pressure_Pa, airDens, h2o_molec);
    
    // Copy to thread-local array
    for (int i = 0; i < NREACT; i++) {
        RCONST_thread[i] = RCONST[i];
    }
}

void callHetRates(double temperature_K, double pressure_atm,
                  double airDens, double relHum, unsigned int state_PSC,
                  const double* species,
                  const double* area, const double* radii,
                  double IWC, const double* kheti_sla, double tropopausePress,
                  double geoSAD, double geoRadius, double geoGamma,
                  double naclSAD, double caco3SAD, double al2o3SAD, double dustSAD, double diamondSAD,
                  double naclRadius, double caco3Radius, double al2o3Radius, double dustRadius, double diamondRadius) {
    
    // Call the KPP GC_SETHET function to compute heterogeneous reaction rates
    // This will populate the global HET array used by KPP during integration
    GC_SETHET(
        temperature_K,           // Temperature [K]
        pressure_atm,           // Pressure [atm]
        airDens,                // Air density [molec/cm3]
        relHum,                 // Relative humidity [0-1]
        state_PSC,              // PSC state flag
        species,                // Species array
        area,                   // Aerosol surface areas
        radii,                  // Aerosol radii
        IWC,                    // Ice water content
        kheti_sla,              // Sticking coefficients
        tropopausePress,        // Tropopause pressure
        geoSAD,                 // Geoengineering SAD
        geoRadius,              // Geoengineering radius
        geoGamma,               // Geoengineering gamma
        naclSAD,                // NaCl SAD
        caco3SAD,               // CaCO3 SAD
        al2o3SAD,               // Al2O3 SAD
        dustSAD,                // Dust SAD
        diamondSAD,             // Diamond SAD
        naclRadius,             // NaCl radius
        caco3Radius,            // CaCO3 radius
        al2o3Radius,            // Al2O3 radius
        dustRadius,             // Dust radius
        diamondRadius           // Diamond radius
    );
}

}} // namespace BoxModel::PerCell