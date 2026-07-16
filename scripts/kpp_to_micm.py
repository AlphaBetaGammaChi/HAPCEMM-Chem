#!/usr/bin/env python3
import os
import sys
import re
import json

def clean_number(s):
    # Convert Fortran double precision "D" to "e"
    s = s.replace('d', 'e').replace('D', 'e').strip()
    # Clean leading plus or double exponents
    return float(s)

def parse_stoich_and_species(side_str):
    # Splits "2*NO2 + O3" into {"NO2": 2.0, "O3": 1.0}
    parts = side_str.split('+')
    result = {}
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # Match optional coefficient like "2.0 * O3" or "2*O3" or "0.05*HO2"
        match = re.match(r'^([0-9.eE+-]+)\s*\*\s*([a-zA-Z0-9_]+)$', p)
        if match:
            coeff = float(match.group(1))
            spec = match.group(2)
        else:
            # Check if it starts with a number like "2O3"
            match_num = re.match(r'^([0-9.]+)\s*([a-zA-Z_][a-zA-Z0-9_]*)$', p)
            if match_num:
                coeff = float(match_num.group(1))
                spec = match_num.group(2)
            else:
                coeff = 1.0
                spec = p
        result[spec] = coeff
    return result

def convert_rate_expression(rate_str):
    rate_str = rate_str.strip()
    
    # 1. Check for simple constant number e.g. "2.0D-11" or "2e-11"
    if re.match(r'^[0-9.eEdD+-]+$', rate_str):
        try:
            val = clean_number(rate_str)
            return {
                "type": "ARRHENIUS",
                "A": val,
                "B": 0.0,
                "C": 0.0
            }
        except ValueError:
            pass

    # 2. Check for standard Arrhenius: A * EXP( C / TEMP )
    # e.g., 1.4D-12*EXP(-1310/TEMP)
    arrh_match = re.match(
        r'^([0-9.eEdD+-]+)\s*\*\s*EXP\(\s*([0-9.eEdD+-]+)\s*/\s*TEMP\s*\)$',
        rate_str, re.IGNORECASE
    )
    if arrh_match:
        try:
            a = clean_number(arrh_match.group(1))
            c = clean_number(arrh_match.group(2))
            return {
                "type": "ARRHENIUS",
                "A": a,
                "B": 0.0,
                "C": c
            }
        except ValueError:
            pass

    # 3. Check for Arrhenius with Temperature Exponent: A * (TEMP/300)**B * EXP( C / TEMP )
    # e.g. 2.03D-16*(TEMP/300)**4.57*EXP(693/TEMP) or 6.0D-34*(TEMP/300)**(-2.6)
    arrh_temp_match = re.match(
        r'^([0-9.eEdD+-]+)\s*\*\s*\(TEMP/300\)\*\*([a-zA-Z0-9.eEdD+-]+)(?:\s*\*\s*EXP\(\s*([0-9.eEdD+-]+)\s*/\s*TEMP\s*\))?$',
        rate_str.replace(' ', ''), re.IGNORECASE
    )
    if arrh_temp_match:
        try:
            a = clean_number(arrh_temp_match.group(1))
            # Remove parentheses from exponent if present
            b_str = arrh_temp_match.group(2).replace('(', '').replace(')', '')
            b = clean_number(b_str)
            c = clean_number(arrh_temp_match.group(3)) if arrh_temp_match.group(3) else 0.0
            return {
                "type": "ARRHENIUS",
                "A": a,
                "B": b,
                "C": c
            }
        except ValueError:
            pass

    # 4. Check for Photolysis (contains "J" or similar photolysis rate references)
    if 'J' in rate_str or 'PHOTOL' in rate_str:
        return {
            "type": "PHOTOLYSIS",
            "kpp_expression": rate_str
        }

    # 5. Default fallback to Troe/Custom or user defined
    return {
        "type": "USER_DEFINED",
        "kpp_expression": rate_str
    }

def parse_kpp(eqn_path, spc_path):
    species = set()
    reactions = []

    # Parse species if .spc path provided
    if spc_path and os.path.exists(spc_path):
        with open(spc_path, 'r') as f:
            lines = f.readlines()
        in_def = False
        for line in lines:
            line = line.strip()
            if line.startswith('#DEFVAR') or line.startswith('#DEFFIX'):
                in_def = True
                continue
            if line.startswith('#') and in_def:
                in_def = False
            if in_def and '=' in line:
                parts = line.split('=')
                spec = parts[0].strip()
                if spec:
                    species.add(spec)

    # Parse reactions from .eqn
    with open(eqn_path, 'r') as f:
        content = f.read()

    # Find the EQUATIONS block
    eq_match = re.search(r'#EQUATIONS(.*)', content, re.DOTALL)
    if not eq_match:
        print("Error: #EQUATIONS block not found in .eqn file", file=sys.stderr)
        sys.exit(1)

    eq_lines = eq_match.group(1).split('\n')
    for line in eq_lines:
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('//'):
            continue
        
        # Format of eqn: reactants = products : rate_constant ;
        if '=' in line and ':' in line:
            # Strip trailing semicolon
            if line.endswith(';'):
                line = line[:-1].strip()
            
            parts = line.split(':')
            rate_expr = parts[1].strip()
            
            eq_part = parts[0].split('=')
            reactants_str = eq_part[0].strip()
            products_str = eq_part[1].strip()
            
            reactants = parse_stoich_and_species(reactants_str)
            products = parse_stoich_and_species(products_str)
            
            # Record any species found if we didn't parse them from .spc
            for r in reactants:
                species.add(r)
            for p in products:
                species.add(p)
                
            rate_data = convert_rate_expression(rate_expr)
            
            rxn = {
                "reactants": {r: {"qty": q} for r, q in reactants.items()},
                "products": {p: {"qty": q} for p, q in products.items()},
                "rate": rate_data
            }
            reactions.append(rxn)

    return sorted(list(species)), reactions

def main():
    if len(sys.argv) < 3:
        print("Usage: python kpp_to_micm.py <mechanism.eqn> <output_dir> [mechanism.spc]")
        sys.exit(1)

    eqn_path = sys.argv[1]
    output_dir = sys.argv[2]
    spc_path = sys.argv[3] if len(sys.argv) > 3 else None

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Parsing KPP files...")
    species, reactions = parse_kpp(eqn_path, spc_path)
    print(f"Found {len(species)} species and {len(reactions)} reactions.")

    # 1. Write species.json
    species_json = []
    for s in species:
        species_json.append({
            "name": s,
            "type": "CHEM_SPEC"
        })
    
    with open(os.path.join(output_dir, "species.json"), "w") as f:
        json.dump(species_json, f, indent=2)
    print(f"Created species.json")

    # 2. Write reactions.json
    processes = []
    for i, r in enumerate(reactions):
        p_type = r["rate"]["type"]
        process = {
            "reactants": {k: {} for k in r["reactants"]},
            "products": {k: {"yield": v["qty"]} for k, v in r["products"].items()}
        }
        
        if p_type == "ARRHENIUS":
            process["type"] = "ARRHENIUS"
            process["A"] = r["rate"]["A"]
            process["B"] = r["rate"]["B"]
            process["C"] = r["rate"]["C"]
        elif p_type == "PHOTOLYSIS":
            process["type"] = "PHOTOLYSIS"
            # Default scaling factor, user can adjust
            process["scaling_factor"] = 1.0
        else:
            # Fallback to CONSTANT or USER_DEFINED
            process["type"] = "CONSTANT"
            # Set a dummy rate if we couldn't parse it
            process["k"] = 0.0
            process["comment"] = f"Unparsed KPP rate: {r['rate']['kpp_expression']}"

        processes.append(process)

    reactions_json = {
        "reactions": processes
    }
    
    with open(os.path.join(output_dir, "reactions.json"), "w") as f:
        json.dump(reactions_json, f, indent=2)
    print(f"Created reactions.json")

    # 3. Write config.json
    config_json = {
        "gas_phase": {
            "species": [s["name"] for s in species_json],
            "reactions": "reactions.json"
        }
    }
    with open(os.path.join(output_dir, "config.json"), "w") as f:
        json.dump(config_json, f, indent=2)
    print(f"Created config.json")
    print(f"MICM configuration files generated at {output_dir}")

if __name__ == "__main__":
    main()
