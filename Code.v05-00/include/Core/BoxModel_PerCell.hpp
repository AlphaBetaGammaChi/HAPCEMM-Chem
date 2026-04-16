/* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */
/*                                                                  */
/*     Aircraft Plume Chemistry, Emission and Microphysics Model    */
/*                             (APCEMM)                             */
/*                                                                  */
/* BoxModel Per-Cell Chemistry Header                               */
/*                                                                  */
/* Author               : AlphaBetaGammaChi                         */
/* Time                 : 4/2024                                   */
/* File                 : BoxModel_PerCell.hpp                       */
/*                                                                  */
/* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */

#ifndef BOXMODEL_PERCELL_HPP
#define BOXMODEL_PERCELL_HPP

#include <string>
#include <vector>

// Forward declarations
struct OptInput;
class Input;

namespace BoxModel {

/**
 * Per-cell chemistry options
 */
enum class PerCellMode {
    INDEPENDENT = 0,  // Each cell runs independently (no species transport)
    COUPLED = 1      // Species are coupled via transport (future extension)
};

/**
 * Run per-grid-cell chemistry on the entire LAGRID grid.
 * 
 * This function applies the box model chemistry to each grid cell
 * independently (simplified mode) or with species transport (full mode).
 * 
 * @param Input_Opt     Input options (contains flags, parameters)
 * @param input         Input data (meteorology, background species)
 * @param nx            Number of cells in x-direction
 * @param ny            Number of cells in y-direction  
 * @param species       3D array [NVAR][ny][nx] of species concentrations [molec/cm3]
 * @param temperature   2D array [ny][nx] of temperature [K]
 * @param pressure      2D array [ny][nx] of pressure [Pa]
 * @param humidity      2D array [ny][nx] of relative humidity (ice)
 * @param aerosolSAD    2D array [ny][nx] of aerosol surface area [m2/kg] (optional, can be null)
 * @param dt            Chemistry timestep [s]
 * @param mode          PerCellMode - INDEPENDENT (simplified) or COUPLED (with transport)
 * @return int          0 on success, negative on error
 */
int runPerCellChemistry(
    const OptInput& Input_Opt,
    const Input& input,
    int nx, int ny,
    double* species,           // [NVAR][ny][nx] - updated in place
    const double* temperature,  // [ny][nx]
    const double* pressure,     // [ny][nx] 
    const double* humidity,    // [ny][nx] - relative humidity w.r.t. ice
    const double* aerosolSAD,  // [ny][nx] - optional, can be nullptr
    double dt,                 // Chemistry timestep [s]
    PerCellMode mode = PerCellMode::INDEPENDENT
);

/**
 * Initialize species array with background concentrations.
 * 
 * @param nx            Number of cells in x-direction
 * @param ny            Number of cells in y-direction
 * @param species       3D array [NVAR][ny][nx] to initialize
 * @param input         Input data with background concentrations
 * @param airDens       Air density [molec/cm3] for conversion
 */
void initSpeciesArray(
    int nx, int ny,
    double* species,
    const Input& input,
    double airDens
);

/**
 * Write per-cell chemistry output to NetCDF file.
 * 
 * @param outputFile   Output filename
 * @param nx            Number of cells in x-direction
 * @param ny            Number of cells in y-direction
 * @param species       3D array [NVAR][ny][nx] of final species
 * @param timeHours     Simulation time [hours]
 */
void writePerCellOutput(
    const std::string& outputFile,
    int nx, int ny,
    const double* species,
    double timeHours
);

/**
 * Get number of chemical species (NVAR)
 */
int getNumSpecies();

/**
 * Get species names for output
 */
const char* getSpeciesName(int index);

} // namespace BoxModel

#endif // BOXMODEL_PERCELL_HPP