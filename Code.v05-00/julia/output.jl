module HapcemmOutput
using NCDatasets, Dates

function write_adjoint_output(filename, timeArray, species_sens, param_sens,
                               species_names, reaction_names)
    NCDataset(filename, "c") do ds
        ds.attrib["title"]   = "HAPCEMM Adjoint Sensitivity"
        ds.attrib["created"] = string(now())
        defDim(ds, "time",     length(timeArray))
        defDim(ds, "species",  length(species_names))
        defDim(ds, "reaction", length(reaction_names))
        tv = defVar(ds, "time", Float64, ("time",))
        tv[:] = timeArray
        sv = defVar(ds, "dJ_dSpecies", Float32, ("species","time"))
        sv.attrib["units"] = "J/(molec cm-3)"
        sv[:,:] = Float32.(species_sens)
        pv = defVar(ds, "dJ_dRCONST", Float32, ("reaction","time"))
        pv.attrib["units"] = "J/(cm3 molec-1 s-1)"
        pv[:,:] = Float32.(param_sens)
        for (i,n) in enumerate(species_names);  ds.attrib["species_$(i)"]  = n; end
        for (j,n) in enumerate(reaction_names); ds.attrib["reaction_$(j)"] = n; end
    end
    println("[HapcemmOutput] Written: $filename")
end

function write_forward_output(filename, timeArray, concentrations, species_names, airDens)
    NCDataset(filename, "c") do ds
        ds.attrib["title"] = "HAPCEMM Forward Chemistry"
        defDim(ds, "time",    length(timeArray))
        defDim(ds, "species", length(species_names))
        tv = defVar(ds, "time", Float64, ("time",))
        tv[:] = timeArray
        cv = defVar(ds, "concentrations", Float32, ("species","time"))
        cv.attrib["units"]     = "ppb"
        cv.attrib["long_name"] = "Mole fraction [X]/n_air * 1e9"
        cv[:,:] = Float32.(concentrations ./ airDens .* 1e9)
        for (i,n) in enumerate(species_names); ds.attrib["species_$(i)"] = n; end
    end
end
end # module HapcemmOutput
