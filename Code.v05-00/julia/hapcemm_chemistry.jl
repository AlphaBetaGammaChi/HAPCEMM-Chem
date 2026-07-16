module HapcemmChemistry
using OrdinaryDiffEq

function kpp_rhs!(du, u, p, t)
    ccall((:Fun_wrapper, "libhapcemm.so"), Cvoid,
          (Ptr{Cdouble}, Ptr{Cdouble}, Ptr{Cdouble}, Ptr{Cdouble}),
          u, p.FIX, p.RCONST, du)
end

function kpp_jac!(J, u, p, t)
    ccall((:Jac_wrapper, "libhapcemm.so"), Cvoid,
          (Ptr{Cdouble}, Ptr{Cdouble}, Ptr{Cdouble}, Ptr{Cdouble}),
          u, p.FIX, p.RCONST, J)
end

function micm_rhs!(du, u, p, t)
    ccall((:MicmFun_wrapper, "libhapcemm.so"), Cvoid,
          (Ptr{Cdouble}, Ptr{Cdouble}, Cint, Cint, Ptr{Cdouble}),
          u, p.RCONST, Cint(length(u)), Cint(length(p.RCONST)), du)
end

function micm_jac!(J, u, p, t)
    ccall((:MicmJac_wrapper, "libhapcemm.so"), Cvoid,
          (Ptr{Cdouble}, Ptr{Cdouble}, Cint, Ptr{Cdouble}),
          u, p.RCONST, Cint(length(u)), J)
end

function chemistry_rhs!(du, u, p, t)
    if p.backend === :kpp
        kpp_rhs!(du, u, p, t)
    elseif p.backend === :micm
        micm_rhs!(du, u, p, t)
    else
        error("Unknown backend: $(p.backend)")
    end
end

function run_chemistry_step(u0, p, tspan)
    prob = ODEProblem(chemistry_rhs!, u0, tspan, p)
    sol  = solve(prob, Rodas5(autodiff=false), reltol=1e-4, abstol=1e-6,
                 save_everystep=false)
    return sol.u[end]
end

end # module HapcemmChemistry
