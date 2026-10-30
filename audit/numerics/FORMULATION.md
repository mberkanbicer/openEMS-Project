# Implemented numerical formulation (code-anchored)

This document describes what the Rust code actually integrates. It is a map to
the implementation, not a re-derivation; every statement cites the module that
implements it.

## 1. Fields, precision, staggering

- State variables are the equivalent-circuit **voltages/currents** on the Yee
  lattice (`openEMS/rust/src/engine.rs`, `operator.rs`).
- `FDTD_FLOAT = f32` (`constants.rs:6`), matching the native build; setup,
  coefficients and accumulators are `f64` and converted where the native code
  does.
- Electric updates use the `vv`/`vi` coefficient arrays, magnetic updates
  `ii`/`iv` (`operator.rs`). Non-uniform meshes use real edge lengths and dual
  face areas (`get_edge_length`, `get_edge_area`), verified analytically in
  `nonuniform_mesh_edge_lengths_and_ec_coefficients`.
- The default time step is the native Var3 method
  (`operator.rs`, `constants.rs`); Var1 is available for the documented
  compatibility path. `var3_matches_native_on_uniform_and_graded_meshes`
  compares the actual `dt` with the pinned binary.

## 2. Boundaries and extensions

| Physics | Implementation | Verification |
|---|---|---|
| PEC/PMC | `operator.rs` electric/magnetic BC; tangential-only PMC | `pmc_boundary_matches_the_native_magnetic_bc` |
| Mur | `extensions.rs::MurOperatorExtension`, local face delta on graded meshes | `mur_uses_the_local_face_delta_on_a_graded_mesh` |
| UPML | `extensions.rs` UPML operator/engine extensions, six faces and corners | UPML reflection gate (RM-043) |
| TFSF | `extensions.rs` plane-wave extension | differential TFSF case (RM-059) |
| Excitations | `excitation.rs`: Gauss, DC-free Gauss, sinus, step, Dirac, custom expression | excitation dump gate (RM-037..039) |
| Dispersive | Debye/Lorentz ADE in `extensions.rs` | dispersive slab differential (RM-056) |
| Conducting sheet | `conducting_sheet.rs` (three sheet models) | `conducting-sheet` differential (RM-057) |
| Lumped RLC | `lumped_rlc.rs`, port coupling in `processing_integral.rs` | native lumped-port comparison (RM-058) |
| Steady state | `extensions.rs::EngineExtSteadyState` (21 probes, `2*period` buffer) | RM-060 |
| Cylindrical | `operator.rs::build_cylinder_extension/build_r0_coefficients`, `extensions.rs::EngineExtCylinder` | r=0 and dump gates; multigrid **not implemented** (E-007) |

## 3. Sources, probes, DFT

- Sources are injected with the native waveform/scale in `openEMS/rust/src/openems.rs`
  and `excitation.rs`.
- Probes and DFT: `processing.rs` accumulates `sample * cos(ωt)` and
  `sample * sin(ωt)`, i.e. the **e^{+jωt}** convention, with the native record
  length and frequency bins. Magnitude/phase dumps use `atan2(im, re)`
  (`processing.rs:2146`).
- The end criteria use the native Nyquist cadence in the first minute and the
  wall-clock cadence afterwards (`openems.rs`, `end_criteria_due`).

## 4. Ports and S-parameters

- Port voltage/current are line integrals on the port plane
  (`processing_integral.rs`), with the native reference impedance and
  normalization; `calcPort`-equivalent quantities are exercised by
  `test_Ports`, the MSL notch differential case and the Coax case.
- Differential bounds: `Z_ref` 1 %, `S21` 0.05 dB, `S11` 2 dB (worst in band),
  see `docs/migration/REFERENCE_TOLERANCES.md`.

## 5. NF2FF

- `nf2ff.rs` integrates the tangential E/H on the Huygens surface with the DFT
  of §3 and writes `E_theta`/`E_phi` and power quantities; `nf2ff_hdf5.rs`
  writes the native compound layout.
- Verification: native `nf2ff` on a Rust dump, every dataset within 1.6e-5 of
  the peak (RM-076); dipole far-field in the Octave suite.

## 6. SAR

- Local power density `0.5 * sigma * |E|^2` (W/m³) divided by the cell density
  (kg/m³) → `sigma * |E_peak|^2 / (2 * rho)` W/kg (`sar.rs` header).
- Averaging uses cell masses and the native region logic
  (`processing.rs`, `sar.rs`); the cylindrical SAR differential gate compares
  per-cell SAR (2.6e-3 vs a 1e-2 bound) and peak/counters.
- **Analytic case (VAL-002, RM-178):** a homogeneous lossy TEM line
  (`eps_r=4`, `sigma=0.1 S/m`, 2 GHz) is compared with the exact
  `alpha + j beta`; see `VALIDATION.md` and
  `reference-data/convergence/analytic_sar.json`. Measured `alpha`
  9.3513 vs 9.3601 Np/m, `beta` 84.3651 vs 84.3547 rad/m, and the SAR
  slope 18.7027 vs 2*alpha 18.7202 1/m (relative 9.4e-4). The absolute
  SAR scale is the DFT convention (validated pointwise against the dump,
  1.7e-7); the analytic comparison is the spatial decay and phase.

## 7. Units and conventions

- SI everywhere internally; CSXCAD `DeltaUnit` is the drawing unit and is
  preserved in XML.
- Geometry/mesh indexing, axes and handedness are the native CSXCAD
  conventions; `native_model_parity.rs` and the 11 XML fixtures pin them.
- Complex sign: e^{+jωt} (see §3). This must be stated in any comparison with a
  tool that uses e^{-jωt}.
