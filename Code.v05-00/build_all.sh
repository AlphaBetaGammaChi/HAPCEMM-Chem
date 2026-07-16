#!/bin/bash
# Script to build UCX and CRI-v2r5 APCEMM chemical mechanism binaries
set -euo pipefail

# Load required compiler modules
module load libfabric
module load gcc-native/13.2

BASE_DIR="/projects/b35as/public/HAPCEMM-Chem/Code.v05-00"
BUILD_DIR="${BASE_DIR}/build"
BIN_DIR="${BASE_DIR}/bin"

mkdir -p "$BIN_DIR"

# Ensure cmake configuration is initialized
cd "$BUILD_DIR"
cmake .. -DCMAKE_BUILD_TYPE=Release -DUSE_MICM=ON

clean_active_kpp() {
    echo "Cleaning active KPP directory..."
    # Remove source files in src/KPP (keeping CMakeLists.txt)
    find "${BASE_DIR}/src/KPP" -mindepth 1 -maxdepth 1 ! -name "CMakeLists.txt" -exec rm -rf {} +
    # Remove header files in include/KPP
    find "${BASE_DIR}/include/KPP" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
}

# 1. Build UCX Binary
echo "=========================================="
echo "=== Building UCX Binary ==="
echo "=========================================="
clean_active_kpp
cp -r "${BASE_DIR}/src/KPP-UCX/"* "${BASE_DIR}/src/KPP/"
cp -r "${BASE_DIR}/include/KPP-UCX/"* "${BASE_DIR}/include/KPP/"
cd "$BUILD_DIR"
make -j$(nproc)
mv "${BUILD_DIR}/APCEMM" "${BIN_DIR}/apcemm_ucx"

# 2. Build CRI Binary
echo "=========================================="
echo "=== Building CRI-v2r5 Binary ==="
echo "=========================================="
clean_active_kpp
cp -r "${BASE_DIR}/src/KPP-CRI-V2R5/"* "${BASE_DIR}/src/KPP/"
cp -r "${BASE_DIR}/include/KPP-CRI-V2R5/"* "${BASE_DIR}/include/KPP/"
cd "$BUILD_DIR"
make -j$(nproc)
mv "${BUILD_DIR}/APCEMM" "${BIN_DIR}/apcemm_cri-v2r5"

echo "=========================================="
echo "=== Binaries rebuilt successfully! ==="
echo "Location: ${BIN_DIR}"
echo "=========================================="
