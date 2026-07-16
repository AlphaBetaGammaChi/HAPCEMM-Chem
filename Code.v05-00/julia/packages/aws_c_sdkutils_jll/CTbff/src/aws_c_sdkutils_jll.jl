# Use baremodule to shave off a few KB from the serialized `.ji` file
baremodule aws_c_sdkutils_jll
using Base
using Base: UUID
import JLLWrappers

JLLWrappers.@generate_main_file_header("aws_c_sdkutils")
JLLWrappers.@generate_main_file("aws_c_sdkutils", UUID("1282aa60-004d-510b-9f52-12498d409daa"))
end  # module aws_c_sdkutils_jll
