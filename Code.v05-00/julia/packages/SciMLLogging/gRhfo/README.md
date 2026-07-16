# SciMLLogging
[![Global Docs](https://img.shields.io/badge/docs-SciML-blue.svg)](https://docs.sciml.ai/SciMLLogging/dev/)
[![Build Status](https://github.com/SciML/SciMLVerbosity.jl/actions/workflows/CI.yml/badge.svg?branch=main)](https://github.com/SciML/SciMLVerbosity.jl/actions/workflows/CI.yml?query=branch%3Amain)

A flexible verbosity control system for the SciML ecosystem that allows fine-grained control over logging and warnings.

Installation

```julia
using Pkg
Pkg.add("SciMLLogging")
```

SciMLLogging.jl provides a structured approach to controlling verbosity in scientific computing workflows. It enables:

- Fine-grained control over which messages are displayed and at what levels
- Hierarchical organization of verbosity settings by component and message type
- Consistent logging patterns across the SciML ecosystem
- Compile-time elimination of disabled logging branches via the `{Enabled}` type parameter

# Basic Usage

The recommended way to define a verbosity specifier is the `@verbosity_specifier` macro. It generates a parametric struct, all the constructors, preset support, and group keyword arguments in one declaration:

```julia
using SciMLLogging

@verbosity_specifier MyVerbosity begin
    toggles = (:algorithm_choice, :iteration_progress)

    presets = (
        None = (
            algorithm_choice   = Silent,
            iteration_progress = Silent,
        ),
        Standard = (
            algorithm_choice   = WarnLevel,
            iteration_progress = InfoLevel,
        ),
        All = (
            algorithm_choice   = InfoLevel,
            iteration_progress = InfoLevel,
        ),
    )

    groups = ()
end

# Create a verbosity instance — defaults to the Standard preset
verbose = MyVerbosity()

# Or pick a preset
verbose = MyVerbosity(Standard())

# Or override individual toggles
verbose = MyVerbosity(algorithm_choice = ErrorLevel)

# Log messages at different levels
@SciMLMessage("Selected algorithm: GMRES", verbose, :algorithm_choice)
@SciMLMessage("Iteration 5/100 complete", verbose, :iteration_progress)

# Use a function form to defer message construction (only evaluated if the
# toggle is non-Silent)
@SciMLMessage(verbose, :iteration_progress) do
    iter = 10
    total = 100
    progress = iter / total * 100
    "Iteration $iter/$total complete ($(round(progress, digits = 1))%)"
end
```

# Message Levels

SciMLLogging defines a single concrete `MessageLevel` type with the following
standard severities:

  - `Silent`: No output
  - `DebugLevel`: Debug messages
  - `InfoLevel`: Informational messages
  - `WarnLevel`: Warning messages
  - `ErrorLevel`: Error messages
  - `MessageLevel(n)`: Custom level with integer value `n`

# Verbosity Presets

Five standard presets are provided: `None()`, `Minimal()`, `Standard()`,
`Detailed()`, and `All()`. The macro generates a constructor for each preset
declared in the `presets = (...)` block. Constructing with `None()` produces a
`{false}` instance — this is what triggers compile-time elimination of logging
branches at `@SciMLMessage` call sites.

```julia
verbose_off = MyVerbosity(None())   # MyVerbosity{false} — disabled at the type level
verbose_on  = MyVerbosity(Standard()) # MyVerbosity{true}
```

# Hierarchical Verbosity (Sub-specifiers)

When a verbosity specifier needs to carry a nested verbosity (e.g. an ODE
solver verbosity that also configures a linear-solve verbosity), use a
`sub_specifiers` block. Each declared sub-specifier becomes a free type
parameter on the generated struct, so the field stays concretely typed at the
instance level — preserving inference when the sub-spec is forwarded to a
downstream API.

```julia
@verbosity_specifier DEVerbosity begin
    toggles        = (:dt_select, :step_rejected)
    sub_specifiers = (:linear_verbosity,)

    presets = (
        Standard = (
            dt_select        = InfoLevel,
            step_rejected    = WarnLevel,
            linear_verbosity = Standard(),  # preset value, deferred to the
                                            # downstream package, OR a
                                            # concrete sub-spec instance
        ),
        # ...
    )

    groups = ()
end
```

A sub-specifier field accepts either an `AbstractVerbositySpecifier` instance
or an `AbstractVerbosityPreset` singleton.

# Manual Implementation

If you need full control over the struct layout, you can define the parametric
struct yourself. Subtype `AbstractVerbositySpecifier{Enabled}` and use concrete
`MessageLevel` field types for inference:

```julia
using SciMLLogging
using SciMLLogging: AbstractVerbositySpecifier, AbstractVerbosityPreset, MessageLevel

struct MyAppVerbosity{Enabled} <: AbstractVerbositySpecifier{Enabled}
    solver_iterations::MessageLevel
    solver_convergence::MessageLevel
    performance_timing::MessageLevel
    performance_memory::MessageLevel
end

# Default kwarg constructor — produces an enabled instance
function MyAppVerbosity(;
        solver_iterations  = InfoLevel,
        solver_convergence = WarnLevel,
        performance_timing = Silent,
        performance_memory = Silent
)
    MyAppVerbosity{true}(solver_iterations, solver_convergence, performance_timing, performance_memory)
end

# Preset constructor — None() returns {false} for the compile-time short-circuit
function MyAppVerbosity(::SciMLLogging.None)
    MyAppVerbosity{false}(Silent, Silent, Silent, Silent)
end
```

# Integration with Julia's Logging System

SciMLLogging integrates with Julia's built-in logging system. You can customize
how logs are handled with `SciMLLogger`, which directs logs to different
outputs, or use your own logger based on the Julia logging system or
LoggingExtras.jl.

```julia
# Create a logger that sends warnings to a file
log_file = "warnings.log"
logger = SciMLLogger(
    info_repl = true,     # Show info in REPL
    warn_repl = true,     # Show warnings in REPL
    error_repl = true,    # Show errors in REPL
    warn_file = log_file  # Also log warnings to file
)

# Use the logger
with_logger(logger) do
    # Your code with @SciMLMessage calls
end
```

# Disabling Verbosity

To disable specific message categories, set them to `Silent`. To disable an
entire specifier (with zero runtime cost via the `{Enabled}` short-circuit),
construct it with the `None()` preset:

```julia
# Per-toggle silencing — emits nothing for these toggles, but the rest still emit
quiet = MyVerbosity(
    algorithm_choice   = Silent,
    iteration_progress = Silent
)

# Whole-specifier disable — compile-time short-circuit at every call site
off = MyVerbosity(None())

@SciMLMessage("This message won't be shown", off, :algorithm_choice)
```

# License

SciMLLogging.jl is licensed under the MIT License.
