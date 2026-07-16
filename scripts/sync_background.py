#!/usr/bin/env python3
import xarray as xr
import numpy as np
import sys
import os
import re

# Paths
GMI_DIR = '/projects/b35as/public/HAPCEMM-Chem/global_data/GMI'
GEOS_FILE = '/projects/b35as/public/HAPCEMM-Chem/global_data/GEOSChem.Restart.fullchem.20190701_0000z.nc4'
INPUT_YAML = '/projects/b35as/public/HAPCEMM-Chem/input_data/input.yaml'
INIT_TXT = '/projects/b35as/public/HAPCEMM-Chem/input_data/init.txt'

SPC_NAMES = [
    "CO2","PPN","BrNO2","IEPOX","PMNN","N2O","N","PAN",
    "ALK4","MAP","MPN","Cl2O2","ETP","HNO2","C3H8","RA3P",
    "RB3P","OClO","ClNO2","ISOP","HNO4","MAOP","MP","ClOO",
    "RP","BrCl","PP","PRPN","SO4","Br2","ETHLN","MVKN",
    "R4P","C2H6","RIP","VRP","ATOOH","IAP","DHMOB","MOBA",
    "MRP","N2O5","ISNOHOO","ISNP","ISOPNB","IEPOXOO","MACRNO2","ROH",
    "MOBAOO","DIBOO","PMN","ISNOOB","INPN","H","BrNO3","PRPE",
    "MVKOO","Cl2","ISOPND","HOBr","A3O2","PROPNN","GLYX","MAOPO2",
    "CH4","GAOO","B3O2","ACET","MACRN","CH2OO","MGLYOO","VRO2",
    "MGLOO","MACROO","PO2","CH3CHOO","MAN2","ISNOOA","H2O2","PRN1",
    "ETO2","KO2","RCO3","HC5OO","GLYC","ClNO3","RIO2","R4N1",
    "HOCl","ATO2","HNO3","ISN1","MAO3","MRO2","INO2","HAC",
    "HC5","MGLY","ISOPNBO2","ISOPNDO2","R4O2","R4N2","BrO","RCHO",
    "MEK","ClO","MACR","SO2","MVK","ALD2","MCO3","CH2O",
    "H2O","Br","NO","NO3","Cl","O","O1D","O3",
    "HO2","NO2","OH","HBr","HCl","CO","MO2","ACTA",
    "EOH","H2","HCOOH","MOH","N2","O2","RCOOH"
]

def get_input_params():
    with open(INPUT_YAML, 'r') as f:
        lines = f.readlines()
        params = {}
        for line in lines:
            if 'LON [deg]' in line: params['lon'] = float(line.split(':')[1].strip().split()[0])
            if 'LAT [deg]' in line: params['lat'] = float(line.split(':')[1].strip().split()[0])
            if 'Emission day' in line: params['day'] = int(line.split(':')[1].strip().split()[0])
            if 'Pressure [hPa]' in line: params['pres'] = float(line.split(':')[1].strip().split()[0])
        return params

def lookup_gmi(lon, lat, month, pres, gmi_spec):
    path = os.path.join(GMI_DIR, f'gmi.clim.{gmi_spec}.geos5.2x25.nc')
    if not os.path.exists(path) or os.path.getsize(path) < 1000: return None
    try:
        ds = xr.open_dataset(path, engine='netcdf4')
        ds_ref = xr.open_dataset(GEOS_FILE, engine='netcdf4')
        p_levels = (ds_ref.hyam * ds_ref.P0 + ds_ref.hybm * 1013.25).values
        lev_idx = np.argmin(np.abs(p_levels - pres))
        lev_val = ds.lev.values[lev_idx]
        try:
            val = ds['species'].isel(time=month-1).sel(lon=lon, lat=lat, method='nearest').sel(lev=lev_val, method='nearest')
        except:
            val = ds['species'].isel(time=month-1).sel(lon=lon, latitude=lat, method='nearest').sel(lev=lev_val, method='nearest')
        return float(val.values)
    except Exception as e:
        return None

def lookup_geos(lon, lat, pres, species_rst_name):
    try:
        ds = xr.open_dataset(GEOS_FILE, engine='netcdf4')
        p_levels = (ds.hyam * ds.P0 + ds.hybm * 1013.25).values
        lev_idx = np.argmin(np.abs(p_levels - pres))
        lev_val = ds.lev.values[lev_idx]
        lon_adj = lon if lon >= 0 else 360 + lon
        val = ds[species_rst_name].isel(time=0).sel(lon=lon_adj, lat=lat, lev=lev_val, method='nearest')
        return float(val.values)
    except Exception as e:
        return None

def main():
    params = get_input_params()
    print(f"Syncing background for Lon: {params['lon']}, Lat: {params['lat']}, Day: {params['day']}, Pres: {params['pres']} hPa")
    month = int((params['day'] - 1) / 30) + 1
    month = max(1, min(12, month))

    gmi_map = {
        'OH': 'OH', 'HO2': 'HO2', 'NO': 'NO', 'NO2': 'NO2', 'O3': 'O3',
        'HNO3': 'HNO3', 'ClO': 'ClO', 'BrO': 'BrO', 'HCl': 'HCl',
        'ClNO3': 'ClONO2', 'BrNO3': 'BrONO2', 'CH4': 'CH4', 'CO': 'CO',
        'PAN': 'PAN', 'PPN': 'PPN', 'SO2': 'SO2'
    }
    rst_map = {
        'CO2': 'SpeciesRst_CO2', 'H2O': 'SpeciesRst_H2O', 'H2': 'SpeciesRst_H2',
        'SO4': 'SpeciesRst_SO4', 'O': 'SpeciesRst_O',
        'O1D': 'SpeciesRst_O1D', 'Cl': 'SpeciesRst_Cl', 'HBr': 'SpeciesRst_HBr',
        'N2O': 'SpeciesRst_N2O', 'N': 'SpeciesRst_N', 'N2': 'SpeciesRst_N2', 'O2': 'SpeciesRst_O2', 'SO2': 'SpeciesRst_SO2', 'MPN': 'SpeciesRst_MPN', 'PAN': 'SpeciesRst_PAN', 'PPN': 'SpeciesRst_PPN'
    }

    results = []
    for spec in SPC_NAMES:
        val = None
        if spec in gmi_map:
            val = lookup_gmi(params['lon'], params['lat'], month, params['pres'], gmi_map[spec])
        if (val is None or np.isnan(val)) and spec in rst_map:
            val = lookup_geos(params['lon'], params['lat'], params['pres'], rst_map[spec])
        
        if val is None or np.isnan(val):
            if spec == 'N2': val = 0.7808
            elif spec == 'O2': val = 0.2095
            elif spec == 'H2': val = 5.0e-7
            elif spec == 'CO2': val = 4.15e-4
            else: val = 1.0e-21 # default background
            
        results.append(val)

    with open(INIT_TXT, 'w') as f:
        f.write("# BOF\n# Automatically generated background concentrations (Full 135 species)\n")
        for i, spec in enumerate(SPC_NAMES):
            f.write(f"# {spec}\n{results[i]:.3E}\n")
        f.write("# EOF\n")
    
    # Update input.yaml
    no_idx, no2_idx = SPC_NAMES.index('NO'), SPC_NAMES.index('NO2')
    hno3_idx, o3_idx = SPC_NAMES.index('HNO3'), SPC_NAMES.index('O3')
    co_idx, ch4_idx, so2_idx = SPC_NAMES.index('CO'), SPC_NAMES.index('CH4'), SPC_NAMES.index('SO2')

    nox_ppt = (results[no_idx] + results[no2_idx]) * 1e12
    hno3_ppt, o3_ppb = results[hno3_idx] * 1e12, results[o3_idx] * 1e9
    co_ppb, ch4_ppm, so2_ppt = results[co_idx] * 1e9, results[ch4_idx] * 1e6, results[so2_idx] * 1e12

    with open(INPUT_YAML, 'r') as f: lines = f.readlines()
    new_lines = []
    for line in lines:
        if 'NOx [ppt]' in line: new_lines.append(f"    NOx [ppt] (double): {nox_ppt:.3f}\n")
        elif 'HNO3 [ppt]' in line: new_lines.append(f"    HNO3 [ppt] (double): {hno3_ppt:.3f}\n")
        elif 'O3 [ppb]' in line: new_lines.append(f"    O3 [ppb] (double): {o3_ppb:.3f}\n")
        elif 'CO [ppb]' in line: new_lines.append(f"    CO [ppb] (double): {co_ppb:.3f}\n")
        elif 'CH4 [ppm]' in line: new_lines.append(f"    CH4 [ppm] (double): {ch4_ppm:.3f}\n")
        elif 'SO2 [ppt]' in line: new_lines.append(f"    SO2 [ppt] (double): {so2_ppt:.3f}\n")
        else: new_lines.append(line)
    with open(INPUT_YAML, 'w') as f: f.writelines(new_lines)
    print("Sync complete: init.txt and input.yaml updated.")

if __name__ == '__main__': main()
