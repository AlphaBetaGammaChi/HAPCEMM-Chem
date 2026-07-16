# Use baremodule to shave off a few KB from the serialized `.ji` file
baremodule aws_c_io_jll
using Base
using Base: UUID
import JLLWrappers

JLLWrappers.@generate_main_file_header("aws_c_io")
JLLWrappers.@generate_main_file("aws_c_io", Base.UUID("13c41daa-f319-5298-b5eb-5754e0170d52"))
end  # module aws_c_io_jll
