import os

filepath = "/projects/b35as/public/HAPCEMM-Chem/Code.v05-00/src/KPP-CRI-V2R5/KPP_LinearAlgebra.cpp"

if os.path.exists(filepath):
    print(f"Patching KPP splitting bug in {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Forward substitution fix
    target1 = "  XX[487] = (X[487]-JVS[12]*"
    target2 = "  XX[487] = XX[487]"
    
    # 2. Transpose solve fix (mismatched opening parenthesis)
    target3 = "  XX[487] = (XX[487]-JVS[4358]*XX[488]"
    
    modified = False
    if target1 in content and target2 in content:
        content = content.replace(target1, "  XX[487] = X[487]-JVS[12]*")
        content = content.replace(target2, "  XX[487] = (XX[487]")
        modified = True
        
    if target3 in content:
        content = content.replace(target3, "  XX[487] = XX[487]-JVS[4358]*XX[488]")
        modified = True
        
    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully patched KPP_LinearAlgebra.cpp splitting bugs!")
    else:
        print("Error: Could not locate the target lines in KPP_LinearAlgebra.cpp.")
else:
    print(f"Error: {filepath} not found.")
