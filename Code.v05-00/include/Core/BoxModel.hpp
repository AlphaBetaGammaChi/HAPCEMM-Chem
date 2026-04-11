/* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */
/*                                                                  */
/*     Aircraft Plume Chemistry, Emission and Microphysics Model    */
/*                             (APCEMM)                             */
/*                                                                  */
/* BoxModel Header File                                            */
/*                                                                  */
/* Author               : Thibaud M. Fritz                          */
/* File                 : BoxModel.hpp                              */
/*                                                                  */
/* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */

#ifndef BOXMODEL_H_INCLUDED
#define BOXMODEL_H_INCLUDED

#include <iostream>
#include <vector>
#include <string>

#include "Core/Input_Mod.hpp"
#include "Core/Input.hpp"

namespace BoxModel {

/**
 * Run the box model chemistry over the entire simulation domain
 * 
 * This is a 0-dimensional model that simulates gas-phase chemistry
 * using KPP (Kinetic Pre-Processor) without spatial transport.
 * 
 * @param Input_Opt   - Input options (contains flags and filenames)
 * @param input      - Input case data (meteorology, emissions, etc.)
 * @return int       - 0 on success, negative on error
 */
int runBoxModel(const OptInput& Input_Opt, const Input& input);

/**
 * Build the time array for the box model integration
 * 
 * @param tStart    - Start time [s]
 * @param tEnd      - End time [s]
 * @param sunRise   - Sunrise time [s]
 * @param sunSet   - Sunset time [s]
 * @param dt       - Timestep [s]
 * @return Vector_1D - Vector of timesteps
 */
std::vector<double> buildTimeArray(double tStart, double tEnd, 
                               double sunRise, double sunSet, 
                               double dt);

} // namespace BoxModel

#endif // BOXMODEL_H_INCLUDED