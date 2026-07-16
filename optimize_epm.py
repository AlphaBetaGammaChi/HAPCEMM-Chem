import sys

# 1. Optimize Solution.cpp (Move setup outside loop)
solution_path = '/lfs1i3/projects/b35as/public/HAPCEMM-Chem/Code.v05-00/src/EPM/Solution.cpp'
with open(solution_path, 'r') as f:
    lines = f.readlines()

new_lines = []
setup_block = []
in_loop = False
loop_start_index = -1

# Extract setup block and comment out inside loop
for i, line in enumerate(lines):
    if 'while ( curr_Time_s < RunUntil )' in line:
        in_loop = True
        loop_start_index = i
        # Prepare setup block from the content we know is inside
        setup_block.append('        /* --- GEOENGINEERING SETUP MOVED OUTSIDE LOOP --- */\n')
        setup_block.append('        double spinup_NACL_SAD = 0.0; double spinup_NACL_RAD = 1.0e-7;\n')
        setup_block.append('        double spinup_CACO3_SAD = 0.0; double spinup_CACO3_RAD = 1.0e-7;\n')
        setup_block.append('        double spinup_AL2O3_SAD = 0.0; double spinup_AL2O3_RAD = 1.0e-7;\n')
        setup_block.append('        double spinup_DUST_SAD = 0.0; double spinup_DUST_RAD = 1.0e-7;\n')
        setup_block.append('        double spinup_DIAMOND_SAD = 0.0; double spinup_DIAMOND_RAD = 1.0e-7;\n')
        setup_block.append('        double spinup_GEO_SAD = 0.0; double spinup_GEO_RADIUS = 1.0e-7; double spinup_GEO_GAMMA = 1.0e-7;\n')
        setup_block.append('        double N_geo = input.backgroundGeoengineeringNumber();\n')
        setup_block.append('        double R_geo = input.backgroundGeoengineeringRadius();\n')
        setup_block.append('        double R_geo_to_cm = R_geo * 100;\n')
        setup_block.append('        double SAD_cgs = N_geo * 4.0 * 3.14159265358979323846 * R_geo_to_cm * R_geo_to_cm;\n')
        setup_block.append('        double spinup_area[NAERO];\n')
        setup_block.append('        double spinup_radi[NAERO];\n')
        setup_block.append('        for(int k=0; k<NAERO; k++) { spinup_area[k] = 0.0; spinup_radi[k] = 1.0e-7; }\n')
        setup_block.append('        int type = 0; // Default\n')
        setup_block.append('        switch (type) { case 1: spinup_NACL_SAD = SAD_cgs; break; case 8: spinup_GEO_SAD = SAD_cgs; break; }\n')
        setup_block.append('        /* ----------------------------------------------- */\n')
    
    # We surgically comment out the redundant parts inside the loop
    # Based on the diff earlier, these lines started around line 440+
    redundant_keywords = ['double spinup_NACL_SAD', 'double N_geo', 'double R_geo', 'double R_geo_to_cm', 'int type = 0', 'double spinup_area[NAERO]', 'double spinup_radi[NAERO]']
    if in_loop and i > loop_start_index:
        matched = False
        for kw in redundant_keywords:
            if kw in line:
                new_lines.append('            // [MOVED OUTSIDE] ' + line.lstrip())
                matched = True
                break
        if not matched:
            new_lines.append(line)
    else:
        new_lines.append(line)

# Insert setup block before the loop
final_solution_lines = []
for line in new_lines:
    if 'while ( curr_Time_s < RunUntil )' in line:
        final_solution_lines.extend(setup_block)
    final_solution_lines.append(line)

with open(solution_path, 'w') as f:
    f.writelines(final_solution_lines)

# 2. Optimize RHS.cpp (Pass-by-Reference)
rhs_path = '/lfs1i3/projects/b35as/public/HAPCEMM-Chem/Code.v05-00/src/EPM/Models/Original/RHS.cpp'
with open(rhs_path, 'r') as f:
    rhs_lines = f.readlines()

new_rhs_lines = []
for line in rhs_lines:
    if 'Vector_1D pdf = nPDF_SO4.getPDF();' in line:
        new_rhs_lines.append('        const Vector_1D &pdf = nPDF_SO4.getPDF();\n')
    elif 'Vector_1D binCenters = nPDF_SO4.getBinCenters();' in line:
        new_rhs_lines.append('        const Vector_1D &binCenters = nPDF_SO4.getBinCenters();\n')
    else:
        new_rhs_lines.append(line)

with open(rhs_path, 'w') as f:
    f.writelines(new_rhs_lines)

print('Optimization scripts completed successfully.')
