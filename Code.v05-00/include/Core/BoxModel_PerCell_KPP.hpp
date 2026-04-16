/* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */
/*                                                                  */
/*     Aircraft Plume Chemistry, Emission and Microphysics Model    */
/*                             (APCEMM)                             */
/*                                                                  */
/* BoxModel Per-Cell KPP Thread Safety Header                      */
/*                                                                  */
/* Author               : Thibaud M. Fritz                          */
/* Time                 : 4/2024                                   */
/* File                 : BoxModel_PerCell_KPP.hpp                   */
/*                                                                  */
/* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */

#ifndef BOXMODEL_PERCELL_KPP_HPP
#define BOXMODEL_PERCELL_KPP_HPP

#include "KPP/KPP_Parameters.h"
#include "KPP/KPP_Global.h"

namespace BoxModel {
namespace PerCell {

/**
 * Thread-local copies of KPP state arrays for per-cell chemistry.
 * Each OpenMP thread gets its own copy of these arrays, preventing
 * race conditions during parallel KPP integration.
 * 
 * These arrays are declared with threadprivate directive to ensure
 * each thread has independent storage.
 */

// Thread-local KPP variable array (species concentrations)
#pragma omp threadprivate(VAR_thread)
// Thread-local KPP rate constant array  
#pragma omp threadprivate(RCONST_thread)
// Thread-local KPP photolysis rate array
#pragma omp threadprivate(PHOTOL_thread)
// Thread-local KPP fixed species array
#pragma omp threadprivate(FIX_thread)

/**
 * Initialize thread-local KPP state from cell conditions.
 * Must be called by each thread before integration.
 * 
 * @param temperature_K  Cell temperature [K]
 * @param pressure_Pa   Cell pressure [Pa]
 * @param h2o_molec     Water vapor concentration [molec/cm3]
 * @param initialSpecies Pointer to initial species array [NVAR] in molec/cm3
 */
void initThreadState(double temperature_K, double pressure_Pa, 
                     double h2o_molec, const double* initialSpecies);

/**
 * Extract results after integration.
 * Call after INTEGRATE() completes to get evolved species.
 * 
 * @param speciesOut Pointer to output species array [NVAR] in molec/cm3
 */
void getResults(double* speciesOut);

/**
 * Update photolysis rates for current cell based on SZA.
 * 
 * @param cosSZA Cosine of solar zenith angle
 */
void updatePhotolysisRates(double cosSZA);

/**
 * Update reaction rate constants for current cell conditions.
 * 
 * @param temperature_K Temperature [K]
 * @param pressure_Pa  Pressure [Pa]
 * @param airDens      Air density [molec/cm3]
 * @param h2o_molec    Water vapor [molec/cm3]
 */
void updateRateConstants(double temperature_K, double pressure_Pa, 
                         double airDens, double h2o_molec);

/**
 * Call GC_SETHET to compute heterogeneous chemistry rates.
 * 
 * @param temperature_K     Temperature [K]
 * @param pressure_atm     Pressure [atm]
 * @param airDens          Air density [molec/cm3]
 * @param relHum           Relative humidity [0-1]
 * @param state_PSC        PSC state flag
 * @param species          Species array [molec/cm3]
 * @param area             Aerosol surface areas [m2/cm3]
 * @param radii            Aerosol radii [m]
 * @param IWC              Ice water content [kg/cm3]
 * @param kheti_sla        Sticking coefficients [11]
 * @param tropopausePress  Tropopause pressure [Pa]
 * @param geoSAD           Geoengineering SAD [cm2/cm3]
 * @param geoRadius        Geoengineering radius [m]
 * @param geoGamma         Geoengineering gamma (accommodation coefficient)
 * @param naclSAD          NaCl SAD [cm2/cm3]
 * @param caco3SAD         CaCO3 SAD [cm2/cm3]
 * @param al2o3SAD         Al2O3 SAD [cm2/cm3]
 * @param dustSAD          Dust SAD [cm2/cm3]
 * @param diamondSAD       Diamond SAD [cm2/cm3]
 * @param naclRadius       NaCl radius [m]
 * @param caco3Radius      CaCO3 radius [m]
 * @param al2o3Radius      Al2O3 radius [m]
 * @param dustRadius       Dust radius [m]
 * @param diamondRadius     Diamond radius [m]
 */
void callHetRates(double temperature_K, double pressure_atm,
                  double airDens, double relHum, unsigned int state_PSC,
                  const double* species,
                  const double* area, const double* radii,
                  double IWC, const double* kheti_sla, double tropopausePress,
                  double geoSAD, double geoRadius, double geoGamma,
                  double naclSAD, double caco3SAD, double al2o3SAD, double dustSAD, double diamondSAD,
                  double naclRadius, double caco3Radius, double al2o3Radius, double dustRadius, double diamondRadius);

}} // namespace BoxModel::PerCell

#endif // BOXMODEL_PERCELL_KPP_HPP