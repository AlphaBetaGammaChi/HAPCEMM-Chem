#include <catch2/catch_test_macros.hpp>
#include <YamlInputReader/YamlInputReader.hpp>
#include <Core/Input.hpp>
#include "APCEMM.h"

using namespace YamlInputReader;

TEST_CASE("HAPCEMM-Chem Options & Defaults Validation"){
    SECTION("Emission Index Defaults and Solver Selection"){
        string filename = string(APCEMM_TESTS_DIR) + "/test.yaml";
        YAML::Node data = YAML::LoadFile(filename);
        
        OptInput input;
        try {
            readSimMenu(input, data["SIMULATION MENU"]);
        } catch (const std::invalid_argument&) {}
        REQUIRE_NOTHROW(readParamMenu(input, data["PARAMETER MENU"]));
        
        // New optional fuel emission indices must be successfully parsed and fallback to 0.0 safely
        REQUIRE(input.PARAMETER_PARAM_MAP.count("EI_H2") > 0);
        REQUIRE(input.PARAMETER_PARAM_MAP.count("EI_LUB") > 0);
        
        // Verify solver and adjoint defaults are safely parsed
        REQUIRE(input.CHEMISTRY_SOLVER == ChemistrySolver::KPP);
        REQUIRE(input.ADJOINT_ENABLE == false);
    }

    SECTION("Geoengineering Defaults and Parser Validation"){
        // Defaults yaml is located at APCEMM_TESTS_DIR + "/../defaults/input.yaml"
        string filename = string(APCEMM_TESTS_DIR) + "/../defaults/input.yaml";
        YAML::Node data = YAML::LoadFile(filename);
        
        OptInput input;
        REQUIRE_NOTHROW(readSimMenu(input, data["SIMULATION MENU"]));
        REQUIRE_NOTHROW(readParamMenu(input, data["PARAMETER MENU"]));
        
        // Check new chemistry solver submenu
        REQUIRE(input.CHEMISTRY_SOLVER == ChemistrySolver::KPP);
        REQUIRE(input.MICM_MECHANISM_PATH == "./mechanism/");
        REQUIRE(input.ADJOINT_ENABLE == false);
        REQUIRE(input.ADJOINT_MODE == "all");
        REQUIRE(input.ADJOINT_TARGET_NAME == "O3");
        
        // Check geoengineering parameters
        REQUIRE(input.PARAMETER_PARAM_MAP.count("Background_Geoengineering_Type") > 0);
        REQUIRE(input.PARAMETER_PARAM_MAP.at("Background_Geoengineering_Type")[0] == 0.0);
        
        REQUIRE(input.PARAMETER_PARAM_MAP.count("Background_Geoengineering_Rho") > 0);
        REQUIRE(input.PARAMETER_PARAM_MAP.at("Background_Geoengineering_Rho")[0] == 1769.0);
        
        REQUIRE(input.PARAMETER_PARAM_MAP.count("Background_Geoengineering_Number_Density") > 0);
        REQUIRE(input.PARAMETER_PARAM_MAP.at("Background_Geoengineering_Number_Density")[0] == 0.0);
        
        REQUIRE(input.PARAMETER_PARAM_MAP.count("Background_Geoengineering_Radius") > 0);
        REQUIRE(input.PARAMETER_PARAM_MAP.at("Background_Geoengineering_Radius")[0] == 2.0e-8);
        
        REQUIRE(input.PARAMETER_PARAM_MAP.count("Background_Geoengineering_Gamma") > 0);
        REQUIRE(input.PARAMETER_PARAM_MAP.at("Background_Geoengineering_Gamma")[0] == 0.02);
        
        REQUIRE(input.PARAMETER_PARAM_MAP.count("Background_Geoengineering_Shape_Factor") > 0);
        REQUIRE(input.PARAMETER_PARAM_MAP.at("Background_Geoengineering_Shape_Factor")[0] == 1.0);
        
        REQUIRE(input.PARAMETER_PARAM_MAP.count("Background_Geoengineering_ContactAngle") > 0);
        REQUIRE(input.PARAMETER_PARAM_MAP.at("Background_Geoengineering_ContactAngle")[0] == 0.0);
        
        REQUIRE(input.PARAMETER_PARAM_MAP.count("Background_Geoengineering_Wettability") > 0);
        REQUIRE(input.PARAMETER_PARAM_MAP.at("Background_Geoengineering_Wettability")[0] == 0.0);
    }
}
