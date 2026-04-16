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

}} // namespace BoxModel::PerCell

#endif // BOXMODEL_PERCELL_KPP_HPP