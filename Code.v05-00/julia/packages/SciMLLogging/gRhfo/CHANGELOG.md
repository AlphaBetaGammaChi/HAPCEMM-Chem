# Changelog

All notable changes to SciMLLogging.jl will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0]

### Breaking

- **`MessageLevel` is now a concrete struct**, no longer an abstract type with
  per-level subtypes. `Silent`, `DebugLevel`, `InfoLevel`, `WarnLevel`, and
  `ErrorLevel` are now `MessageLevel` constants. Custom levels are constructed
  by calling `MessageLevel(n)` directly. The `AbstractMessageLevel` and
  `CustomLevel` names have been removed — code referring to them must be
  updated to use `MessageLevel`.
  - `Silent()`, `InfoLevel()`, etc. still work — calling a `MessageLevel`
    instance returns itself, so existing call-site syntax is unaffected.
  - Code that dispatched on the old subtypes (e.g. `f(::WarnLevel)`) needs to
    be rewritten to compare values (`level == WarnLevel`).

- **`AbstractVerbositySpecifier` is now parametric on `{Enabled}`**. Concrete
  specifier types must subtype `AbstractVerbositySpecifier{Enabled}` for some
  `Enabled` parameter. The macro-generated specifiers do this automatically;
  hand-written specifiers must be updated:
  ```julia
  # Before
  struct MyVerbosity <: AbstractVerbositySpecifier
      option_a
      option_b
  end

  # After
  struct MyVerbosity{Enabled} <: AbstractVerbositySpecifier{Enabled}
      option_a::MessageLevel
      option_b::MessageLevel
  end
  ```
  The `Enabled` parameter drives a compile-time short-circuit in
  `@SciMLMessage`: instances constructed via `None()` produce
  `MyVerbosity{false}`, and `get_message_level(::AbstractVerbositySpecifier{false}, ::Any)`
  returns `nothing`, eliminating logging branches at compile time.

### Added

- **`sub_specifiers = (...)` block in `@verbosity_specifier`** — declare fields
  that hold another verbosity specifier or preset. Each declared sub_specifier
  becomes its own free type parameter on the generated struct, so the field is
  concretely typed at the instance level. This preserves inference when the
  sub-specifier is forwarded to a downstream API, and lets a package hold a
  sub-specifier whose type it does not depend on at definition time
  (e.g. DiffEqBase holding a NonlinearVerbosity without depending on
  NonlinearSolve).
  ```julia
  @verbosity_specifier DEVerbosity begin
      toggles        = (:dt_select, :step_rejected)
      sub_specifiers = (:nonlinear_verbosity, :linear_verbosity)
      presets = (
          Standard = (
              dt_select           = InfoLevel,
              step_rejected       = WarnLevel,
              nonlinear_verbosity = Standard(),       # preset OR
              linear_verbosity    = LinearVerbosity(), # sub-spec instance
          ),
          # ...
      )
      groups = ()
  end
  ```

  The macro generates roughly:

  ```julia
  # Toggle-only specifier: single Enabled type parameter; toggle fields are
  # concretely typed `::MessageLevel`.
  struct VerbSpec{Enabled} <: AbstractVerbositySpecifier{Enabled}
      toggle1::MessageLevel
      toggle2::MessageLevel
      # ...
  end

  # With `sub_specifiers = (:nonlinear_verbosity, :linear_verbosity)`:
  # one extra type parameter per declared sub_specifier; sub_specifier fields
  # are typed by their per-instance type param, so they specialize to whatever
  # concrete sub-spec or preset the user passes.
  struct DEVerbosity{Enabled, __SPEC_T_1, __SPEC_T_2} <: AbstractVerbositySpecifier{Enabled}
      dt_select::MessageLevel
      step_rejected::MessageLevel
      nonlinear_verbosity::__SPEC_T_1
      linear_verbosity::__SPEC_T_2
  end

  # A partial-application constructor lets the generated preset/kwarg call
  # sites keep writing `DEVerbosity{true}(...)`; Julia infers the trailing
  # type params from the positional arg types.
  function DEVerbosity{Enabled}(t1, t2, s1, s2) where {Enabled}
      return DEVerbosity{Enabled, typeof(s1), typeof(s2)}(t1, t2, s1, s2)
  end

  # Plus a preset constructor per declared preset (None ⇒ {false}, others ⇒ {true}):
  DEVerbosity(::Standard) = DEVerbosity{true}(InfoLevel, WarnLevel, Standard(), LinearVerbosity())
  DEVerbosity(::None)     = DEVerbosity{false}(Silent,    Silent,    None(),     None())
  # ...

  # Plus the keyword constructor with `preset=`, group kwargs, and field kwargs.
  ```

  Concrete instance types end up looking like
  `DEVerbosity{true, Standard, LinearVerbosity{true}}` — both sub_specifier
  type params are concrete, so `verb.linear_verbosity` returns a concrete type
  and inference flows through into downstream APIs.

  Sub_specifier fields accept either an `AbstractVerbositySpecifier` instance
  or an `AbstractVerbosityPreset` singleton; the kwarg constructor validates
  this. Toggle fields are restricted to `MessageLevel` values.

### Changed

- **Toggle fields are always concretely typed `::MessageLevel`**. Previously a
  toggle could hold a preset or another verbosity specifier as a workaround for
  hierarchical configuration; that role now belongs to the new `sub_specifiers`
  block. Macro-generated specifiers reject non-`MessageLevel` values for
  toggles at the kwarg constructor.
- **`@SciMLMessage` short-circuits at compile time** when the verbosity
  specifier has `Enabled === false`. The
  `get_message_level(::AbstractVerbositySpecifier{false}, ::Any)` method
  returns `nothing`, the macro guards on that, and the compiler eliminates
  the logging branch for disabled specifiers.

### Migration notes for downstream packages

1. **Manually-defined verbosity specifiers**: add the `{Enabled}` type
   parameter and update the abstract supertype to
   `AbstractVerbositySpecifier{Enabled}`. Default kwarg constructors should
   return `MyVerbosity{true}(...)`; the `None()` preset constructor should
   return `MyVerbosity{false}(...)`.
2. **Macro-using specifiers with sub-specs**: any field that previously held a
   preset or another verbosity specifier as a "toggle" must move out of
   `toggles` and into a new `sub_specifiers` block. Toggles are now strictly
   `MessageLevel`-only. Toggle-only specifiers don't need any change.
3. **Functions accepting a `verbose=` argument** should accept both an
   `AbstractVerbositySpecifier` instance and an `AbstractVerbosityPreset`
   singleton — that's what specifier fields can hand them. The macro-generated
   `name(::PresetType)` constructors satisfy this on the construction side; on
   the consumption side it is a pattern to follow.
4. **Code that introspected `MessageLevel` subtypes via dispatch** (e.g.
   `function f(::InfoLevel)`) must be rewritten to compare values
   (`level == InfoLevel`) since the subtypes no longer exist.

## Earlier versions

For changes prior to 2.0.0, see the git history.
