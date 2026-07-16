#ifndef JULIA_BRIDGE_HPP_INCLUDED
#define JULIA_BRIDGE_HPP_INCLUDED

#include <vector>
#include "Util/ForwardDecl.hpp"

namespace JuliaBridge {
    bool SpinUp(std::vector<double>& varSpecies, double airDens, double temp, double press, double duration);
    bool Integrate(double* varSpecies, double* fixSpecies, double tStart, double tEnd, double temp, double press, double airDens, double iceArea);

    bool IntegrateMicm(double* varSpecies, double* fixSpecies,
                       double* micmRCONST, double tStart, double tEnd,
                       double temp, double press, double airDens);
    bool RunAdjoint(const double* varSpecies, const double* fixSpecies,
                    const double* rconst, double tStart, double tEnd,
                    double temp, double press, double airDens,
                    int mode, int targetIdx, double* dJ_dVar, double* dJ_dRconst);
}

#endif
