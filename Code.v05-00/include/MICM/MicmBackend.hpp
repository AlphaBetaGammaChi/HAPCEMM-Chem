#pragma once
#ifdef USE_MICM
#include <string>
#include <vector>
#include <memory>
namespace HAPCEMM {
class MicmBackend {
public:
    explicit MicmBackend(const std::string& mechanismPath);
    ~MicmBackend();
    MicmBackend(const MicmBackend&) = delete;
    MicmBackend& operator=(const MicmBackend&) = delete;
    void setConditions(double temperature_K, double pressure_Pa,
                       double airDens_cm3, const double* photolRates);
    void setConcentrations(const double* VAR, int nVar) const;
    void getRateConstants(double* RCONST_out, int nReact) const;
    void computeVdot(const double* VAR, double* Vdot, int nVar) const;
    void computeJacobian(const double* VAR, double* J, int nVar) const;
    void solve(double* VAR, double dt);
    int nVar() const;
    int nReact() const;
    int micmToHapcemmIndex(int micmIdx) const;
    int hapcemmToMicmIndex(int hapcemmIdx) const;
    void setCustomRateConstants(const double* PHOTOL, const double* RCONST, bool usePhotol, bool useHetchem);
    void computePL(const double* VAR, double* P_out, double* L_out) const;
    void computeRxnRates(const double* VAR, double* A_out) const;
private:
    struct Impl;
    mutable std::unique_ptr<Impl> impl_;
};
} // namespace HAPCEMM
#endif // USE_MICM
