# Use baremodule to shave off a few KB from the serialized `.ji` file
baremodule aws_c_auth_jll
using Base
using Base: UUID
import JLLWrappers

JLLWrappers.@generate_main_file_header("aws_c_auth")
JLLWrappers.@generate_main_file("aws_c_auth", Base.UUID("2b3700d1-4306-52e2-a478-c162f0c514be"))
end  # module aws_c_auth_jll
