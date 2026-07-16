
#include <iostream>
#include <iomanip>
#include <vector>
#include <cmath>
#include <memory>
#include <stdexcept>
#include <cstring>
#include <algorithm>

#include <micm/configure/solver_config.hpp>
#include <micm/solver/solver_builder.hpp>
#include <micm/solver/rosenbrock.hpp>
#include <micm/util/matrix.hpp>
#include <micm/util/sparse_matrix.hpp>
#include <micm/process/process_set.hpp>
#include <micm/solver/linear_solver.hpp>
#include <micm/solver/lu_decomposition.hpp>
#include <micm/util/constants.hpp>

// Include KPP files for equivalence testing
#include <KPP/KPP_Global.h>
#include <KPP/KPP_Parameters.h>
#include <MICM/MicmBackend.hpp>

// Forward declaration of KPP INTEGRATE
extern "C" void INTEGRATE(double* Y, double* FIX, double tStart, double tEnd, double* ATOL, double* RTOL, double r);

void run_jacobian_test() {
    std::cout << "\n========================================\n";
    std::cout << " TEST 1: Jacobian Sign and Value Verification\n";
    std::cout << "========================================\n";

    micm::SolverConfig<> config;
    config.ReadAndParse("/projects/b35as/public/HAPCEMM-Chem/mechanisms/toy_jacobian/");
    auto solver_params = config.GetSolverParams();

    using RosenbrockType = micm::RosenbrockSolver<
        micm::ProcessSet,
        micm::LinearSolver<micm::SparseMatrix<double, micm::SparseMatrixStandardOrdering>, micm::LuDecomposition>
    >;
    using StateType = micm::State<micm::Matrix<double>, micm::SparseMatrix<double, micm::SparseMatrixStandardOrdering>>;
    using SolverType = micm::Solver<RosenbrockType, StateType>;

    auto solver = SolverType(
        micm::CpuSolverBuilder<micm::RosenbrockSolverParameters>(
            micm::RosenbrockSolverParameters::ThreeStageRosenbrockParameters())
        .SetSystem(solver_params.system_)
        .SetReactions(solver_params.processes_)
        .Build()
    );

    auto state = solver.GetState();
    
    // Scale concentrations to SI units (mol/m3) so they align mathematically with the converted rate constants
    double F = micm::MOLES_M3_TO_MOLECULES_CM3;
    state.variables_[0] = { 2.0 / F, 4.0 / F, 0.0 };
    state.conditions_[0].temperature_ = 298.15;
    state.conditions_[0].pressure_ = 1e5;
    state.conditions_[0].air_density_ = 2.5e19;

    solver.CalculateRateConstants(state);

    state.jacobian_.Fill(0.0);
    solver.solver_.rates_.SubtractJacobianTerms(state.rate_constants_, state.variables_, state.jacobian_);

    // Negate Jacobian elements to get +J
    double micm_J[3][3] = {0};
    auto nonzero_elements = solver.solver_.rates_.NonZeroJacobianElements();
    for (const auto& elem : nonzero_elements) {
        std::size_t r = elem.first;
        std::size_t c = elem.second;
        micm_J[r][c] = -state.jacobian_[0][r][c];
    }

    // Analytical Jacobian (evaluated at A=2, B=4)
    double analytical_J[3][3] = {
        { -14.0, -6.0, 0.0 },
        { -10.0, -6.0, 0.0 },
        {  12.0,  6.0, 0.0 }
    };

    std::cout << std::left << std::setw(25) << "Analytical Jacobian (J)" << "   " << "Negated MICM Jacobian (+J)\n";
    std::cout << "---------------------------------------------------------\n";
    for (int i = 0; i < 3; ++i) {
        std::cout << "[";
        for (int j = 0; j < 3; ++j) {
            std::cout << std::right << std::setw(6) << analytical_J[i][j] << " ";
        }
        std::cout << "]   [";
        for (int j = 0; j < 3; ++j) {
            std::cout << std::right << std::setw(6) << micm_J[i][j] << " ";
        }
        std::cout << "]\n";
    }

    // Verify equality
    bool match = true;
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 3; ++j) {
            if (std::abs(analytical_J[i][j] - micm_J[i][j]) > 1e-9) match = false;
        }
    }
    std::cout << "\nResult: " << (match ? "[PASS] Matrices match perfectly." : "[FAIL] Mismatch detected.") << "\n";
}

void run_decay_test() {
    std::cout << "\n========================================\n";
    std::cout << " TEST 2: First-Order Decay Verification (10 Steps)\n";
    std::cout << "========================================\n";

    micm::SolverConfig<> config;
    config.ReadAndParse("/projects/b35as/public/HAPCEMM-Chem/mechanisms/toy_decay/");
    auto solver_params = config.GetSolverParams();

    using RosenbrockType = micm::RosenbrockSolver<
        micm::ProcessSet,
        micm::LinearSolver<micm::SparseMatrix<double, micm::SparseMatrixStandardOrdering>, micm::LuDecomposition>
    >;
    using StateType = micm::State<micm::Matrix<double>, micm::SparseMatrix<double, micm::SparseMatrixStandardOrdering>>;
    using SolverType = micm::Solver<RosenbrockType, StateType>;

    auto solver = SolverType(
        micm::CpuSolverBuilder<micm::RosenbrockSolverParameters>(
            micm::RosenbrockSolverParameters::ThreeStageRosenbrockParameters())
        .SetSystem(solver_params.system_)
        .SetReactions(solver_params.processes_)
        .Build()
    );

    auto state = solver.GetState();
    state.variables_[0] = { 100.0 }; // Initial concentration A = 100.0
    state.conditions_[0].temperature_ = 298.15;
    state.conditions_[0].pressure_ = 1e5;
    state.conditions_[0].air_density_ = 2.5e19;

    double dt = 1.0;
    std::cout << std::left << std::setw(6) << "Step" 
              << std::setw(15) << "MICM Conc A" 
              << std::setw(20) << "Analytical A" 
              << "Relative Error\n";
    std::cout << "---------------------------------------------------------\n";
    
    std::cout << std::left << std::setw(6) << 0 
              << std::setw(15) << state.variables_[0][0] 
              << std::setw(20) << 100.0 
              << "0.0\n";

    for (int step = 1; step <= 10; ++step) {
        solver.CalculateRateConstants(state);
        auto result = solver.Solve(dt, state);
        if (result.state_ != micm::SolverState::Converged) {
            std::cerr << "Solver failed at step " << step << " with state: " 
                      << micm::SolverStateToString(result.state_) << "\n";
            break;
        }

        double analytical = 100.0 * std::exp(-0.1 * step);
        double error = std::abs(state.variables_[0][0] - analytical) / analytical;

        std::cout << std::left << std::setw(6) << step 
                  << std::setw(15) << state.variables_[0][0] 
                  << std::setw(20) << analytical 
                  << std::scientific << error << std::defaultfloat << "\n";
    }
}

void run_equivalence_test() {
    std::cout << "\n========================================\n";
    std::cout << " TEST 3: KPP vs MICM Equivalence Test (UCX Mechanism)\n";
    std::cout << "========================================\n";

    // Setup initial conditions: set all to 0.0 to disable inlined reactions
    std::vector<double> VAR_kpp(NVAR, 0.0);
    std::vector<double> VAR_micm(NVAR, 0.0);
    std::vector<double> FIX_arr(NSPEC - NVAR, 0.0);

    VAR_kpp[ind_O3] = 1e10;  VAR_micm[ind_O3] = 1e10;
    VAR_kpp[ind_NO] = 1e10;  VAR_micm[ind_NO] = 1e10;
    VAR_kpp[ind_NO2] = 1e10; VAR_micm[ind_NO2] = 1e10;

    // Initialize global KPP threadprivate pointers before instantiating MicmBackend
    FIX = FIX_arr.data();
    VAR = VAR_kpp.data();

    // Populate the static RCONST array: set all to 0, and only index 1219 to 2.5e-12
    for (int i = 0; i < NREACT; ++i) {
        RCONST[i] = 0.0;
    }
    RCONST[1219] = 2.5e-12;

    // Populate KPP species name array for active species we map
    std::memset(SPC_NAMES, 0, sizeof(const char*) * NSPEC);
    SPC_NAMES[ind_O3] = "O3";
    SPC_NAMES[ind_NO] = "NO";
    SPC_NAMES[ind_NO2] = "NO2";

    HAPCEMM::MicmBackend micm_backend("/projects/b35as/public/HAPCEMM-Chem/mechanisms/ucx_modified");

    double tStart = 0.0;
    double dt = 1.0;
    double ATOL[NVAR], RTOL[NVAR];
    for (int i = 0; i < NVAR; ++i) { ATOL[i] = 1.0e-12; RTOL[i] = 1.0e-8; }

    // Run first step
    double tEnd = tStart + dt;
    INTEGRATE(VAR_kpp.data(), FIX_arr.data(), tStart, tEnd, ATOL, RTOL, 0.0);

    micm_backend.setConditions(298.15, 1e5, 2.5e19, nullptr);
    micm_backend.solve(VAR_micm.data(), dt);

    std::cout << "\n--- After Step 1 ---\n";
    std::cout << std::left << std::setw(6) << "Idx" << std::setw(12) << "Species" << std::setw(18) << "KPP Conc" << "MICM Conc\n";
    std::cout << "---------------------------------------------------------\n";
    for (int i = 0; i < NVAR; ++i) {
        if (SPC_NAMES[i]) {
            std::cout << std::left << std::setw(6) << i 
                      << std::setw(12) << SPC_NAMES[i] 
                      << std::setw(18) << VAR_kpp[i] 
                      << VAR_micm[i] << "\n";
        }
    }

    // Continue loop
    std::cout << "\nStep  Max Relative Difference Across All Species\n";
    std::cout << "---------------------------------------------------------\n";

    // Re-initialize to initial state
    VAR_kpp.assign(NVAR, 0.0);
    VAR_micm.assign(NVAR, 0.0);
    FIX_arr.assign(NSPEC - NVAR, 0.0);

    VAR_kpp[ind_O3] = 1e10;  VAR_micm[ind_O3] = 1e10;
    VAR_kpp[ind_NO] = 1e10;  VAR_micm[ind_NO] = 1e10;
    VAR_kpp[ind_NO2] = 1e10; VAR_micm[ind_NO2] = 1e10;

    for (int i = 0; i < NREACT; ++i) {
        RCONST[i] = 0.0;
    }
    RCONST[1219] = 2.5e-12;

    for (int step = 1; step <= 10; ++step) {
        double tEnd_step = tStart + dt;
        INTEGRATE(VAR_kpp.data(), FIX_arr.data(), tStart, tEnd_step, ATOL, RTOL, 0.0);
        micm_backend.solve(VAR_micm.data(), dt);

        double max_diff = 0.0;
        for (int i = 0; i < NVAR; ++i) {
            if (SPC_NAMES[i]) {
                double diff = std::abs(VAR_kpp[i] - VAR_micm[i]) / std::max(VAR_kpp[i], 1e-30);
                if (diff > max_diff) max_diff = diff;
            }
        }
        std::cout << std::left << std::setw(6) << step << std::scientific << max_diff << std::defaultfloat << "\n";
        tStart = tEnd_step;
    }
}

int main() {
    try {
        run_jacobian_test();
        run_decay_test();
        run_equivalence_test();
    } catch (const std::exception& e) {
        std::cerr << "Exception in tests: " << e.what() << "\n";
        return 1;
    }
    return 0;
}
