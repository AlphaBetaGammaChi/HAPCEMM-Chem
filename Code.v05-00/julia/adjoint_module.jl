module HapcemmAdjoint
using Enzyme, EnzymeCore
using EnzymeCore: EnzymeRules
using OrdinaryDiffEq
include("hapcemm_chemistry.jl")
import .HapcemmChemistry: run_chemistry_step, kpp_rhs!, micm_rhs!

# KPP custom pullback — uses analytic Jac_wrapper instead of autodiff through ccall
function EnzymeRules.augmented_primal(
        config, func::Const{typeof(kpp_rhs!)}, ::Type{<:Const}, du, u, p, t)
    func.val(du.val, u.val, p.val, t.val)
    return EnzymeRules.AugmentedReturn(nothing, nothing, nothing)
end
function EnzymeRules.reverse(
        config, func::Const{typeof(kpp_rhs!)}, ::Type{<:Const}, tape, du, u, p, t)
    nvar = length(u.val); J = zeros(Float64, nvar, nvar)
    ccall((:Jac_wrapper, "libhapcemm.so"), Cvoid,
          (Ptr{Cdouble}, Ptr{Cdouble}, Ptr{Cdouble}, Ptr{Cdouble}),
          u.val, p.val.FIX, p.val.RCONST, J)
    u.dval .+= J' * du.dval
    return (nothing, nothing, nothing, nothing)
end

# MICM custom pullback
function EnzymeRules.augmented_primal(
        config, func::Const{typeof(micm_rhs!)}, ::Type{<:Const}, du, u, p, t)
    func.val(du.val, u.val, p.val, t.val)
    return EnzymeRules.AugmentedReturn(nothing, nothing, nothing)
end
function EnzymeRules.reverse(
        config, func::Const{typeof(micm_rhs!)}, ::Type{<:Const}, tape, du, u, p, t)
    nvar = length(u.val); J = zeros(Float64, nvar, nvar)
    ccall((:MicmJac_wrapper, "libhapcemm.so"), Cvoid,
          (Ptr{Cdouble}, Ptr{Cdouble}, Cint, Ptr{Cdouble}),
          u.val, p.val.RCONST, Cint(nvar), J)
    u.dval .+= J' * du.dval
    return (nothing, nothing, nothing, nothing)
end

function run_adjoint_pass(u0, rconst, FIX, tspan, backend, mode, target_idx=1)
    sg = zeros(Float64, length(u0))
    pg = zeros(Float64, length(rconst))
    function fwd(u, r, F, ts, be, mo, ti)
        p = (backend=be, RCONST=r, FIX=F)
        uf = run_chemistry_step(u, p, ts)
        mo === :all ? sum(uf) : uf[ti]
    end
    Enzyme.autodiff(Enzyme.Reverse, fwd, Active,
        Enzyme.Duplicated(copy(u0), sg),
        Enzyme.Duplicated(copy(rconst), pg),
        Enzyme.Const(FIX), Enzyme.Const(tspan),
        Enzyme.Const(backend), Enzyme.Const(mode), Enzyme.Const(target_idx))
    return sg, pg
end

end # module HapcemmAdjoint
