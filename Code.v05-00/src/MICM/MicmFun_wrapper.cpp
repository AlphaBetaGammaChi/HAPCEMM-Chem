#ifdef USE_MICM
#include "MICM/MicmBackend.hpp"
#include <cstring>
#include <iostream>
static HAPCEMM::MicmBackend* g_micm = nullptr;
extern "C" {
void MicmBackend_init(const char* path) {
    delete g_micm;
    g_micm = new HAPCEMM::MicmBackend(std::string(path));
}
void MicmFun_wrapper(const double* V, const double* RCONST,
                     int nVar, int nReact, double* Vdot) {
    if (!g_micm) { std::memset(Vdot,0,sizeof(double)*static_cast<std::size_t>(nVar)); return; }
    g_micm->computeVdot(V, Vdot, nVar); (void)RCONST; (void)nReact;
}
void MicmJac_wrapper(const double* V, const double* RCONST, int nVar, double* J) {
    if (!g_micm) { std::memset(J,0,sizeof(double)*static_cast<std::size_t>(nVar)*static_cast<std::size_t>(nVar)); return; }
    g_micm->computeJacobian(V, J, nVar); (void)RCONST;
}
} // extern C
#endif // USE_MICM
