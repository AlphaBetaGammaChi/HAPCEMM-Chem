import sys

file_path = 'Code.v05-00/src/EPM/Solution.cpp'
with open(file_path, 'r') as f:
    lines = f.readlines()

new_lines = []
in_loop = False
loop_start_index = -1

for i, line in enumerate(lines):
    if 'while ( curr_Time_s < RunUntil )' in line:
        in_loop = True
        loop_start_index = i
    
    if in_loop and i > loop_start_index:
        # Match all the variables that were causing shadowing or redefined issues
        to_comment = [
            'double spinup_CACO3_SAD', 'double spinup_AL2O3_SAD', 'double spinup_DUST_SAD', 
            'double spinup_DIAMOND_SAD', 'double spinup_GEO_SAD', 'double SAD_cgs =', 
            'double spinup_area[NAERO]', 'double spinup_radi[NAERO]', 'for(int k=0, k<NAERO',
            'spinup_area[k] = 0.0', 'spinup_radi[k] = 1.0e-7', 'double R_geo_to_cm ='
        ]
        matched = False
        for kw in to_comment:
            if kw in line:
                new_lines.append('            // [FIXED] ' + line.lstrip())
                matched = True
                break
        if not matched:
            new_lines.append(line)
    else:
        new_lines.append(line)

# Also fix the NAERO loop which was broken in the previous cat
final_lines = []
for line in new_lines:
    if 'for(int k=0; k<NAERO; k++) { spinup_area[k] = 0.0; spinup_radi[k] = 1.0e-7; }' in line:
         final_lines.append('        for(int k=0; k<NAERO; k++) { spinup_area[k] = 0.0; spinup_radi[k] = 1.0e-7; }\n')
    else:
         final_lines.append(line)

with open(file_path, 'w') as f:
    f.writelines(final_lines)
