#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <ctime>
#include <sys/stat.h>
#include <sstream>
#include <mutex>
static std::mutex kpp_mutex;

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
#include "Util/JuliaBridge.hpp"
#include "AIM/Coagulation.hpp"
#include "AIM/Aerosol.hpp"
#include <netcdf>

namespace BoxModel {

static thread_local LAGRIDCouplingData g_finalSpecies;
LAGRIDCouplingData getFinalSpecies() { return g_finalSpecies; }

static double getMolecularWeight(const std::string& name) {
    if (name == "O3") return 48.0;
    if (name == "NO") return 30.01;
    if (name == "NO2") return 46.01;
    if (name == "HNO3") return 63.01;
    if (name == "SO2") return 64.06;
    if (name == "H2O") return 18.015;
    if (name == "H2O2") return 34.01;
    if (name == "OH") return 17.01;
    if (name == "HO2") return 33.01;
    if (name == "CO") return 28.01;
    if (name == "CH4") return 16.04;
    if (name == "H2") return 2.016;
    if (name == "NH3") return 17.03;
    if (name == "N2O") return 44.01;
    return 50.0;
}

std::vector<double> buildTimeArray(double tStart, double tEnd, double sunRise, double sunSet, double dt) {
    std::vector<double> timeArray;
    double currentTime = tStart;
    while (currentTime <= tEnd) {
        timeArray.push_back(currentTime);
        currentTime += dt;
        if (currentTime > tEnd && timeArray.back() < tEnd) { 
            // Avoid duplicate or extremely small final time steps (less than 1 ms) due to float rounding
            if (tEnd - timeArray.back() > 1e-3) {
                timeArray.push_back(tEnd); 
            } else {
                timeArray.back() = tEnd; // Snap the last time step exactly to tEnd
            }
            break; 
        }
    }
    return timeArray;
}

void writeBoxModelOutput(
    const std::string& outputFile,
    const std::string& outputList,
    const std::vector<double>& timeArray,
    const std::vector<std::vector<double>>& speciesHistory,
    const std::vector<std::vector<double>>& prodHistory,
    const std::vector<std::vector<double>>& lossHistory,
    const std::vector<std::vector<double>>& tauHistory,
    const std::vector<std::vector<double>>& cumProdHistory,
    const std::vector<std::vector<double>>& cumLossHistory,
    const std::vector<std::vector<double>>& rxnRateHistory,
    const std::vector<double>& cosSZASeries,
    double airDens, double relHumidity_i, int nVar,
    const std::vector<double>& tempHistory,
    const std::vector<double>& pressHistory,
    const std::vector<double>& altitudeHistory,
    const std::vector<double>& rhiHistory,
    const std::vector<double>& h2oHistory,
    const std::vector<double>& iceNumberHistory,
    const std::vector<double>& iceAreaHistory,
    const std::vector<double>& iceVolumeHistory,
    const std::vector<double>& effRadiusHistory,
    const std::vector<double>& xODHistory,
    const std::vector<double>& yODHistory,
    const std::vector<double>& iceMassHistory,
    const std::vector<double>& numberIceParticlesHistory,
    const std::vector<double>& extinctionHistory,
    const std::vector<double>& iwcHistory,
    const std::vector<double>& widthHistory,
    const std::vector<double>& depthHistory,
    const std::vector<double>& intODHistory,
    const std::vector<double>& geoNumberHistory,
    const std::vector<double>& geoAreaHistory,
    const std::vector<double>& geoRadiusHistory,
    const std::vector<double>& plumeAreaHistory,
    const std::vector<double>& dxHistory,
    const std::vector<double>& dyHistory,
    const std::vector<double>& binCenters,
    const std::vector<double>& binEdges,
    const std::vector<std::vector<double>>& psdHistory,
    const std::vector<std::vector<double>>& tauSSHistory,
    const std::vector<std::vector<double>>& jRatesHistory,
    const std::vector<std::vector<double>>& rconstHistory,
    const std::vector<double>& viscosityHistory,
    const std::vector<double>& meanFreePathHistory,
    const std::vector<std::vector<double>>& tauDepHistory,
    const std::vector<std::vector<double>>& depLossHistory,
    const std::vector<std::vector<double>>& cumDepMassHistory,
    const std::vector<double>& opeHistory,
    const std::vector<double>& roxHistory)
{
    using namespace netCDF;
    using namespace netCDF::exceptions;
    try {
        NcFile ncFile(outputFile, NcFile::replace);
        size_t nTime = timeArray.size();
        size_t nBin = binCenters.size();
        NcDim timeDim = ncFile.addDim("time", nTime);
        NcDim speciesDim = ncFile.addDim("species", nVar);
        NcDim binRadDim  = ncFile.addDim("r", nBin);
        NcDim binEdgeDim = ncFile.addDim("r_b", nBin + 1);

        ncFile.addVar("time", ncFloat, timeDim).putVar(timeArray.data());
        ncFile.addVar("cosSZA", ncFloat, timeDim).putVar(cosSZASeries.data());
        if (!binEdges.empty()) {
            ncFile.addVar("r_e", ncFloat, binEdgeDim).putVar(binEdges.data());
        }
        if (!binCenters.empty()) {
            ncFile.addVar("r", ncFloat, binRadDim).putVar(binCenters.data());
        }
        ncFile.addVar("dx", ncFloat, timeDim).putVar(dxHistory.data());
        ncFile.addVar("dy", ncFloat, timeDim).putVar(dyHistory.data());
        ncFile.addVar("plume_area", ncFloat, timeDim).putVar(plumeAreaHistory.data());

        NcVar specVar = ncFile.addVar("concentrations", ncFloat, {timeDim, speciesDim});
        std::vector<float> specData(nTime * nVar);
        for (size_t j = 0; j < nTime; j++) {
            for (int i = 0; i < nVar; i++) {
                specData[j * nVar + i] = static_cast<float>(speciesHistory[i][j] * 1.0e9);
            }
        }
        specVar.putVar(specData.data());

        /* Helper lambda: flatten [species][time] -> [time x species] float buffer
         * and write as a 2D NetCDF variable */
        auto write2D = [&](const std::string& varName,
                           const std::string& units,
                           const std::string& longName,
                           const std::vector<std::vector<double>>& data,
                           const netCDF::NcDim& dim1,
                           const netCDF::NcDim& dim2,
                           int n2,
                           double scale = 1.0)
        {
            netCDF::NcVar v = ncFile.addVar(varName, netCDF::ncFloat, {dim1, dim2});
            v.putAtt("units",     units);
            v.putAtt("long_name", longName);
            if (nTime == 0 || n2 == 0) return;
            std::vector<float> buf(nTime * static_cast<size_t>(n2));
            for (size_t t = 0; t < nTime; t++) {
                for (int s = 0; s < n2; s++) {
                    buf[t * static_cast<size_t>(n2) + static_cast<size_t>(s)] =
                        static_cast<float>(data[static_cast<size_t>(s)][t] * scale);
                }
            }
            v.putVar(buf.data());
        };

        netCDF::NcDim rxnDim  = ncFile.addDim("reaction", static_cast<size_t>(NREACT));

        write2D("prod_rate",  "molec cm-3 s-1",
                "Instantaneous net production rate P[i] (positive Vdot)",
                prodHistory,    timeDim, speciesDim, nVar);

        write2D("loss_rate",  "molec cm-3 s-1",
                "Instantaneous net loss rate |L[i]| (positive magnitude)",
                lossHistory,    timeDim, speciesDim, nVar);

        write2D("lifetime",   "s",
                "Chemical lifetime [X]/L (1e30 where L is negligible)",
                tauHistory,     timeDim, speciesDim, nVar);

        write2D("cum_prod",   "molec cm-3",
                "Cumulative integrated production (trapezoidal sum)",
                cumProdHistory, timeDim, speciesDim, nVar);

        write2D("cum_loss",   "molec cm-3",
                "Cumulative integrated loss (trapezoidal sum)",
                cumLossHistory, timeDim, speciesDim, nVar);

        write2D("rxn_rate",   "molec cm-3 s-1",
                "Instantaneous reaction rate A[j] for each KPP reaction",
                rxnRateHistory, timeDim, rxnDim, NREACT);

        write2D("n_aer", "# / cm^3",
                "Ice aerosol particle size distribution over time",
                psdHistory, timeDim, binRadDim, nBin);

        auto add1D = [&](const std::string& name, const std::string& units, const std::string& desc, const std::vector<double>& data) {
            NcVar v = ncFile.addVar(name, ncFloat, timeDim);
            v.putAtt("units", units);
            v.putAtt("long_name", desc);
            if (data.empty()) return;
            std::vector<float> fbuf(data.begin(), data.end());
            v.putVar(fbuf.data());
        };

        add1D("Pressure", "Pa", "Pressure", pressHistory);
        add1D("Altitude", "m", "Altitude", altitudeHistory);
        add1D("Temperature", "K", "Temperature", tempHistory);
        add1D("RHi", "%", "Relative Humidity w.r.t. Ice", rhiHistory);
        add1D("H2O", "molec / cm^3", "H2O molecular concentration", h2oHistory);
        add1D("Ice aerosol particle number", "# / cm^3", "Ice aerosol particle number concentration", iceNumberHistory);
        add1D("Ice aerosol surface area", "m^2 / cm^3", "Ice aerosol surface area density", iceAreaHistory);
        add1D("Ice aerosol volume", "m^3 / cm^3", "Ice aerosol volume", iceVolumeHistory);
        add1D("Effective radius", "m", "Ice aerosol effective radius", effRadiusHistory);
        add1D("Horizontal optical depth", "-", "Horizontally-integrated optical depth", xODHistory);
        add1D("Vertical optical depth", "-", "Vertically-integrated optical depth", yODHistory);
        add1D("Ice Mass", "kg / m", "Total Mass of Ice Crystals of Cross Section", iceMassHistory);
        add1D("Number Ice Particles", "# / m", "Total Number of Ice Particles of Cross Section", numberIceParticlesHistory);
        add1D("Extinction", "m^-1", "Extinction", extinctionHistory);
        add1D("IWC", "kg / m^3", "Ice Water Content", iwcHistory);
        add1D("width", "m", "Contrail Extinction-Defined Width", widthHistory);
        add1D("depth", "m", "Contrail Extinction-Defined Depth", depthHistory);
        add1D("intOD", "m", "Integrated Vertical Optical Depth", intODHistory);
        add1D("Geo-particle number", "# / cm^3", "Geoengineering background particle concentration", geoNumberHistory);
        add1D("Geo-particle surface area", "m^2 / cm^3", "Geoengineering background particle surface area density", geoAreaHistory);
        add1D("Geo-particle radius", "m", "Geoengineering background particle effective radius", geoRadiusHistory);

        // steady states
        write2D("tau_ss", "s", "Steady-State Lifetime [X]/P", tauSSHistory, timeDim, speciesDim, nVar);

        // photolytic lifetimes (tau_photo = 1/J)
        std::vector<float> photoLifeBuf(nTime * NPHOTOL);
        for (size_t t = 0; t < nTime; t++) {
            for (int j = 0; j < NPHOTOL; j++) {
                photoLifeBuf[t * NPHOTOL + j] = (jRatesHistory[j][t] > 1e-30) ? 1.0 / jRatesHistory[j][t] : 1e30;
            }
        }
        netCDF::NcDim photolDim = ncFile.addDim("photol_reaction", NPHOTOL);
        ncFile.addVar("tau_photo", netCDF::ncFloat, {timeDim, photolDim}).putVar(photoLifeBuf.data());

        // reaction rate constants k_ij
        write2D("k_ij", "cm3 molec-1 s-1 or s-1", "KPP Reaction Rate Constants", rconstHistory, timeDim, rxnDim, NREACT);

        // std::string outputList = Input_Opt.BOX_OUTPUT_VARIABLES;
        bool saveAll = (outputList == "all");
        auto include = [&](const std::string& category) {
            return saveAll || outputList.find(category) != std::string::npos;
        };

        if (include("meteorology")) {
            // air viscosity and mean free path
            ncFile.addVar("viscosity", netCDF::ncFloat, timeDim).putVar(viscosityHistory.data());
            ncFile.addVar("mean_free_path", netCDF::ncFloat, timeDim).putVar(meanFreePathHistory.data());
        }

        if (include("chemistry")) { 
            // deposition lifetime
            ncFile.addVar("tau_dep", netCDF::ncFloat, timeDim).putVar(tauDepHistory[0].data());

            // deposition loss rates and cumulative deposited mass
            write2D("Deposition_loss", "molec cm-3 s-1", "Instantaneous loss rate due to deposition", depLossHistory, timeDim, speciesDim, nVar);
            write2D("Cumulative_deposition_loss", "g m-2", "Cumulative deposited species mass", cumDepMassHistory, timeDim, speciesDim, nVar);
        }

    } catch (const std::exception& e) { std::cout << "Output Error: " << e.what() << std::endl; }
}

int runBoxModel(const OptInput& Input_Opt, const Input& input, const EPMCouplingData& epmCoupling, int jCase) {
    double dt = std::min(Input_Opt.CHEMISTRY_TIMESTEP, Input_Opt.TRANSPORT_TIMESTEP) * 60.0;
    if (dt <= 0.0) dt = 60.0;
    double temperature_K = input.temperature_K();
    double pressure_Pa = input.pressure_Pa();
    double airDens = pressure_Pa / (physConst::kB * temperature_K) * 1.0e-6; // air density in molec/cm3
    SZA sun(input.latitude_deg(), input.emissionDOY());
    std::vector<double> timeArray = buildTimeArray(input.emissionTime()*3600.0, (input.emissionTime()+input.boxModelDuration())*3600.0, sun.sunRise*3600.0, sun.sunSet*3600.0, dt);
    
    // SCIENTIFIC INITIALIZATION
    for (int i = 0; i < NVAR; i++) VAR[i] = 1.0e-15 * airDens; // Scientific floor

    int box_ind_NH3 = -1;
    int box_ind_N2O = -1;
    int box_ind_LUB = -1;
    int box_ind_MO2 = -1;
    int box_ind_ETO2 = -1;
    for (int i = 0; i < NVAR; i++) {
        if (SPC_NAMES[i] != nullptr) {
            std::string name(SPC_NAMES[i]);
            if (name == "NH3") box_ind_NH3 = i;
            else if (name == "N2O") box_ind_N2O = i;
            else if (name == "LUB") box_ind_LUB = i;
            else if (name == "MO2" || name == "CH3O2") box_ind_MO2 = i;
            else if (name == "ETO2" || name == "C2H5O2") box_ind_ETO2 = i;
        }
    }

    int ind_Custom = -1;
    if (Input_Opt.SIMULATION_FUEL == "custom" && !Input_Opt.SIMULATION_CUSTOM_SPECIES.empty()) {
        const std::string& spcName = Input_Opt.SIMULATION_CUSTOM_SPECIES[0];
        for (int i = 0; i < NVAR; i++) {
            if (SPC_NAMES[i] != nullptr && spcName == SPC_NAMES[i]) {
                ind_Custom = i;
                break;
            }
        }
    }

    // Plume physical parameters declaration
    const size_t nTimeSteps = timeArray.size();
    std::vector<double> tempHistory(nTimeSteps, 0.0);
    std::vector<double> pressHistory(nTimeSteps, 0.0);
    std::vector<double> altitudeHistory(nTimeSteps, 0.0);
    std::vector<double> rhiHistory(nTimeSteps, 0.0);
    std::vector<double> h2oHistory(nTimeSteps, 0.0);
    std::vector<double> iceNumberHistory(nTimeSteps, 0.0);
    std::vector<double> iceAreaHistory(nTimeSteps, 0.0);
    std::vector<double> iceVolumeHistory(nTimeSteps, 0.0);
    std::vector<double> effRadiusHistory(nTimeSteps, 0.0);
    std::vector<double> xODHistory(nTimeSteps, 0.0);
    std::vector<double> yODHistory(nTimeSteps, 0.0);
    std::vector<double> iceMassHistory(nTimeSteps, 0.0);
    std::vector<double> numberIceParticlesHistory(nTimeSteps, 0.0);
    std::vector<double> extinctionHistory(nTimeSteps, 0.0);
    std::vector<double> iwcHistory(nTimeSteps, 0.0);
    std::vector<double> widthHistory(nTimeSteps, 0.0);
    std::vector<double> depthHistory(nTimeSteps, 0.0);
    std::vector<double> intODHistory(nTimeSteps, 0.0);
    std::vector<double> geoNumberHistory(nTimeSteps, 0.0);
    std::vector<double> geoAreaHistory(nTimeSteps, 0.0);
    std::vector<double> geoRadiusHistory(nTimeSteps, 0.0);
    std::vector<double> plumeAreaHistory(nTimeSteps, 0.0);
    std::vector<double> dxHistory(nTimeSteps, 0.0);
    std::vector<double> dyHistory(nTimeSteps, 0.0);
    std::vector<double> binCenters;
    std::vector<double> binEdges;
    std::vector<std::vector<double>> psdHistory;

    // Diagnostic history vectors
    std::vector<std::vector<double>> tauSSHistory(NVAR, std::vector<double>(nTimeSteps, 0.0));
    std::vector<std::vector<double>> jRatesHistory(NPHOTOL, std::vector<double>(nTimeSteps, 0.0));
    std::vector<std::vector<double>> rconstHistory(NREACT, std::vector<double>(nTimeSteps, 0.0));
    std::vector<std::vector<double>> rhi2DHistory(NVAR, std::vector<double>(nTimeSteps, 0.0));
    std::vector<std::vector<double>> depLossHistory(NVAR, std::vector<double>(nTimeSteps, 0.0));
    std::vector<std::vector<double>> cumDepMassHistory(NVAR, std::vector<double>(nTimeSteps, 0.0));
    std::vector<std::vector<double>> tauDepHistory(NVAR, std::vector<double>(nTimeSteps, 0.0));
    std::vector<double> viscosityHistory(nTimeSteps, 0.0);
    std::vector<double> meanFreePathHistory(nTimeSteps, 0.0);
    std::vector<double> opeHistory(nTimeSteps, 0.0);
    std::vector<double> roxHistory(nTimeSteps, 0.0);

    // Initial Emitted Species Concentrations Calculation
    double plumeArea_cm2 = epmCoupling.isValid ? epmCoupling.LA_SAD * 1.0e4 : 1.0e6;
    double H2_emitted = input.EI_H2();
    double H2O2_emitted_conc = input.EI_H2O2();
    double N2O_emitted_conc = input.EI_N2O();
    double NH3_emitted_conc = input.EI_NH3();
    double Lub_emitted_conc = input.EI_LUB();

    // Load major background species directly from input [ppb to molec/cm3]
    VAR[ind_NO]  = input.backgNOx() * 0.5 * 1e-9 * airDens;
    VAR[ind_NO2] = input.backgNOx() * 0.5 * 1e-9 * airDens;
    VAR[ind_O3]  = input.backgO3()  * 1e-9 * airDens;
    VAR[ind_SO2] = input.backgSO2() * 1e-12 * airDens; 
    VAR[ind_CO]  = input.backgCO()  * 1e-9 * airDens;
    VAR[ind_CH4] = input.backgCH4() * 1e-6 * airDens;
    VAR[ind_H2O] = airDens * (input.relHumidity_w() / 100.0) * physFunc::pSat_H2Ol(temperature_K) / pressure_Pa;

    VAR[ind_H2] = (1.0e-15 * airDens) + (H2_emitted / plumeArea_cm2);
    VAR[ind_H2O2] = (1.0e-15 * airDens) + H2O2_emitted_conc;
    if (box_ind_N2O >= 0) {
        VAR[box_ind_N2O] = (1.0e-15 * airDens) + N2O_emitted_conc;
    }
    if (box_ind_NH3 >= 0) {
        VAR[box_ind_NH3] = (1.0e-15 * airDens) + NH3_emitted_conc;
    }
    if (box_ind_LUB >= 0) {
        VAR[box_ind_LUB] = (1.0e-15 * airDens) + Lub_emitted_conc;
    }

    // Load custom fuel species dynamically by looking up their index
    if (Input_Opt.SIMULATION_FUEL == "custom") {
        for (size_t k = 0; k < Input_Opt.SIMULATION_CUSTOM_SPECIES.size(); k++) {
            const std::string& spcName = Input_Opt.SIMULATION_CUSTOM_SPECIES[k];
            double custom_ei_ppb = (k < Input_Opt.SIMULATION_CUSTOM_EIS.size()) ? Input_Opt.SIMULATION_CUSTOM_EIS[k] : 0.0;
            double custom_conc = custom_ei_ppb * 1e-9 * airDens;
            int spcIndex = -1;
            for (int i = 0; i < NVAR; i++) {
                if (SPC_NAMES[i] != nullptr && spcName == SPC_NAMES[i]) {
                    spcIndex = i;
                    break;
                }
            }
            if (spcIndex >= 0) {
                VAR[spcIndex] = (1.0e-15 * airDens) + custom_conc;
            }
        }
    }

    std::vector<std::vector<double>> speciesHistory(NVAR, std::vector<double>(timeArray.size()));

    /* ---- P/L and reaction rate diagnostic storage ---- */
    std::vector<std::vector<double>> prodHistory   (NVAR,   std::vector<double>(nTimeSteps, 0.0));
    std::vector<std::vector<double>> lossHistory   (NVAR,   std::vector<double>(nTimeSteps, 0.0));
    std::vector<std::vector<double>> tauHistory    (NVAR,   std::vector<double>(nTimeSteps, 0.0));
    std::vector<std::vector<double>> cumProdHistory(NVAR,   std::vector<double>(nTimeSteps, 0.0));
    std::vector<std::vector<double>> cumLossHistory(NVAR,   std::vector<double>(nTimeSteps, 0.0));
    /* Per-reaction rates: [NREACT x nTimeSteps] */
    std::vector<std::vector<double>> rxnRateHistory(NREACT, std::vector<double>(nTimeSteps, 0.0));
    std::vector<double> cosSZASeries(timeArray.size());
    double RTOL[NVAR], ATOL[NVAR];
    for (int i=0; i<NVAR; i++) { RTOL[i] = 1.0e-4; ATOL[i] = 1.0e+6; }

    std::cout << "Starting chemistry integration. O3 Baseline: " << input.backgO3() << " ppb" << std::endl;
    
#ifdef USE_MICM
    static std::unique_ptr<HAPCEMM::MicmBackend> micmBackendPtr = nullptr;
    static std::mutex micm_init_mutex;
    if (Input_Opt.CHEMISTRY_SOLVER == ChemistrySolver::MICM) {
        std::lock_guard<std::mutex> lock(micm_init_mutex);
        if (!micmBackendPtr) {
            micmBackendPtr = std::make_unique<HAPCEMM::MicmBackend>(Input_Opt.MICM_MECHANISM_PATH);
        }
    }
#endif

    // --------------------------------------------------------------------------
    // GEO-ENGINEERING AEROSOL MICROPHYSICS SETUP
    // --------------------------------------------------------------------------
    const double LA_R_LOW_LOCAL = 1.00E-10;
    const double LA_R_HIG_LOCAL = 5.00E-07;
    const double LA_VRAT_LOCAL = 1.80E+00;
    const UInt SO4_NBIN = static_cast<UInt>(std::floor(1 + log(pow(LA_R_HIG_LOCAL / LA_R_LOW_LOCAL, 3.0)) / log(LA_VRAT_LOCAL)));
    std::vector<double> SO4_rJ(SO4_NBIN, 0.0);
    std::vector<double> SO4_rE(SO4_NBIN + 1, 0.0);
    std::vector<double> SO4_vJ(SO4_NBIN, 0.0);
    const double LA_RRAT = pow(LA_VRAT_LOCAL, 1.0 / 3.0);
    SO4_rE[0] = LA_R_LOW_LOCAL;
    for (UInt iBin = 1; iBin < SO4_NBIN + 1; iBin++) SO4_rE[iBin] = SO4_rE[iBin-1] * LA_RRAT;
    for (UInt iBin = 0; iBin < SO4_NBIN; iBin++) {
        SO4_rJ[iBin] = 0.5 * (SO4_rE[iBin] + SO4_rE[iBin+1]);
        SO4_vJ[iBin] = 4.0 / 3.0 * physConst::PI * SO4_rJ[iBin] * SO4_rJ[iBin] * SO4_rJ[iBin];
    }
    
    double geo_N_init = input.backgroundGeoengineeringNumber();
    double geo_R_init = input.backgroundGeoengineeringRadius();
    double geo_Rho = input.backgroundGeoengineeringRho();
    double geo_Kappa = input.backgroundGeoengineeringWettability();
    
    AIM::Aerosol geoAer(SO4_rJ, SO4_rE, std::max(geo_N_init, 1.0e-20), std::max(geo_R_init, 1.5 * LA_R_LOW_LOCAL), 1.4, "lognormal");
    const AIM::Coagulation Kernel_Geo( "liquid", SO4_rJ, physConst::RHO_SULF, geo_R_init, geo_Rho, temperature_K, pressure_Pa );
    // --------------------------------------------------------------------------

    for (size_t iTime = 0; iTime < timeArray.size(); iTime++) {
        double t = timeArray[iTime];
        for (int i = 0; i < NVAR; i++) {
            speciesHistory[i][iTime] = VAR[i];
        }

        sun.Update(t);
        cosSZASeries[iTime] = sun.CSZA;

        kpp_mutex.lock();
        for (int i = 0; i < NPHOTOL; i++) PHOTOL[i] = 0.0;
        if (sun.CSZA > 0.0) Update_JRates(PHOTOL, sun.CSZA);
        Update_RCONST(temperature_K, pressure_Pa, airDens, VAR[ind_H2O]);

        // --------------------------------------------------------------------------
        // GEO-ENGINEERING AEROSOL MICROPHYSICS (Inside loop)
        // --------------------------------------------------------------------------
        if (iTime > 0) {
            double dt_step = timeArray[iTime] - timeArray[iTime - 1];
            geoAer.Coagulate(dt_step, Kernel_Geo);
            
            double p_water_Pa = VAR[ind_H2O] / airDens * pressure_Pa; 
            double p_sat_Pa = physFunc::pSat_H2Ol(temperature_K);
            double RH_frac = std::min(p_water_Pa / std::max(p_sat_Pa, 1.0e-30), 0.999);
            double Growth_kappa = std::cbrt(1.0 + geo_Kappa * RH_frac / std::max(1.0 - RH_frac, 1.0e-3));
            
            geo_N_init = geoAer.Moment();
            geo_R_init = geoAer.Radius() * Growth_kappa; 
        }
        
        double geo_SAD_current = geo_N_init * 4.0 * physConst::PI * pow(geo_R_init * 100.0, 2.0); 
        
        geoNumberHistory[iTime] = geo_N_init;
        geoRadiusHistory[iTime] = geo_R_init;
        geoAreaHistory[iTime] = geo_SAD_current;

        if (epmCoupling.isValid) {
            double AREA[NAERO] = {epmCoupling.LA_SAD, 0, 0, 0};
            double RADI[NAERO] = {epmCoupling.MeanRadius, 0, 0, 0};
            double KHETI_SLA[11]; for(int k=0; k<11; k++) KHETI_SLA[k] = 0.1;
            
            GC_SETHET(temperature_K, pressure_Pa, airDens, 1.4, 0, VAR, AREA, RADI, epmCoupling.LA_LWC, KHETI_SLA, 20000.0, 
                      geo_SAD_current, geo_R_init, input.backgroundGeoengineeringGamma(), 0,0,0,0,geo_SAD_current,0,0,0,0,geo_R_init);
        }

//        if (iTime < timeArray.size() - 1) INTEGRATE(VAR, FIX, t, timeArray[iTime+1], ATOL, RTOL, 0.0);
//        for (int i = 0; i < NVAR; i++) speciesHistory[i][iTime] = VAR[i];
          if (iTime < timeArray.size() - 1) {
#ifdef USE_MICM
              if (Input_Opt.CHEMISTRY_SOLVER == ChemistrySolver::MICM) {
                  double dt = timeArray[iTime+1] - t;
                  micmBackendPtr->setConditions(temperature_K, pressure_Pa, airDens, PHOTOL);
                  micmBackendPtr->setCustomRateConstants(PHOTOL, RCONST, Input_Opt.MICM_USE_KPP_PHOTOL, Input_Opt.MICM_USE_KPP_HETCHEM);
                  micmBackendPtr->solve(VAR, dt);
              } else
#endif
              if (Input_Opt.CHEMISTRY_SOLVER == ChemistrySolver::TEST) {
                  JuliaBridge::Integrate(VAR, FIX, t, timeArray[iTime+1], temperature_K, pressure_Pa, airDens, 0.0);
              } else {
                   INTEGRATE(VAR, FIX, t, timeArray[iTime+1], ATOL, RTOL, 0.0);
		   // INTEGRATE(TIN, TOUT); // Assuming this was a typo
		   // for(int i=0; i<NVAR; i++) currentState[i] = VAR[i];
              }

        // Point 3: Negative Clamping
        for (int i = 0; i < NVAR; i++) {
            if (VAR[i] < 0.0) {
                VAR[i] = 0.0;
            }
        }

        }
        kpp_mutex.unlock();
        
        // Physical coupling (dilution and entrainment)

        if (Input_Opt.ENABLE_STRANG_SPLITTING && iTime < timeArray.size() - 1) {
            double dt_step = timeArray[iTime+1] - t;
            geoAer.Coagulate(dt_step / 2.0, Kernel_Geo);
        }

        // Physical coupling (dilution and entrainment)
        if (Input_Opt.ENABLE_DILUTION || Input_Opt.ENABLE_ENTRAINMENT) {
            double dt_step = timeArray[iTime+1] - t;
            double k_dil = Input_Opt.ENABLE_DILUTION ? 1.0e-5 : 0.0; // Example dilution rate
	        double k_ent = Input_Opt.ENABLE_ENTRAINMENT ? 1.0e-5 : 0.0; // Example entrainment rate
            for (int i = 0; i < NVAR; i++) {
                double VAR_amb = 0.0; // Background concentration placeholder
                VAR[i] = VAR_amb + (VAR[i] - VAR_amb) * std::exp(-(k_dil + k_ent) * dt_step);
            }
        }
        /* ---- P/L and per-reaction-rate diagnostics (after each timestep) ---- */
        {
            /* 1. Per-reaction rates A[j] [molec/cm3/s] */
            double A_now[NREACT];
#ifdef USE_MICM
            if (Input_Opt.CHEMISTRY_SOLVER == ChemistrySolver::MICM) {
                micmBackendPtr->computeRxnRates(VAR, A_now);
            } else
#endif
            {
                ComputeRxnRates(VAR, FIX, A_now, NREACT);
            }
            for (int j = 0; j < NREACT; j++)
                rxnRateHistory[static_cast<size_t>(j)][iTime] = A_now[j];

            /* 2. Net production P[i] and loss L[i] from Vdot sign split */
            double P_now[NVAR], L_now[NVAR];
#ifdef USE_MICM
            if (Input_Opt.CHEMISTRY_SOLVER == ChemistrySolver::MICM) {
                micmBackendPtr->computePL(VAR, P_now, L_now);
            } else
#endif
            {
                ComputePL(VAR, FIX, P_now, L_now, NVAR);
            }

            constexpr double L_FLOOR = 1.0e-30;  /* molec/cm3/s */
            for (int i = 0; i < NVAR; i++) {
                prodHistory[static_cast<size_t>(i)][iTime] = P_now[i];
                lossHistory[static_cast<size_t>(i)][iTime] = L_now[i];

                /* 3. Chemical lifetime tau = [X] / L  (1e30 where L negligible) */
                tauHistory[static_cast<size_t>(i)][iTime] =
                    (L_now[i] > L_FLOOR) ? std::min(VAR[i] / L_now[i], 1.0e30) : 1.0e30;

                /* 4. Cumulative integrals (trapezoidal rule) */
                if (iTime == 0) {
                    cumProdHistory[static_cast<size_t>(i)][0] = 0.0;
                    cumLossHistory[static_cast<size_t>(i)][0] = 0.0;
                } else {
                    double dT = timeArray[iTime] - timeArray[iTime - 1];
                    cumProdHistory[static_cast<size_t>(i)][iTime] =
                        cumProdHistory[static_cast<size_t>(i)][iTime-1]
                        + 0.5 * (prodHistory[static_cast<size_t>(i)][iTime-1] + P_now[i]) * dT;
                    cumLossHistory[static_cast<size_t>(i)][iTime] =
                        cumLossHistory[static_cast<size_t>(i)][iTime-1]
                        + 0.5 * (lossHistory[static_cast<size_t>(i)][iTime-1] + L_now[i]) * dT;
                }

                // Steady state lifetime
                tauSSHistory[i][iTime] = (P_now[i] > 1.0e-30) ? VAR[i] / P_now[i] : 1.0e30;

                // Dry and wet deposition sinks
                double v_d = 0.2; // dry deposition velocity [cm/s]
                double H_bl = 1.0e5; // Boundary layer/ plume thickness [cm]
                double k_dry = v_d / H_bl;
                double Lambda = 1.0e-4; // washout coefficient [s-1 / (mm/hr)]
                double rainRate = 0.0;
                double k_wet = Lambda * rainRate;
                double k_dep = k_dry + k_wet;
                tauDepHistory[i][iTime] = (k_dep > 0.0) ? 1.0 / k_dep : 1.0e30;
                depLossHistory[i][iTime] = k_dep * VAR[i];

                if (iTime < timeArray.size() - 1) {
                    double dT = timeArray[iTime+1] - timeArray[iTime];
                    VAR[i] = VAR[i] * std::exp(-k_dep * dT);
                }

                // Cumulative deposited mass [g/m2]
                std::string specName = "";
                if (SPC_NAMES[i] != nullptr) specName = SPC_NAMES[i];
                double MW_species = getMolecularWeight(specName);

                double factor = H_bl * (MW_species / physConst::Na) * 1.0e6; // conversion factor
                if (iTime == 0) {
                    cumDepMassHistory[i][0] = 0.0;
                } else {
                    double dT = timeArray[iTime] - timeArray[iTime - 1];
                    cumDepMassHistory[i][iTime] = cumDepMassHistory[i][iTime-1] + 0.5 * (depLossHistory[i][iTime-1] + depLossHistory[i][iTime]) * dT * factor;
                }
            }

            // Save reaction and photolysis rates (outside the species loop)
            for (int j = 0; j < NPHOTOL; j++) {
                jRatesHistory[j][iTime] = PHOTOL[j];
            }
            for (int k = 0; k < NREACT; k++) {
                rconstHistory[k][iTime] = RCONST[k];
            }

            // Viscosity and Mean Free Path of Air
            viscosityHistory[iTime] = 1.458e-6 * std::pow(temperature_K, 1.5) / (temperature_K + 110.4);
            meanFreePathHistory[iTime] = (physConst::kB * temperature_K) / (std::sqrt(2.0) * physConst::PI * std::pow(3.7e-10, 2) * pressure_Pa);

            // Ozone production Efficiency
            double net_O3_prod = P_now[ind_O3] - L_now[ind_O3];
            double NOx_net_loss = L_now[ind_NO] + L_now[ind_NO2] - P_now[ind_NO] - P_now[ind_NO2];
            opeHistory[iTime] = (NOx_net_loss > 1.0e-30) ? net_O3_prod / NOx_net_loss : 0.0;

            // Radical budget (ROx in ppb)
            double rox_sum = VAR[ind_OH] + VAR[ind_HO2];
            if (box_ind_MO2 >= 0) rox_sum += VAR[box_ind_MO2];
            if (box_ind_ETO2 >= 0) rox_sum += VAR[box_ind_ETO2];
            roxHistory[iTime] = rox_sum / airDens * 1.0e9;

            // Physical and grid metrics
            tempHistory[iTime] = temperature_K;
            pressHistory[iTime] = pressure_Pa;
            rhiHistory[iTime] = input.relHumidity_i();
            h2oHistory[iTime] = VAR[ind_H2O];
            if (epmCoupling.isValid) {
                plumeAreaHistory[iTime] = epmCoupling.LA_SAD;
                iceMassHistory[iTime]   = epmCoupling.LA_LWC;
                effRadiusHistory[iTime] = epmCoupling.MeanRadius;
            }
        }
    }

    std::vector<std::vector<double>> tauBurdenHistory(NVAR, std::vector<double>(nTimeSteps, 0.0));
    for (int i = 0; i < NVAR; i++) {
        for (size_t t = 0; t < nTimeSteps; t++) {
            double molecules = speciesHistory[i][t];
            double loss_rate = lossHistory[i][t];
            tauBurdenHistory[i][t] = (loss_rate > 1.0e-30) ? molecules / loss_rate : 1.0e30;
        }
    }

    std::string outFile = input.fileName_BOX();
    size_t pos = outFile.find("*");
    if (pos != std::string::npos) outFile.replace(pos, 1, std::to_string(jCase));
    if (outFile.find(".nc") == std::string::npos) outFile += ".nc";

    writeBoxModelOutput(outFile, Input_Opt.BOX_OUTPUT_VARIABLES, timeArray, speciesHistory,
                        prodHistory, lossHistory, tauHistory,
                        cumProdHistory, cumLossHistory, rxnRateHistory,
                        cosSZASeries, airDens, 1.4, NVAR,
                        tempHistory, pressHistory, altitudeHistory, rhiHistory, h2oHistory,
                        iceNumberHistory, iceAreaHistory, iceVolumeHistory, effRadiusHistory,
                        xODHistory, yODHistory, iceMassHistory, numberIceParticlesHistory,
                        extinctionHistory, iwcHistory, widthHistory, depthHistory, intODHistory,
                        geoNumberHistory, geoAreaHistory, geoRadiusHistory, plumeAreaHistory,
                        dxHistory, dyHistory, binCenters, binEdges, psdHistory,
                        tauSSHistory, jRatesHistory, rconstHistory, viscosityHistory,
                        meanFreePathHistory, tauDepHistory, depLossHistory, cumDepMassHistory,
                        opeHistory, roxHistory);

    g_finalSpecies.isValid = true;
    g_finalSpecies.NO = VAR[ind_NO] / airDens * 1e9;
    g_finalSpecies.NO2 = VAR[ind_NO2] / airDens * 1e9;
    g_finalSpecies.O3 = VAR[ind_O3] / airDens * 1e9;
    g_finalSpecies.CO = VAR[ind_CO] / airDens * 1e9;
    g_finalSpecies.CH4 = VAR[ind_CH4] / airDens * 1e9;
    g_finalSpecies.SO2 = VAR[ind_SO2] / airDens * 1e9;
    g_finalSpecies.HNO3 = VAR[ind_HNO3] / airDens * 1e9;
    g_finalSpecies.H2O = VAR[ind_H2O] / airDens * 1e9;
    g_finalSpecies.H2 = VAR[ind_H2] / airDens * 1e9;
    g_finalSpecies.NH3 = (box_ind_NH3 >= 0) ? VAR[box_ind_NH3] / airDens * 1e9 : 0.0;
    g_finalSpecies.N2O = (box_ind_N2O >= 0) ? VAR[box_ind_N2O] / airDens * 1e9 : 0.0;
    g_finalSpecies.Lub = (box_ind_LUB >= 0) ? VAR[box_ind_LUB] / airDens * 1e9 : 0.0;
    g_finalSpecies.Custom = (ind_Custom >= 0 && VAR[ind_Custom] >= 0) ? VAR[ind_Custom] / airDens * 1e9 : 0.0;
    return 0;
}

} // namespace BoxModel
