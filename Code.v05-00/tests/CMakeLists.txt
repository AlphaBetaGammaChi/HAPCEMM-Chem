include(Catch)

set(SRC_TEST
	testmain.cpp
    test_physfunction.cpp
    test_nucleation.cpp
    test_buildkernel.cpp
    test_aerosol.cpp
	#test_meteorology.cpp
    test_integrate.cpp
    test_metfunction.cpp
    test_aircraft.cpp
    test_yamlreader.cpp
    test_hapcemm_chem.cpp
)
#Add preprocessor def of the tests dir
add_definitions(-DAPCEMM_TESTS_DIR="${CMAKE_SOURCE_DIR}/tests")

add_executable(unittest ${SRC_TEST})
target_link_libraries(unittest  Catch2::Catch2WithMain Util AIM EPM YamlInputReader)
catch_discover_tests(unittest)

add_executable(test_solver test_adv_diff_solver.cpp)
target_link_libraries(test_solver  Catch2::Catch2WithMain FVM_ANDS Core LAGRID OpenSSL::SSL OpenSSL::Crypto)
catch_discover_tests(test_solver)

add_executable(test_LAGRID test_LAGRID.cpp)
target_link_libraries(test_LAGRID  Catch2::Catch2WithMain LAGRID)
catch_discover_tests(test_LAGRID)

find_package(micm QUIET)
if (micm_FOUND)
    add_executable(run_chemistry_tests run_chemistry_tests.cpp ${CMAKE_SOURCE_DIR}/src/MICM/MicmBackend.cpp ${CMAKE_SOURCE_DIR}/src/MICM/MicmFun_wrapper.cpp)
    target_compile_definitions(run_chemistry_tests PRIVATE USE_MICM=1)
    target_include_directories(run_chemistry_tests PRIVATE ${CMAKE_SOURCE_DIR}/include/MICM)
    target_link_libraries(run_chemistry_tests Core KPP Util musica::micm)
endif()


