#ifdef USE_MICM
#include "MICM/MicmBackend.hpp"
#include <micm/configure/solver_config.hpp>
#include <micm/solver/solver_builder.hpp>
#include <micm/solver/rosenbrock.hpp>
#include <micm/util/matrix.hpp>
#include <micm/util/sparse_matrix.hpp>
#include <micm/process/process_set.hpp>
#include <micm/solver/linear_solver.hpp>
#include <micm/solver/lu_decomposition.hpp>
#include <micm/util/constants.hpp> // Contains MOLES_M3_TO_MOLECULES_CM3
#include <iostream>
#include <cstring>
#include <vector>
#include <map>
#include <memory>
#include <algorithm>
#include <stdexcept>

// Include HAPCEMM KPP definitions for species names and arrays
#include "KPP/KPP_Global.h"
#include "KPP/KPP_Parameters.h"

namespace HAPCEMM {

struct MicmBackend::Impl {
    micm::SolverConfig<> config;
    
    using RosenbrockType = micm::RosenbrockSolver<
        micm::ProcessSet,
        micm::LinearSolver<micm::SparseMatrix<double, micm::SparseMatrixStandardOrdering>, micm::LuDecomposition>
    >;
    using StateType = micm::State<micm::Matrix<double>, micm::SparseMatrix<double, micm::SparseMatrixStandardOrdering>>;
    using SolverType = micm::Solver<RosenbrockType, StateType>;

    std::unique_ptr<SolverType> solver;
    StateType state;

    std::size_t n_species   = 0;
    std::size_t n_reactions = 0;
    std::vector<int> micm_to_hapcemm;
    std::vector<int> hapcemm_to_micm;

    explicit Impl(const std::string& mpath)
        : state() { // Default construct State, then assign in constructor body
        // Read and parse mechanism JSON files from directory
        config.ReadAndParse(mpath);
        
        auto solver_params = config.GetSolverParams();
        
        // Build the CPU Rosenbrock solver (wrapped in micm::Solver)
        solver = std::make_unique<SolverType>(
            micm::CpuSolverBuilder<micm::RosenbrockSolverParameters>(
                micm::RosenbrockSolverParameters::ThreeStageRosenbrockParameters())
            .SetSystem(solver_params.system_)
            .SetReactions(solver_params.processes_)
            .Build()
        );
        
        // Get the State object (holds concentrations, conditions, rate constants)
        state = solver->GetState();
        
        n_species   = solver_params.system_.gas_phase_.species_.size();
        n_reactions = solver_params.processes_.size();

        // Build name mappings between MICM and HAPCEMM (KPP) species
        micm_to_hapcemm.resize(n_species, -1);
        hapcemm_to_micm.assign(NSPEC, -1);

        for (std::size_t i = 0; i < n_species; ++i) {
            std::string micm_name = solver_params.system_.gas_phase_.species_[i].name_;
            for (int j = 0; j < NSPEC; ++j) {
                // Add safety check: check SPC_NAMES[j] is not nullptr before string comparison
                if (SPC_NAMES[j] && micm_name == SPC_NAMES[j]) {
                    micm_to_hapcemm[i] = j;
                    hapcemm_to_micm[j] = static_cast<int>(i);

                    break;
                }
            }
        }
        
        std::cout << "[MicmBackend] Successfully initialized with mechanism: " << mpath
                  << " | Species: " << n_species
                  << " | Reactions: " << n_reactions << std::endl;
    }
};

MicmBackend::MicmBackend(const std::string& mechanismPath)
    : impl_(std::make_unique<Impl>(mechanismPath)) {}

MicmBackend::~MicmBackend() = default;

void MicmBackend::setConditions(double temperature_K, double pressure_Pa,
                               double airDens_cm3, const double* /*photolRates*/) {
    // Set environmental conditions on the State object (first grid cell, index 0)
    impl_->state.conditions_[0].temperature_ = temperature_K;
    impl_->state.conditions_[0].pressure_ = pressure_Pa;
    impl_->state.conditions_[0].air_density_ = airDens_cm3;
}

void MicmBackend::setConcentrations(const double* VAR, int nVar) const {
    // Copy concentrations from HAPCEMM's VAR/FIX arrays to MICM's state variables (convert to mol/m3)
    auto variables = impl_->state.variables_[0];
    
    for (std::size_t i = 0; i < impl_->n_species; ++i) {
        int hapcemm_idx = impl_->micm_to_hapcemm[i];
        if (hapcemm_idx < 0) {
            variables[i] = 0.0;
            continue;
        }
        
        double val = 0.0;
        if (hapcemm_idx < NVAR) {
            // Variable species are read from VAR array
            val = VAR[hapcemm_idx];
        } else if (hapcemm_idx < NSPEC) {
            // Fixed species are read from FIX array (using index offset)
            val = FIX[hapcemm_idx - NVAR];
        }
        
        variables[i] = val / micm::MOLES_M3_TO_MOLECULES_CM3;
    }
}

void MicmBackend::getRateConstants(double* RCONST_out, int nReact) const {
    // Calculate rate constants using the solver
    impl_->solver->CalculateRateConstants(impl_->state);
    
    // Copy rate constants from state to output array
    std::size_t limit = std::min(static_cast<std::size_t>(nReact), impl_->n_reactions);
    for (std::size_t i = 0; i < limit; ++i) {
        RCONST_out[i] = impl_->state.rate_constants_[0][i];
    }
    
    // Zero out any remaining entries
    if (static_cast<std::size_t>(nReact) > limit) {
        std::memset(RCONST_out + limit, 0, sizeof(double) * (static_cast<std::size_t>(nReact) - limit));
    }
}

void MicmBackend::computeVdot(const double* VAR, double* Vdot, int nVar) const {
    // 1. Copy HAPCEMM concentrations to MICM state
    setConcentrations(VAR, nVar);
    
    // 2. Compute rate constants
    impl_->solver->CalculateRateConstants(impl_->state);
    
    // 3. Compute forcing (tendencies dy/dt) using the solver's process set
    micm::Matrix<double> forcing(1, impl_->n_species, 0.0);
    impl_->solver->solver_.rates_.AddForcingTerms(impl_->state.rate_constants_, impl_->state.variables_, forcing);
    
    // 4. Map tendencies back to HAPCEMM's Vdot (convert back to molecules/cm3/s)
    std::memset(Vdot, 0, sizeof(double) * static_cast<std::size_t>(nVar));
    for (std::size_t i = 0; i < impl_->n_species; ++i) {
        int hapcemm_idx = impl_->micm_to_hapcemm[i];
        if (hapcemm_idx >= 0 && hapcemm_idx < nVar) {
            Vdot[hapcemm_idx] = forcing[0][i] * micm::MOLES_M3_TO_MOLECULES_CM3;
        }
    }
}

void MicmBackend::computeJacobian(const double* VAR, double* J, int nVar) const {
    // Evaluate the sparse Jacobian and map it to a dense row-major matrix J
    setConcentrations(VAR, nVar);
    impl_->solver->CalculateRateConstants(impl_->state);
    
    // Fill the sparse Jacobian matrix
    impl_->state.jacobian_.Fill(0.0);
    impl_->solver->solver_.rates_.SubtractJacobianTerms(impl_->state.rate_constants_, impl_->state.variables_, impl_->state.jacobian_);
    
    // Initialize J to 0
    std::memset(J, 0, sizeof(double) * static_cast<std::size_t>(nVar) * static_cast<std::size_t>(nVar));
    
    // Copy/map sparse elements
    auto nonzero_elements = impl_->solver->solver_.rates_.NonZeroJacobianElements();
    for (const auto& elem : nonzero_elements) {
        std::size_t r = elem.first;
        std::size_t c = elem.second;
        
        int hapcemm_r = impl_->micm_to_hapcemm[r];
        int hapcemm_c = impl_->micm_to_hapcemm[c];
        
        if (hapcemm_r >= 0 && hapcemm_r < nVar && hapcemm_c >= 0 && hapcemm_c < nVar) {
            // SubtractJacobianTerms fills the sparse matrix with -J
            // We negate it to get the actual J.
            // Note: Jacobian elements require no scaling factor because the unit scaling factor cancels out.
            double val = -impl_->state.jacobian_[0][r][c];
            J[hapcemm_r * nVar + hapcemm_c] = val;
        }
    }
}

void MicmBackend::solve(double* VAR, double dt) {
    // 1. Copy HAPCEMM concentrations to MICM state
    setConcentrations(VAR, NVAR);
    
    // 2. Recalculate rate constants for current conditions
    impl_->solver->CalculateRateConstants(impl_->state);
    
    // 3. Solve the chemistry step
    auto result = impl_->solver->Solve(dt, impl_->state);
    
    // Verify successful convergence
    if (result.state_ != micm::SolverState::Converged) {
        std::cerr << "[MicmBackend] ERROR: Solver failed to converge! State: " 
                  << micm::SolverStateToString(result.state_) 
                  << " | dt = " << dt << std::endl;
        throw std::runtime_error("MICM Solver failed: " + micm::SolverStateToString(result.state_));
    }
    
    // 4. Copy updated concentrations back to HAPCEMM's VAR array (convert back to molecules/cm3)
    auto variables = impl_->state.variables_[0];
    for (std::size_t i = 0; i < impl_->n_species; ++i) {
        int hapcemm_idx = impl_->micm_to_hapcemm[i];
        if (hapcemm_idx >= 0 && hapcemm_idx < NVAR) {
            VAR[hapcemm_idx] = variables[i] * micm::MOLES_M3_TO_MOLECULES_CM3;
        }
    }
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

void MicmBackend::setCustomRateConstants(const double* PHOTOL, const double* RCONST, bool usePhotol, bool useHetchem) {
    if (usePhotol || useHetchem) {
        // Map KPP RCONST and PHOTOL into MICM rate_constants_ based on process mapping.
        // For a full implementation, this requires mapping KPP reaction indices to MICM reaction indices.
        // As a placeholder for fully mapping, we iterate and overwrite if mapped.
        for (std::size_t i = 0; i < impl_->n_reactions; ++i) {
            // Placeholder: overwrite with KPP values if mapped
        }
    }
}

void MicmBackend::computePL(const double* VAR, double* P_out, double* L_out) const {
    setConcentrations(VAR, NVAR);
    impl_->solver->CalculateRateConstants(impl_->state);
    
    std::memset(P_out, 0, sizeof(double) * NVAR);
    std::memset(L_out, 0, sizeof(double) * NVAR);

    micm::Matrix<double> forcing(1, impl_->n_species, 0.0);
    // In MICM, we typically get forcing from AddForcingTerms.
    // To separate P and L, we evaluate each reaction's rate:
    // auto num_reactions = impl_->solver_params.processes_.size();
    // for (std::size_t i = 0; i < num_reactions; ++i) {
    //     // Placeholder for evaluating reaction rate * stoichiometric coeff
    // }
}

void MicmBackend::computeRxnRates(const double* VAR, double* A_out) const {
    setConcentrations(VAR, NVAR);
    impl_->solver->CalculateRateConstants(impl_->state);
    getRateConstants(A_out, NREACT);
}

} // namespace HAPCEMM
#endif // USE_MICM


