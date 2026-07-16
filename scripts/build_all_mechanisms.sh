#!/bin/bash
module load gcc-native/14
# automated build script to compile different mechanisms into separate binaries

# Exit on error
set -e

# Define directories
ROOT="/projects/b35as/public/HAPCEMM-Chem/Code.v05-00"
SRC_KPP="$ROOT/src/KPP"
INC_KPP="$ROOT/include/KPP"
BUILD_DIR="$ROOT/build"
BIN_DIR="$ROOT/bin"

mkdir -p "$BIN_DIR" "$BUILD_DIR"

# Step 1: Ensure UCX backup directory exists. If not, copy current KPP files.
if [ ! -d "$ROOT/src/KPP-UCX" ]; then
    echo "Creating backup of current UCX mechanism..."
    mkdir -p "$ROOT/src/KPP-UCX"
    mkdir -p "$ROOT/include/KPP-UCX"
    cp -r "$SRC_KPP"/* "$ROOT/src/KPP-UCX/"
    cp -r "$INC_KPP"/* "$ROOT/include/KPP-UCX/"
fi

# Function to build a specific mechanism
build_mechanism() {
    local name=$1
    local src_back="$ROOT/src/KPP-${name}"
    local inc_back="$ROOT/include/KPP-${name}"

    echo "============================================="
    echo "Building mechanism: $name"
    echo "============================================="

    if [ ! -d "$src_back" ] || [ ! -d "$inc_back" ]; then
        echo "Error: Backup directories for $name do not exist!"
        echo "Please place KPP generated files in:"
        echo "  - $src_back"
        echo "  - $inc_back"
        return 1
    fi

    # Swap files
    echo "Swapping files for $name..."
    rm -rf "$SRC_KPP"/*
    rm -rf "$INC_KPP"/*
    cp -r "$src_back"/* "$SRC_KPP"/
    cp -r "$inc_back"/* "$INC_KPP"/

    # Rebuild
    echo "Compiling..."
    cd "$BUILD_DIR" && rm -rf *
    cmake -DCMAKE_TOOLCHAIN_FILE=../submodules/vcpkg/scripts/buildsystems/vcpkg.cmake ..
    make -j

    # Copy binary to bin folder
    echo "Moving binary..."
    cp APCEMM "$BIN_DIR/apcemm_${name,,}" # lowercase
    echo "Successfully built $BIN_DIR/apcemm_${name,,}"
}

# Capture current trap to restore UCX files if the script exits or fails
cleanup() {
    echo "Restoring default UCX mechanism files..."
    rm -rf "$SRC_KPP"/*
    rm -rf "$INC_KPP"/*
    cp -r "$ROOT/src/KPP-UCX"/* "$SRC_KPP"/
    cp -r "$ROOT/include/KPP-UCX"/* "$INC_KPP"/
    echo "Restore completed."
}
trap cleanup EXIT

# Step 2: Build other mechanisms if their files exist
if [ -d "$ROOT/src/KPP-CRI-V2R5" ]; then
    build_mechanism "CRI-V2R5"
else
    echo "Skipping CRI-V2R5: directory src/KPP-CRI-V2R5 not found."
fi

# Skip MCM build to save time
# if [ -d "$ROOT/src/KPP-MCM" ]; then
#     build_mechanism "MCM"
# else
#     echo "Skipping MCM: directory src/KPP-MCM not found."
# fi

# Always rebuild UCX to ensure default binary is fresh and the state is clean
build_mechanism "UCX"
