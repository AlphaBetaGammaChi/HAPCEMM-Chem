module DataInterpolationsMooncakeExt

using DataInterpolations, Mooncake, ChainRulesCore
using DataInterpolations: _interpolate, munge_data, AbstractInterpolation,
    LinearInterpolation, QuadraticInterpolation
import Mooncake: @from_chainrules, MinimalCtx

# When the ChainRules pullback for _interpolate returns a Tangent{AbstractInterpolation},
# this tells Mooncake how to accumulate the u-component into the interpolation's fdata.
function Mooncake.increment_and_get_rdata!(
        f::Mooncake.FData{<:NamedTuple},
        r::Mooncake.NoRData,
        t::ChainRulesCore.Tangent{<:AbstractInterpolation}
    )
    u_tang = ChainRulesCore.unthunk(t.u)
    if !(u_tang isa ChainRulesCore.AbstractZero)
        f.data.u .+= u_tang
    end
    return Mooncake.NoRData()
end

# Constructor rules: stop Mooncake recursing into LinearParameterCache and other
# internal structs. The 6-arg and 7-arg forms are the internal constructors that
# have ChainRules rrules defined in DataInterpolationsChainRulesCoreExt.
@from_chainrules MinimalCtx Tuple{Type{LinearInterpolation}, Any, Any, Any, Any, Any, Any} true
@from_chainrules MinimalCtx Tuple{Type{QuadraticInterpolation}, Any, Any, Any, Any, Any, Any, Any} true

# _interpolate: the core computation for all interpolation calls (A(t) dispatches here)
@from_chainrules MinimalCtx Tuple{typeof(_interpolate), LinearInterpolation, Number} true
@from_chainrules MinimalCtx Tuple{typeof(_interpolate), QuadraticInterpolation, Number} true

# munge_data: validates/reshapes u and t - identity in the non-missing case.
# Match all three method dispatches that exist in DataInterpolations.
@from_chainrules MinimalCtx Tuple{typeof(munge_data), AbstractVector, AbstractVector} true
@from_chainrules MinimalCtx Tuple{typeof(munge_data), AbstractMatrix, AbstractVector} true
@from_chainrules MinimalCtx Tuple{typeof(munge_data), AbstractArray, Any} true

end
