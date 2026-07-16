# Use baremodule to shave off a few KB from the serialized `.ji` file
baremodule aws_c_cal_jll
using Base
using Base: UUID
import JLLWrappers

JLLWrappers.@generate_main_file_header("aws_c_cal")
JLLWrappers.@generate_main_file("aws_c_cal", UUID("70f11efc-bab2-57f1-b0f3-22aad4e67c4b"))
end  # module aws_c_cal_jll
