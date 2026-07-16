# Use baremodule to shave off a few KB from the serialized `.ji` file
baremodule aws_c_common_jll
using Base
using Base: UUID
import JLLWrappers

JLLWrappers.@generate_main_file_header("aws_c_common")
JLLWrappers.@generate_main_file("aws_c_common", UUID("73048d1d-b8c4-5092-a58d-866c5e8d1e50"))
end  # module aws_c_common_jll
