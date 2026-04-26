#ifndef BOXMODEL_H_INCLUDED
#define BOXMODEL_H_INCLUDED

#include <iostream>
#include <vector>
#include <string>

#include "Core/Input_Mod.hpp"
#include "Core/Input.hpp"

namespace BoxModel {

struct EPMCouplingData {
    double LA_SAD;  
    double PA_SAD;  
    double LA_LWC;  
    double PA_LWC;  
    double MeanRadius;
    bool isValid;   
    
    EPMCouplingData() : LA_SAD(0.0), PA_SAD(0.0), LA_LWC(0.0), PA_LWC(0.0), MeanRadius(0.0), isValid(false) {}
    
    EPMCouplingData(double la_sad, double pa_sad, double la_lwc, double pa_lwc, double mean_radius) 
        : LA_SAD(la_sad), PA_SAD(pa_sad), LA_LWC(la_lwc), PA_LWC(pa_lwc), MeanRadius(mean_radius), isValid(true) {}
};

struct LAGRIDCouplingData {
    double NO;     
    double NO2;    
    double O3;     
    double CO;     
    double CH4;    
    double SO2;    
    double HNO3;   
    double H2O;    
    bool isValid;  
    
    LAGRIDCouplingData() : NO(0.0), NO2(0.0), O3(0.0), CO(0.0), CH4(0.0), SO2(0.0), HNO3(0.0), H2O(0.0), isValid(false) {}
};

LAGRIDCouplingData getFinalSpecies();

int runBoxModel(const OptInput& Input_Opt, const Input& input, 
                const EPMCouplingData& epmCoupling, int jCase);

std::vector<double> buildTimeArray(double tStart, double tEnd, 
                               double sunRise, double sunSet, 
                               double dt);

} // namespace BoxModel

#endif 
