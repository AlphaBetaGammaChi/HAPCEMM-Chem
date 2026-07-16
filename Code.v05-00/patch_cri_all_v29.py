import os
import shutil
import re

base_dir = "/projects/b35as/public/HAPCEMM-Chem/Code.v05-00"
kpp_cri_dir = "/projects/b35as/public/HAPCEMM-Chem/kpp_cri"

param_path = os.path.join(base_dir, "include/KPP-CRI-V2R5/KPP_Parameters.h")
global_path = os.path.join(base_dir, "src/KPP-CRI-V2R5/KPP_Global.cpp")
global_h_path = os.path.join(base_dir, "src/KPP-CRI-V2R5/cri_Global.h")
rates_path = os.path.join(base_dir, "src/KPP-CRI-V2R5/KPP_Rates.cpp")
monitor_path = os.path.join(base_dir, "src/KPP-CRI-V2R5/KPP_Monitor.cpp")
function_path = os.path.join(base_dir, "src/KPP-CRI-V2R5/KPP_Function.cpp")
integrator_path = os.path.join(base_dir, "src/KPP-CRI-V2R5/KPP_Integrator.cpp")
la_path = os.path.join(base_dir, "src/KPP-CRI-V2R5/KPP_LinearAlgebra.cpp")

# 1. Restore files from kpp_cri/ to ensure clean state
print("Restoring clean files from kpp_cri...")
shutil.copy(os.path.join(kpp_cri_dir, "cri_Parameters.h"), param_path)
shutil.copy(os.path.join(kpp_cri_dir, "cri_Global.h"), global_h_path)
shutil.copy(os.path.join(kpp_cri_dir, "cri_Rates.c"), rates_path)
shutil.copy(os.path.join(kpp_cri_dir, "cri_Monitor.c"), monitor_path)
shutil.copy(os.path.join(kpp_cri_dir, "cri_Function.c"), function_path)
shutil.copy(os.path.join(kpp_cri_dir, "cri_Integrator.c"), integrator_path)
shutil.copy(os.path.join(kpp_cri_dir, "cri_LinearAlgebra.c"), la_path)

# 2. Extract equation rates block from function_path for ComputeRxnRates
print("Extracting equation rates from cri_Function.c...")
with open(function_path, 'r', encoding='utf-8') as f:
    func_lines = f.readlines()

rates_lines = []
inside_rates = False
for line in func_lines:
    if "/* Computation of equation rates */" in line:
        inside_rates = True
        continue
    if inside_rates:
        if "Vdot[" in line or "/* ~~~" in line or "/* Cumulative life time" in line:
            break
        # Replace the local A array with A_out
        patched_line = line.replace("  A[", "  A_out[")
        rates_lines.append(patched_line)

rates_calculation_code = "".join(rates_lines)

# 3. Patch KPP_Parameters.h
print(f"Patching {param_path}...")
with open(param_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("#define NLOOKAT              0", "#define NLOOKAT              1")
content = content.replace("#define NMONITOR             0", "#define NMONITOR             1")

# Remove PI macro which conflicts with namespace constants
content = re.sub(r'#define\s+PI\s+3\.14159265358979.*?\n', '/* Removed duplicate PI macro */\n', content)

# Clean header guards
content = content.replace("#ifndef __CRI_PARAMETERS_H__", "")
content = content.replace("#define __CRI_PARAMETERS_H__", "")
if content.strip().endswith("#endif"):
    content = content.strip()[:-6].strip()

header_guard = "#ifndef KPP_PARAMETERS_H_INCLUDED\n#define KPP_PARAMETERS_H_INCLUDED\n\n"
content = header_guard + content

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

/* Dummy indices for aerosol species used by EPM but not present in CRI */
#define ind_NACL             NSPEC
#define ind_AGI              NSPEC
#define ind_AL2O3            NSPEC
#define ind_CACO3            NSPEC
#define ind_DUST             NSPEC
#define ind_SO4              NSPEC

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

# 4. Write/Overwrite KPP_Global.cpp with correct variable definitions
print(f"Writing global definitions to {global_path}...")
global_cpp_content = """#include "KPP/KPP_Global.h"
#include "KPP/KPP_Parameters.h"

/* Definition of global chemistry variables for CRI-v2r5 */
double C[NSPECALL];
double * VAR = &C[0];
double * FIX = &C[NVAR];
double RCONST[NREACT];
double TIME;
int LOOKAT[1];
int MONITOR[1];
const char * SPC_NAMES[NSPEC];
const char * EQN_NAMES[NREACT];
char * EQN_TAGS[NREACT];

double NOON_JRATES[NPHOTOL];
double PHOTOL[NPHOTOL];
double HET[NSPEC][3];
double SZA_CST[3];

/* Additional solver variables defined in KPP_Global.h */
double SUN;
double TEMP;
double RTOLS;
double TSTART;
double TEND;
double DT;
double ATOL[NVAR];
double RTOL[NVAR];
double STEPMIN;
double STEPMAX;
double CFACTOR;
int DDMTYPE;
"""
with open(global_path, 'w', encoding='utf-8') as f:
    f.write(global_cpp_content)
print("Successfully wrote KPP_Global.cpp!")

# 5. Patch cri_Global.h to match KPP_Global.h and include threadprivate directives
print(f"Patching {global_h_path}...")
with open(global_h_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = '#include "KPP/KPP_Parameters.h"\n' + content
content = content.replace("extern double C[NSPEC];", "extern double C[NSPECALL];")
content = content.replace("extern int LOOKAT[NLOOKAT];", "extern int LOOKAT[1];")
content = content.replace("extern int MONITOR[NMONITOR];", "extern int MONITOR[1];")
content = content.replace("extern char * SPC_NAMES[NSPEC];", "extern const char * SPC_NAMES[NSPEC];")
content = content.replace("extern char * EQN_NAMES[NREACT];", "extern const char * EQN_NAMES[NREACT];")

# Add OMP threadprivate pragma with sized arrays to resolve incomplete type issues
content += """
/* Declarations of other variables present in KPP_Global.h to satisfy threadprivate pragma */
extern double TIME;
extern double SUN;
extern double TEMP;
extern double RTOLS;
extern double TSTART;
extern double TEND;
extern double DT;
extern double ATOL[NVAR];
extern double RTOL[NVAR];
extern double STEPMIN;
extern double STEPMAX;
extern double CFACTOR;
extern int DDMTYPE;
extern double NOON_JRATES[NPHOTOL];
extern double PHOTOL[NPHOTOL];
extern double HET[NSPEC][3];
extern double SZA_CST[3];

#pragma omp threadprivate( C, VAR, FIX, RCONST, TIME, SUN, TEMP, RTOLS, TSTART, TEND, DT, ATOL, RTOL, STEPMIN, STEPMAX, CFACTOR, DDMTYPE, NOON_JRATES, PHOTOL, HET, SZA_CST )
"""

with open(global_h_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Successfully patched cri_Global.h!")

# 6. Patch KPP_Monitor.cpp
print(f"Patching {monitor_path}...")
with open(monitor_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("char *  SPC_NAMES[] =", "const char *  SPC_NAMES[] =")
content = content.replace("char *  EQN_NAMES[] =", "const char *  EQN_NAMES[] =")

with open(monitor_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Successfully patched KPP_Monitor.cpp!")

# 7. Append ComputeRxnRates and ComputePL to KPP_Function.cpp
print(f"Appending diagnostics functions to {function_path}...")
with open(function_path, 'r', encoding='utf-8') as f:
    func_content = f.read()

diagnostics_impl = f"""

/* --- APCEMM diagnostics functions implementation --- */

#ifdef __cplusplus
extern "C" {{
#endif

void ComputeRxnRates( const double VAR[], const double FIX[],
                      double A_out[], int nReact )
{{
    double* V = const_cast<double*>(VAR);
    double* F = const_cast<double*>(FIX);
    (void)F;

    double* RCT = RCONST;

    /* ---- Reaction rate computation extracted from Fun ---- */
{rates_calculation_code}
}}

void ComputePL( const double VAR[], const double FIX[],
                double P[], double L[], int nVar )
{{
    double Vdot[NVAR];
    Fun( const_cast<double*>(VAR), const_cast<double*>(FIX), RCONST, Vdot );

    int n = (nVar < NVAR) ? nVar : NVAR;
    for (int i = 0; i < n; i++) {{
        P[i] = (Vdot[i] > 0.0) ?  Vdot[i] : 0.0;
        L[i] = (Vdot[i] < 0.0) ? -Vdot[i] : 0.0;
    }}
}}

#ifdef __cplusplus
}}
#endif
"""

with open(function_path, 'w', encoding='utf-8') as f:
    f.write(func_content + diagnostics_impl)
print("Successfully patched KPP_Function.cpp!")

# 8. Patch KPP_Rates.cpp (Prepend KPP/KPP.hpp for C linkage)
print(f"Patching {rates_path}...")
with open(rates_path, 'r', encoding='utf-8') as f:
    content = f.read()

top_functions = """#include "KPP/KPP_Global.h"
#include "KPP/KPP_Parameters.h"
#include "KPP/KPP.hpp"
#include <string>
#include <cmath>

#define J(x) PHOTOL[x]

double GCARR(double a, double b, double c, double TEMP) {
    return a * exp(-b/TEMP) * pow(TEMP/300.0, c);
}

double GCJPLPR( float A0, float B0, float C0, float A1, float B1, float C1, float FV, float FCT1, float FCT2, double AIRDENS, double TEMP )
{
    double JPLPR_RES;
    double K0, KINF;
    double FCT, XYRAT, BLOG, FEXP;

    K0   = GCARR( (double)A0, (double)B0, (double)C0, TEMP ) * AIRDENS;
    KINF = GCARR( (double)A1, (double)B1, (double)C1, TEMP );

    if ( FCT2 != 0 ) {
        FCT = exp( -TEMP / (double)FCT1 ) + exp( -(double)FCT2 / TEMP );
        XYRAT = K0/KINF;
        BLOG = log10(XYRAT);
        FEXP = 1.0E+00 / (1.0E+00 + BLOG * BLOG );
        JPLPR_RES = K0*pow( FCT, FEXP )/(1.0E+00+XYRAT);
    } else if ( FCT1 != 0 ) {
        FCT = exp( -TEMP / (double)FCT1 );
        XYRAT = K0/KINF;
        BLOG = log10(XYRAT);
        FEXP = 1.0E+00 / (1.0E+00 + BLOG * BLOG );
        JPLPR_RES = K0*pow( FCT, FEXP )/(1.0E+00 + XYRAT);
    } else {
        XYRAT = K0/KINF;
        BLOG = log10(XYRAT);
        FEXP = 1.0E+00 / (1.0E+00 + BLOG * BLOG );
        JPLPR_RES = K0*pow( (double)FV, FEXP)/(1.0E+00 + XYRAT);
    }
    return JPLPR_RES;
}

"""

if "#include <stdio.h>" in content:
    parts = content.split("#include <stdio.h>", 1)
    content = parts[0] + top_functions + "#include <stdio.h>" + parts[1]
else:
    content = top_functions + content
    
# Multi-line match using DOTALL flag
content = re.sub(r'void\s+Update_RCONST\s*\(\s*\)', 
                 'void Update_RCONST( const double TEMP, const double PRESS, const double AIRDENS, const double H2O )', 
                 content, flags=re.DOTALL)

kmt_calculations = """/* Begin INLINED RCONST                                             */

    double M = AIRDENS;
    double H2O_val = H2O;
    double N2 = 0.78 * M;
    double O2 = 0.21 * M;
    
    // Dynamically sum all organic peroxy radicals (RO2)
    double RO2 = 0.0;
    for (int i = 0; i < NSPEC; i++) {
        std::string name = SPC_NAMES[i];
        if (name.find("O2") != std::string::npos && name != "HO2" && name != "NO2" && name != "SO2" && name != "O2" && name != "RO2") {
            RO2 += C[i];
        }
    }

    double K14ISOM1 = 3.00E7*exp(-5300./TEMP);
    double KAPHO2 = 5.2E-13*exp(980./TEMP);
    double KAPNO = 7.5E-12*exp(290./TEMP);
    double KCH3O2 = 1.03E-13*exp(365./TEMP);
    double KRO2HO2 = 2.91E-13*exp(1300./TEMP);
    double KRO2NO = 2.7E-12*exp(360./TEMP);
    double KRO2NO3 = 2.3E-12;
    double KHO2 = KRO2HO2*C[ind_HO2]*0.706;
    double KNO = KRO2NO*C[ind_NO];
    double KNO3 = KRO2NO3*C[ind_NO3];
    double KRO2 = 1.26E-12*RO2;
    double KTR = KNO + KHO2 + KRO2 + KNO3;
    double K16ISOM = (KTR*5.18E-04*exp(1308./TEMP)) +(2.76E+07*exp(-6759./TEMP));

    double FCD = 0.30;
    double KD0 = 1.10E-05*M*exp(-10100./TEMP);
    double KDI = 1.90E17*exp(-14100./TEMP);
    double KRD = KD0/KDI;
    double NCD = 0.75-1.27*(log10(FCD));
    double FD = pow(10., (log10(FCD)/(1.+(pow(log10(KRD)/NCD, 2.)))));
    double KBPAN = (KD0*KDI)*FD/(KD0+KDI);

    double FCC = 0.30;
    double KC0 = 3.28E-28*M*pow(TEMP/300., -6.87);
    double KCI = 1.125E-11*pow(TEMP/300., -1.105);
    double KRC = KC0/KCI;
    double NC = 0.75-1.27*(log10(FCC));
    double FC = pow(10., (log10(FCC)/(1.+(pow(log10(KRC)/NC, 2.)))));
    double KFPAN = (KC0*KCI)*FC/(KC0+KCI);

    double KMT05 = 1.44E-13*(1.+(M/4.2E+19));
    double KMT06 = 1. + (1.40E-21*exp(2200./TEMP)*H2O_val);
    double KNO3AL = 1.44E-12*exp(-1862./TEMP);
    
    double FC1 = 0.85;
    double K10 = 1.0E-31*M*pow(TEMP/300., -1.6);
    double K1I = 5.0E-11*pow(TEMP/300., -0.3);
    double KR1 = K10/K1I;
    double NC1 = 0.75-1.27*(log10(FC1));
    double F1 = pow(10., (log10(FC1)/(1.+pow(log10(KR1)/NC1, 2.))));
    double KMT01 = (K10*K1I)*F1/(K10+K1I);
    
    double FC2 = 0.6;
    double K20 = 1.3E-31*M*pow(TEMP/300., -1.5);
    double K2I = 2.3E-11*pow(TEMP/300., 0.24);
    double KR2 = K20/K2I;
    double NC2 = 0.75-1.27*(log10(FC2));
    double F2 = pow(10., (log10(FC2)/(1.+pow(log10(KR2)/NC2, 2.))));
    double KMT02 = (K20*K2I)*F2/(K20+K2I);
    
    double FC3 = 0.35;
    double K30 = 3.6E-30*M*pow(TEMP/300., -4.1);
    double K3I = 1.9E-12*pow(TEMP/300., 0.2);
    double KR3 = K30/K3I;
    double NC3 = 0.75-1.27*(log10(FC3));
    double F3 = pow(10., (log10(FC3)/(1.+pow(log10(KR3)/NC3, 2.))));
    double KMT03 = (K30*K3I)*F3/(K30+K3I);
    
    double FC4 = 0.35;
    double K40 = 1.3E-3*M*pow(TEMP/300., -3.5)*exp(-11000./TEMP);
    double K4I = 9.7E+14*pow(TEMP/300., 0.1)*exp(-11080./TEMP);
    double KR4 = K40/K4I;
    double NC4 = 0.75-1.27*(log10(FC4));
    double F4 = pow(10., (log10(FC4)/(1.+pow(log10(KR4)/NC4, 2.))));
    double KMT04 = (K40*K4I)*F4/(K40+K4I);
    
    double FC7 = 0.81;
    double K70 = 7.4E-31*M*pow(TEMP/300., -2.4);
    double K7I = 3.3E-11*pow(TEMP/300., -0.3);
    double KR7 = K70/K7I;
    double NC7 = 0.75-1.27*(log10(FC7));
    double F7 = pow(10., (log10(FC7)/(1.+pow(log10(KR7)/NC7, 2.))));
    double KMT07 = (K70*K7I)*F7/(K70+K7I);
    
    double FC8 = 0.41;
    double K80 = 3.2E-30*M*pow(TEMP/300., -4.5);
    double K8I = 3.0E-11;
    double KR8 = K80/K8I;
    double NC8 = 0.75-1.27*(log10(FC8));
    double F8 = pow(10., (log10(FC8)/(1.+pow(log10(KR8)/NC8, 2.))));
    double KMT08 = (K80*K8I)*F8/(K80+K8I);
    
    double FC9 = 0.4;
    double K90 = 1.4E-31*M*pow(TEMP/300., -3.1);
    double K9I = 4.0E-12;
    double KR9 = K90/K9I;
    double NC9 = 0.75-1.27*(log10(FC9));
    double F9 = pow(10., (log10(FC9)/(1.+pow(log10(KR9)/NC9, 2.))));
    double KMT09 = (K90*K9I)*F9/(K90+K9I);
    
    double FC10 = 0.4;
    double K100 = 4.10E-05*M*exp(-10650./TEMP);
    double K10I = 6.0E+15*exp(-11170./TEMP);
    double KR10 = K100/K10I;
    double NC10 = 0.75-1.27*(log10(FC10));
    double F10 = pow(10., (log10(FC10)/(1.+pow(log10(KR10)/NC10, 2.))));
    double KMT10 = (K100*K10I)*F10/(K100+K10I);
    
    double K3_val = 6.50E-34*exp(1335./TEMP);
    double K4_val = 2.70E-17*exp(2199./TEMP);
    double K1_val = 2.40E-14*exp(460./TEMP);
    double K2_val = (K3_val*M)/(1.+(K3_val*M/K4_val));
    double KMT11 = K1_val + K2_val;
    
    double FC12 = 0.53;
    double K120 = 2.5E-31*M*pow(TEMP/300., -2.6);
    double K12I = 2.0E-12;
    double KR12 = K120/K12I;
    double NC12 = 0.75-1.27*(log10(FC12));
    double F12 = pow(10., (log10(FC12)/(1.0+pow(log10(KR12)/NC12, 2.))));
    double KMT12 = (K120*K12I*F12)/(K120+K12I);
    
    double FC15 = 0.48;
    double K150 = 8.6E-29*M*pow(TEMP/300., -3.1);
    double K15I = 9.0E-12*pow(TEMP/300., -0.85);
    double KR15 = K150/K15I;
    double NC15 = 0.75-1.27*(log10(FC15));
    double F15 = pow(10., (log10(FC15)/(1.+pow(log10(KR15)/NC15, 2.))));
    double KMT15 = (K150*K15I)*F15/(K150+K15I);
    
    double FC16 = 0.5;
    double K160 = 8.E-27*M*pow(TEMP/300., -3.5);
    double K16I = 3.0E-11*pow(TEMP/300., -1.);
    double KR16 = K160/K16I;
    double NC16 = 0.75-1.27*(log10(FC16));
    double F16 = pow(10., (log10(FC16)/(1.+pow(log10(KR16)/NC16, 2.))));
    double KMT16 = (K160*K16I)*F16/(K160+K16I);
    
    double FC17 = 0.17*exp(-51./TEMP)+exp(-TEMP/204.);
    double K170 = 5.0E-30*M*pow(TEMP/300., -1.5);
    double K17I = 1.0E-12;
    double KR17 = K170/K17I;
    double NC17 = 0.75-1.27*(log10(FC17));
    double F17 = pow(10., (log10(FC17)/(1.0+pow(log10(KR17)/NC17, 2.))));
    double KMT17 = (K170*K17I*F17)/(K170+K17I);

    double KMT20 = GCJPLPR(2.00E-31, 3.4, 0.0, 2.9e-12, 1.1, 0.0, 0.6, 0.0, 0.0, AIRDENS, TEMP);
    double KMT22 = GCJPLPR(9.52E-05, 3.4, -10900.0, 1.38E15, 1.1, -10900.0, 0.6, 0.0, 0.0, AIRDENS, TEMP);
    double KMT21 = GCJPLPR(7.00E-31, 2.6, 0.0, 3.60E-11, 0.1, 0.0, 0.6, 0.0, 0.0, AIRDENS, TEMP);
    double KMT23 = GCJPLPR(9.52E-05, 2.6, -10900.0, 1.38E15, 0.1, -10900.0, 0.6, 0.0, 0.0, AIRDENS, TEMP);
"""

if "/* Begin INLINED RCONST" in content:
    parts = content.split("/* Begin INLINED RCONST", 1)
    right_part = parts[1]
    if "/* End INLINED RCONST" in right_part:
        subparts = right_part.split("/* End INLINED RCONST", 1)
        content = parts[0] + kmt_calculations + "/* End INLINED RCONST" + subparts[1]
    else:
        content = parts[0] + kmt_calculations + parts[1]

# Fix the specific split-line KPP wrapping bugs
content = content.replace("*(TEMP/30\n                0.)**(-2.6)", "*pow(TEMP/300.0, -2.6)")
content = content.replace("EXP(98\n                0./TEMP)", "exp(980.0/TEMP)")
content = content.replace("EXP(", "exp(")

with open(rates_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Successfully patched KPP_Rates.cpp!")

# 9. Read and rewrite KPP_Integrator.cpp to replace the INTEGRATE function and comment out Update_RCONST()
print(f"Patching {integrator_path}...")
with open(integrator_path, 'r', encoding='utf-8') as f:
    int_content = f.read()

# Comment out parameter-less Update_RCONST declarations and calls cleanly using C++ style comments
int_content = int_content.replace("void Update_RCONST();", "// void Update_RCONST();")
int_content = int_content.replace("Update_RCONST();", "// Update_RCONST();")

# Replace the signature and body of INTEGRATE
pattern = r'void\s+INTEGRATE\s*\(\s*double\s+TIN\s*,\s*double\s+TOUT\s*\).*?/\*\s*INTEGRATE\s*\*/'
replacement = """int INTEGRATE( double VAR_param[] , double FIX_param[], double TIN   , double TOUT,
               double ATOL_param[], double RTOL_param[], double STEPMIN_param )
/*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*/
{
   static double  RPAR[20];
   static int  i, IERR, IPAR[20];
   static int Ns=0, Na=0, Nr=0, Ng=0;
   #pragma omp threadprivate( RPAR )
   #pragma omp threadprivate( i, IERR, IPAR )
   #pragma omp threadprivate( Ns, Na, Nr, Ng )

   (void)FIX_param;

   for ( i = 0; i < 20; i++ ) {
     IPAR[i] = 0;
     RPAR[i] = ZERO;
   } /* for */
   
   IPAR[0] = 0;    /* non-autonomous */
   IPAR[1] = 1;    /* vector tolerances */
   RPAR[2] = STEPMIN_param; /* starting step */
   IPAR[3] = 5;    /* choice of the method */

   IERR = Rosenbrock(VAR_param, TIN, TOUT,
           ATOL_param, RTOL_param,
           &FunTemplate, &JacTemplate,
           RPAR, IPAR);
	     
   Ns=Ns+IPAR[12];
   Na=Na+IPAR[13];
   Nr=Nr+IPAR[14];
   Ng=Ng+IPAR[17];

   return IERR;
} /* INTEGRATE */"""

int_content_patched = re.sub(pattern, replacement, int_content, flags=re.DOTALL)

# Prepend include to top
int_content_patched = '#include "KPP/KPP.hpp"\n' + int_content_patched

with open(integrator_path, 'w', encoding='utf-8') as f:
    f.write(int_content_patched)
print("Successfully patched KPP_Integrator.cpp!")

# 10. Patch KPP_LinearAlgebra.cpp to define KppSolve as wrapper to cri_KppSolve
print(f"Patching {la_path}...")
with open(la_path, 'a', encoding='utf-8') as f:
    f.write("\n\n/* Wrapper function to satisfy KppSolve reference */\n")
    f.write('extern "C" void KppSolve( double A[], double b[] ) {\n')
    f.write('    cri_KppSolve(A, b);\n')
    f.write('}\n')
print("Successfully patched KPP_LinearAlgebra.cpp!")
