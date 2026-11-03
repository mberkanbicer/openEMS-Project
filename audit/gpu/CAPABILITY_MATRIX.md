# GPU capability matrix

| Capability | CPU (Rust) | GPU (Rust) | Upstream C++ |
|---|---|---|---|
| Cartesian FDTD stepping | yes | **none** | yes |
| UPML / Mur / TFSF | yes | **none** | yes |
| Dispersive ADE | yes | **none** | yes |
| Conducting sheet / RLC | yes | **none** | yes |
| Cylindrical / multigrid | cylindrical yes, multigrid **no** (E-007) | **none** | yes |
| Probes / DFT / HDF5 dumps | yes | **none** | yes |
| NF2FF / SAR | yes | **none** | yes |
| Device enumeration / backend selection | n/a | **none** | HIP/Metal/gpu-reference |
| Precision | f32 fields, f64 setup | n/a | f32/f64 per backend |

A GPU request cannot be satisfied by this port. The correct response is the
explicit Python error (`RuntimeError`) / no GPU CLI flag; there is no automatic
fallback pretending to be GPU.

Evidence: source inventory (no GPU compute modules), ADR 0002, upstream
`FDTD/gpu_*`.
