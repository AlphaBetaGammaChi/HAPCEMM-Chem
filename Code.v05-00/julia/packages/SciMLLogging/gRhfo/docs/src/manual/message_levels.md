# Message Levels

Message levels in SciMLLogging determine the severity and importance of log messages. Understanding these levels is essential for configuring appropriate verbosity in your applications.

## Overview

SciMLLogging defines a single concrete `MessageLevel` type (backed by an
integer) that represents the severity of a log message. Standard severities are
exposed as constants (`Silent`, `DebugLevel`, `InfoLevel`, `WarnLevel`,
`ErrorLevel`); custom severities can be constructed by calling
`MessageLevel(n)` directly with any integer.

```@docs
MessageLevel
```

Each level apart from `Silent` corresponds to a Julia Logging `LogLevel` with
an associated integer. See the [Julia Logging documentation](https://docs.julialang.org/en/v1/stdlib/Logging/#Log-event-structure)
for more details. 

## Standard Message Levels

### Silent Level
```@docs
Silent
```

The `Silent` level is special - it completely suppresses output for a message. As such, it does not have an associated `LogLevel`.

### Debug Level
```@docs
DebugLevel
```
`DebugLevel` is for messages with a very low priority. 
By default, these messages are not logged at all, and the `JULIA_DEBUG` environment variable needs to be set.
For details see the [Julia Logging documentation](https://docs.julialang.org/en/v1/stdlib/Logging/#Environment-variables). 

### Information Level
```@docs
InfoLevel
```

Use `InfoLevel` for general status updates, progress information, and routine diagnostic messages that users might want to see during normal operation.

### Warning Level
```@docs
WarnLevel
```

`WarnLevel` should be used for potentially problematic situations that don't prevent execution but may require user attention.

### Error Level
```@docs
ErrorLevel
```

`ErrorLevel` is reserved for serious problems and failures that indicate something has gone wrong in the computation.

## Custom Message Levels

For specialized use cases, you can construct a `MessageLevel` directly with any
integer. This provides flexibility beyond the standard Info/Warn/Error hierarchy.

## Usage Examples

```julia
using SciMLLogging

# Standard levels
debug_level = DebugLevel
info_level = InfoLevel
warn_level = WarnLevel
error_level = ErrorLevel
silent_level = Silent

# Custom levels for specialized needs
trace_level = MessageLevel(-500)     # Low priority debugging
critical_level = MessageLevel(2000)  # Higher than standard error level
```

## Level Hierarchy

The message levels have a natural hierarchy that affects logging behavior:
- `Silent`: No output (always suppressed)
- `DebugLevel`: Lowest priority message
- `InfoLevel`: Low priority for general information
- `WarnLevel`: Medium priority
- `ErrorLevel`: Highest standard priority
- `MessageLevel(n)`: Priority determined by integer value `n`

Higher priority messages are more likely to be displayed by logging systems, while lower priority messages may be filtered out depending on the logger configuration.
