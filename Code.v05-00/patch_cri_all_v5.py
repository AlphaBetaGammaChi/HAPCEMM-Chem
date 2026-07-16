import os

base_dir = "/projects/b35as/public/HAPCEMM-Chem/Code.v05-00"
param_path = os.path.join(base_dir, "include/KPP-CRI-V2R5/KPP_Parameters.h")
global_path = os.path.join(base_dir, "src/KPP-CRI-V2R5/KPP_Global.cpp")
rates_path = os.path.join(base_dir, "src/KPP-CRI-V2R5/KPP_Rates.cpp")

# 1. Patch KPP_Parameters.h
if os.path.exists(param_path):
    print(f"Patching {param_path}...")
    with open(param_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if "/* Custom APCEMM parameter additions */" in content:
        content = content.split("/* Custom APCEMM parameter additions */")[0]
    
    content = content.strip()
    while content.endswith("#endif"):
        content = content[:-6].strip()

    header_guard = "#ifndef KPP_PARAMETERS_H_INCLUDED\n#define KPP_PARAMETERS_H_INCLUDED\n\n"
    if "#ifndef KPP_PARAMETERS_H_INCLUDED" not in content:
        content = header_guard + content

    content = content.replace("#define NLOOKAT              0", "#define NLOOKAT              1")
    content = content.replace("#define NMONITOR             0", "#define NMONITOR             1")

    # Appended custom defines
    custom_defines = """
/* Custom APCEMM parameter additions */
#define NAERO                4           /* Number of aerosol types considered for heterogeneous chemistry */
#define PSC                  1           /* Consider PSCs? */
#define NOPT                 3           /* Number of optimization variables for KPP_Adjoint */
#define NPHOTOL              114         /* Number of photolysis reactions */

/* Dummy indices for stratospheric/halogen/water species not solved by CRI */
#define ind_BrNO3            NSPEC
#define ind_HOBr             NSPEC
#define ind_HBr              NSPEC
#define ind_ClNO3            NSPEC
#define ind_HOCl             NSPEC
#define ind_H2SO4            NSPEC
#define ind_HCl              NSPEC
#define ind_H2O              NSPEC

/* Photolysis reaction name indices (0-based C++ equivalents of 1-based Fortran indices) */
#define J_O3_O1D             0
#define J_O3_O3P             1
#define J_H2O2               2
#define J_NO2                3
#define J_NO3_NO             4
#define J_NO3_NO2            5
#define J_HONO               6
#define J_HNO3               7
#define J_HCHO_H             8
#define J_HCHO_H2            9
#define J_CH3CHO             10
#define J_C2H5CHO            11
#define J_C3H7CHO_HCO        12
#define J_C3H7CHO_C2H4       13
#define J_IPRCHO             14
#define J_MACR_HCO           15
#define J_MACR_H             16
#define J_C5HPALD1           17
#define J_CH3COCH3           18
#define J_MEK                19
#define J_MVK_CO             20
#define J_MVK_C2H3           21
#define J_GLYOX_H2           22
#define J_GLYOX_HCHO         23
#define J_GLYOX_HCO          24
#define J_MGLYOX             25
#define J_BIACET             26
#define J_CH3OOH             27
#define J_CH3NO3             28
#define J_C2H5NO3            29
#define J_NC3H7NO3           30
#define J_IC3H7NO3           31
#define J_TC4H9NO3           32
#define J_NOA                33

/* Index declaration for additional species in APCEMM               */
#define ind_NIT      NSPEC
#define ind_NAT      NSPEC+1
#define ind_SO4L     NSPEC+2
#define ind_H2OL     NSPEC+3
#define ind_H2OS     NSPEC+4
#define ind_HNO3L    NSPEC+5
#define ind_HNO3S    NSPEC+6
#define ind_HClL     NSPEC+7
#define ind_HOClL    NSPEC+8
#define ind_HBrL     NSPEC+9
#define ind_HOBrL    NSPEC+10
#define NSPECREACT   NSPEC+11
#define ind_SO4T     NSPEC+11
#define ind_H2Omet   NSPEC+12
#define ind_H2Oplume NSPEC+13
#define NSPECALL     NSPEC+14

#endif /* KPP_PARAMETERS_H_INCLUDED */
"""
    with open(param_path, 'w', encoding='utf-8') as f:
        f.write(content + "\n" + custom_defines)
    print("Successfully patched KPP_Parameters.h!")
else:
    print(f"Error: {param_path} not found.")

# 2. Patch KPP_Global.cpp
if os.path.exists(global_path):
    print(f"Patching {global_path}...")
    with open(global_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if '#include "KPP/KPP_Global.h"' in content:
        content = content.replace('#include "KPP/KPP_Global.h"', '')
    if '#include "KPP/KPP_Parameters.h"' in content:
        content = content.replace('#include "KPP/KPP_Parameters.h"', '')

    includes = '#include "KPP/KPP_Global.h"\n#include "KPP/KPP_Parameters.h"\n\n'
    if "/*" in content:
        parts = content.split("*/", 1)
        content = parts[0] + "*/\n\n" + includes + parts[1]
    else:
        content = includes + content

    content = content.replace("extern double C[NSPEC];", "extern double C[NSPECALL];")
    content = content.replace("extern char * SPC_NAMES[NSPEC];", "extern const char * SPC_NAMES[NSPEC];")
    content = content.replace("extern char * EQN_NAMES[NREACT];", "extern const char * EQN_NAMES[NREACT];")
    content = content.replace("extern // int LOOKAT", "// int LOOKAT")
    content = content.replace("extern // char * SMASS", "// char * SMASS")
    content = content.replace("extern // char * EQN_NAMES", "// char * EQN_NAMES")
    content = content.replace("extern int MONITOR[NMONITOR];", "int MONITOR[NMONITOR];")
    content = content.replace("extern char * EQN_TAGS[NREACT];", "char * EQN_TAGS[NREACT];")

    with open(global_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully patched KPP_Global.cpp!")
else:
    print(f"Error: {global_path} not found.")

# 3. Patch KPP_Rates.cpp
if os.path.exists(rates_path):
    print(f"Patching {rates_path}...")
    with open(rates_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if '#include "KPP/KPP_Global.h"' in content:
        content = content.replace('#include "KPP/KPP_Global.h"', '')
    if '#include "KPP/KPP_Parameters.h"' in content:
        content = content.replace('#include "KPP/KPP_Parameters.h"', '')

    includes = '#include "KPP/KPP_Global.h"\n#include "KPP/KPP_Parameters.h"\n\n#define J(x) PHOTOL[x]\n\n'
    if "#include <stdio.h>" in content:
        parts = content.split("#include <stdio.h>", 1)
        content = parts[0] + includes + "#include <stdio.h>" + parts[1]
    else:
        content = includes + content
        
    content = content.replace("void Update_RCONST()", "void Update_RCONST( const double TEMP, const double PRESS, const double AIRDENS, const double H2O )")

    with open(rates_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully patched KPP_Rates.cpp!")
else:
    print(f"Error: {rates_path} not found.")
