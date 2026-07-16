import os
import re

filepath = "/projects/b35as/public/HAPCEMM-Chem/Code.v05-00/src/KPP-CRI-V2R5/KPP_Rates.cpp"

if os.path.exists(filepath):
    print(f"Patching exponentiations, photol brackets, and D exponents in {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace Fortran exponentiation ** with C equivalents
    content = content.replace('TEMP**(2.)', '(TEMP*TEMP)')
    content = content.replace('TEMP**(2)', '(TEMP*TEMP)')
    content = content.replace('(TEMP/300.)**(-2.6)', 'pow(TEMP/300., -2.6)')
    content = content.replace('(TEMP/300.)**(4.57)', 'pow(TEMP/300., 4.57)')

    # Replace PHOTOL(number) with PHOTOL[number]
    content = re.sub(r'PHOTOL\((\d+)\)', r'PHOTOL[\1]', content)

    # Replace Fortran double precision float D exponents with E (e.g. 7.6D15 -> 7.6E15)
    content = re.sub(r'(\d+(?:\.\d+)?)[Dd]([+-]?\d+)', r'\1E\2', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully patched KPP_Rates.cpp!")
else:
    print(f"Error: {filepath} not found.")
