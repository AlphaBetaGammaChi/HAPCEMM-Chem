# Use baremodule to shave off a few KB from the serialized `.ji` file
baremodule s2n_tls_jll
using Base
using Base: UUID
import JLLWrappers

JLLWrappers.@generate_main_file_header("s2n_tls")
JLLWrappers.@generate_main_file("s2n_tls", Base.UUID("cddc5d3d-934d-5d3a-9747-62fc12ea3f48"))
end  # module s2n_tls_jll
