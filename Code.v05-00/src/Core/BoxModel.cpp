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

namespace BoxModel {

static LAGRIDCouplingData g_finalSpecies;

LAGRIDCouplingData getFinalSpecies() { return g_finalSpecies; }

std::vector<double> buildTimeArray(double tStart, double tEnd, double sunRise, double sunSet, double dt) {
    std::vector<double> timeArray;
    double currentTime = tStart;
    while (currentTime <= tEnd) {
        timeArray.push_back(currentTime);
        currentTime += dt;
        if (currentTime > tEnd && timeArray.back() < tEnd) { timeArray.push_back(tEnd); break; }
    }
    return timeArray;
}

void writeBoxModelOutput(const std::string& outputFile, const std::vector<double>& timeArray, const std::vector<std::vector<double>>& speciesHistory, const std::vector<double>& cosSZASeries, double airDens, double relHumidity_i, int nVar) {
    using namespace netCDF;
    using namespace netCDF::exceptions;
    try {
        NcFile ncFile(outputFile, NcFile::replace);
        size_t nTime = timeArray.size();
        NcDim timeDim = ncFile.addDim("time", nTime);
        NcDim speciesDim = ncFile.addDim("species", nVar);
        ncFile.addVar("time", ncFloat, timeDim).putVar(timeArray.data());
        ncFile.addVar("cosSZA", ncFloat, timeDim).putVar(cosSZASeries.data());
        NcVar specVar = ncFile.addVar("concentrations", ncFloat, {timeDim, speciesDim});
        std::vector<float> specData(nTime * nVar);
        for (size_t j = 0; j < nTime; j++) {
            for (int i = 0; i < nVar; i++) {
                specData[j * nVar + i] = static_cast<float>((speciesHistory[i][j] / airDens) * 1.0e9);
            }
        }
        specVar.putVar(specData.data());
    } catch (const std::exception& e) { std::cout << "Output Error: " << e.what() << std::endl; }
}

int runBoxModel(const OptInput& Input_Opt, const Input& input, const EPMCouplingData& epmCoupling, int jCase) {
    double dt = std::min(Input_Opt.CHEMISTRY_TIMESTEP, Input_Opt.TRANSPORT_TIMESTEP) * 60.0;
    if (dt <= 0.0) dt = 60.0;
    double temperature_K = input.temperature_K();
    double pressure_Pa = input.pressure_Pa();
    double airDens = pressure_Pa / (physConst::kB * temperature_K) * 1.0e-6;
    SZA sun(input.latitude_deg(), input.emissionDOY());
    std::vector<double> timeArray = buildTimeArray(input.emissionTime()*3600.0, (input.emissionTime()+input.simulationTime())*3600.0, sun.sunRise*3600.0, sun.sunSet*3600.0, dt);
    
    for (int i = 0; i < NVAR; i++) VAR[i] = 1.230e-21 * airDens;
    VAR[ind_NO] = input.backgNOx() * 0.5 * 1e-9 * airDens;
    VAR[ind_NO2] = input.backgNOx() * 0.5 * 1e-9 * airDens;
    VAR[ind_O3] = input.backgO3() * 1e-9 * airDens;
    VAR[ind_SO2] = input.backgSO2() * 1e-12 * airDens;
    VAR[ind_H2O] = airDens * (input.relHumidity_w() / 100.0) * physFunc::pSat_H2Ol(temperature_K) / pressure_Pa;

    std::vector<std::vector<double>> speciesHistory(NVAR, std::vector<double>(timeArray.size()));
    std::vector<double> cosSZASeries(timeArray.size());
    double RTOL[NVAR], ATOL[NVAR];
    for (int i=0; i<NVAR; i++) { RTOL[i] = 1.0e-4; ATOL[i] = 1.0e-2; }

    for (size_t iTime = 0; iTime < timeArray.size(); iTime++) {
        double t = timeArray[iTime];
        sun.Update(t / 3600.0);
        cosSZASeries[iTime] = sun.CSZA;
        for (int i = 0; i < NPHOTOL; i++) PHOTOL[i] = 0.0;
        if (sun.CSZA > 0.0) Update_JRates(PHOTOL, sun.CSZA);
        Update_RCONST(temperature_K, pressure_Pa, airDens, VAR[ind_H2O]);
        if (epmCoupling.isValid) {
            double AREA[NAERO] = {epmCoupling.LA_SAD, 0, 0, 0};
            double RADI[NAERO] = {epmCoupling.MeanRadius, 0, 0, 0};
            double KHETI_SLA[11] = {0.0};
            GC_SETHET(temperature_K, pressure_Pa, airDens, 1.4, 0, VAR, AREA, RADI, epmCoupling.LA_LWC, KHETI_SLA, 20000.0, 
                      input.backgroundGeoengineeringNumber(), input.backgroundGeoengineeringRadius(), 0.02, 0,0,0,0,0,0,0,0,0,0);
        }
        if (iTime < timeArray.size() - 1) INTEGRATE(VAR, FIX, t, timeArray[iTime+1], ATOL, RTOL, 0.0);
        for (int i = 0; i < NVAR; i++) speciesHistory[i][iTime] = VAR[i];
    }
    std::string outFile = Input_Opt.SIMULATION_BOX_FILENAME;
    size_t pos = outFile.find("*");
    if (pos != std::string::npos) outFile.replace(pos, 1, std::to_string(jCase));
    if (outFile.find(".nc") == std::string::npos) outFile += ".nc";
    writeBoxModelOutput(outFile, timeArray, speciesHistory, cosSZASeries, airDens, 1.4, NVAR);
    g_finalSpecies.isValid = true;
    g_finalSpecies.O3 = VAR[ind_O3] / airDens * 1e9;
    return 0;
}
}
