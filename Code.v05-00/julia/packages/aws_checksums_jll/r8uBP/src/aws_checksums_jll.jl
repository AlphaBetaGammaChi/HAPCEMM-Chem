# Use baremodule to shave off a few KB from the serialized `.ji` file
baremodule aws_checksums_jll
using Base
using Base: UUID
import JLLWrappers

JLLWrappers.@generate_main_file_header("aws_checksums")
JLLWrappers.@generate_main_file("aws_checksums", Base.UUID("b2a88e68-78e7-5e94-8c20-c02986ec140e"))
end  # module aws_checksums_jll
