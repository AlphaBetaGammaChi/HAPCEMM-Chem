# Use baremodule to shave off a few KB from the serialized `.ji` file
baremodule aws_c_http_jll
using Base
using Base: UUID
import JLLWrappers

JLLWrappers.@generate_main_file_header("aws_c_http")
JLLWrappers.@generate_main_file("aws_c_http", Base.UUID("3254fc65-9028-534d-aa9d-d76d128babc6"))
end  # module aws_c_http_jll
