# Use baremodule to shave off a few KB from the serialized `.ji` file
baremodule LibTracyClient_jll
using Base
using Base: UUID
import JLLWrappers

JLLWrappers.@generate_main_file_header("LibTracyClient")
JLLWrappers.@generate_main_file("LibTracyClient", Base.UUID("ad6e5548-8b26-5c9f-8ef3-ef0ad883f3a5"))
end  # module LibTracyClient_jll
