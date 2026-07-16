#!/bin/bash
#SBATCH --nodes=1
#SBATCH --mem=64G  
#SBATCH --time=01:00:00
#SBATCH --partition=grace
#SBATCH --job-name=test_sens


cd /projects/b35as/public/HAPCEMM-Chem/kpp_mcm

# 1. Set the KPP_HOME environment variable
export KPP_HOME=/lfs1i3/projects/public/b35as/WRF-Chem-4.7.1-Isambard/WRF-Chem-4.7.1/WRF-Chem-4.7.1/chem/KPP/kpp/kpp-2.1

# 2. Run KPP
$KPP_HOME/bin/kpp mcm.kpp
