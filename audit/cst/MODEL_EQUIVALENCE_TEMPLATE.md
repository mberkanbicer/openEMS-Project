# CST model-equivalence template

Copy this block per case and fill both columns before comparing results.

| Item | Rust / openEMS | CST MWS | Match? |
|---|---|---|---|
| Case id | | | |
| Geometry (units, coordinates, tolerances) | | | |
| Material: eps_r / mu_r / sigma / loss tangent | | | |
| Dispersive model (Debye/Lorentz) and fit | | | |
| Mesh: lines/cells, local refinement, adaptation | | | |
| Boundary: PEC/PMC/periodic/open | | | |
| PML: layers, distance, corner treatment | | | |
| Excitation: type, amplitude, phase, time window | | | |
| Port: type, modes, reference impedance, reference plane | | | |
| Frequency grid / DFT window / end criteria | | | |
| Field sampling locations and interpolation | | | |
| Far-field basis and normalization (gain/efficiency) | | | |
| SAR: accepted power, density, averaging | | | |
| Solver version/build | | | |
| Precision / engine / threads | | | |
| Hardware | | | |

Only after every row is matched may a numeric difference be attributed to the
numerical method rather than the model. Agreement case-specific limits must be
agreed and recorded before the result is seen.
