using NCDatasets
using Dates
using Statistics

# --- G6Sulfur Extraction Script ---

function extract_cmip_data(dir_path, target_lat, target_lon, target_press_hpa, target_date)
    println("--- G6-Sulfur Extraction (CESM2-WACCM) ---")
    println("Location: $target_lat N, $target_lon E")
    println("Target Pressure: $target_press_hpa hPa")
    println("Target Date: $target_date")
    println("-------------------------------------------")

    files = filter(f -> endswith(f, ".nc"), readdir(dir_path, join=true))
    
    for file in files
        ds = Dataset(file)
        
        # 1. Identify primary variable (usually filename prefix before _)
        var_name = split(basename(file), "_")[1]
        if !(var_name in keys(ds))
            # Try to find the float variable with 4 dimensions
            var_name = first(filter(k -> length(size(ds[k])) == 4, keys(ds)))
        end

        # 2. Coordinate Indices
        lats = ds["lat"][:]
        lons = ds["lon"][:]
        # Convert -180/180 to 0-360 if needed
        adj_lon = target_lon < 0 ? target_lon + 360 : target_lon
        
        lat_idx = argmin(abs.(lats .- target_lat))
        lon_idx = argmin(abs.(lons .- adj_lon))

        # 3. Time Index
        times = ds["time"][:]
        # Convert target_date to match CMIP time (days since 0001-01-01 usually)
        # For simplicity in this script, we'll find the closest month
        time_idx = argmin(abs.(Dates.value.(times .- target_date)))

        # 4. Vertical Level (Hybrid Sigma-Pressure)
        # p = a*p0 + b*ps
        p0 = ds["p0"][] # Reference pressure in Pa
        a = ds["a"][:]  # Hybrid A
        b = ds["b"][:]  # Hybrid B
        ps = ds["ps"][time_idx, lat_idx, lon_idx] # Surface pressure at this point
        
        pressures = (a .* p0 .+ b .* ps) ./ 100.0 # Convert Pa to hPa
        lev_idx = argmin(abs.(pressures .- target_press_hpa))

        # 5. Extract Value
        val = ds[var_name][time_idx, lev_idx, lat_idx, lon_idx]
        units = get(ds[var_name].attrib, "units", "unknown")
        long_name = get(ds[var_name].attrib, "long_name", var_name)

        # 6. Scaling for APCEMM
        display_val = val
        if units == "mol mol-1"
            if val < 1e-6
                display_val = val * 1e12
                units = "ppt"
            else
                display_val = val * 1e9
                units = "ppb"
            end
        end

        printf_fmt = "%-10s: %10.4f %-10s (%s)\n"
        @eval @printf($printf_fmt, $var_name, $display_val, $units, $long_name)

        close(ds)
    end
end

# Usage Example:
# extract_cmip_data("/path/to/data", 60.0, -15.0, 265.0, DateTime(2050, 6, 15))
