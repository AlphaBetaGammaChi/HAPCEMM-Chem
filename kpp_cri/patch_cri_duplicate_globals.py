import os

path_monitor = '/projects/b35as/public/HAPCEMM-Chem/Code.v05-00/src/KPP-CRI-V2R5/KPP_Monitor.cpp'
if os.path.exists(path_monitor):
    with open(path_monitor, 'r') as f:
        content = f.read()
    
    replacements = {
        '  const char * SPC_NAMES[] = {': '  extern const char * SPC_NAMES[] = {',
        '  int  LOOKAT[] = {': '  extern int  LOOKAT[] = {',
        '  char *  SMASS[] = {': '  extern char *  SMASS[] = {',
        '  const char *  EQN_NAMES[] = {': '  extern const char *  EQN_NAMES[] = {'
    }
    
    for old, new in replacements.items():
        if old in content:
            content = content.replace(old, new)
            print(f'Replaced in CRI KPP_Monitor.cpp: {old[:20]}...')
            
    with open(path_monitor, 'w') as f:
        f.write(content)
else:
    print('CRI KPP_Monitor.cpp not found')

path_global = '/projects/b35as/public/HAPCEMM-Chem/Code.v05-00/src/KPP-CRI-V2R5/KPP_Global.cpp'
if os.path.exists(path_global):
    with open(path_global, 'r') as f:
        content = f.read()
    
    replacements = {
        'int LOOKAT[NLOOKAT];': '// int LOOKAT[NLOOKAT] is defined in KPP_Monitor.cpp',
        'char * SMASS[NMASS];': '// char * SMASS[NMASS] is defined in KPP_Monitor.cpp',
        'const char * EQN_NAMES[NREACT];': '// const char * EQN_NAMES[NREACT] is defined in KPP_Monitor.cpp'
    }
    
    dummy_spc = '''const char * SPC_NAMES[NSPEC] = {
    "NO", "NO2", "O3", "CO", "CH4", "SO2", "HNO3", "H2O", 
    /* This list is incomplete and just a placeholder to satisfy the linker if needed.
       The actual names are usually in KPP_Monitor.cpp */
    "TEMP"
};'''
    if dummy_spc in content:
        content = content.replace(dummy_spc, '// const char * SPC_NAMES[NSPEC] is defined in KPP_Monitor.cpp')
        print('Removed dummy SPC_NAMES from CRI KPP_Global.cpp')
        
    for old, new in replacements.items():
        if old in content:
            content = content.replace(old, new)
            print(f'Replaced in CRI KPP_Global.cpp: {old[:20]}...')
            
    with open(path_global, 'w') as f:
        f.write(content)
else:
    print('CRI KPP_Global.cpp not found')
