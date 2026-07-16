#!/usr/bin/env python3
"""
Plan C: HAPCEMM MICM + Adjoint — input/config layer + Julia files
Run on the Isambard cluster:
  python3 implement_plan_c_micm.py
"""
import re, sys, os

ROOT = "/projects/b35as/public/HAPCEMM-Chem/Code.v05-00"

def read(path):
    with open(path, 'r') as f:
        return f.read()

def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)
    print(f"  [WROTE] {path}")

def done(msg): print(f"  [DONE ] {msg}")
def skip(msg): print(f"  [SKIP ] {msg}")
def warn(msg): print(f"  [WARN ] {msg}", file=sys.stderr)

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== C1: defaults/input.yaml — CHEMISTRY SOLVER SUBMENU ===")
p = f"{ROOT}/defaults/input.yaml"
c = read(p)
if 'CHEMISTRY SOLVER SUBMENU' not in c:
    submenu = """
  CHEMISTRY SOLVER SUBMENU:
    # kpp  = KPP-generated C++ solver (default, existing behaviour — no extra deps)
    # micm = NCAR MUSICA/MICM solver via Julia/Rodas5 bridge (requires -DUSE_MICM=ON cmake)
    Chemistry solver (string): kpp
    # Path to MICM mechanism JSON directory (used only when solver = micm)
    # Directory must contain: config.json, species.json, reactions.json
    MICM mechanism path (string): ./mechanism/
    ADJOINT SUBMENU:
      # Enable Enzyme.jl reverse-mode adjoint sensitivity analysis
      Enable adjoint (T/F): F
      # Adjoint mode: species (dJ/d[X] one species), parameter (dJ/dk one rate), all (dJ all)
      Adjoint mode (string): all
      # Name of target species or rate constant when mode = species or parameter
      Adjoint target name (string): O3
"""
    # Insert into SIMULATION MENU — find a reliable anchor
    # Try after "External EPM NetCDF file" or after "EPM type" line
    anchors = [
        r'(External EPM NetCDF file[^\n]*\n)',
        r'(EPM type[^\n]*\n)',
        r'(Random number[^\n]*\n)',
        r'(SIMULATION MENU[^\n]*\n)',
    ]
    inserted = False
    for pat in anchors:
        m = re.search(pat, c, re.IGNORECASE)
        if m:
            c = c[:m.end()] + submenu + c[m.end():]
            inserted = True
            done(f"CHEMISTRY SOLVER SUBMENU inserted after '{m.group().strip()[:50]}'")
            break
    if not inserted:
        c = c.rstrip() + '\n' + submenu + '\n'
        done("CHEMISTRY SOLVER SUBMENU appended (no anchor found)")
    write(p, c)
else:
    skip("CHEMISTRY SOLVER SUBMENU already present")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== C2: include/Core/Input_Mod.hpp — add 5 new fields ===")
p = f"{ROOT}/include/Core/Input_Mod.hpp"
c = read(p)
if 'CHEMISTRY_SOLVER' not in c:
    new_fields = """    /* Chemistry solver selection */
    std::string CHEMISTRY_SOLVER;          /*!< "kpp" or "micm" */
    std::string MICM_MECHANISM_PATH;       /*!< Path to MICM JSON mechanism directory */

    /* Enzyme.jl adjoint sensitivity settings */
    bool        ADJOINT_ENABLE;            /*!< Enable Enzyme reverse-mode adjoint pass */
    std::string ADJOINT_MODE;              /*!< "species", "parameter", or "all" */
    std::string ADJOINT_TARGET_NAME;       /*!< Target species/rate name for non-all modes */

"""
    # Insert before ADV_USE_JULIA_CHEMISTRY if it exists, else before struct closing
    if 'ADV_USE_JULIA_CHEMISTRY' in c:
        c = c.replace('bool ADV_USE_JULIA_CHEMISTRY;',
                      new_fields + '    bool ADV_USE_JULIA_CHEMISTRY;', 1)
        done("Fields inserted before ADV_USE_JULIA_CHEMISTRY")
    else:
        # Insert before the last }; of the struct
        idx = c.rfind('};')
        if idx >= 0:
            c = c[:idx] + '\n' + new_fields + c[idx:]
            done("Fields inserted before closing }; of struct")
        else:
            c = c.rstrip() + '\n' + new_fields + '\n'
            warn("Appended fields — could not find struct closing")
    write(p, c)
else:
    skip("CHEMISTRY_SOLVER already in Input_Mod.hpp")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== C3: src/YamlInputReader/YamlInputReader.cpp — parse solver + adjoint fields ===")
p = f"{ROOT}/src/YamlInputReader/YamlInputReader.cpp"
c = read(p)
if 'CHEMISTRY_SOLVER' not in c:
    parse_block = """
        /* ---- Chemistry solver + Enzyme adjoint settings ---- */
        {
            YAML::Node chemNode = simNode["CHEMISTRY SOLVER SUBMENU"];
            if (chemNode) {
                input.CHEMISTRY_SOLVER = chemNode["Chemistry solver (string)"]
                    ? chemNode["Chemistry solver (string)"].as<std::string>() : "kpp";
                input.MICM_MECHANISM_PATH = chemNode["MICM mechanism path (string)"]
                    ? chemNode["MICM mechanism path (string)"].as<std::string>() : "./mechanism/";
                YAML::Node adjNode = chemNode["ADJOINT SUBMENU"];
                if (adjNode) {
                    input.ADJOINT_ENABLE = parseBoolString(
                        adjNode["Enable adjoint (T/F)"]
                            ? adjNode["Enable adjoint (T/F)"].as<std::string>() : "F",
                        "Enable adjoint");
                    input.ADJOINT_MODE = adjNode["Adjoint mode (string)"]
                        ? adjNode["Adjoint mode (string)"].as<std::string>() : "all";
                    input.ADJOINT_TARGET_NAME = adjNode["Adjoint target name (string)"]
                        ? adjNode["Adjoint target name (string)"].as<std::string>() : "";
                } else {
                    input.ADJOINT_ENABLE      = false;
                    input.ADJOINT_MODE        = "all";
                    input.ADJOINT_TARGET_NAME = "";
                }
            } else {
                input.CHEMISTRY_SOLVER    = "kpp";
                input.MICM_MECHANISM_PATH = "./mechanism/";
                input.ADJOINT_ENABLE      = false;
                input.ADJOINT_MODE        = "all";
                input.ADJOINT_TARGET_NAME = "";
            }
        }
"""
    # Insert before the random number submenu or before function closing
    anchors = [
        r'(YAML::Node\s+rngNode\s*=)',
        r'(if\s*\(\s*simNode\s*\[\s*"RANDOM NUMBER',
        r'(//\s*--- end of readSimMenu)',
    ]
    inserted = False
    for pat in anchors:
        m = re.search(pat, c, re.IGNORECASE)
        if m:
            c = c[:m.start()] + parse_block + c[m.start():]
            inserted = True
            done(f"CHEMISTRY_SOLVER parse block inserted before '{c[m.start():m.start()+40].strip()}'")
            break
    if not inserted:
        # Append default assignments and warn
        defaults = """        /* Chemistry solver defaults */
        input.CHEMISTRY_SOLVER    = "kpp";
        input.MICM_MECHANISM_PATH = "./mechanism/";
        input.ADJOINT_ENABLE      = false;
        input.ADJOINT_MODE        = "all";
        input.ADJOINT_TARGET_NAME = "";
"""
        if 'ADV_USE_JULIA_CHEMISTRY' in c:
            c = c.replace(
                'input.ADV_USE_JULIA_CHEMISTRY = false;',
                'input.ADV_USE_JULIA_CHEMISTRY = false;\n' + defaults, 1
            )
            done("CHEMISTRY_SOLVER defaults added near ADV_USE_JULIA_CHEMISTRY")
        else:
            c = c.rstrip() + '\n' + parse_block + '\n'
            warn("Could not find anchor; appended parse block")

    write(p, c)
else:
    skip("CHEMISTRY_SOLVER already in YamlInputReader.cpp")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== C4: include/MICM/MicmBackend.hpp [NEW] ===")
p = f"{ROOT}/include/MICM/MicmBackend.hpp"
if not os.path.exists(p):
    write(p, r"""#pragma once
// HAPCEMM MICM Backend Wrapper
// Wraps NCAR MICM (https://github.com/NCAR/micm) chemistry solver.
// This header is only meaningful when compiled with -DUSE_MICM=ON.
// Without USE_MICM the BoxModel will use the KPP backend (existing behaviour).
#ifdef USE_MICM

#include <string>
#include <vector>
#include <memory>

namespace HAPCEMM {

/// Opaque wrapper around a MICM solver instance.
/// Translates between MICM's internal state representation and HAPCEMM's
/// flat double[] arrays (VAR[], FIX[], RCONST[]).
class MicmBackend {
public:
    /// Load mechanism from a MICM JSON mechanism directory.
    /// Directory must contain: config.json, species.json, reactions.json
    /// @param mechanismPath Absolute or relative path to the mechanism directory
    explicit MicmBackend(const std::string& mechanismPath);
    ~MicmBackend();

    MicmBackend(const MicmBackend&) = delete;
    MicmBackend& operator=(const MicmBackend&) = delete;

    /// Set atmospheric conditions before computing rate constants.
    /// @param temperature_K   Air temperature [K]
    /// @param pressure_Pa     Air pressure [Pa]
    /// @param airDens_cm3     Air number density [molec cm-3]
    /// @param photolRates     Photolysis J-values array (length NPHOTOL; may be nullptr)
    void setConditions(double temperature_K, double pressure_Pa,
                       double airDens_cm3, const double* photolRates);

    /// Copy HAPCEMM's VAR[] concentrations into the MICM state object.
    /// Uses the internal index mapping (hapcemm->micm) built at construction.
    void setConcentrations(const double* VAR, int nVar);

    /// Evaluate rate constants for the current conditions and copy to RCONST_out.
    /// @param RCONST_out  Output array [molec cm-3 s-1], length nReact
    /// @param nReact      Expected length
    void getRateConstants(double* RCONST_out, int nReact) const;

    /// Compute net chemical tendencies Vdot[i] = dVAR[i]/dt [molec cm-3 s-1].
    void computeVdot(const double* VAR, double* Vdot, int nVar) const;

    /// Compute Jacobian dVdot/dVAR [nVar x nVar row-major].
    /// Used by the Enzyme custom pullback rule in adjoint_module.jl.
    void computeJacobian(const double* VAR, double* J, int nVar) const;

    int nVar()   const; ///< Number of variable species in MICM mechanism
    int nReact() const; ///< Number of reactions in MICM mechanism

    /// MICM species index -> HAPCEMM ind_*. Returns -1 if no mapping.
    int micmToHapcemmIndex(int micmIdx) const;
    /// HAPCEMM ind_* -> MICM species index. Returns -1 if not found.
    int hapcemmToMicmIndex(int hapcemmIdx) const;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace HAPCEMM

#endif // USE_MICM
""")
    done("include/MICM/MicmBackend.hpp created")
else:
    skip("MicmBackend.hpp already exists")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== C5: src/MICM/MicmBackend.cpp [NEW] ===")
p = f"{ROOT}/src/MICM/MicmBackend.cpp"
if not os.path.exists(p):
    write(p, r"""// HAPCEMM MicmBackend implementation
// Only compiled with cmake -DUSE_MICM=ON (MICM library must be installed).
// Stub implementation: all compute functions return zeros until MICM is
// fully wired. This allows the codebase to compile and the KPP path to
// remain unaffected.
#ifdef USE_MICM

#include "MICM/MicmBackend.hpp"

// MICM C++ headers — available when micm is installed (spack install micm)
#include <micm/configure/solver_config.hpp>
#include <micm/solver/cpu_solver_builder.hpp>
#include <micm/solver/rosenbrock.hpp>

#include <iostream>
#include <stdexcept>
#include <map>
#include <cstring>

namespace HAPCEMM {

struct MicmBackend::Impl {
    micm::SolverConfig config;
    std::map<std::string, std::size_t> variable_map;
    std::size_t n_species  = 0;
    std::size_t n_reactions = 0;
    std::vector<int> micm_to_hapcemm;
    std::vector<int> hapcemm_to_micm;
    double temperature_K = 273.15;
    double pressure_Pa   = 101325.0;
    double air_density   = 2.55e19;

    explicit Impl(const std::string& mechanismPath) {
        // Load the mechanism JSON from directory
        // config.ReadAndParse populates species/reaction lists
        config.ReadAndParse(mechanismPath);

        // After loading, query the solver params for species and reaction counts
        // (exact API depends on MICM version — adjust if needed)
        auto solver_params = config.GetSolverParams();
        n_species   = solver_params.system_.gas_phase_.species_.size();
        n_reactions = solver_params.processes_.size();

        // Build variable_map from species list
        for (std::size_t i = 0; i < solver_params.system_.gas_phase_.species_.size(); ++i)
            variable_map[solver_params.system_.gas_phase_.species_[i].name_] = i;

        // TODO: Build micm_to_hapcemm index mapping by matching MICM species
        // names against KPP's SPC_NAMES[] array (from KPP_Monitor.h).
        // For now initialise as identity mapping (will be wrong for most species).
        micm_to_hapcemm.resize(n_species, -1);
        hapcemm_to_micm.assign(200, -1);  // HAPCEMM NVAR ~ 150-200

        std::cout << "[MicmBackend] Loaded mechanism: " << mechanismPath
                  << "  species=" << n_species
                  << "  reactions=" << n_reactions << std::endl;
    }
};

MicmBackend::MicmBackend(const std::string& mechanismPath)
    : impl_(std::make_unique<Impl>(mechanismPath)) {}

MicmBackend::~MicmBackend() = default;

void MicmBackend::setConditions(double temperature_K, double pressure_Pa,
                                 double airDens_cm3, const double* /*photolRates*/) {
    impl_->temperature_K = temperature_K;
    impl_->pressure_Pa   = pressure_Pa;
    impl_->air_density   = airDens_cm3;
    // TODO: set photolysis rates in MICM state via custom rate parameters
}

void MicmBackend::setConcentrations(const double* VAR, int nVar) {
    // TODO: copy VAR[hapcemm_idx] -> MICM state.variables_[0][micm_idx]
    (void)VAR; (void)nVar;
}

void MicmBackend::getRateConstants(double* RCONST_out, int nReact) const {
    // TODO: call solver.CalculateRateConstants(state) and copy flat array out
    // Stub: return zeros to allow compilation testing
    std::memset(RCONST_out, 0, sizeof(double) * static_cast<std::size_t>(nReact));
}

void MicmBackend::computeVdot(const double* VAR, double* Vdot, int nVar) const {
    // TODO: set concentrations in MICM state, call Solve in rate-only mode, extract Vdot
    (void)VAR;
    std::memset(Vdot, 0, sizeof(double) * static_cast<std::size_t>(nVar));
}

void MicmBackend::computeJacobian(const double* VAR, double* J, int nVar) const {
    // TODO: extract full Jacobian from MICM for Enzyme pullback rule
    (void)VAR;
    std::memset(J, 0, sizeof(double) * static_cast<std::size_t>(nVar) * static_cast<std::size_t>(nVar));
}

int MicmBackend::nVar()   const { return static_cast<int>(impl_->n_species);   }
int MicmBackend::nReact() const { return static_cast<int>(impl_->n_reactions); }

int MicmBackend::micmToHapcemmIndex(int micmIdx) const {
    if (micmIdx < 0 || static_cast<std::size_t>(micmIdx) >= impl_->micm_to_hapcemm.size())
        return -1;
    return impl_->micm_to_hapcemm[static_cast<std::size_t>(micmIdx)];
}

int MicmBackend::hapcemmToMicmIndex(int hapcemmIdx) const {
    if (hapcemmIdx < 0 || static_cast<std::size_t>(hapcemmIdx) >= impl_->hapcemm_to_micm.size())
        return -1;
    return impl_->hapcemm_to_micm[static_cast<std::size_t>(hapcemmIdx)];
}

} // namespace HAPCEMM

#endif // USE_MICM
""")
    done("src/MICM/MicmBackend.cpp created")
else:
    skip("MicmBackend.cpp already exists")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== C6: src/MICM/MicmFun_wrapper.cpp [NEW] ===")
p = f"{ROOT}/src/MICM/MicmFun_wrapper.cpp"
if not os.path.exists(p):
    write(p, r"""// C-linkage wrappers exposing MICM RHS and Jacobian to Julia's ccall.
// These functions are called from julia/hapcemm_chemistry.jl and
// julia/adjoint_module.jl via: ccall((:MicmFun_wrapper, "libhapcemm.so"), ...)
// Only compiled when USE_MICM=ON.
#ifdef USE_MICM

#include "MICM/MicmBackend.hpp"
#include <cstring>
#include <iostream>

// Global MICM backend instance — initialised once by BoxModel before the time loop.
static HAPCEMM::MicmBackend* g_micm_backend = nullptr;

extern "C" {

/// Initialise the global MICM backend from a mechanism directory path.
/// Must be called once before MicmFun_wrapper or MicmJac_wrapper.
void MicmBackend_init(const char* mechanismPath) {
    delete g_micm_backend;
    g_micm_backend = new HAPCEMM::MicmBackend(std::string(mechanismPath));
    std::cout << "[MicmFun_wrapper] Backend initialised." << std::endl;
}

/// MICM RHS: compute Vdot = d(VAR)/dt for the current chemical state.
/// Called from julia/hapcemm_chemistry.jl via:
///   ccall((:MicmFun_wrapper, "libhapcemm.so"), Cvoid,
///         (Ptr{Cdouble}, Ptr{Cdouble}, Cint, Cint, Ptr{Cdouble}),
///         V, RCONST, nVar, nReact, Vdot)
/// @param V       Variable species concentrations [molec cm-3], length nVar
/// @param RCONST  Pre-computed rate constants, length nReact
/// @param nVar    Length of V and Vdot
/// @param nReact  Length of RCONST (unused in this stub — use MicmBackend internally)
/// @param Vdot    Output net tendency [molec cm-3 s-1], length nVar
void MicmFun_wrapper(const double* V, const double* RCONST,
                     int nVar, int nReact, double* Vdot) {
    if (!g_micm_backend) {
        std::memset(Vdot, 0, sizeof(double) * static_cast<std::size_t>(nVar));
        return;
    }
    // TODO: Use RCONST + V to compute Vdot via MICM stoichiometry matrix.
    // For now delegate to the stub computeVdot.
    g_micm_backend->computeVdot(V, Vdot, nVar);
    (void)RCONST; (void)nReact;
}

/// MICM Jacobian: compute dVdot/dV for the Enzyme custom pullback rule.
/// Called from julia/adjoint_module.jl via:
///   ccall((:MicmJac_wrapper, "libhapcemm.so"), Cvoid,
///         (Ptr{Cdouble}, Ptr{Cdouble}, Cint, Ptr{Cdouble}),
///         V, RCONST, nVar, J)
/// @param V      Variable species [molec cm-3], length nVar
/// @param RCONST Rate constants, length nReact
/// @param nVar   Length of V; J has shape [nVar x nVar] row-major
/// @param J      Output Jacobian [nVar x nVar]
void MicmJac_wrapper(const double* V, const double* RCONST,
                     int nVar, double* J) {
    if (!g_micm_backend) {
        std::memset(J, 0, sizeof(double)
                    * static_cast<std::size_t>(nVar) * static_cast<std::size_t>(nVar));
        return;
    }
    g_micm_backend->computeJacobian(V, J, nVar);
    (void)RCONST;
}

} // extern "C"
#endif // USE_MICM
""")
    done("src/MICM/MicmFun_wrapper.cpp created")
else:
    skip("MicmFun_wrapper.cpp already exists")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== C7: src/Core/BoxModel.cpp — MICM solver branch (guarded #ifdef) ===")
p = f"{ROOT}/src/Core/BoxModel.cpp"
c = read(p)

# Add includes
if 'MicmBackend.hpp' not in c:
    c = re.sub(
        r'(#include\s+"Util/JuliaBridge\.hpp")',
        r'\1\n#ifdef USE_MICM\n#include "MICM/MicmBackend.hpp"\n#endif',
        c, count=1
    )
    done("C7a: #include MicmBackend.hpp added (guarded)")
else:
    skip("C7a: MicmBackend.hpp already included")

# Add MICM backend instantiation before the time loop
if 'micmBackendPtr' not in c:
    micm_init = """
#ifdef USE_MICM
    std::unique_ptr<HAPCEMM::MicmBackend> micmBackendPtr;
    if (Input_Opt.CHEMISTRY_SOLVER == "micm") {
        std::cout << "[BoxModel] Initialising MICM backend: "
                  << Input_Opt.MICM_MECHANISM_PATH << std::endl;
        micmBackendPtr = std::make_unique<HAPCEMM::MicmBackend>(
                            Input_Opt.MICM_MECHANISM_PATH);
    }
#endif /* USE_MICM */
"""
    # Insert before the time loop
    c, n = re.subn(
        r'(for\s*\(\s*(?:size_t|int|unsigned\s+int)\s+iTime\s*=\s*0)',
        micm_init + r'    \1',
        c, count=1
    )
    if n: done("C7b: MICM backend instantiation added before time loop")
    else: warn("C7b: Could not find time loop for MICM init insertion")
else:
    skip("C7b: micmBackendPtr already present")

# Add MICM solver branch inside the time loop
if 'CHEMISTRY_SOLVER' not in c:
    micm_branch = r"""#ifdef USE_MICM
                if (Input_Opt.CHEMISTRY_SOLVER == "micm" && micmBackendPtr) {
                    /* MICM path: compute rate constants then call Julia/Rodas5 */
                    if (iTime < timeArray.size() - 1) {
                        micmBackendPtr->setConditions(
                            temperature_K, pressure_Pa, airDens, PHOTOL);
                        std::vector<double> micmRCONST(
                            static_cast<size_t>(micmBackendPtr->nReact()));
                        micmBackendPtr->getRateConstants(
                            micmRCONST.data(), micmBackendPtr->nReact());
                        JuliaBridge::IntegrateMicm(
                            VAR, FIX, micmRCONST.data(),
                            t, timeArray[iTime+1],
                            temperature_K, pressure_Pa, airDens);
                    }
                } else
#endif /* USE_MICM */
                """
    c, n = re.subn(
        r'(if\s*\(\s*iTime\s*<\s*timeArray\.size\(\)\s*-\s*1\s*\)\s*INTEGRATE)',
        micm_branch + r'if (iTime < timeArray.size() - 1) INTEGRATE',
        c, count=1
    )
    if n: done("C7c: MICM solver branch added before INTEGRATE call")
    else: warn("C7c: Could not find INTEGRATE call for MICM branch insertion")
else:
    skip("C7c: CHEMISTRY_SOLVER branch already in BoxModel.cpp")

write(p, c)

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== C8: include/Util/JuliaBridge.hpp — add IntegrateMicm + RunAdjoint ===")
p = f"{ROOT}/include/Util/JuliaBridge.hpp"
c = read(p)
if 'IntegrateMicm' not in c:
    new_decls = """
    // ── MICM backend integration via Julia/Rodas5 ──────────────────────────
    // Integrates one chemistry timestep using the MICM RHS callback.
    // micmRCONST: rate constants pre-computed by MicmBackend::getRateConstants().
    bool IntegrateMicm(double* varSpecies, double* fixSpecies,
                       double* micmRCONST,
                       double tStart, double tEnd,
                       double temp, double press, double airDens);

    // ── Enzyme adjoint sensitivity pass ────────────────────────────────────
    // Runs Enzyme.jl reverse-mode AD over the chemistry ODE and returns
    // dJ/d(varSpecies) and dJ/d(rconst) in the output arrays.
    // mode: 0=single species, 1=single rate constant, 2=all species+parameters
    // targetIdx: ind_* or reaction index (ignored when mode=2)
    bool RunAdjoint(const double* varSpecies, const double* fixSpecies,
                    const double* rconst,
                    double tStart, double tEnd,
                    double temp, double press, double airDens,
                    int mode, int targetIdx,
                    double* dJ_dVar, double* dJ_dRconst);
"""
    for close in ['} // namespace JuliaBridge', '} /* namespace JuliaBridge */', '}  // namespace']:
        if close in c:
            c = c.replace(close, new_decls + '\n' + close, 1)
            done("IntegrateMicm + RunAdjoint declared in JuliaBridge.hpp")
            break
    else:
        idx = c.rfind('}')
        c = c[:idx] + new_decls + c[idx:]
        done("Declarations inserted before last } in JuliaBridge.hpp")
    write(p, c)
else:
    skip("IntegrateMicm already declared in JuliaBridge.hpp")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== C9: src/Util/JuliaBridge.cpp — add MICM + adjoint stubs ===")
p = f"{ROOT}/src/Util/JuliaBridge.cpp"
c = read(p)
if 'IntegrateMicm' not in c:
    stubs = r"""

bool JuliaBridge::IntegrateMicm(double* varSpecies, double* /*fixSpecies*/,
                                 double* /*micmRCONST*/,
                                 double tStart, double tEnd,
                                 double /*temp*/, double /*press*/, double /*airDens*/) {
    // TODO: Call julia/hapcemm_chemistry.jl -> HapcemmChemistry.run_chemistry_step
    // with backend = :micm and p.RCONST = micmRCONST, write result back into varSpecies.
    // Requires jl_init() at program start and jl_call() wrappers.
    std::cout << " [JuliaBridge::IntegrateMicm] stub called  t=" << tStart
              << " -> " << tEnd << " s" << std::endl;
    (void)varSpecies;
    return true;
}

bool JuliaBridge::RunAdjoint(const double* /*varSpecies*/, const double* /*fixSpecies*/,
                              const double* /*rconst*/,
                              double tStart, double tEnd,
                              double /*temp*/, double /*press*/, double /*airDens*/,
                              int mode, int targetIdx,
                              double* dJ_dVar, double* dJ_dRconst) {
    // TODO: Call julia/adjoint_module.jl -> HapcemmAdjoint.run_adjoint_pass
    // Returns dJ/d[X] (dJ_dVar) and dJ/dRCONST (dJ_dRconst) via Enzyme reverse mode.
    std::cout << " [JuliaBridge::RunAdjoint] stub called  mode=" << mode
              << "  target=" << targetIdx
              << "  t=" << tStart << " -> " << tEnd << " s" << std::endl;
    (void)dJ_dVar; (void)dJ_dRconst;
    return true;
}
"""
    c = c.rstrip() + stubs + '\n'
    write(p, c)
    done("IntegrateMicm + RunAdjoint stubs added to JuliaBridge.cpp")
else:
    skip("IntegrateMicm already in JuliaBridge.cpp")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== C10: julia/hapcemm_chemistry.jl [NEW] ===")
julia_dir = f"{ROOT}/julia"
os.makedirs(julia_dir, exist_ok=True)

p = f"{julia_dir}/hapcemm_chemistry.jl"
if not os.path.exists(p):
    write(p, r'''"""
    HapcemmChemistry

Pure-math ODE RHS module for HAPCEMM chemistry integration via Julia/Rodas5.
Supports two backends: :kpp (KPP-generated C++) and :micm (NCAR MICM).

DESIGN RULE: This module contains NO I/O, NO file writes, NO print statements
inside any function that Enzyme will differentiate. All logging is in output.jl.
"""
module HapcemmChemistry

using OrdinaryDiffEq

# =============================================================================
# BACKEND 1: KPP RHS
# Fun() is exported as a C symbol from libhapcemm.so by KPP_Function.cpp.
# Signature: void Fun(double* V, double* F, double* RCT, double* Vdot)
# =============================================================================
function kpp_rhs!(du::Vector{Float64}, u::Vector{Float64}, p, t::Float64)
    # p.RCONST is updated by C++ before each Rodas step and passed in p
    ccall((:Fun_wrapper, "libhapcemm.so"), Cvoid,
          (Ptr{Cdouble}, Ptr{Cdouble}, Ptr{Cdouble}, Ptr{Cdouble}),
          u, p.FIX, p.RCONST, du)
    return nothing
end

# Analytic Jacobian for KPP (used by Enzyme pullback rule + Rodas stiffness detection)
function kpp_jac!(J::Matrix{Float64}, u::Vector{Float64}, p, t::Float64)
    ccall((:Jac_wrapper, "libhapcemm.so"), Cvoid,
          (Ptr{Cdouble}, Ptr{Cdouble}, Ptr{Cdouble}, Ptr{Cdouble}),
          u, p.FIX, p.RCONST, J)
    return nothing
end

# =============================================================================
# BACKEND 2: MICM RHS
# MicmFun_wrapper exposed via C-linkage from src/MICM/MicmFun_wrapper.cpp.
# Rate constants are pre-computed by MicmBackend::getRateConstants() in C++
# and passed in via p.RCONST — identical interface to KPP by design.
# =============================================================================
function micm_rhs!(du::Vector{Float64}, u::Vector{Float64}, p, t::Float64)
    ccall((:MicmFun_wrapper, "libhapcemm.so"), Cvoid,
          (Ptr{Cdouble}, Ptr{Cdouble}, Cint, Cint, Ptr{Cdouble}),
          u, p.RCONST, Cint(length(u)), Cint(length(p.RCONST)), du)
    return nothing
end

function micm_jac!(J::Matrix{Float64}, u::Vector{Float64}, p, t::Float64)
    ccall((:MicmJac_wrapper, "libhapcemm.so"), Cvoid,
          (Ptr{Cdouble}, Ptr{Cdouble}, Cint, Ptr{Cdouble}),
          u, p.RCONST, Cint(length(u)), J)
    return nothing
end

# =============================================================================
# UNIFIED DISPATCH: selects backend at runtime from p.backend symbol
# =============================================================================
function chemistry_rhs!(du, u, p, t)
    if p.backend === :kpp
        kpp_rhs!(du, u, p, t)
    elseif p.backend === :micm
        micm_rhs!(du, u, p, t)
    else
        error("Unknown chemistry backend: $(p.backend). Use :kpp or :micm.")
    end
end

# =============================================================================
# FORWARD PASS — pure numeric, no I/O
# p must be a NamedTuple: (backend::Symbol, RCONST::Vector{Float64}, FIX::Vector{Float64})
# Returns: final concentration vector u[end]
# =============================================================================
function run_chemistry_step(u0::Vector{Float64},
                             p,
                             tspan::Tuple{Float64,Float64})
    prob = ODEProblem(chemistry_rhs!, u0, tspan, p)
    sol  = solve(prob, Rodas5(autodiff=false),
                 reltol=1e-4, abstol=1e-6,
                 save_everystep=false)
    return sol.u[end]
end

end # module HapcemmChemistry
''')
    done("julia/hapcemm_chemistry.jl created")
else:
    skip("hapcemm_chemistry.jl already exists")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== C11: julia/adjoint_module.jl [NEW] ===")
p = f"{julia_dir}/adjoint_module.jl"
if not os.path.exists(p):
    write(p, r'''"""
    HapcemmAdjoint

Enzyme.jl reverse-mode automatic differentiation adjoint for HAPCEMM chemistry.

CRITICAL RULES:
1. NO I/O (print, file write, NetCDF) inside any differentiated function.
2. Custom EnzymeRules defined for kpp_rhs! and micm_rhs! — Enzyme uses the
   analytic Jacobian from C++ (Jac_wrapper / MicmJac_wrapper) for the reverse
   pass instead of trying to differentiate through ccall directly.
3. Objective functions return a scalar Float64.
4. All output writing happens AFTER this module returns, in output.jl.
"""
module HapcemmAdjoint

using Enzyme
using EnzymeCore
using EnzymeCore: EnzymeRules
using OrdinaryDiffEq

include("hapcemm_chemistry.jl")
import .HapcemmChemistry: run_chemistry_step, kpp_rhs!, micm_rhs!

# =============================================================================
# CUSTOM ENZYME RULES for kpp_rhs!
# Prevents Enzyme from trying to differentiate through the ccall to C++.
# The reverse pass uses the analytic KPP Jacobian from Jac_wrapper.
# =============================================================================
function EnzymeRules.augmented_primal(
        config, func::Const{typeof(kpp_rhs!)}, ::Type{<:Const},
        du, u, p, t)
    func.val(du.val, u.val, p.val, t.val)
    return EnzymeRules.AugmentedReturn(nothing, nothing, nothing)
end

function EnzymeRules.reverse(
        config, func::Const{typeof(kpp_rhs!)}, ::Type{<:Const}, tape,
        du, u, p, t)
    nvar = length(u.val)
    J = zeros(Float64, nvar, nvar)
    ccall((:Jac_wrapper, "libhapcemm.so"), Cvoid,
          (Ptr{Cdouble}, Ptr{Cdouble}, Ptr{Cdouble}, Ptr{Cdouble}),
          u.val, p.val.FIX, p.val.RCONST, J)
    u.dval .+= J' * du.dval
    return (nothing, nothing, nothing, nothing)
end

# =============================================================================
# CUSTOM ENZYME RULES for micm_rhs! (same pattern, uses MicmJac_wrapper)
# =============================================================================
function EnzymeRules.augmented_primal(
        config, func::Const{typeof(micm_rhs!)}, ::Type{<:Const},
        du, u, p, t)
    func.val(du.val, u.val, p.val, t.val)
    return EnzymeRules.AugmentedReturn(nothing, nothing, nothing)
end

function EnzymeRules.reverse(
        config, func::Const{typeof(micm_rhs!)}, ::Type{<:Const}, tape,
        du, u, p, t)
    nvar = length(u.val)
    J = zeros(Float64, nvar, nvar)
    ccall((:MicmJac_wrapper, "libhapcemm.so"), Cvoid,
          (Ptr{Cdouble}, Ptr{Cdouble}, Cint, Ptr{Cdouble}),
          u.val, p.val.RCONST, Cint(nvar), J)
    u.dval .+= J' * du.dval
    return (nothing, nothing, nothing, nothing)
end

# =============================================================================
# OBJECTIVE FUNCTIONS (pure math, scalar output — Enzyme targets)
# =============================================================================
"""Single-species objective: J = u_final[target_idx]"""
function obj_single(u_final::Vector{Float64}, idx::Int)::Float64
    return u_final[idx]
end

"""All-species objective: J = sum(u_final)"""
function obj_all(u_final::Vector{Float64})::Float64
    return sum(u_final)
end

# =============================================================================
# PURE FORWARD WRAPPER — what Enzyme differentiates.
# MUST be pure math: no I/O, no println, no allocations in hot path.
# =============================================================================
function forward_for_adjoint(u0::Vector{Float64},
                              rconst::Vector{Float64},
                              FIX::Vector{Float64},
                              tspan::Tuple{Float64,Float64},
                              backend::Symbol,
                              mode::Symbol,
                              target_idx::Int)::Float64
    p       = (backend=backend, RCONST=rconst, FIX=FIX)
    u_final = run_chemistry_step(u0, p, tspan)
    return (mode === :all) ? obj_all(u_final) : obj_single(u_final, target_idx)
end

# =============================================================================
# ADJOINT PASS
#
# Returns:
#   species_grad  = dJ/d(u0)     — sensitivity to initial concentrations
#   param_grad    = dJ/d(rconst) — sensitivity to rate constants
#
# mode options:
#   :species   — J = [target_species] at end of integration
#   :parameter — same J; param_grad gives dJ/dk for each rate constant
#   :all       — J = sum of all species at end
#
# One Enzyme reverse pass computes both species_grad and param_grad.
# =============================================================================
function run_adjoint_pass(
        u0::Vector{Float64},
        rconst::Vector{Float64},
        FIX::Vector{Float64},
        tspan::Tuple{Float64,Float64},
        backend::Symbol,
        mode::Symbol,
        target_idx::Int = 1)

    species_grad = zeros(Float64, length(u0))
    param_grad   = zeros(Float64, length(rconst))

    Enzyme.autodiff(
        Enzyme.Reverse,
        forward_for_adjoint,
        Active,                                         # scalar output
        Enzyme.Duplicated(copy(u0),     species_grad),  # dJ/du0
        Enzyme.Duplicated(copy(rconst), param_grad),    # dJ/drconst
        Enzyme.Const(FIX),
        Enzyme.Const(tspan),
        Enzyme.Const(backend),
        Enzyme.Const(mode),
        Enzyme.Const(target_idx)
    )

    return species_grad, param_grad
end

end # module HapcemmAdjoint
''')
    done("julia/adjoint_module.jl created")
else:
    skip("adjoint_module.jl already exists")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== C12: julia/output.jl [NEW] ===")
p = f"{julia_dir}/output.jl"
if not os.path.exists(p):
    write(p, r'''"""
    HapcemmOutput

NetCDF output routines for HAPCEMM Julia-side chemistry results.

CRITICAL: This module is NEVER called inside any Enzyme-differentiated path.
All writes happen AFTER Enzyme adjoint pass has returned.
"""
module HapcemmOutput

using NCDatasets
using Dates

"""
    write_adjoint_output(filename, timeArray, species_sensitivity,
                         param_sensitivity, species_names, reaction_names)

Write Enzyme adjoint sensitivity results to a NetCDF file.
Called AFTER `HapcemmAdjoint.run_adjoint_pass()` has returned.
"""
function write_adjoint_output(
        filename::String,
        timeArray::Vector{Float64},
        species_sensitivity::Matrix{Float64},   # [nVar × nTime] or [nTime × nVar]
        param_sensitivity::Matrix{Float64},     # [nReact × nTime]
        species_names::Vector{String},
        reaction_names::Vector{String})

    NCDataset(filename, "c") do ds
        ds.attrib["title"]       = "HAPCEMM Enzyme Adjoint Sensitivity Output"
        ds.attrib["created"]     = string(now())
        ds.attrib["Conventions"] = "CF-1.8"

        nTime  = length(timeArray)
        nVar   = length(species_names)
        nReact = length(reaction_names)

        defDim(ds, "time",     nTime)
        defDim(ds, "species",  nVar)
        defDim(ds, "reaction", nReact)

        t_var = defVar(ds, "time", Float64, ("time",))
        t_var.attrib["units"]     = "seconds since emission"
        t_var.attrib["long_name"] = "Simulation time"
        t_var[:]                  = timeArray

        # dJ/d[X_initial] — sensitivity of objective to initial concentrations
        sv = defVar(ds, "dJ_dSpecies", Float32, ("species", "time"))
        sv.attrib["units"]     = "J / (molec cm-3)"
        sv.attrib["long_name"] = "Adjoint sensitivity dJ/d[X_initial]"
        sv[:, :]               = Float32.(species_sensitivity)

        # dJ/dk — sensitivity to rate constants
        pv = defVar(ds, "dJ_dRCONST", Float32, ("reaction", "time"))
        pv.attrib["units"]     = "J / (cm3 molec-1 s-1)"
        pv.attrib["long_name"] = "Adjoint sensitivity dJ/d(rate constant)"
        pv[:, :]               = Float32.(param_sensitivity)

        for (i, name) in enumerate(species_names)
            ds.attrib["species_$(i)"] = name
        end
        for (j, name) in enumerate(reaction_names)
            ds.attrib["reaction_$(j)"] = name
        end
    end
    println("[HapcemmOutput] Adjoint output written to: $filename")
end

"""
    write_forward_output(filename, timeArray, concentrations, species_names, airDens)

Write forward chemistry concentration history to NetCDF.
"""
function write_forward_output(
        filename::String,
        timeArray::Vector{Float64},
        concentrations::Matrix{Float64},   # [nVar × nTime] in molec/cm3
        species_names::Vector{String},
        airDens::Float64)

    NCDataset(filename, "c") do ds
        ds.attrib["title"]   = "HAPCEMM Forward Chemistry Output"
        ds.attrib["created"] = string(now())
        defDim(ds, "time",    length(timeArray))
        defDim(ds, "species", length(species_names))
        t_var    = defVar(ds, "time", Float64, ("time",))
        t_var[:] = timeArray
        c_var    = defVar(ds, "concentrations", Float32, ("species", "time"))
        c_var.attrib["units"]     = "ppb"
        c_var.attrib["long_name"] = "Mole fraction [X] / n_air × 1e9"
        c_var[:, :]               = Float32.(concentrations ./ airDens .* 1e9)
        for (i, name) in enumerate(species_names)
            ds.attrib["species_$(i)"] = name
        end
    end
end

end # module HapcemmOutput
''')
    done("julia/output.jl created")
else:
    skip("output.jl already exists")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== C13: CMakeLists.txt — USE_MICM option ===")
p = f"{ROOT}/CMakeLists.txt"
c = read(p)
if 'USE_MICM' not in c:
    micm_block = """
# ============================================================
# Optional MICM chemistry backend (NCAR micm library)
# Enable with: cmake .. -DUSE_MICM=ON
# Requires micm installed (e.g. spack install micm) and BLAS+LAPACK.
# The KPP backend remains available and is the default (USE_MICM=OFF).
# ============================================================
option(USE_MICM "Build with NCAR MICM chemistry backend" OFF)

if(USE_MICM)
    find_package(micm QUIET)
    if(micm_FOUND)
        message(STATUS "[HAPCEMM] MICM found at: ${micm_DIR}")
        find_package(BLAS   REQUIRED)
        find_package(LAPACK REQUIRED)
        target_link_libraries(${PROJECT_NAME} PRIVATE
            micm::micm BLAS::BLAS LAPACK::LAPACK)
        target_compile_definitions(${PROJECT_NAME} PRIVATE USE_MICM=1)
        target_include_directories(${PROJECT_NAME} PRIVATE
            ${CMAKE_SOURCE_DIR}/include/MICM)
        target_sources(${PROJECT_NAME} PRIVATE
            ${CMAKE_SOURCE_DIR}/src/MICM/MicmBackend.cpp
            ${CMAKE_SOURCE_DIR}/src/MICM/MicmFun_wrapper.cpp)
        message(STATUS "[HAPCEMM] MICM chemistry backend ENABLED")
    else()
        message(WARNING
            "[HAPCEMM] USE_MICM=ON but 'micm' package not found. "
            "Install with: spack install micm  or set -Dmicm_DIR=<path>. "
            "Falling back to KPP-only build.")
        set(USE_MICM OFF CACHE BOOL "" FORCE)
    endif()
endif()
"""
    c = c.rstrip() + '\n' + micm_block + '\n'
    write(p, c)
    done("USE_MICM option added to CMakeLists.txt")
else:
    skip("USE_MICM already in CMakeLists.txt")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== C14: julia/Project.toml [NEW] ===")
p = f"{julia_dir}/Project.toml"
if not os.path.exists(p):
    write(p, """[deps]
OrdinaryDiffEq = "1dea7af3-3e70-54e6-95c3-0bf5283fa5ed"
Enzyme         = "7da242da-08ed-463a-9acd-ee780be4f1d9"
EnzymeCore     = "f151be2c-9106-41f4-ab19-57ee4f262869"
NCDatasets     = "85f8d34a-cbdd-5861-8df4-14fed0d494ab"

[compat]
julia          = "1.10"
OrdinaryDiffEq = "6"
Enzyme         = "0.13"
NCDatasets     = "0.14"

# Musica.jl (NCAR Julia wrapper for MICM) is not yet in the Julia General registry.
# Track: https://github.com/NCAR/musica/issues/639
# Once released: add    Musica = "<uuid>"    here.
""")
    done("julia/Project.toml created")
else:
    skip("Project.toml already exists")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== Plan C verification ===")
for path, pattern in [
    (f"{ROOT}/defaults/input.yaml",                      "CHEMISTRY SOLVER SUBMENU"),
    (f"{ROOT}/include/Core/Input_Mod.hpp",               "CHEMISTRY_SOLVER"),
    (f"{ROOT}/src/YamlInputReader/YamlInputReader.cpp",  "CHEMISTRY_SOLVER"),
    (f"{ROOT}/include/MICM/MicmBackend.hpp",             "MicmBackend"),
    (f"{ROOT}/src/MICM/MicmBackend.cpp",                 "MicmBackend"),
    (f"{ROOT}/src/MICM/MicmFun_wrapper.cpp",             "MicmFun_wrapper"),
    (f"{ROOT}/src/Core/BoxModel.cpp",                    "USE_MICM"),
    (f"{ROOT}/include/Util/JuliaBridge.hpp",             "IntegrateMicm"),
    (f"{ROOT}/src/Util/JuliaBridge.cpp",                 "IntegrateMicm"),
    (f"{ROOT}/julia/hapcemm_chemistry.jl",               "run_chemistry_step"),
    (f"{ROOT}/julia/adjoint_module.jl",                  "run_adjoint_pass"),
    (f"{ROOT}/julia/output.jl",                          "write_adjoint_output"),
    (f"{ROOT}/CMakeLists.txt",                           "USE_MICM"),
    (f"{ROOT}/julia/Project.toml",                       "OrdinaryDiffEq"),
]:
    try:
        content = read(path)
        status = "✓ FOUND" if pattern in content else "✗ MISSING"
    except FileNotFoundError:
        status = "✗ FILE MISSING"
    print(f"  {status}: '{pattern}' in {os.path.relpath(path, ROOT)}")

print("\n=== Plan C COMPLETE ===")
