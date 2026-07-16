#!/usr/bin/env python3
import glob
import os
import shutil
import re

base_path = "/projects/b35as/public/HAPCEMM-Chem/Code.v05-00"

print("Starting CRI-V2R5 mechanism fix script...")

# 1. Clean up the nested directories
for path in [
    os.path.join(base_path, 'include/KPP-CRI-V2R5/KPP'),
    os.path.join(base_path, 'include/KPP-UCX/KPP')
]:
    if os.path.exists(path):
        shutil.rmtree(path)
        print(f"Removed nested directory: {path}")
    else:
        print(f"Nested directory not present: {path}")

# 2. Update include/KPP-CRI-V2R5/KPP_Parameters.h
params_path = os.path.join(base_path, 'include/KPP-CRI-V2R5/KPP_Parameters.h')
if os.path.exists(params_path):
    with open(params_path, 'r', encoding='utf-8') as fh:
        c = fh.read()
    
    # Inject index declarations for additional species referenced in microphysics/Solution code
    # and increase NSPECALL size accordingly to prevent out-of-bounds errors.
    c = re.sub(
        r'#define\s+NSPECALL\s+NSPEC\+14\b',
        '#define ind_SO4      NSPEC+14\n'
        '#define ind_CACO3    NSPEC+15\n'
        '#define ind_AL2O3    NSPEC+16\n'
        '#define ind_NACL     NSPEC+17\n'
        '#define ind_AGI      NSPEC+18\n'
        '#define ind_DUST     NSPEC+19\n'
        '#define NSPECALL     NSPEC+20',
        c
    )

    # Clean out any previous guards, NAERO, NPHOTOL, PI, or J definitions to start fresh
    lines = c.splitlines()
    clean_lines = []
    for line in lines:
        sline = line.strip()
        if re.match(r'^#define\s+PI\b', sline):
            continue
        if any(keyword in line for keyword in [
            'KPP_PARAMETERS_H_INCLUDED',
            '#define NAERO',
            '#define NPHOTOL',
            '#define NOPT',
            '#define PSC',
            '#define J(',
            '#define J_O3_',
            '#define J_H2O2',
            '#define J_NO2',
            '#define J_NO3_',
            '#define J_HONO',
            '#define J_HNO3',
            '#define J_HCHO_',
            '#define J_CH3CHO',
            '#define J_C2H5CHO',
            '#define J_C3H7CHO_',
            '#define J_IPRCHO',
            '#define J_MACR_',
            '#define J_C5HPALD1',
            '#define J_CH3COCH3',
            '#define J_MEK',
            '#define J_MVK_',
            '#define J_GLYOX_',
            '#define J_MGLYOX',
            '#define J_BIACET',
            '#define J_CH3OOH',
            '#define J_CH3NO3',
            '#define J_C2H5NO3',
            '#define J_NC3H7NO3',
            '#define J_IC3H7NO3',
            '#define J_TC4H9NO3',
            '#define J_NOA'
        ]):
            continue
        clean_lines.append(line)

    # Find the end of header comment block to insert guard macro definition
    header_comment_end = 0
    for idx, line in enumerate(clean_lines):
        if '/* ~~~~~' in line and idx > 15:
            header_comment_end = idx + 1
            break
    if header_comment_end == 0:
        header_comment_end = 20

    body = clean_lines[header_comment_end:]
    
    # Replace NLOOKAT and NMONITOR definitions to be 1 instead of 0
    updated_body = []
    for line in body:
        if '#define NLOOKAT' in line:
            updated_body.append('#define NLOOKAT              1           /* Number of species to look at (redefined to 1 for C++ array compatibility) */')
        elif '#define NMONITOR' in line:
            updated_body.append('#define NMONITOR             1           /* Number of species to monitor (redefined to 1 for C++ array compatibility) */')
        else:
            updated_body.append(line)
    body = updated_body

    body.append('#define NOPT                 3')
    body.append('#define NAERO                4')
    body.append('#define NPHOTOL              114')
    body.append('#define PSC                  1           /* Consider PSCs? (added manually) */')
    body.append('')
    body.append('/* Dummy definitions for missing gas-phase species to prevent heterogeneous chemistry compilation failures */')
    body.append('#ifndef ind_HCl')
    body.append('#define ind_HCl 0')
    body.append('#endif')
    body.append('#ifndef ind_HOCl')
    body.append('#define ind_HOCl 0')
    body.append('#endif')
    body.append('#ifndef ind_ClNO3')
    body.append('#define ind_ClNO3 0')
    body.append('#endif')
    body.append('#ifndef ind_HBr')
    body.append('#define ind_HBr 0')
    body.append('#endif')
    body.append('#ifndef ind_HOBr')
    body.append('#define ind_HOBr 0')
    body.append('#endif')
    body.append('#ifndef ind_BrNO3')
    body.append('#define ind_BrNO3 0')
    body.append('#endif')
    body.append('#ifndef ind_H2SO4')
    body.append('#define ind_H2SO4 0')
    body.append('#endif')
    body.append('#ifndef ind_H2O')
    body.append('#define ind_H2O NSPEC')
    body.append('#endif')
    body.append('')
    body.append('#define J_O3_O1D             0')
    body.append('#define J_O3_O3P             1')
    body.append('#define J_H2O2               2')
    body.append('#define J_NO2                3')
    body.append('#define J_NO3_NO             4')
    body.append('#define J_NO3_NO2            5')
    body.append('#define J_HONO               6')
    body.append('#define J_HNO3               7')
    body.append('#define J_HCHO_H             8')
    body.append('#define J_HCHO_H2            9')
    body.append('#define J_CH3CHO             10')
    body.append('#define J_C2H5CHO            11')
    body.append('#define J_C3H7CHO_HCO        12')
    body.append('#define J_C3H7CHO_C2H4       13')
    body.append('#define J_IPRCHO             14')
    body.append('#define J_MACR_HCO           15')
    body.append('#define J_MACR_H             16')
    body.append('#define J_C5HPALD1           17')
    body.append('#define J_CH3COCH3           18')
    body.append('#define J_MEK                19')
    body.append('#define J_MVK_CO             20')
    body.append('#define J_MVK_C2H3           21')
    body.append('#define J_GLYOX_H2           22')
    body.append('#define J_GLYOX_HCHO         23')
    body.append('#define J_GLYOX_HCO          24')
    body.append('#define J_MGLYOX             25')
    body.append('#define J_BIACET             26')
    body.append('#define J_CH3OOH             27')
    body.append('#define J_CH3NO3             28')
    body.append('#define J_C2H5NO3            29')
    body.append('#define J_NC3H7NO3           30')
    body.append('#define J_IC3H7NO3           31')
    body.append('#define J_TC4H9NO3           32')
    body.append('#define J_NOA                33')

    new_lines = clean_lines[:header_comment_end] + [
        '',
        '#ifndef KPP_PARAMETERS_H_INCLUDED',
        '#define KPP_PARAMETERS_H_INCLUDED',
        ''
    ] + body + [
        '',
        '#endif /* KPP_PARAMETERS_H_INCLUDED */'
    ]
    with open(params_path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(new_lines) + '\n')
    print("Updated KPP_Parameters.h with guards, NAERO, NPHOTOL, NOPT, PSC, and J macro maps.")
else:
    print(f"Error: KPP_Parameters.h not found at {params_path}!")

# 3. Create the corrected include/KPP-CRI-V2R5/KPP_Global.h
global_path = os.path.join(base_path, 'include/KPP-CRI-V2R5/KPP_Global.h')
kpp_global_content = """#ifndef KPP_GLOBAL_H_INCLUDED
#define KPP_GLOBAL_H_INCLUDED

#include "omp.h"
#include "KPP/KPP_Parameters.h"

/* Declaration of global variables                                  */

extern double C[NSPECALL];                         /* Concentration of all species */
extern double * VAR;
extern double * FIX;
extern double RCONST[NREACT];                   /* Rate constants (global) */
extern double TIME;                             /* Current integration time */
extern double SUN;                              /* Sunlight intensity between [0,1] */
extern double TEMP;                             /* Temperature */
extern double RTOLS;                            /* (scalar) Relative tolerance */
extern double TSTART;                           /* Integration start time */
extern double TEND;                             /* Integration end time */
extern double DT;                               /* Integration step */
extern double ATOL[NSPEC];                      /* Absolute tolerance */
extern double RTOL[NSPEC];                      /* Relative tolerance */
extern double STEPMIN;                          /* Lower bound for integration step */
extern double STEPMAX;                          /* Upper bound for integration step */
extern double CFACTOR;                          /* Conversion factor for concentration units */
extern int DDMTYPE;                             /* DDM sensitivity w.r.t.: 0=init.val., 1=params */
extern int LOOKAT[NLOOKAT];                     /* Indexes of species to look at */
extern int MONITOR[NMONITOR];                   /* Indexes of species to monitor */
extern const char * SPC_NAMES[NSPEC];           /* Names of chemical species (const char*) */
extern char * SMASS[NMASS];                     /* Names of atoms for mass balance */
extern const char * EQN_NAMES[NREACT];          /* Equation names (const char*) */
extern char * EQN_TAGS[NREACT];                 /* Equation tags */

/* INLINED global variable declarations                             */

extern double NOON_JRATES[NPHOTOL];             /* Noon-time photolysis rates */
extern double PHOTOL[NPHOTOL];                  /* Photolysis rates */
extern double HET[NSPEC][3];                    /* Heterogeneous reaction rates */
extern double SZA_CST[3];                       /* Constants to compute cosSZA */

/* The following variables need to be declared THREADPRIVATE
 * because they get written to within an OpenMP parallel loop */
#pragma omp threadprivate( C, VAR, FIX, RCONST, TIME, SUN, TEMP, RTOLS, TSTART, TEND, DT, ATOL, RTOL, STEPMIN, STEPMAX, CFACTOR, DDMTYPE, NOON_JRATES, PHOTOL, HET, SZA_CST )

#endif /* KPP_GLOBAL_H_INCLUDED */
"""

with open(global_path, 'w', encoding='utf-8') as fh:
    fh.write(kpp_global_content)
print("Rewrote KPP_Global.h with threadprivates and type fixes.")

# 3b. Patch src/KPP-CRI-V2R5/KPP_Global.cpp
global_cpp_path = os.path.join(base_path, 'src/KPP-CRI-V2R5/KPP_Global.cpp')
if os.path.exists(global_cpp_path):
    with open(global_cpp_path, 'r', encoding='utf-8') as fh:
        c = fh.read()
    c = c.replace('double C[NSPEC];', 'double C[NSPECALL];')
    
    # Append the missing globals if they aren't already there
    if 'double SUN;' not in c:
        c += "\n\n/* Added by fix script to resolve missing globals */\n"
        c += "double SUN;\n"
        c += "double TEMP;\n"
        c += "double RTOLS;\n"
        c += "double TSTART;\n"
        c += "double TEND;\n"
        c += "double DT;\n"
        c += "double ATOL[NSPEC];\n"
        c += "double RTOL[NSPEC];\n"
        c += "double STEPMIN;\n"
        c += "double STEPMAX;\n"
        c += "double CFACTOR;\n"
        c += "int DDMTYPE;\n"
        c += "int MONITOR[NMONITOR];\n"

    with open(global_cpp_path, 'w', encoding='utf-8') as fh:
        fh.write(c)
    print("Patched KPP_Global.cpp to size array C to NSPECALL and define missing globals.")

# 3c. Patch src/KPP-CRI-V2R5/KPP_Main_ADJ.cpp
main_adj_path = os.path.join(base_path, 'src/KPP-CRI-V2R5/KPP_Main_ADJ.cpp')
if os.path.exists(main_adj_path):
    with open(main_adj_path, 'r', encoding='utf-8') as fh:
        c = fh.read()
    c = c.replace('double VAR_RUN[NVAR];', 'double VAR_RUN[NSPECALL];')
    with open(main_adj_path, 'w', encoding='utf-8') as fh:
        fh.write(c)
    print("Patched KPP_Main_ADJ.cpp to size array VAR_RUN to NSPECALL.")

# 4. Replace all "cri_Parameters.h", "cri_Global.h", "cri_Sparse.h" in src/KPP-CRI-V2R5/*.cpp
cpp_files = glob.glob(os.path.join(base_path, 'src/KPP-CRI-V2R5/*.cpp'))
for f in cpp_files:
    with open(f, 'r', encoding='utf-8') as fh:
        c = fh.read()
    updated = False
    for old, new in [
        ('cri_Parameters.h', 'KPP/KPP_Parameters.h'),
        ('cri_Global.h', 'KPP/KPP_Global.h'),
        ('cri_Sparse.h', 'KPP/KPP_Sparse.h')
    ]:
        if old in c:
            c = c.replace(old, new)
            updated = True
    
    # Inject KPP.hpp include if not present to ensure C linkage (extern "C") matching KPP.hpp declarations
    if 'KPP/KPP.hpp' not in c:
        for header in ['KPP/KPP_Global.h', 'KPP/KPP_Parameters.h']:
            if f'#include "{header}"' in c:
                c = c.replace(f'#include "{header}"', f'#include "{header}"\n#include "KPP/KPP.hpp"')
                updated = True
                break
                
    if updated:
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write(c)
        print(f"Patched header includes in {os.path.basename(f)}")

# 5. Patch KPP_Rates.cpp
rates_path = os.path.join(base_path, 'src/KPP-CRI-V2R5/KPP_Rates.cpp')
if os.path.exists(rates_path):
    with open(rates_path, 'r', encoding='utf-8') as fh:
        c = fh.read()
    
    # 5a. First merge split lines in KPP_Rates.cpp
    lines = c.splitlines()
    merged_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        while line.strip().startswith("RCONST[") and not line.strip().endswith(";") and i + 1 < len(lines):
            next_line = lines[i+1]
            line = line.rstrip() + next_line.strip()
            i += 1
        merged_lines.append(line)
        i += 1
    c = "\n".join(merged_lines)
    
    # Remove spaces in the middle of split numbers (e.g. "30 0." -> "300.", "98 0." -> "980.")
    c = re.sub(r'(\b[0-9]+)\s+([0-9]+\b)', r'\1\2', c)
    
    # 5b. Define the full injected block containing all declarations and custom calculations.
    injected_block = """void Update_RCONST( const double TEMP, const double PRESS, const double AIRDENS, const double H2O )
{
  double M = AIRDENS;
  double O2 = 0.2095 * AIRDENS;
  double N2 = 0.7808 * AIRDENS;

  double RO2 = C[ind_CH3O2] + C[ind_C2H5O2] + C[ind_IC3H7O2] + C[ind_RN10O2] + \\
      C[ind_RN13O2] + C[ind_RN16O2] + C[ind_RN19O2] + C[ind_RN22O2] + \\
      C[ind_RN25O2] + C[ind_RN28O2] + C[ind_RN31O2] + C[ind_RN34O2] + \\
      C[ind_RN37O2] + C[ind_RI13O2] + C[ind_RI16O2] + C[ind_RI16AO2] + \\
      C[ind_RN19BO2] + C[ind_RI19O2] + C[ind_RN19AO2] + C[ind_RN22AO2] + \\
      C[ind_RC18O2] + C[ind_HOCH2CH2O2] + C[ind_RN9O2] + C[ind_RN12O2] + \\
      C[ind_RN15O2] + C[ind_RN18O2] + C[ind_RI12O2] + C[ind_RN15AO2] + \\
      C[ind_RI15O2] + C[ind_NRN6O2] + C[ind_NRN9O2] + C[ind_NRN12O2] + \\
      C[ind_NRN15O2] + C[ind_NRN18O2] + C[ind_NRI12O2] + C[ind_NRI15O2] + \\
      C[ind_RN8O2] + C[ind_RU11O2] + C[ind_RU14O2] + C[ind_NRU14O2] + \\
      C[ind_RTN28O2] + C[ind_NRTN28O2] + C[ind_RN18AO2] + C[ind_RTX28O2] + \\
      C[ind_NRTX28O2] + C[ind_RTX24O2] + C[ind_RA13O2] + C[ind_RA16O2] + \\
      C[ind_RA19AO2] + C[ind_RA19CO2] + C[ind_RA19BO2] + C[ind_RA22AO2] + \\
      C[ind_RA22BO2] + C[ind_RA25O2] + C[ind_RA28O2] + C[ind_RUA20O2] + \\
      C[ind_NRUA20O2] + C[ind_RA16BO2] + C[ind_CH3CO3] + C[ind_C2H5CO3] + \\
      C[ind_RN11O2] + C[ind_RI11O2] + C[ind_RN14O2] + C[ind_RI14O2] + \\
      C[ind_RN17O2] + C[ind_RI17O2] + C[ind_RC16O2] + C[ind_RN16AO2] + \\
      C[ind_RE6O2] + C[ind_RE12O2] + C[ind_RE15O2] + C[ind_RE18O2] + \\
      C[ind_RN13AO2] + C[ind_RN21AO2] + C[ind_RN24AO2] + C[ind_RN27AO2] + \\
      C[ind_RN30AO2] + C[ind_RN33AO2] + C[ind_RN36AO2] + C[ind_RN21O2] + \\
      C[ind_RN24O2] + C[ind_RN25AO2] + C[ind_RN27O2] + C[ind_RN28AO2] + \\
      C[ind_RN30O2] + C[ind_RN31AO2] + C[ind_RN33O2] + C[ind_RN34AO2] + \\
      C[ind_RN36O2] + C[ind_RC14O2] + C[ind_HOCH2CO3] + C[ind_RN20O2] + \\
      C[ind_RN23O2] + C[ind_RN26O2] + C[ind_RN29O2] + C[ind_RN32O2] + \\
      C[ind_RN35O2] + C[ind_RU12O2] + C[ind_RU10O2] + C[ind_NRU12O2] + \\
      C[ind_RTN25O2] + C[ind_RTN26O2] + C[ind_RTN24O2] + C[ind_RTN23O2] + \\
      C[ind_RTN14O2] + C[ind_RTN10O2] + C[ind_RTX22O2] + C[ind_MACO3] + \\
      C[ind_DHPR12O2] + C[ind_RU10AO2];

  double K14ISOM1 = 3.00E7*exp(-5300./TEMP);
  double K298CH3O2 = 3.5E-13;
  double KAPHO2 = 5.2E-13*exp(980./TEMP);
  double KAPNO = 7.5E-12*exp(290./TEMP);
  double KCH3O2 = 1.03E-13*exp(365./TEMP);
  double KDEC = 1.00E+06;
  double KMT05 = 1.44E-13*(1.+(M/4.2E+19));
  double KMT06 = 1. + (1.40E-21*exp(2200./TEMP)*H2O);
  double KMT18 = 9.5E-39*O2*exp(5270./TEMP)/(1.+7.5E-29*O2*exp(5610./TEMP));
  double KNO3AL = 1.44E-12*exp(-1862./TEMP);
  double KRO2HO2 = 2.91E-13*exp(1300./TEMP);
  double KRO2NO = 2.7E-12*exp(360./TEMP);
  double KRO2NO3 = 2.3E-12;
  double KROPRIM = 2.50E-14*exp(-300./TEMP);
  double KROSEC = 2.50E-14*exp(-300./TEMP);
  double FCD = 0.30;
  double KD0 = 1.10E-05*M*exp(-10100./TEMP);
  double KDI = 1.90E17*exp(-14100./TEMP);
  double KRD = KD0/KDI;
  double NCD = 0.75-1.27*(log10(FCD));
  double FD = pow(10.,(log10(FCD)/(1.+pow((log10(KRD)/NCD),2.))));
  double KBPAN = (KD0*KDI)*FD/(KD0+KDI);
  double FCPPN = 0.36;
  double KPPN0 = 1.7E-03*exp(-11280./TEMP)*M;
  double KPPNI = 8.3E+16*exp(-13940./TEMP);
  double KRPPN = KPPN0/KPPNI;
  double NCPPN = 0.75-1.27*(log10(FCPPN));
  double FPPN = pow(10.,(log10(FCPPN)/(1.+pow((log10(KRPPN)/NCPPN),2.))));
  double KBPPN = (KPPN0*KPPNI)*FPPN/(KPPN0+KPPNI);
  double FCC = 0.30;
  double KC0 = 3.28E-28*M*pow((TEMP/300.),-6.87);
  double KCI = 1.125E-11*pow((TEMP/300.),-1.105);
  double KRC = KC0/KCI;
  double NC = 0.75-1.27*(log10(FCC));
  double FC = pow(10.,(log10(FCC)/(1.+pow((log10(KRC)/NC),2.))));
  double KFPAN = (KC0*KCI)*FC/(KC0+KCI);
  double FC1 = 0.85;
  double K10 = 1.0E-31*M*pow((TEMP/300.),-1.6);
  double K1I = 5.0E-11*pow((TEMP/300.),-0.3);
  double KR1 = K10/K1I;
  double NC1 = 0.75-1.27*(log10(FC1));
  double F1 = pow(10.,(log10(FC1)/(1.+pow((log10(KR1)/NC1),2.))));
  double KMT01 = (K10*K1I)*F1/(K10+K1I);
  double FC2 = 0.6;
  double K20 = 1.3E-31*M*pow((TEMP/300.),-1.5);
  double K2I = 2.3E-11*pow((TEMP/300.),0.24);
  double KR2 = K20/K2I;
  double NC2 = 0.75-1.27*(log10(FC2));
  double F2 = pow(10.,(log10(FC2)/(1.+pow((log10(KR2)/NC2),2.))));
  double KMT02 = (K20*K2I)*F2/(K20+K2I);
  double FC3 = 0.35;
  double K30 = 3.6E-30*M*pow((TEMP/300.),-4.1);
  double K3I = 1.9E-12*pow((TEMP/300.),0.2);
  double KR3 = K30/K3I;
  double NC3 = 0.75-1.27*(log10(FC3));
  double F3 = pow(10.,(log10(FC3)/(1.+pow((log10(KR3)/NC3),2.))));
  double KMT03 = (K30*K3I)*F3/(K30+K3I);
  double FC4 = 0.35;
  double K40 = 1.3E-3*M*pow((TEMP/300.),-3.5)*exp(-11000./TEMP);
  double K4I = 9.7E+14*pow((TEMP/300.),0.1)*exp(-11080./TEMP);
  double KR4 = K40/K4I;
  double NC4 = 0.75-1.27*(log10(FC4));
  double F4 = pow(10.,(log10(FC4)/(1.+pow((log10(KR4)/NC4),2.))));
  double KMT04 = (K40*K4I)*F4/(K40+K4I);
  double FC7 = 0.81;
  double K70 = 7.4E-31*M*pow((TEMP/300.),-2.4);
  double K7I = 3.3E-11*pow((TEMP/300.),-0.3);
  double KR7 = K70/K7I;
  double NC7 = 0.75-1.27*(log10(FC7));
  double F7 = pow(10.,(log10(FC7)/(1.+pow((log10(KR7)/NC7),2.))));
  double KMT07 = (K70*K7I)*F7/(K70+K7I);
  double FC8 = 0.41;
  double K80 = 3.2E-30*M*pow((TEMP/300.),-4.5);
  double K8I = 3.0E-11;
  double KR8 = K80/K8I;
  double NC8 = 0.75-1.27*(log10(FC8));
  double F8 = pow(10.,(log10(FC8)/(1.+pow((log10(KR8)/NC8),2.))));
  double KMT08 = (K80*K8I)*F8/(K80+K8I);
  double FC9 = 0.4;
  double K90 = 1.4E-31*M*pow((TEMP/300.),-3.1);
  double K9I = 4.0E-12;
  double KR9 = K90/K9I;
  double NC9 = 0.75-1.27*(log10(FC9));
  double F9 = pow(10.,(log10(FC9)/(1.+pow((log10(KR9)/NC9),2.))));
  double KMT09 = (K90*K9I)*F9/(K90+K9I);
  double FC10 = 0.4;
  double K100 = 4.10E-05*M*exp(-10650./TEMP);
  double K10I = 6.0E+15*exp(-11170./TEMP);
  double KR10 = K100/K10I;
  double NC10 = 0.75-1.27*(log10(FC10));
  double F10 = pow(10.,(log10(FC10)/(1.+pow((log10(KR10)/NC10),2.))));
  double KMT10 = (K100*K10I)*F10/(K100+K10I);
  double K3_const = 6.50E-34*exp(1335./TEMP);
  double K4_const = 2.70E-17*exp(2199./TEMP);
  double K1_const = 2.40E-14*exp(460./TEMP);
  double K2_const = (K3_const*M)/(1.+(K3_const*M/K4_const));
  double KMT11 = K1_const + K2_const;
  double FC12 = 0.53;
  double K120 = 2.5E-31*M*pow((TEMP/300.),-2.6);
  double K12I = 2.0E-12;
  double KR12 = K120/K12I;
  double NC12 = 0.75-1.27*(log10(FC12));
  double F12 = pow(10.,(log10(FC12)/(1.0+pow((log10(KR12)/NC12),2.))));
  double KMT12 = (K120*K12I*F12)/(K120+K12I);
  double FC13 = 0.36;
  double K130 = 2.5E-30*M*pow((TEMP/300.),-5.5);
  double K13I = 1.8E-11;
  double KR13 = K130/K13I;
  double NC13 = 0.75-1.27*(log10(FC13));
  double F13 = pow(10.,(log10(FC13)/(1.+pow((log10(KR13)/NC13),2.))));
  double KMT13 = (K130*K13I)*F13/(K130+K13I);
  double K140 = 9.0E-5*exp(-9690./TEMP)*M;
  double K14I = 1.1E+16*exp(-10560./TEMP);
  double KR14 = K140/K14I;
  double FC14 = 0.36;
  double NC14 = 0.75-1.27*(log10(FC14));
  double F14 = pow(10.,(log10(FC14)/(1.+pow((log10(KR14)/NC14),2.))));
  double KMT14 = (K140*K14I)*F14/(K140+K14I);
  double FC15 = 0.48;
  double K150 = 8.6E-29*M*pow((TEMP/300.),-3.1);
  double K15I = 9.0E-12*pow((TEMP/300.),-0.85);
  double KR15 = K150/K15I;
  double NC15 = 0.75-1.27*(log10(FC15));
  double F15 = pow(10.,(log10(FC15)/(1.+pow((log10(KR15)/NC15),2.))));
  double KMT15 = (K150*K15I)*F15/(K150+K15I);
  double FC16 = 0.5;
  double K160 = 8.E-27*M*pow((TEMP/300.),-3.5);
  double K16I = 3.0E-11*pow((TEMP/300.),-1.);
  double KR16 = K160/K16I;
  double NC16 = 0.75-1.27*(log10(FC16));
  double F16 = pow(10.,(log10(FC16)/(1.+pow((log10(KR16)/NC16),2.))));
  double KMT16 = (K160*K16I)*F16/(K160+K16I);
  double FC17 = 0.17*exp(-51./TEMP)+exp(-TEMP/204.);
  double K170 = 5.0E-30*M*pow((TEMP/300.),-1.5);
  double K17I = 1.0E-12;
  double KR17 = K170/K17I;
  double NC17 = 0.75-1.27*(log10(FC17));
  double F17 = pow(10.,(log10(FC17)/(1.0+pow((log10(KR17)/NC17),2.))));
  double KMT17 = (K170*K17I*F17)/(K170+K17I);

  double KNO_val = KRO2NO * C[ind_NO];
  double KHO2_val = KRO2HO2 * C[ind_HO2] * 0.706;
  double KNO3_val = KRO2NO3 * C[ind_NO3];
  double KRO2_val = 1.26E-12 * RO2;
  double KTR = KNO_val + KHO2_val + KRO2_val + KNO3_val;
  double K16ISOM = (KTR*5.18E-04*exp(1308./TEMP)) + (2.76E+07*exp(-6759./TEMP));

  /* Begin INLINED RCONST */"""

    # We replace from void Update_RCONST up to /* Begin INLINED RCONST */
    # Matches Update_RCONST with 3 or 4 parameters, with or without previous edits
    pattern = r'void\s+Update_RCONST\s*\(\s*const\s+double\s+TEMP,\s*const\s+double\s+PRESS,\s*const\s+double\s+AIRDENS(?:,\s*const\s+double\s+H2O)?\s*\)\s*\{.*?(/\*\s*Begin\s+INLINED\s+RCONST\s*\*/)'
    c, count = re.subn(pattern, injected_block, c, flags=re.DOTALL)
    if count > 0:
        print("Successfully injected Update_RCONST function signature and all variable declarations!")
    else:
        print("Error: Could not find Update_RCONST or /* Begin INLINED RCONST */ to inject variables!")

    # 5c. Standardize math operators (EXP to exp, ** to pow)
    c = c.replace('EXP(', 'exp(')
    c = re.sub(r'TEMP\*\*\(?([0-9.]+)\)?', r'pow(TEMP, \1)', c)
    c = re.sub(r'\(TEMP/300\.\)\*\*\(?(-?[0-9.]+)\)?', r'pow(TEMP/300., \1)', c)

    # 5d. Replace PI with the literal value
    c = re.sub(r'\bPI\b', '3.14159265358979323846', c)

    # 5e. Insert local J definition at the top of the file
    c = c.replace('#include "KPP/KPP_Sparse.h"', '#include "KPP/KPP_Sparse.h"\n\n#ifndef J\n#define J(x)                 PHOTOL[x]\n#endif')

    # 5f. Append undef J at the end of the file
    c = c + '\n#ifdef J\n#undef J\n#endif\n'

    with open(rates_path, 'w', encoding='utf-8') as fh:
        fh.write(c)
    print("Patched KPP_Rates.cpp with signature, RO2, K16ISOM, variable declarations, math operators, PI literal, and local J macro.")
else:
    print(f"Error: KPP_Rates.cpp not found at {rates_path}!")

# 6. Patch KPP_Monitor.cpp
monitor_path = os.path.join(base_path, 'src/KPP-CRI-V2R5/KPP_Monitor.cpp')
if os.path.exists(monitor_path):
    with open(monitor_path, 'r', encoding='utf-8') as fh:
        c = fh.read()
    
    c = c.replace('char *  SPC_NAMES[]', 'const char * SPC_NAMES[]')
    c = c.replace('char *  EQN_NAMES[]', 'const char * EQN_NAMES[]')
    
    with open(monitor_path, 'w', encoding='utf-8') as fh:
        fh.write(c)
    print("Patched KPP_Monitor.cpp with const char * declarations.")
else:
    print(f"Error: KPP_Monitor.cpp not found at {monitor_path}!")

# 7. Patch KPP_LinearAlgebra.cpp
la_path = os.path.join(base_path, 'src/KPP-CRI-V2R5/KPP_LinearAlgebra.cpp')
if os.path.exists(la_path):
    with open(la_path, 'r', encoding='utf-8') as fh:
        c = fh.read()
    
    # Merge physical lines for statements in KPP_LinearAlgebra.cpp
    lines = c.splitlines()
    merged_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("XX[") and not line.strip().endswith(";"):
            while i + 1 < len(lines) and not line.strip().endswith(";"):
                next_line = lines[i+1]
                line = line + next_line.strip()
                i += 1
        merged_lines.append(line)
        i += 1
        
    # Process merged lines to fix unmatched parentheses
    new_lines = []
    for line in merged_lines:
        sline = line.strip()
        if sline.startswith("XX["):
            match = re.match(r'^(\s*)XX\[(\d+)\]\s*=\s*(.*)$', line)
            if match:
                indent = match.group(1)
                idx = match.group(2)
                rhs = match.group(3)
                
                # Case A: starts with (X[idx] and has no closing parenthesis before ;
                if rhs.startswith(f"(X[{idx}]") and not rhs.endswith(");") and not ")" in rhs[:-1]:
                    line = line.rstrip()[:-1] + ");"
                
                # Case B/C: starts with XX[idx]
                elif rhs.startswith(f"XX[{idx}]"):
                    if rhs.endswith(";") and ")" in rhs:
                        # Case B: last assignment of a split
                        line = line.replace(f"XX[{idx}] = XX[{idx}]", f"XX[{idx}] = (XX[{idx}]")
                    else:
                        # Case C: middle assignment of a split
                        line = line.replace(f"XX[{idx}] = XX[{idx}]", f"XX[{idx}] = (XX[{idx}]")
                        line = line.rstrip()[:-1] + ");"
        new_lines.append(line)
        
    c = "\n".join(new_lines)
    c = "\n".join(new_lines)
    c = c.replace('cri_KppSolve', 'KppSolve')
    with open(la_path, 'w', encoding='utf-8') as fh:
        fh.write(c)
    print("Patched KPP_LinearAlgebra.cpp to fix parenthesization and rename cri_KppSolve.")
else:
    print(f"Error: KPP_LinearAlgebra.cpp not found at {la_path}!")

# 7b. Patch src/KPP-CRI-V2R5/KPP_Function.cpp
func_cpp_path = os.path.join(base_path, 'src/KPP-CRI-V2R5/KPP_Function.cpp')
if os.path.exists(func_cpp_path):
    with open(func_cpp_path, 'r', encoding='utf-8') as fh:
        c = fh.read()
    
    # Strip any previous ComputeRxnRates / ComputePL implementation to make it clean/re-runnable
    if 'void ComputeRxnRates' in c:
        idx = c.find('void ComputeRxnRates')
        # Go back to find the comment header if possible
        comment_idx = c.rfind('/* ====================================================================== */', 0, idx)
        if comment_idx != -1:
            c = c[:comment_idx]
        else:
            c = c[:idx]
            
    # Extract all A[j] = ... lines from Fun() body
    a_lines = re.findall(r'^\s*A\[\d+\] = [^\n]+;', c, re.MULTILINE)
    print(f"Extracted {len(a_lines)} reaction rate lines from Fun() in KPP_Function.cpp")
    if not a_lines:
        print("Warning: No A[j] lines found in KPP_Function.cpp!")
    
    a_block = '\n    '.join(a_lines)
    
    new_functions = f"""
/* ====================================================================== */
/* ComputeRxnRates                                                         */
/*   Returns the instantaneous rate of each reaction [molec/cm3/s].       */
/*   RCONST[] must be populated by Update_RCONST() before calling.        */
/* ====================================================================== */
void ComputeRxnRates( const double VAR[], const double FIX[],
                      double A_out[], int nReact )
{{
    /* Cast away const to match KPP's internal non-const interface */
    double* V = const_cast<double*>(VAR);
    double* F = const_cast<double*>(FIX);
    (void)F;   /* suppresses unused-variable warning if FIX unused */

    double A[NREACT];
    double* RCT = RCONST;  /* alias global RCONST to match Fun()'s local RCT param */

    /* ---- Reaction rate computation (copied from Fun) ---- */
    {a_block}
    /* ---- End of reaction rate computation ---- */

    int n = (nReact < NREACT) ? nReact : NREACT;
    for (int j = 0; j < n; j++) A_out[j] = A[j];
}}

/* ====================================================================== */
/* ComputePL                                                               */
/*   Splits net chemical tendency (Vdot) into production P[i] >= 0        */
/*   and loss L[i] >= 0.                                                  */
/*   P[i] = max(Vdot[i], 0)    if species is net produced                */
/*   L[i] = max(-Vdot[i], 0)   if species is net destroyed               */
/* ====================================================================== */
void ComputePL( const double VAR[], const double FIX[],
                double P[], double L[], int nVar )
{{
    double Vdot[NVAR];
    /* RCONST is a global array in KPP_Global.h, already set by Update_RCONST() */
    Fun( const_cast<double*>(VAR), const_cast<double*>(FIX), RCONST, Vdot );

    int n = (nVar < NVAR) ? nVar : NVAR;
    for (int i = 0; i < n; i++) {{
        P[i] = (Vdot[i] > 0.0) ?  Vdot[i] : 0.0;
        L[i] = (Vdot[i] < 0.0) ? -Vdot[i] : 0.0;
    }}
}}
"""
    c = c.rstrip() + '\n' + new_functions + '\n'
    with open(func_cpp_path, 'w', encoding='utf-8') as fh:
        fh.write(c)
    print("Patched KPP_Function.cpp with ComputeRxnRates and ComputePL.")
else:
    print(f"Error: KPP_Function.cpp not found at {func_cpp_path}!")

# 7c. Patch src/KPP-CRI-V2R5/KPP_Integrator.cpp
integrator_cpp_path = os.path.join(base_path, 'src/KPP-CRI-V2R5/KPP_Integrator.cpp')
if os.path.exists(integrator_cpp_path):
    with open(integrator_cpp_path, 'r', encoding='utf-8') as fh:
        c = fh.read()
    
    # Revert previous rename if present to start fresh
    c = c.replace('INTEGRATE_2arg', 'INTEGRATE')
    
    # Revert commented out Update_SUN/Update_RCONST declarations/calls if they were commented before to start fresh
    c = c.replace('//void Update_SUN();', 'void Update_SUN();')
    c = c.replace('//void Update_RCONST();', 'void Update_RCONST();')
    c = c.replace('//Update_SUN();', 'Update_SUN();')
    c = c.replace('//Update_RCONST();', 'Update_RCONST();')
    c = c.replace('  //Update_SUN();', '  Update_SUN();')
    c = c.replace('  //Update_RCONST();', '  Update_RCONST();')
    
    # Strip any previous wrapper implementation
    if 'extern "C" int INTEGRATE' in c:
        idx = c.find('extern "C" int INTEGRATE')
        c = c[:idx]
        
    # Rename void INTEGRATE( double TIN, double TOUT )
    c = c.replace('void INTEGRATE( double TIN, double TOUT )', 'void INTEGRATE_2arg( double TIN, double TOUT )')
    # Also rename void INTEGRATE(double TIN, double TOUT)
    c = c.replace('void INTEGRATE(double TIN, double TOUT)', 'void INTEGRATE_2arg(double TIN, double TOUT)')
    
    # Comment out Update_SUN / Update_RCONST
    c = c.replace('void Update_SUN();', '//void Update_SUN();')
    c = c.replace('void Update_RCONST();', '//void Update_RCONST();')
    c = c.replace('  Update_SUN();', '  //Update_SUN();')
    c = c.replace('  Update_RCONST();', '  //Update_RCONST();')
    
    # Append the 7-argument wrapper
    wrapper_code = """
extern "C" int INTEGRATE( double VAR_in[] , double FIX_in[], double TIN   , double TOUT,
               double ATOL_in[], double RTOL_in[], double STEPMIN_in )
{
   // Copy local species array to KPP global arrays
   for ( int i = 0; i < NVAR; i++ ) {
       VAR[i] = VAR_in[i];
   }
   for ( int i = 0; i < NFIX; i++ ) {
       FIX[i] = FIX_in[i];
   }
   for ( int i = 0; i < NSPEC; i++ ) {
       ATOL[i] = ATOL_in[i];
       RTOL[i] = RTOL_in[i];
   }
   STEPMIN = STEPMIN_in;

   // Call the 2-argument integrate
   INTEGRATE_2arg( TIN, TOUT );

   // Copy back KPP global arrays to local species array
   for ( int i = 0; i < NVAR; i++ ) {
       VAR_in[i] = VAR[i];
   }

   return 1; // Success
}
"""
    c = c.rstrip() + '\n' + wrapper_code + '\n'
    with open(integrator_cpp_path, 'w', encoding='utf-8') as fh:
        fh.write(c)
    print("Patched KPP_Integrator.cpp with INTEGRATE wrapper.")
else:
    print(f"Error: KPP_Integrator.cpp not found at {integrator_cpp_path}!")

# 8. Patch Core C++ files for H2O size safety
model_cpp_path = os.path.join(base_path, 'src/EPM/Models/Original/Model.cpp')
if os.path.exists(model_cpp_path):
    with open(model_cpp_path, 'r', encoding='utf-8') as fh:
        c = fh.read()
    c = c.replace('VAR_(NVAR)', 'VAR_(NSPECALL)')
    with open(model_cpp_path, 'w', encoding='utf-8') as fh:
        fh.write(c)
    print("Patched Model.cpp to size VAR_ to NSPECALL.")

solution_cpp_path = os.path.join(base_path, 'src/EPM/Solution.cpp')
if os.path.exists(solution_cpp_path):
    with open(solution_cpp_path, 'r', encoding='utf-8') as fh:
        c = fh.read()
    
    # Add include if not present
    if 'Util/PhysFunction.hpp' not in c:
        c = c.replace('#include "Util/PhysConstant.hpp"', '#include "Util/PhysConstant.hpp"\n#include "Util/PhysFunction.hpp"')
    
    # Initialize amb_Value[ind_H2O] in Solution::Initialize before SpinUp
    target_init = 'const double AMBIENT_VALID_TIME = 8.0; //hours'
    replacement_init = """if ( ind_H2O >= NSPEC ) {
        double H2Oval = (input.relHumidity_w()/((double) 100.0) * \\
                          physFunc::pSat_H2Ol( input.temperature_K() ) / ( kB * input.temperature_K() )) / 1.00E+06;
        amb_Value[ind_H2O] = H2Oval / airDens;
    }
    const double AMBIENT_VALID_TIME = 8.0; //hours"""
    if target_init in c and 'ind_H2O >= NSPEC' not in c:
        c = c.replace(target_init, replacement_init)
    
    # Initialize varSpeciesArray[ind_H2O] in Solution::SpinUp
    target_spinup = """    /* Initialize arrays */
    for ( UInt iVar = 0; iVar < NVAR; iVar++ )
        varSpeciesArray[iVar] = amb_Value[iVar] * airDens;"""
    
    replacement_spinup = """    /* Initialize arrays */
    for ( UInt iVar = 0; iVar < NVAR; iVar++ )
        varSpeciesArray[iVar] = amb_Value[iVar] * airDens;
    if ( ind_H2O >= NVAR && ind_H2O < varSpeciesArray.size() ) {
        varSpeciesArray[ind_H2O] = amb_Value[ind_H2O] * airDens;
    }"""
    if target_spinup in c and 'ind_H2O >= NVAR' not in c:
        c = c.replace(target_spinup, replacement_spinup)
    
    with open(solution_cpp_path, 'w', encoding='utf-8') as fh:
        fh.write(c)
    print("Patched Solution.cpp for H2O initialization.")

print("CRI-V2R5 mechanism patches applied successfully!")
