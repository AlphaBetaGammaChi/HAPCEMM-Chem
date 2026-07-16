#!/bin/bash
set -e

# Load compiler module
module load gcc-native/13.2

# Define directories
BASE_DIR="/projects/b35as/public/HAPCEMM-Chem"
SRC_DIR="${BASE_DIR}/micm_src"
INSTALL_DIR="${BASE_DIR}/micm_installed"

echo "=== Cleaning and creating directories ==="
rm -rf "${SRC_DIR}"
mkdir -p "${SRC_DIR}"
mkdir -p "${INSTALL_DIR}"

echo "=== Cloning NCAR micm repository ==="
git clone --recursive https://github.com/NCAR/micm.git "${SRC_DIR}"

cd "${SRC_DIR}"

echo "=== Creating build environment ==="
mkdir -p build
cd build

echo "=== Configuring CMake ==="
# Install locally under base directory and build in Release mode
cmake .. \
  -DCMAKE_INSTALL_PREFIX="${INSTALL_DIR}" \
  -DCMAKE_BUILD_TYPE=Release

echo "=== Compiling MICM C++ Library ==="
make -j4

echo "=== Installing MICM locally ==="
make install

echo "=== MICM compilation and installation complete ==="
