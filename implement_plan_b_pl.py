#!/usr/bin/env python3
"""
Plan B: HAPCEMM P/L Diagnostics
Run on the Isambard cluster:
  python3 implement_plan_b_pl.py
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
print("\n=== B0: Read KPP dimensions from KPP_Parameters.h ===")
params_h = f"{ROOT}/include/KPP/KPP_Parameters.h"
c_params = read(params_h)
m_nreact = re.search(r'#define\s+NREACT\s+(\d+)', c_params)
m_nvar   = re.search(r'#define\s+NVAR\s+(\d+)',   c_params)
NREACT   = int(m_nreact.group(1)) if m_nreact else 475
NVAR     = int(m_nvar.group(1))   if m_nvar   else 150
print(f"  NREACT = {NREACT},  NVAR = {NVAR}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== B1: include/KPP/KPP.hpp — declare ComputeRxnRates() + ComputePL() ===")
p = f"{ROOT}/include/KPP/KPP.hpp"
c = read(p)
if 'ComputeRxnRates' not in c:
    new_decls = f"""
    /* ------------------------------------------------------------------ */
    /* P/L and per-reaction rate diagnostics                               */
    /* ------------------------------------------------------------------ */

    /* Returns the instantaneous rate of each reaction [molec/cm3/s].
     * RCONST[] must already be set by Update_RCONST() before calling.
     * A_out must have space for nReact (={NREACT}) doubles.             */
    void ComputeRxnRates( const double VAR[], const double FIX[],
                          double A_out[], int nReact );

    /* Returns per-species net production P[i] and loss L[i] [molec/cm3/s].
     * P[i] = max(Vdot[i], 0), L[i] = max(-Vdot[i], 0).
     * Arrays P and L must have space for nVar (={NVAR}) doubles.        */
    void ComputePL( const double VAR[], const double FIX[],
                    double P[], double L[], int nVar );
"""
    # Insert before the closing } of extern "C"
    inserted = False
    for close_marker in ['} // extern "C"', '} /* extern "C" */', '}//extern "C"']:
        if close_marker in c:
            c = c.replace(close_marker, new_decls + close_marker, 1)
            inserted = True
            break
    if not inserted:
        # Try finding the last } in the file
        idx = c.rfind('}')
        if idx >= 0:
            c = c[:idx] + new_decls + c[idx:]
            inserted = True
    if inserted:
        write(p, c)
        done("ComputeRxnRates + ComputePL declared in KPP.hpp")
    else:
        warn("Could not insert into KPP.hpp — no closing brace found")
else:
    skip("ComputeRxnRates already declared in KPP.hpp")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== B2: src/KPP/KPP_Function.cpp — implement ComputeRxnRates() + ComputePL() ===")
p = f"{ROOT}/src/KPP/KPP_Function.cpp"
c = read(p)
if 'ComputeRxnRates' not in c:
    # Extract all A[j] = ... lines from Fun() body
    a_lines = re.findall(r'^  A\[\d+\] = [^\n]+;', c, re.MULTILINE)
    print(f"  Extracted {len(a_lines)} reaction rate lines from Fun()")
    if not a_lines:
        warn("No A[j] lines found — KPP_Function.cpp may have unusual formatting")

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

    double A[{NREACT}];

    /* ---- Reaction rate computation (copied from Fun) ---- */
    {a_block}
    /* ---- End of reaction rate computation ---- */

    int n = (nReact < {NREACT}) ? nReact : {NREACT};
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
    double Vdot[{NVAR}];
    /* RCONST is a global array in KPP_Global.h, already set by Update_RCONST() */
    Fun( const_cast<double*>(VAR), const_cast<double*>(FIX), RCONST, Vdot );

    int n = (nVar < {NVAR}) ? nVar : {NVAR};
    for (int i = 0; i < n; i++) {{
        P[i] = (Vdot[i] > 0.0) ?  Vdot[i] : 0.0;
        L[i] = (Vdot[i] < 0.0) ? -Vdot[i] : 0.0;
    }}
}}
"""
    c = c.rstrip() + '\n' + new_functions + '\n'
    write(p, c)
    done(f"ComputeRxnRates ({len(a_lines)} A[] lines) + ComputePL added to KPP_Function.cpp")
else:
    skip("ComputeRxnRates already in KPP_Function.cpp")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== B3–B5: src/Core/BoxModel.cpp — storage arrays, time loop, output ===")
p = f"{ROOT}/src/Core/BoxModel.cpp"
c = read(p)

# --- B3: Add 6 diagnostic storage arrays after speciesHistory declaration ---
if 'prodHistory' not in c:
    diag_arrays = f"""

        /* --- P/L and reaction rate diagnostic storage --- */
        const size_t nTimeSteps = timeArray.size();
        std::vector<std::vector<double>> prodHistory   (NVAR,   std::vector<double>(nTimeSteps, 0.0));
        std::vector<std::vector<double>> lossHistory   (NVAR,   std::vector<double>(nTimeSteps, 0.0));
        std::vector<std::vector<double>> tauHistory    (NVAR,   std::vector<double>(nTimeSteps, 0.0));
        std::vector<std::vector<double>> cumProdHistory(NVAR,   std::vector<double>(nTimeSteps, 0.0));
        std::vector<std::vector<double>> cumLossHistory(NVAR,   std::vector<double>(nTimeSteps, 0.0));
        /* Per-reaction rates: [NREACT x nTimeSteps] */
        std::vector<std::vector<double>> rxnRateHistory(NREACT, std::vector<double>(nTimeSteps, 0.0));"""

    c, n = re.subn(
        r'(std::vector<std::vector<double>>\s+speciesHistory\s*\([^;]+;)',
        r'\1' + diag_arrays,
        c, count=1
    )
    if n:
        done("B3: 6 diagnostic storage arrays added after speciesHistory")
    else:
        warn("B3: Could not find speciesHistory declaration")
else:
    skip("B3: prodHistory already present")

# --- B4: Insert diagnostic calls in the time loop ---
if 'ComputeRxnRates' not in c:
    diag_calls = f"""

            /* ---- P/L and per-reaction-rate diagnostics (after each timestep) ---- */
            {{
                /* 1. Per-reaction rates A[j] [molec/cm3/s] */
                double A_now[NREACT];
                ComputeRxnRates(VAR, FIX, A_now, NREACT);
                for (int j = 0; j < NREACT; j++)
                    rxnRateHistory[static_cast<size_t>(j)][iTime] = A_now[j];

                /* 2. Net production P[i] and loss L[i] from Vdot sign split */
                double P_now[NVAR], L_now[NVAR];
                ComputePL(VAR, FIX, P_now, L_now, NVAR);

                constexpr double L_FLOOR = 1.0e-30;  /* molec/cm3/s */
                for (int i = 0; i < NVAR; i++) {{
                    prodHistory[static_cast<size_t>(i)][iTime] = P_now[i];
                    lossHistory[static_cast<size_t>(i)][iTime] = L_now[i];

                    /* 3. Chemical lifetime tau = [X] / L  (1e30 where L negligible) */
                    tauHistory[static_cast<size_t>(i)][iTime] =
                        (L_now[i] > L_FLOOR) ? (VAR[i] / L_now[i]) : 1.0e30;

                    /* 4. Cumulative integrals (trapezoidal rule) */
                    if (iTime == 0) {{
                        cumProdHistory[static_cast<size_t>(i)][0] = 0.0;
                        cumLossHistory[static_cast<size_t>(i)][0] = 0.0;
                    }} else {{
                        double dT = timeArray[iTime] - timeArray[iTime - 1];
                        cumProdHistory[static_cast<size_t>(i)][iTime] =
                            cumProdHistory[static_cast<size_t>(i)][iTime-1]
                            + 0.5 * (prodHistory[static_cast<size_t>(i)][iTime-1] + P_now[i]) * dT;
                        cumLossHistory[static_cast<size_t>(i)][iTime] =
                            cumLossHistory[static_cast<size_t>(i)][iTime-1]
                            + 0.5 * (lossHistory[static_cast<size_t>(i)][iTime-1] + L_now[i]) * dT;
                    }}
                }}
            }}
            /* ---- End P/L diagnostics ---- */"""

    # Insert after the speciesHistory[i][iTime] = VAR[i] copy line
    c, n = re.subn(
        r'(for\s*\(\s*int\s+i\s*=\s*0\s*;\s*i\s*<\s*NVAR\s*;\s*i\+\+\s*\)\s*speciesHistory\[i\]\[iTime\]\s*=\s*VAR\[i\]\s*;)',
        r'\1' + diag_calls,
        c, count=1
    )
    if n:
        done("B4: Diagnostic calls inserted after speciesHistory copy in time loop")
    else:
        warn("B4: Could not find speciesHistory[i][iTime] = VAR[i] line")
else:
    skip("B4: ComputeRxnRates call already in BoxModel.cpp")

# --- B5: Update writeBoxModelOutput ---
# First: update its signature
if 'prodHistory' not in c or 'rxnRateHistory' not in c:
    warn("B5: prodHistory or rxnRateHistory not yet in file — check B3 succeeded")

# Find and update the function definition signature
sig_match = re.search(
    r'(void\s+writeBoxModelOutput\s*\()([^)]+)(\))',
    c
)
if sig_match and 'prodHistory' not in sig_match.group(2):
    old_sig = sig_match.group(0)
    # Build new extended signature
    new_sig = """void writeBoxModelOutput(
    const std::string& outputFile,
    const std::vector<double>& timeArray,
    const std::vector<std::vector<double>>& speciesHistory,
    const std::vector<std::vector<double>>& prodHistory,
    const std::vector<std::vector<double>>& lossHistory,
    const std::vector<std::vector<double>>& tauHistory,
    const std::vector<std::vector<double>>& cumProdHistory,
    const std::vector<std::vector<double>>& cumLossHistory,
    const std::vector<std::vector<double>>& rxnRateHistory,
    const std::vector<double>& cosSZASeries,
    double airDens, double relHumidity_i, int nVar)"""
    c = c.replace(old_sig, new_sig, 1)
    done("B5a: writeBoxModelOutput signature updated")
elif sig_match:
    skip("B5a: signature already has prodHistory")
else:
    warn("B5a: Could not find writeBoxModelOutput signature")

# Add NetCDF diagnostic variable writes inside the function body
if 'prod_rate' not in c:
    new_nc_code = f"""
        /* ------------------------------------------------------------------ */
        /* Diagnostic output variables                                          */
        /* ------------------------------------------------------------------ */
        const size_t nTime_diag = timeArray.size();

        /* Helper lambda: flatten [species][time] -> [time x species] float buffer
         * and write as a 2D NetCDF variable                                   */
        auto write2D = [&](const std::string& varName,
                           const std::string& units,
                           const std::string& longName,
                           const std::vector<std::vector<double>>& data,
                           const netCDF::NcDim& dim1,
                           const netCDF::NcDim& dim2,
                           int n2,
                           double scale = 1.0)
        {{
            netCDF::NcVar v = ncFile.addVar(varName, netCDF::ncFloat, {{dim1, dim2}});
            v.putAtt("units",     units);
            v.putAtt("long_name", longName);
            std::vector<float> buf(nTime_diag * static_cast<size_t>(n2));
            for (size_t t = 0; t < nTime_diag; t++)
                for (int s = 0; s < n2; s++)
                    buf[t * static_cast<size_t>(n2) + static_cast<size_t>(s)] =
                        static_cast<float>(data[static_cast<size_t>(s)][t] * scale);
            v.putVar(buf.data());
        }};

        netCDF::NcDim specDim = ncFile.addDim("species",  static_cast<size_t>(nVar));
        netCDF::NcDim rxnDim  = ncFile.addDim("reaction", static_cast<size_t>(NREACT));
        netCDF::NcDim timDim  = ncFile.addDim("diag_time", nTime_diag);

        write2D("prod_rate",  "molec cm-3 s-1",
                "Instantaneous net production rate P[i] (positive Vdot)",
                prodHistory,    timDim, specDim, nVar);

        write2D("loss_rate",  "molec cm-3 s-1",
                "Instantaneous net loss rate |L[i]| (positive magnitude)",
                lossHistory,    timDim, specDim, nVar);

        write2D("lifetime",   "s",
                "Chemical lifetime [X]/L (1e30 where L is negligible)",
                tauHistory,     timDim, specDim, nVar);

        write2D("cum_prod",   "molec cm-3",
                "Cumulative integrated production (trapezoidal sum)",
                cumProdHistory, timDim, specDim, nVar);

        write2D("cum_loss",   "molec cm-3",
                "Cumulative integrated loss (trapezoidal sum)",
                cumLossHistory, timDim, specDim, nVar);

        write2D("rxn_rate",   "molec cm-3 s-1",
                "Instantaneous reaction rate A[j] for each KPP reaction",
                rxnRateHistory, timDim, rxnDim, NREACT);
"""
    # Insert before the catch block of the NetCDF try
    c, n = re.subn(
        r'(\s*\}\s*catch\s*\(.*?(?:NcException|exception|std::).*?\))',
        new_nc_code + r'\1',
        c, count=1, flags=re.DOTALL
    )
    if n:
        done("B5b: NetCDF diagnostic variables added to writeBoxModelOutput")
    else:
        warn("B5b: Could not find NetCDF catch block — appending before last }")
else:
    skip("B5b: prod_rate already in writeBoxModelOutput")

# Update the call site of writeBoxModelOutput
# Find the call and add the new arguments
call_match = re.search(r'writeBoxModelOutput\s*\([^;]+;', c, re.DOTALL)
if call_match and 'prodHistory' not in call_match.group():
    old_call = call_match.group()
    # Replace: inject new args after speciesHistory,
    new_call = re.sub(
        r'(writeBoxModelOutput\s*\(\s*\S+\s*,\s*timeArray\s*,\s*speciesHistory\s*,)',
        r'\1\n                             prodHistory, lossHistory, tauHistory,\n'
        r'                             cumProdHistory, cumLossHistory, rxnRateHistory,',
        old_call
    )
    c = c.replace(old_call, new_call, 1)
    done("B5c: writeBoxModelOutput call site updated with new arguments")
elif call_match:
    skip("B5c: call site already has prodHistory")
else:
    warn("B5c: Could not find writeBoxModelOutput call site")

write(p, c)

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== Plan B verification ===")
for path, pattern in [
    (f"{ROOT}/include/KPP/KPP.hpp",         "ComputeRxnRates"),
    (f"{ROOT}/src/KPP/KPP_Function.cpp",    "ComputeRxnRates"),
    (f"{ROOT}/src/KPP/KPP_Function.cpp",    "ComputePL"),
    (f"{ROOT}/src/Core/BoxModel.cpp",        "prodHistory"),
    (f"{ROOT}/src/Core/BoxModel.cpp",        "ComputeRxnRates"),
    (f"{ROOT}/src/Core/BoxModel.cpp",        "prod_rate"),
    (f"{ROOT}/src/Core/BoxModel.cpp",        "rxnRateHistory"),
]:
    content = read(path)
    status = "✓ FOUND" if pattern in content else "✗ MISSING"
    print(f"  {status}: '{pattern}' in {os.path.basename(path)}")

print("\n=== Plan B COMPLETE ===")
