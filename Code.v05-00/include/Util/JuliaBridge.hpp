#ifndef JULIA_BRIDGE_HPP_INCLUDED
#define JULIA_BRIDGE_HPP_INCLUDED

#include <vector>
#include "Util/ForwardDecl.hpp"

namespace JuliaBridge {
    bool SpinUp(std::vector<double>& varSpecies, double airDens, double temp, double press, double duration);
    bool Integrate(double* varSpecies, double* fixSpecies, double tStart, double tEnd, double temp, double press, double airDens);
}

#endif
