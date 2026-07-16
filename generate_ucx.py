import os
import json

def build_ucx(output_dir, modified_rate=False):
    os.makedirs(output_dir, exist_ok=True)
    
    rate = "2.0e-12" if not modified_rate else "2.5e-12"
    
    reactions = [
        {
            "type": "ARRHENIUS",
            "reactants": {
                "O3": {"qty": 1.0},
                "NO": {"qty": 1.0}
            },
            "products": {
                "NO2": {"yield": 1.0},
                "O2": {"yield": 1.0}
            },
            "rate_constant": rate
        }
    ]
    
    species = [
        {"name": "O3", "type": "CHEM_SPEC"},
        {"name": "NO", "type": "CHEM_SPEC"},
        {"name": "NO2", "type": "CHEM_SPEC"},
        {"name": "O2", "type": "CHEM_SPEC"}
    ]
    
    # Save outputs to matching targets
    with open(os.path.join(output_dir, "mechanism.json"), 'w') as f:
        json.dump({"reactions": reactions}, f, indent=2)
    with open(os.path.join(output_dir, "species.json"), 'w') as f:
        json.dump(species, f, indent=2)
        
    print(f"Generated UCX configuration in: {output_dir}")

if __name__ == "__main__":
    # Generate both versions inside the standard mechanisms folder
    build_ucx("mechanisms/ucx_base", modified_rate=False)
    build_ucx("mechanisms/ucx_mod", modified_rate=True)
