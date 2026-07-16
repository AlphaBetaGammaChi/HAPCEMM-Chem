import os
import re
import json
import sys

def parse_kpp_equation(line):
    # Strip comments: {} and //
    line = re.sub(r'\{.*?\}', '', line)
    line = re.sub(r'//.*', '', line)
    line = line.strip()
    
    if not line or ':' not in line or '=' not in line:
        return None
        
    # Strip equation tag like <1>
    line = re.sub(r'^<\d+>\s*', '', line)
    
    # Split equations and rates (Format: Reactants = Products : Rate;)
    eq_part, rate_part = line.split(':')
    rate_constant = rate_part.replace(';', '').strip()
    
    # Strip double precision Fortran suffixes (e.g. 1.0D-12 -> 1.0e-12, 2.0D0 -> 2.0e0)
    rate_constant = re.sub(r'(\d+\.?\d*)[Dd]([+-]?\d+)', r'\1e\2', rate_constant)
    
    reactants_str, products_str = eq_part.split('=')
    
    # Extract species and coefficients
    def extract_species(part_str):
        species_list = []
        parts = part_str.split('+')
        for p in parts:
            p = p.strip()
            if not p or p.upper() in ["PROD", "IGNORE", "M"]: 
                # Note: M is the generic third-body background species, handled separately by MICM/MusicBox
                continue
            # Check for coefficients like 2O3 or 0.5NO
            match = re.match(r'^([0-9\.]+)?\s*([A-Za-z0-9_]+)', p)
            if match:
                coeff = float(match.group(1)) if match.group(1) else 1.0
                name = match.group(2)
                species_list.append({"name": name, "coefficient": coeff})
        return species_list

    return {
        "type": "ARRHENIUS" if ("temp" in rate_constant.lower() or "t" in rate_constant.lower()) else "CONSTANT", 
        "rate_constant": rate_constant,
        "reactants": extract_species(reactants_str),
        "products": extract_species(products_str)
    }

def convert_kpp_to_micm(kpp_file_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    reactions = []
    unique_species = set()
    
    in_equations = False

    with open(kpp_file_path, 'r') as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#EQUATIONS"):
                in_equations = True
                continue
            if stripped.startswith("#") and not stripped.startswith("#EQUATIONS"):
                if in_equations:
                    in_equations = False # Exit equations section if another starts
                continue
            
            if not in_equations:
                continue
                
            parsed = parse_kpp_equation(line)
            if parsed:
                reactions.append(parsed)
                for sp in parsed["reactants"] + parsed["products"]:
                    unique_species.add(sp["name"])

    # Format into official MICM species list
    species_json = [{"name": sp, "type": "CHEM_SPEC"} for sp in sorted(unique_species)]
    mechanism_json = {"reactions": reactions}

    # Save to directory
    with open(os.path.join(output_dir, "species.json"), 'w') as f:
        json.dump(species_json, f, indent=2)
    with open(os.path.join(output_dir, "mechanism.json"), 'w') as f:
        json.dump(mechanism_json, f, indent=2)
        
    print(f"Successfully generated MICM files in: {output_dir}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python kpp_to_micm.py <input.eqn> <output_directory>")
        sys.exit(1)
    convert_kpp_to_micm(sys.argv[1], sys.argv[2])
