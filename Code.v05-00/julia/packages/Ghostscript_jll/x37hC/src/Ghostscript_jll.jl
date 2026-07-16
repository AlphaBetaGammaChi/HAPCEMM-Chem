# Use baremodule to shave off a few KB from the serialized `.ji` file
baremodule Ghostscript_jll
using Base
using Base: UUID
import JLLWrappers

JLLWrappers.@generate_main_file_header("Ghostscript")
JLLWrappers.@generate_main_file("Ghostscript", UUID("61579ee1-b43e-5ca0-a5da-69d92c66a64b"))
end  # module Ghostscript_jll
