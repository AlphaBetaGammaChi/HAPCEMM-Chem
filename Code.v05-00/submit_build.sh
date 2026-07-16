#!/bin/bash
#SBATCH --job-name=APCEMM-BuildAll
#SBATCH --output=/projects/b35as/public/HAPCEMM-Chem/Code.v05-00/build_%j.log
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --partition=grace

cd /projects/b35as/public/HAPCEMM-Chem/Code.v05-00
./build_all.sh
