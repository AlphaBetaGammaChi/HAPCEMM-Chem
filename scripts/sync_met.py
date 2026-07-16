#!/usr/bin/env python3
import xarray as xr
import numpy as np
import os
import re

# Paths
ERA5_FILE = '/projects/b35as/public/HAPCEMM-Chem/global_data/ERA5/ERA5_met_climatology_2000.nc'
INPUT_YAML = '/projects/b35as/public/HAPCEMM-Chem/input_data/input.yaml'
OUTPUT_NC = '/projects/b35as/public/HAPCEMM-Chem/input_data/met_input.nc'

def get_input_params():
    with open(INPUT_YAML, 'r') as f:
        lines = f.readlines()
        params = {}
        for line in lines:
            if 'LON [deg]' in line:
                params['lon'] = float(line.split(':')[1].strip().split()[0])
            if 'LAT [deg]' in line:
                params['lat'] = float(line.split(':')[1].strip().split()[0])
            if 'Emission day' in line:
                params['day'] = int(line.split(':')[1].strip().split()[0])
        return params

def sat_vapor_pressure_water(T):
    return np.exp(-5.8002206e3 / T + 1.3914993 - 4.8640239e-2 * T + 
                  4.1764768e-5 * T**2 - 1.4452093e-8 * T**3 + 
                  6.5459673 * np.log(T))

def sat_vapor_pressure_ice(T):
    return np.exp(-5.6745359e3 / T + 6.3925247 - 9.677843e-3 * T + 
                  6.2215701e-7 * T**2 + 2.0747825e-9 * T**3 - 
                  9.484024e-13 * T**4 + 4.1635019 * np.log(T))

def main():
    if not os.path.exists(ERA5_FILE):
        print(f"Error: {ERA5_FILE} not found.")
        return
    params = get_input_params()
    print(f"Syncing meteorology for Lon: {params['lon']}, Lat: {params['lat']}, Day: {params['day']}")
    month = int((params['day'] - 1) / 30) + 1
    month = max(1, min(12, month))
    ds = xr.open_dataset(ERA5_FILE, engine='netcdf4')
    lon_adj = params['lon'] if params['lon'] >= 0 else 360 + params['lon']
    # Use dimension names from ncdump: valid_time, pressure_level, latitude, longitude
    col = ds.sel(valid_time=ds.valid_time[month-1], longitude=lon_adj, latitude=params['lat'], method='nearest')
    levels = col.pressure_level.values # hPa
    temp = col.t.values # K
    rhw = col.r.values # %
    omega = col.w.values # Pa/s
    u = col.u.values # m/s
    v = col.v.values # m/s
    esw = sat_vapor_pressure_water(temp)
    esi = sat_vapor_pressure_ice(temp)
    rhi = rhw * (esw / esi)
    rd = 287.05
    g = 9.80665
    idx_sorted = np.argsort(levels)[::-1] # 1000 down to 1
    z_dict = {}
    current_z = 0.0
    for i in range(len(idx_sorted)):
        curr_idx = idx_sorted[i]
        z_dict[curr_idx] = current_z
        if i < len(idx_sorted) - 1:
            next_idx = idx_sorted[i+1]
            p1, p2 = levels[curr_idx], levels[next_idx]
            t_avg = (temp[curr_idx] + temp[next_idx]) / 2.0
            current_z += (rd * t_avg / g) * np.log(p1 / p2)
    z = np.array([z_dict[i] for i in range(len(levels))])
    shear = np.zeros_like(levels)
    for i in range(len(idx_sorted)):
        curr_idx = idx_sorted[i]
        if i == 0:
            n_idx = idx_sorted[i+1]
            dz = z[n_idx] - z[curr_idx]
            du, dv = u[n_idx] - u[curr_idx], v[n_idx] - v[curr_idx]
        elif i == len(idx_sorted) - 1:
            p_idx = idx_sorted[i-1]
            dz = z[curr_idx] - z[p_idx]
            du, dv = u[curr_idx] - u[p_idx], v[curr_idx] - v[p_idx]
        else:
            p_idx, n_idx = idx_sorted[i-1], idx_sorted[i+1]
            dz = z[n_idx] - z[p_idx]
            du, dv = u[n_idx] - u[p_idx], v[n_idx] - v[p_idx]
        shear[curr_idx] = np.sqrt((du/dz)**2 + (dv/dz)**2)
    out_ds = xr.Dataset(
        data_vars={
            "pressure": (["altitude"], levels),
            "temperature": (["altitude", "time"], temp[:, np.newaxis]),
            "relative_humidity_ice": (["altitude", "time"], rhi[:, np.newaxis]),
            "shear": (["altitude", "time"], shear[:, np.newaxis]),
            "w": (["altitude", "time"], omega[:, np.newaxis]),
        },
        coords={"altitude": np.arange(len(levels)), "time": [0.0]}
    )
    out_ds.to_netcdf(OUTPUT_NC)
    print(f"Successfully created {OUTPUT_NC}")
    with open(INPUT_YAML, 'r') as f: lines = f.readlines()
    new_lines = []
    in_met = False
    for line in lines:
        if 'METEOROLOGICAL INPUT SUBMENU' in line: in_met = True
        elif in_met and 'Use met. input (T/F):' in line: new_lines.append("    Use met. input (T/F): T\n")
        elif in_met and 'Met input file path (string):' in line: new_lines.append(f"    Met input file path (string): {OUTPUT_NC}\n")
        elif in_met and 'Interpolate met data (T/F):' in line: new_lines.append("    Interpolate met data (T/F): T\n")
        elif in_met and 'PARAMETER MENU' in line: in_met = False; new_lines.append(line)
        else: new_lines.append(line)
    with open(INPUT_YAML, 'w') as f: f.writelines(new_lines)
    print("Successfully updated input.yaml for meteorology.")
if __name__ == '__main__':
    main()
