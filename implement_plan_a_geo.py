#!/usr/bin/env python3
"""
Plan A: HAPCEMM Geo-Engineering Fix
Run on the Isambard cluster:
  python3 implement_plan_a_geo.py
"""
import re, sys, os

ROOT = "/projects/b35as/public/HAPCEMM-Chem/Code.v05-00"

def read(path):
    with open(path, 'r') as f:
        return f.read()

def write(path, content):
    with open(path, 'w') as f:
        f.write(content)
    print(f"  [WROTE] {path}")

def done(msg): print(f"  [DONE ] {msg}")
def skip(msg): print(f"  [SKIP ] {msg}")
def warn(msg): print(f"  [WARN ] {msg}", file=sys.stderr)

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== A1: defaults/input.yaml — GEOENGINEERING SUBMENU ===")
p = f"{ROOT}/defaults/input.yaml"
c = read(p)
if 'GEOENGINEERING SUBMENU' not in c:
    geo_block = """
  GEOENGINEERING SUBMENU:
    # Geoengineering aerosol type: 0=None, 1=NaCl, 2=AgI, 3=BiI3, 4=Al2O3, 5=CaCO3, 6=Diamond, 7=Dust
    Background_Geoengineering_Type (int): 0
    Background_Geoengineering_Rho (double): 1769.0
    Background_Geoengineering_Number_Density (double): 0.0
    Background_Geoengineering_Radius (double): 2.0e-8
    Background_Geoengineering_Gamma (double): 0.02
    Background_Geoengineering_Shape_Factor (double): 1.0
    Background_Geoengineering_ContactAngle (double): 0.0
    Background_Geoengineering_Wettability (double): 0.0
"""
    # Find the PARAMETER MENU section and insert after the last existing submenu before end
    # Try inserting after "EMISSION INDICES SUBMENU" closing block
    # Fallback: insert before the very last line of the file
    patterns = [
        r'(Background_Geoengineering_Wettability.*?\n)',
        r'(Soot Radius.*?\n)',
        r'(  Particle Radius.*?\n)',
        r'(  Number density.*?\n)',
    ]
    inserted = False
    for pat in patterns:
        m = re.search(pat, c)
        if m:
            # Insert after this line
            c = c[:m.end()] + geo_block + c[m.end():]
            inserted = True
            break
    if not inserted:
        # Append before EOF
        c = c.rstrip() + '\n' + geo_block + '\n'
    write(p, c)
    done("GEOENGINEERING SUBMENU added")
else:
    skip("GEOENGINEERING SUBMENU already present")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== A2: YamlInputReader.cpp — parse geo keys ===")
p = f"{ROOT}/src/YamlInputReader/YamlInputReader.cpp"
c = read(p)
if 'GEOENGINEERING SUBMENU' not in c:
    geo_parse = r'''
        /* --- Geoengineering particle parameters --- */
        YAML::Node geoSubmenu = paramNode["GEOENGINEERING SUBMENU"];
        if (geoSubmenu) {
            auto parseGeo = [&](const std::string& key, const std::string& label) {
                if (geoSubmenu[label]) {
                    try {
                        input.PARAMETER_PARAM_MAP[key] =
                            parseParamSweepInput(geoSubmenu[label].as<std::string>(), label);
                    } catch (...) {
                        input.PARAMETER_PARAM_MAP[key] =
                            parseParamSweepInput(std::to_string(geoSubmenu[label].as<double>()), label);
                    }
                }
            };
            parseGeo("Background_Geoengineering_Type",          "Background_Geoengineering_Type (int)");
            parseGeo("Background_Geoengineering_Rho",           "Background_Geoengineering_Rho (double)");
            parseGeo("Background_Geoengineering_Number_Density","Background_Geoengineering_Number_Density (double)");
            parseGeo("Background_Geoengineering_Radius",        "Background_Geoengineering_Radius (double)");
            parseGeo("Background_Geoengineering_Gamma",         "Background_Geoengineering_Gamma (double)");
            parseGeo("Background_Geoengineering_Shape_Factor",  "Background_Geoengineering_Shape_Factor (double)");
            parseGeo("Background_Geoengineering_ContactAngle",  "Background_Geoengineering_ContactAngle (double)");
            parseGeo("Background_Geoengineering_Wettability",   "Background_Geoengineering_Wettability (double)");
        }
'''
    # Insert at the end of readParamMenu, before the closing return/}
    # Find a reliable anchor: the BACKGROUND MIXING RATIOS block
    # Look for a known key like BACKG_NOX or BACKG_SO2
    anchor_patterns = [
        r'(PARAMETER_PARAM_MAP\["BACKG_[A-Z0-9]+"\][^;]+;)',
    ]
    for pat in anchor_patterns:
        matches = list(re.finditer(pat, c, re.DOTALL))
        if matches:
            m = matches[-1]   # last BACKG_ line
            c = c[:m.end()] + '\n' + geo_parse + c[m.end():]
            break
    else:
        warn("Could not find BACKG_ anchor; appending geo parse before readParamMenu closing brace")
        # Find readParamMenu closing } by looking for "void readSimMenu" or end of file section
        c = c.rstrip() + '\n' + geo_parse + '\n'
    write(p, c)
    done("Geo YAML parsing added to YamlInputReader.cpp")
else:
    skip("Geo parsing already present")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== A3: include/Core/Input.hpp — add int type field + getter ===")
p = f"{ROOT}/include/Core/Input.hpp"
c = read(p)
if 'backgroundGeoengineeringType_' not in c:
    # Add private field before backgroundGeoengineeringRho_
    c = re.sub(
        r'(double\s+backgroundGeoengineeringRho_;)',
        r'int    backgroundGeoengineeringType_;    /*!< 0=None 1=NaCl 2=AgI 3=BiI3 4=Al2O3 5=CaCO3 6=Diamond 7=Dust */\n    \1',
        c, count=1
    )
    # Add getter - find backgroundGeoengineeringRho() getter
    c = re.sub(
        r'(double\s+backgroundGeoengineeringRho\s*\(\s*\)\s*const\s*\{[^}]+\})',
        r'int    backgroundGeoengineeringType()    const { return backgroundGeoengineeringType_; }\n        \1',
        c, count=1
    )
    write(p, c)
    done("backgroundGeoengineeringType_ field + getter added to Input.hpp")
else:
    skip("backgroundGeoengineeringType_ already present")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== A4: src/Core/Input.cpp — init type from param map + validation ===")
p = f"{ROOT}/src/Core/Input.cpp"
c = read(p)
if 'backgroundGeoengineeringType_' not in c:
    # Add to constructor initialiser list before backgroundGeoengineeringRho_
    c = re.sub(
        r'(backgroundGeoengineeringRho_\s*\(\s*parameters\[iCase\]\.count)',
        r'backgroundGeoengineeringType_     ( parameters[iCase].count("Background_Geoengineering_Type")\n'
        r'                                    ? static_cast<int>(parameters[iCase].at("Background_Geoengineering_Type"))\n'
        r'                                    : 0 ),\n    \1',
        c, count=1
    )
    # Add validation — insert before first backgroundGeoengineering validation
    validation_block = '''    if ( backgroundGeoengineeringType_ < 0 || backgroundGeoengineeringType_ > 7 ) {
        std::cout << " In Input::Input:";
        std::cout << " backgroundGeoengineeringType_ must be 0-7, got: "
                  << backgroundGeoengineeringType_ << std::endl;
        exit(-1);
    }
'''
    # Find first backgroundGeoengineering validation block
    c = re.sub(
        r'(if\s*\(\s*backgroundGeoengineeringRho_)',
        validation_block + r'    \1',
        c, count=1
    )
    write(p, c)
    done("backgroundGeoengineeringType_ init + validation added to Input.cpp")
else:
    skip("backgroundGeoengineeringType_ already present")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== A5: src/EPM/Solution.cpp — fix if(false) wrapper + switch cases ===")
p = f"{ROOT}/src/EPM/Solution.cpp"
c = read(p)

changes = 0

# Fix: replace hardcoded type=0 with getter call
for old, new in [
    ('int type = 0;  // Default: no geoengineering',
     'int type = input.backgroundGeoengineeringType();  // Read from input'),
    ('int type = 0; // Default: no geoengineering',
     'int type = input.backgroundGeoengineeringType();  // Read from input'),
    ('int type = 0;',
     'int type = input.backgroundGeoengineeringType();  // Read from input'),
]:
    if old in c:
        c = c.replace(old, new, 1)
        changes += 1
        done(f"Replaced '{old[:40]}' with getter call")
        break

if changes == 0:
    warn("Could not find 'int type = 0;' in Solution.cpp — checking with regex")
    c, n = re.subn(r'int\s+type\s*=\s*0\s*;',
                    'int type = input.backgroundGeoengineeringType();  // Read from input',
                    c, count=1)
    if n:
        done("Replaced int type = 0 via regex")
    else:
        warn("Could not find int type = 0 anywhere")

# Fix case 4 (AL2O3): wrong spinup_NACL_SAD -> spinup_AL2O3_SAD, wrong ind_NACL -> ind_AL2O3
c = re.sub(
    r'(case\s+4\s*:.*?/\*.*?AL2O3.*?\*/.*?)spinup_NACL_SAD\s*=\s*SAD_cgs\s*;',
    r'\1spinup_AL2O3_SAD = SAD_cgs;',
    c, count=1, flags=re.DOTALL
)
c = re.sub(
    r'(case\s+4\s*:.*?)varSpeciesArray\[ind_NACL\]\s*=\s*N_geo\s*;',
    r'\1varSpeciesArray[ind_AL2O3] = N_geo;',
    c, count=1, flags=re.DOTALL
)

# Fix case 5 (CACO3): wrong ind_NACL -> ind_CACO3, wrong spinup_NACL -> spinup_CACO3
c = re.sub(
    r'(case\s+5\s*:.*?/\*.*?CACO3.*?\*/.*?)spinup_NACL_SAD\s*=\s*SAD_cgs\s*;',
    r'\1spinup_CACO3_SAD = SAD_cgs;',
    c, count=1, flags=re.DOTALL
)
c = re.sub(
    r'(case\s+5\s*:.*?)varSpeciesArray\[ind_NACL\]\s*=\s*N_geo\s*;',
    r'\1varSpeciesArray[ind_CACO3] = N_geo;',
    c, count=1, flags=re.DOTALL
)

# Fix case 6 (DIAMOND): wrong ind_NACL -> remove, spinup_NACL -> spinup_DIAMOND_SAD
c = re.sub(
    r'(case\s+6\s*:.*?/\*.*?DIAMOND.*?\*/.*?)spinup_NACL_SAD\s*=\s*SAD_cgs\s*;',
    r'\1spinup_DIAMOND_SAD = SAD_cgs;\n\t   spinup_GEO_SAD     = SAD_cgs;',
    c, count=1, flags=re.DOTALL
)
# Remove wrong ind_NACL for diamond (diamond has no species index)
c = re.sub(
    r'(case\s+6\s*:.*?)varSpeciesArray\[ind_NACL\]\s*=\s*N_geo\s*;',
    r'\1/* Diamond: no dedicated KPP species index */',
    c, count=1, flags=re.DOTALL
)

# Fix case 7 (DUST): wrong ind_NACL -> ind_DUST, wrong spinup_NACL -> spinup_DUST
c = re.sub(
    r'(case\s+7\s*:.*?/\*.*?DUST.*?\*/.*?)spinup_NACL_SAD\s*=\s*SAD_cgs\s*;',
    r'\1spinup_DUST_SAD = SAD_cgs;',
    c, count=1, flags=re.DOTALL
)
c = re.sub(
    r'(case\s+7\s*:.*?)varSpeciesArray\[ind_NACL\]\s*=\s*N_geo\s*;',
    r'\1varSpeciesArray[ind_DUST] = N_geo;',
    c, count=1, flags=re.DOTALL
)

# Also add RAD assignments for cases that are missing them
for case_num, sad_var, rad_var in [
    (2, 'spinup_NACL_SAD', 'spinup_NACL_RAD'),
    (4, 'spinup_AL2O3_SAD', 'spinup_AL2O3_RAD'),
    (5, 'spinup_CACO3_SAD', 'spinup_CACO3_RAD'),
    (7, 'spinup_DUST_SAD', 'spinup_DUST_RAD'),
]:
    # Add RAD assignment right after SAD assignment for each case
    c = re.sub(
        rf'({sad_var}\s*=\s*SAD_cgs\s*;)(?!\s*{rad_var})',
        rf'\1\n\t   {rad_var} = R_geo;',
        c, count=1
    )

write(p, c)
done("Solution.cpp switch cases fixed (type getter + correct ind_* mappings)")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== A6-A10: src/EPM/Models/Original/Integrate.cpp — restore geo microphysics ===")
p = f"{ROOT}/src/EPM/Models/Original/Integrate.cpp"
c = read(p)

# Find out if averaged_radius already exists
if 'averaged_radius' in c:
    skip("averaged_radius already present in Integrate.cpp")
else:
    geo_physics_block = r"""
        /* ================================================================== */
        /* Geo-engineering particle physics: hygroscopic growth, water uptake, */
        /* combined aerosol PDF, and effective radius for EPM RHS.            */
        /* ================================================================== */
        double geoengineering_concentration = input_.backgroundGeoengineeringNumber();
        double geoengineering_radius        = input_.backgroundGeoengineeringRadius();
        double geoengineering_shape         = input_.backgroundGeoengineeringShapeFactor();
        double kappa                        = input_.backgroundGeoengineeringWettability();

        /* Effective dry radius corrected for non-spherical shape factor */
        /* Shape factor phi = V_particle/V_sphere; r_eff = r_nominal * phi^(-1/3) */
        double effective_geoengineering_radius = (geoengineering_shape > 1.0e-15)
                                                 ? geoengineering_radius / std::cbrt(geoengineering_shape)
                                                 : geoengineering_radius;

        /* Kappa-Koehler hygroscopic growth: grows dry radius to wet radius */
        /* r_wet = r_dry * (1 + kappa * RH / (1 - RH))^(1/3)              */
        double p_water_Pa   = VAR_[ind_H2O] * n_air_amb * physConst::kB * temperature_K * 1.0e6;
        double p_sat_Pa     = pSat_H2Ol(temperature_K);
        double RH_frac      = std::min(p_water_Pa / std::max(p_sat_Pa, 1.0e-30), 0.999);
        double Growth_kappa = std::cbrt(1.0 + kappa * RH_frac / std::max(1.0 - RH_frac, 1.0e-3));
        double wet_geo_radius = effective_geoengineering_radius * Growth_kappa;

        /* Water uptake: remove absorbed H2O from gas-phase mixing ratio */
        if (geoengineering_concentration > 1.0e-25 && kappa > 1.0e-15) {
            constexpr double MW_H2O_kg   = 18.015e-3;  /* kg/mol */
            constexpr double rho_H2O     = 1000.0;     /* kg/m3  */
            const double vol_H2O_per_mol = MW_H2O_kg / (physConst::Na * rho_H2O); /* m3/molec */
            double dry_vol = (4.0/3.0) * physConst::PI * std::pow(effective_geoengineering_radius, 3);
            double wet_vol = (4.0/3.0) * physConst::PI * std::pow(wet_geo_radius, 3);
            /* water_taken_up [molec/cm3] = N_geo * delta_V / vol_per_molec */
            double water_taken_up = geoengineering_concentration
                                    * (wet_vol - dry_vol) / vol_H2O_per_mol;
            VAR_[ind_H2O] -= water_taken_up;
            VAR_[ind_H2O]  = std::max(VAR_[ind_H2O], 0.0);
        }
        /* Use wet radius for all subsequent EPM particle calculations */
        effective_geoengineering_radius = wet_geo_radius;

        /* Number-RMS averaged particle radius (conserves geometric cross-section) */
        double soot_concentration = varSoot * n_air_eng;  /* [#/cm3] */
        double radius_soot        = EI_.getSootRad();      /* [m]    */
        double Total_Number_Density = soot_concentration + geoengineering_concentration;

        double averaged_radius;
        if (Total_Number_Density > 1.0e-25) {
            averaged_radius = std::sqrt(
                (soot_concentration * radius_soot * radius_soot
                 + geoengineering_concentration * effective_geoengineering_radius
                                                * effective_geoengineering_radius)
                / Total_Number_Density);
        } else {
            averaged_radius = radius_soot;
        }

        /* Combined aerosol PDF: merge soot + geo particle distributions */
        double sSO4_sigma = 1.4;  /* lognormal geometric standard deviation */
        AIM::Aerosol nPDF_Soot (SO4_rJ, SO4_rE,
                                soot_concentration, radius_soot,
                                sSO4_sigma, "lognormal");
        AIM::Aerosol nPDF_Geo  (SO4_rJ, SO4_rE,
                                geoengineering_concentration,
                                effective_geoengineering_radius,
                                sSO4_sigma, "lognormal");
        AIM::Aerosol nPDF_Total(nPDF_Soot);
        nPDF_Total.addAerosolToPDF(nPDF_Geo);  /* merge geo into soot bins */

        /* Ambient particle mixing ratios for RHS dilution targets */
        double Geo_amb  = (n_air_amb > 1.0e-30) ? geoengineering_concentration / n_air_amb : 0.0;
        double Part_amb = Soot_amb + Geo_amb;

"""
    # Insert before the gas_aerosol_rhs constructor call
    c, n = re.subn(
        r'(\s+gas_aerosol_rhs\s+rhs\s*\()',
        geo_physics_block + r'\n        \1',
        c, count=1
    )
    if n:
        done("Geo physics block (hygroscopic growth + nPDF_Total) inserted before gas_aerosol_rhs")
    else:
        warn("Could not find gas_aerosol_rhs constructor — check Integrate.cpp manually")

# Now fix the gas_aerosol_rhs constructor call itself
# Replace Soot_amb with Part_amb and EI_.getSootRad() with averaged_radius and nPDF_SO4 with nPDF_Total
if 'averaged_radius' in c:
    # Fix Soot_amb -> Part_amb in the rhs constructor
    c, n = re.subn(
        r'(gas_aerosol_rhs\s+rhs\s*\([^;]*?)Soot_amb,(\s*)\n?(\s*)EI_\.getSootRad\(\)',
        r'\1Part_amb,\2\n\3averaged_radius',
        c, count=1, flags=re.DOTALL
    )
    if n: done("gas_aerosol_rhs: Soot_amb -> Part_amb, getSootRad() -> averaged_radius")

    # Fix nPDF_SO4 -> nPDF_Total
    c, n = re.subn(
        r'(gas_aerosol_rhs\s+rhs\s*\([^;]*?)nPDF_SO4\)',
        r'\1nPDF_Total)',
        c, count=1, flags=re.DOTALL
    )
    if n: done("gas_aerosol_rhs: nPDF_SO4 -> nPDF_Total")

write(p, c)

# Add ice nucleation geo contribution in the persistent contrail branch
if 'Geo particles are potential' not in c:
    c = read(p)
    # Find the empty geo ice-nucleation stub and fill it
    c, n = re.subn(
        r'(if\s*\(\s*geoengineering_concentration\s*>\s*1\.0e-20\s*\)\s*\{)([^}]*?)(//.*?ice.*?\n)([^}]*?\})',
        r'\1\2'
        r'                    /* Geo particles are potential ice nucleating particles (INPs). */\n'
        r'                    /* Conservative upper bound: all geo particles nucleate ice.    */\n'
        r'                    Ice_den += geoengineering_concentration;  /* [#/cm3] */\n'
        r'                    /* For precise treatment: filter by backgroundGeoengineeringContactAngle. */\n'
        r'                    /* See Karcher & Lohmann (2003) for parameterisation.                    */\n'
        r'\4',
        c, count=1, flags=re.DOTALL
    )
    if n:
        write(p, c)
        done("Ice nucleation geo contribution added")
    else:
        warn("Could not find geo ice-nucleation stub in Integrate.cpp — may need manual edit")

print("\n=== Plan A verification ===")
import subprocess
for path, pattern in [
    (f"{ROOT}/defaults/input.yaml", "GEOENGINEERING SUBMENU"),
    (f"{ROOT}/src/YamlInputReader/YamlInputReader.cpp", "GEOENGINEERING SUBMENU"),
    (f"{ROOT}/include/Core/Input.hpp", "backgroundGeoengineeringType_"),
    (f"{ROOT}/src/Core/Input.cpp", "backgroundGeoengineeringType_"),
    (f"{ROOT}/src/EPM/Solution.cpp", "backgroundGeoengineeringType()"),
    (f"{ROOT}/src/EPM/Models/Original/Integrate.cpp", "averaged_radius"),
]:
    content = read(path)
    status = "✓ FOUND" if pattern in content else "✗ MISSING"
    print(f"  {status}: '{pattern}' in {os.path.basename(path)}")

print("\n=== Plan A COMPLETE ===")
