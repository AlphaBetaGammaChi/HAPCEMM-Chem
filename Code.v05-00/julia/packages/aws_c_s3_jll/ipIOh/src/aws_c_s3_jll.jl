# Use baremodule to shave off a few KB from the serialized `.ji` file
baremodule aws_c_s3_jll
using Base
using Base: UUID
import JLLWrappers

JLLWrappers.@generate_main_file_header("aws_c_s3")
JLLWrappers.@generate_main_file("aws_c_s3", Base.UUID("bd1f34fb-993f-5903-a121-aaf302eed6d4"))
end  # module aws_c_s3_jll
