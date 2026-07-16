# Use baremodule to shave off a few KB from the serialized `.ji` file
baremodule aws_c_compression_jll
using Base
using Base: UUID
import JLLWrappers

JLLWrappers.@generate_main_file_header("aws_c_compression")
JLLWrappers.@generate_main_file("aws_c_compression", UUID("73a04cd5-f3d7-5bac-9290-e8adb709f224"))
end  # module aws_c_compression_jll
