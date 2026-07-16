# Use baremodule to shave off a few KB from the serialized `.ji` file
baremodule MPIABI_jll
using Base
using Base: UUID
using LazyArtifacts
using MPIPreferences
Base.include(@__MODULE__, joinpath("..", ".pkg", "platform_augmentation.jl"))
import JLLWrappers

JLLWrappers.@generate_main_file_header("MPIABI")
JLLWrappers.@generate_main_file("MPIABI", Base.UUID("b5ada748-db0f-5fc0-8972-9331c762740c"))
end  # module MPIABI_jll
