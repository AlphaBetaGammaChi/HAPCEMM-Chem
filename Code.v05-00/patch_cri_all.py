import os

base_dir = "/projects/b35as/public/HAPCEMM-Chem/Code.v05-00"
param_path = os.path.join(base_dir, "include/KPP-CRI-V2R5/KPP_Parameters.h")
global_path = os.path.join(base_dir, "src/KPP-CRI-V2R5/KPP_Global.cpp")

# 1. Patch KPP_Parameters.h
if os.path.exists(param_path):
    print(f"Patching {param_path}...")
    with open(param_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    custom_defines = """
/* Custom APCEMM parameter additions */
#define NAERO                4           /* Number of aerosol types considered for heterogeneous chemistry */
#define PSC                  1           /* Consider PSCs? */
#define NOPT                 3           /* Number of optimization variables for KPP_Adjoint */
#define NPHOTOL              114         /* Number of photolysis reactions */

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
"""
    # Replace existing custom defines if we already ran the old script, or append them
    if "NPHOTOL" not in content:
        # If the old script ran, it has NSPECALL. We replace from the old comment onwards
        if "/* Custom APCEMM parameter additions */" in content:
            content = content.split("/* Custom APCEMM parameter additions */")[0] + "#endif"
        
        if "#endif" in content:
            parts = content.rsplit("#endif", 1)
            new_content = parts[0] + custom_defines + "\n#endif" + parts[1]
        else:
            new_content = content + "\n" + custom_defines
            
        with open(param_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Successfully patched KPP_Parameters.h!")
    else:
        print("KPP_Parameters.h already patched.")
else:
    print(f"Error: {param_path} not found.")

# 2. Patch KPP_Global.cpp
if os.path.exists(global_path):
    print(f"Patching {global_path}...")
    with open(global_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    includes = '#include "KPP/KPP_Global.h"\n#include "KPP/KPP_Parameters.h"\n\n'
    
    if '#include "KPP/KPP_Global.h"' not in content:
        # Find where to insert it - insert right before the first comment or declaration
        if "/*" in content:
            # Insert right after the top comment block
            parts = content.split("*/", 1)
            new_content = parts[0] + "*/\n\n" + includes + parts[1]
        else:
            new_content = includes + content
            
        with open(global_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Successfully patched KPP_Global.cpp!")
    else:
        print("KPP_Global.cpp already contains includes.")
else:
    print(f"Error: {global_path} not found.")
