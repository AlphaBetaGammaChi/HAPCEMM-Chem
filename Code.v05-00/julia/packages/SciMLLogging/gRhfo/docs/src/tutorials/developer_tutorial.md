# Developer Tutorial: Adding SciMLLogging to Your Package

This tutorial is for Julia package developers who want to integrate SciMLLogging.jl into their packages to provide users with fine-grained verbosity control.

## Overview

SciMLLogging.jl provides four main components for package developers:

1. `AbstractVerbositySpecifier` - Base type for creating custom verbosity types
2. `@SciMLMessage` - Macro for emitting conditional log messages
3.  Log levels - Predefined log levels (`Silent`, `DebugLevel`, `InfoLevel`, `WarnLevel`, `ErrorLevel`, or `MessageLevel(n)` for a custom integer). These are the fields of the `AbstractVerbositySpecifier`s that determine which messages get logged, and at what log level. 
4.  Verbosity preset levels - `None`, `Minimal`, `Standard`, `Detailed`, `All`. These represent predefined sets of log levels. 

### AbstractVerbositySpecifier
    `AbstractVerbositySpecifier` is the base type that package developers implement a subtype of to create custom verbosity type for their packages.
      
### @SciMLMessage     
In order to use the the `@SciMLMessage` macro, simply choose which of the fields of your `AbstractVerbositySpecifier` should control that particular message. Then when the macro is called, the field of the verbosity object corresponding with the `option` argument to the macro is used to control the logging of the message. 


## Step 1: Design Your Verbosity Interface

First, decide what aspects of your package should be controllable by users. For example, a solver might have:
- Initialization messages
- Iteration progress
- Convergence information
- Error control information

## Step 2: Create Your Verbosity Type

There are two ways to define a verbosity specifier: the `@verbosity_specifier`
macro (recommended for new code) or a manual struct definition (useful when you
need full control).

### Option A: Use the `@verbosity_specifier` macro

The macro generates the parametric struct, all the constructors, preset
support, group keyword arguments, and validation in one declaration:

```julia
using SciMLLogging

@verbosity_specifier MySolverVerbosity begin
    # Toggles control individual message categories. Each toggle field is
    # typed as `MessageLevel`.
    toggles = (:initialization, :iterations, :convergence, :warnings)

    # Optional. Sub-specifier fields hold either another verbosity specifier
    # or a verbosity preset. Use this when your spec needs to configure
    # nested behavior — e.g., a solver verbosity that controls the verbosity
    # of an inner linear-solve step.
    sub_specifiers = (:linear_verbosity,)

    presets = (
        None = (
            initialization   = Silent,
            iterations       = Silent,
            convergence      = Silent,
            warnings         = Silent,
            linear_verbosity = None(),
        ),
        Standard = (
            initialization   = InfoLevel,
            iterations       = Silent,
            convergence      = InfoLevel,
            warnings         = WarnLevel,
            linear_verbosity = Standard(),  # preset value, deferred to
                                            # the downstream package
        ),
        All = (
            initialization   = InfoLevel,
            iterations       = InfoLevel,
            convergence      = InfoLevel,
            warnings         = WarnLevel,
            linear_verbosity = All(),
        ),
    )

    # Groups let users set multiple toggles at once via a single kwarg.
    groups = (
        solver = (:initialization, :iterations, :convergence),
    )
end
```

The macro generates:
- `MySolverVerbosity{Enabled, S1}` — parametric on `Enabled` and one type
  parameter per sub-specifier slot.
- A preset constructor per preset name (`MySolverVerbosity(::None)`, etc.).
- A keyword constructor with `preset=`, group kwargs (`solver=`), and field
  kwargs, applying precedence: individual > group > preset.

When a sub-specifier field is set to a concrete sub-spec instance (e.g.
`LinearVerbosity(Detailed())`), the outer specifier's type parameter
specializes to that concrete type — preserving inference into downstream
APIs that consume the sub-spec.

When the field holds a preset value (e.g. `Standard()`), the type parameter
specializes to the preset's singleton type — also concrete. Downstream code
that drills into the field can dispatch on whether it received a preset or
a fully-configured sub-spec.

### Option B: Define the struct manually

Sometimes you need full control over the struct layout (e.g. when you have
complex constructors, additional fields, or want to integrate with another
type system). Define a parametric struct that subtypes
`AbstractVerbositySpecifier{Enabled}`:

```julia
using SciMLLogging

struct MySolverVerbosity{Enabled} <: AbstractVerbositySpecifier{Enabled}
    initialization::MessageLevel
    iterations::MessageLevel
    convergence::MessageLevel
    warnings::MessageLevel
end

# Constructor with defaults — produces an enabled instance
function MySolverVerbosity(;
        initialization = InfoLevel,
        iterations = Silent,
        convergence = InfoLevel,
        warnings = WarnLevel
)
    MySolverVerbosity{true}(initialization, iterations, convergence, warnings)
end
```
- Concretely typing fields as `MessageLevel` lets the compiler constant-fold logging branches
- The `{Enabled}` type parameter selects between two `get_message_level` methods at compile time
- Each field represents a category of messages your package can emit

## Step 3: Add Convenience Constructors (manual path only)

If you used the macro in Step 2, the preset constructors and keyword
constructor are already generated — skip ahead to Step 4. For a manually
defined specifier, add a preset-based constructor that maps each preset to a
field configuration, and let the kwarg constructor from Step 2 handle ad-hoc
configurations:

```julia
# Preset-based constructor. Note that `None()` returns a {false} instance —
# the type parameter signals "disabled" so logging calls compile away.
function MySolverVerbosity(preset::AbstractVerbosityPreset)
    if preset isa None
        MySolverVerbosity{false}(Silent, Silent, Silent, Silent)
    elseif preset isa All
        MySolverVerbosity{true}(InfoLevel, InfoLevel, InfoLevel, WarnLevel)
    elseif preset isa Minimal
        MySolverVerbosity{true}(Silent, Silent, ErrorLevel, ErrorLevel)
    else
        MySolverVerbosity()  # Default
    end
end
```

## Step 4: Integrate Messages Into Your Code

Use `@SciMLMessage` throughout your package code:

```julia
function my_solve(problem, verbose::MySolverVerbosity)
    @SciMLMessage("Initializing solver for $(typeof(problem))", verbose, :initialization)

    # Setup code here...

    for iteration in 1:maxiters
        # Solver iteration...

        @SciMLMessage(verbose, :iterations) do
            "Iteration $iteration: residual = $(compute_residual())"
        end

        if converged
            @SciMLMessage("Converged after $iteration iterations", verbose, :convergence)
            return solution
        end

        if should_warn_about_something()
            @SciMLMessage("Convergence is slow, consider adjusting parameters", verbose, :error_control)
        end
    end

    @SciMLMessage("Failed to converge after $maxiters iterations", verbose, :convergence)
    return nothing
end
```
## Step 5: Document for Users

Provide clear documentation for your users:

```julia
"""
    MySolverVerbosity(; kwargs...)

Controls verbosity output from MySolver functions.

# Keyword Arguments
- `initialization = InfoLevel`: Messages about solver setup
- `iterations = Silent`: Per-iteration progress messages
- `convergence = InfoLevel`: Convergence/failure notifications
- `error_control = WarnLevel`: Messages about solver error control

# Constructors
- `MySolverVerbosity()`: Default enabled verbosity
- `MySolverVerbosity(None())`: Disabled (zero overhead)
- `MySolverVerbosity(All())`: Enable all message categories
- `MySolverVerbosity(Minimal())`: Only errors and convergence

# Example
```julia
# Default verbosity
verbose = MySolverVerbosity()

# Custom verbosity - show everything except iterations
verbose = MySolverVerbosity(iterations = Silent)

# Silent mode
verbose = MySolverVerbosity(
    initialization = Silent,
    iterations = Silent,
    convergence = Silent,
    warnings = Silent
)
```
"""
```

## Complete Example

Here's a complete minimal example:

```@example
using SciMLLogging
import SciMLLogging: AbstractVerbositySpecifier, MessageLevel

struct ExampleVerbosity{Enabled} <: AbstractVerbositySpecifier{Enabled}
    progress::MessageLevel
end

# Constructor with default — produces an enabled instance
ExampleVerbosity(; progress = InfoLevel) = ExampleVerbosity{true}(progress)

function solve_example(n::Int, verbose::ExampleVerbosity)
    result = 0
    for i in 1:n
        result += i
        @SciMLMessage("Step $i: sum = $result", verbose, :progress)
    end
    return result
end
```

This example shows the minimal structure needed to integrate SciMLLogging into a package.
