import os

filepath = "/projects/b35as/public/HAPCEMM-Chem/Code.v05-00/include/KPP-CRI-V2R5/KPP_Parameters.h"

if os.path.exists(filepath):
    print(f"Appending custom APCEMM parameters to {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Append the custom defines if they are not already there
    custom_defines = """
/* Custom APCEMM parameter additions */
#define NAERO                4           /* Number of aerosol types considered for heterogeneous chemistry */
#define PSC                  1           /* Consider PSCs? */
#define NOPT                 3           /* Number of optimization variables for KPP_Adjoint */

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
    if "NSPECALL" not in content:
        # Append before the closing #endif if it exists, otherwise just append to end
        if "#endif" in content:
            # Replace the last occurrence of #endif
            parts = content.rsplit("#endif", 1)
            new_content = parts[0] + custom_defines + "\n#endif" + parts[1]
        else:
            new_content = content + "\n" + custom_defines
            
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Successfully appended custom APCEMM parameters!")
    else:
        print("Custom parameters already present in KPP_Parameters.h.")
else:
    print(f"Error: {filepath} not found.")
