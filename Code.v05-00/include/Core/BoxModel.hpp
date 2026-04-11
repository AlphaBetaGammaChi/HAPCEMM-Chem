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
 * Data structure to pass EPM microphysical properties to box model
 * for heterogeneous chemistry calculations
 */
struct EPMCouplingData {
    double LA_SAD;  // Liquid aerosol surface area density [m2/kg-air]
    double PA_SAD;  // Polar stratospheric aerosol surface area [m2/kg-air]
    double LA_LWC;  // Liquid water content [kg/kg-air]
    double PA_LWC;  // Polar stratospheric water content [kg/kg-air]
    bool isValid;   // Whether data was successfully passed
    
    // Default constructor
    EPMCouplingData() : LA_SAD(0.0), PA_SAD(0.0), LA_LWC(0.0), PA_LWC(0.0), isValid(false) {}
    
    // Constructor with values
    EPMCouplingData(double la_sad, double pa_sad, double la_lwc, double pa_lwc)
        : LA_SAD(la_sad), PA_SAD(pa_sad), LA_LWC(la_lwc), PA_LWC(pa_lwc), isValid(true) {}
};

/**
 * Run the box model chemistry over the entire simulation domain
 * 
 * This is a 0-dimensional model that simulates gas-phase chemistry
 * using KPP (Kinetic Pre-Processor) without spatial transport.
 * 
 * @param Input_Opt     - Input options (contains flags and filenames)
 * @param input         - Input case data (meteorology, emissions, etc.)
 * @param epmCoupling   - Optional EPM coupling data (aerosol SAD, LWC)
 * @return int          - 0 on success, negative on error
 */
int runBoxModel(const OptInput& Input_Opt, const Input& input, 
                const EPMCouplingData& epmCoupling = EPMCouplingData());

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