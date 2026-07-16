# Use baremodule to shave off a few KB from the serialized `.ji` file
baremodule mpif_jll
using Base
using Base: UUID
using LazyArtifacts
using MPIPreferences
Base.include(@__MODULE__, joinpath("..", ".pkg", "platform_augmentation.jl"))
import JLLWrappers

JLLWrappers.@generate_main_file_header("mpif")
JLLWrappers.@generate_main_file("mpif", Base.UUID("9aeb927a-4695-514f-a259-621a69f20ec0"))
end  # module mpif_jll
