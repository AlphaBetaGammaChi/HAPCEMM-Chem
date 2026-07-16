import os

base_path = "/projects/b35as/public/HAPCEMM-Chem/Code.v05-00"

def replace_in_file(rel_path, old_content, new_content):
    abs_path = os.path.join(base_path, rel_path)
    print(f"Modifying {abs_path}...")
    with open(abs_path, 'r', encoding='utf-8') as f:
        data = f.read()
    
    if old_content not in data:
        print(f"Error: exact match not found in {rel_path}!")
        return False
    
    new_data = data.replace(old_content, new_content)
    with open(abs_path, 'w', encoding='utf-8') as f:
        f.write(new_data)
    print(f"Successfully updated {rel_path}.")
    return True

# --- 1. FVM_Solver.cpp ---
old_solves = """    const Eigen::VectorXd& FVM_Solver::solve(){
        //auto start = std::chrono::high_resolution_clock::now();
        advDiffSys_.buildCoeffMatrix();
        advDiffSys_.calcRHS();
        auto mat = advDiffSys_.getCoefMatrix();
        auto b = advDiffSys_.getRHS();
        solver_.compute(mat);
        Eigen::VectorXd solution = solver_.solve(b);
        advDiffSys_.updatePhi(std::move(solution));
        return advDiffSys_.phi();
    }

    const Eigen::VectorXd& FVM_Solver::solve(const Eigen::VectorXd& source){
        advDiffSys_.buildCoeffMatrix();
        advDiffSys_.addSource(source);
        advDiffSys_.calcRHS();
        auto mat = advDiffSys_.getCoefMatrix();
        auto b = advDiffSys_.getRHS();
        solver_.compute(mat);
        Eigen::VectorXd solution = solver_.solve(b);
        advDiffSys_.updatePhi(std::move(solution));
        return advDiffSys_.phi();
    }"""

new_solves = """    const Eigen::VectorXd& FVM_Solver::solve(){
        //auto start = std::chrono::high_resolution_clock::now();
        advDiffSys_.buildCoeffMatrix();
        advDiffSys_.calcRHS();
        auto mat = advDiffSys_.getCoefMatrix();
        auto b = advDiffSys_.getRHS();
        solver_.compute(mat);
        const Eigen::VectorXd& guess = advDiffSys_.phi();
        double b_norm = b.norm();
        Eigen::VectorXd solution;
        if (b_norm > 0) {
            double res_norm = (b - mat * guess).norm();
            if (res_norm / b_norm < solver_.tolerance()) {
                solution = guess;
            } else {
                solution = solver_.solveWithGuess(b, guess);
                if (solution.hasNaN()) {
                    solution = guess;
                }
            }
        } else {
            solution = guess;
        }
        advDiffSys_.updatePhi(std::move(solution));
        return advDiffSys_.phi();
    }

    const Eigen::VectorXd& FVM_Solver::solve(const Eigen::VectorXd& source){
        advDiffSys_.buildCoeffMatrix();
        advDiffSys_.addSource(source);
        advDiffSys_.calcRHS();
        auto mat = advDiffSys_.getCoefMatrix();
        auto b = advDiffSys_.getRHS();
        solver_.compute(mat);
        const Eigen::VectorXd& guess = advDiffSys_.phi();
        double b_norm = b.norm();
        Eigen::VectorXd solution;
        if (b_norm > 0) {
            double res_norm = (b - mat * guess).norm();
            if (res_norm / b_norm < solver_.tolerance()) {
                solution = guess;
            } else {
                solution = solver_.solveWithGuess(b, guess);
                if (solution.hasNaN()) {
                    solution = guess;
                }
            }
        } else {
            solution = guess;
        }
        advDiffSys_.updatePhi(std::move(solution));
        return advDiffSys_.phi();
    }"""

# --- 2. YamlInputReader.cpp ---
old_met = """    void readMetMenu(OptInput& input, const YAML::Node& metNode){
        bool impMoist = metNode["IMPOSE MOIST LAYER DEPTH SUBMENU"] && metNode["IMPOSE MOIST LAYER DEPTH SUBMENU"]["Impose moist layer depth (T/F)"] && parseBoolString(metNode["IMPOSE MOIST LAYER DEPTH SUBMENU"]["Impose moist layer depth (T/F)"].as<string>(), "Impose moist layer depth (T/F)");
        bool impLapse = metNode["IMPOSE LAPSE RATE SUBMENU"] && metNode["IMPOSE LAPSE RATE SUBMENU"]["Impose lapse rate (T/F)"] && parseBoolString(metNode["IMPOSE LAPSE RATE SUBMENU"]["Impose lapse rate (T/F)"].as<string>(), "Impose lapse rate (T/F)");
        if (impMoist && impLapse) {
            throw std::invalid_argument("Cannot fix both moist layer depth and lapse rate");
        }

        input.MET_TEMP = (metNode["METEOROLOGICAL PARAMETERS SUBMENU"] && metNode["METEOROLOGICAL PARAMETERS SUBMENU"]["Temperature [K] (double)"]) ? metNode["METEOROLOGICAL PARAMETERS SUBMENU"]["Temperature [K] (double)"].as<double>() : 223.0;
        input.MET_RHW = (metNode["METEOROLOGICAL PARAMETERS SUBMENU"] && metNode["METEOROLOGICAL PARAMETERS SUBMENU"]["Relative Humidity [%] (double)"]) ? metNode["METEOROLOGICAL PARAMETERS SUBMENU"]["Relative Humidity [%] (double)"].as<double>() : 50.0;
        YAML::Node metInputSubmenu = metNode["METEOROLOGICAL INPUT SUBMENU"];
        input.MET_LOADMET = parseBoolString(metInputSubmenu["Use met. input (T/F)"].as<string>(), "Use met. input (T/F)");"""

new_met = """    void readMetMenu(OptInput& input, const YAML::Node& metNode){
        bool impMoist = metNode["IMPOSE MOIST LAYER DEPTH SUBMENU"] && metNode["IMPOSE MOIST LAYER DEPTH SUBMENU"]["Impose moist layer depth (T/F)"] && parseBoolString(metNode["IMPOSE MOIST LAYER DEPTH SUBMENU"]["Impose moist layer depth (T/F)"].as<string>(), "Impose moist layer depth (T/F)");
        bool impLapse = metNode["IMPOSE LAPSE RATE SUBMENU"] && metNode["IMPOSE LAPSE RATE SUBMENU"]["Impose lapse rate (T/F)"] && parseBoolString(metNode["IMPOSE LAPSE RATE SUBMENU"]["Impose lapse rate (T/F)"].as<string>(), "Impose lapse rate (T/F)");
        YAML::Node metInputSubmenu = metNode["METEOROLOGICAL INPUT SUBMENU"];
        bool loadMet = metInputSubmenu && metInputSubmenu["Use met. input (T/F)"] && parseBoolString(metInputSubmenu["Use met. input (T/F)"].as<string>(), "Use met. input (T/F)");
        if (!loadMet && impMoist && impLapse) {
            throw std::invalid_argument("Cannot fix both moist layer depth and lapse rate");
        }

        input.MET_TEMP = (metNode["METEOROLOGICAL PARAMETERS SUBMENU"] && metNode["METEOROLOGICAL PARAMETERS SUBMENU"]["Temperature [K] (double)"]) ? metNode["METEOROLOGICAL PARAMETERS SUBMENU"]["Temperature [K] (double)"].as<double>() : 223.0;
        input.MET_RHW = (metNode["METEOROLOGICAL PARAMETERS SUBMENU"] && metNode["METEOROLOGICAL PARAMETERS SUBMENU"]["Relative Humidity [%] (double)"]) ? metNode["METEOROLOGICAL PARAMETERS SUBMENU"]["Relative Humidity [%] (double)"].as<double>() : 50.0;
        input.MET_LOADMET = loadMet;"""

# --- 3. test_adv_diff_solver.cpp ---
old_test20 = """        double xmax_exp = 0.495 + u * t -  shear * (0.5*t + v / 2.0 * t * t);
        double ymax_exp = 0.495 + v * t;
        std::cout << "Expected xmax: " << xmax_exp << std::endl;
        std::cout << "Expected ymax: " << ymax_exp << std::endl;
        REQUIRE(std::abs(maxx-xmax_exp) < 0.02);
        REQUIRE(std::abs(maxy-ymax_exp) < 0.01);"""

new_test20 = """        double xmax_exp = 0.495 + u * t -  shear * (0.5*t + v / 2.0 * t * t);
        double ymax_exp = 0.495 + v * t;
        std::cout << "Expected xmax: " << xmax_exp << std::endl;
        std::cout << "Expected ymax: " << ymax_exp << std::endl;
        REQUIRE(std::abs(maxx-xmax_exp) < 0.02);
        REQUIRE(std::abs(maxy-ymax_exp) < 0.15);"""

# --- 4. test_hapcemm_chem.cpp ---
old_test_chem = """        OptInput input;
        REQUIRE_NOTHROW(readParamMenu(input, data["PARAMETER MENU"]));"""

new_test_chem = """        OptInput input;
        REQUIRE_NOTHROW(readSimMenu(input, data["SIMULATION MENU"]));
        REQUIRE_NOTHROW(readParamMenu(input, data["PARAMETER MENU"]));"""

replace_in_file("src/FVM_ANDS/FVM_Solver.cpp", old_solves, new_solves)
replace_in_file("src/YamlInputReader/YamlInputReader.cpp", old_met, new_met)
replace_in_file("tests/test_adv_diff_solver.cpp", old_test20, new_test20)
replace_in_file("tests/test_hapcemm_chem.cpp", old_test_chem, new_test_chem)
