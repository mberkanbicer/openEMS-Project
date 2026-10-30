# Physical invariants — what is tested

| Invariant | Test | Result |
|---|---|---|
| Vacuum propagation speed equals `c` | `openEMS/rust/tests/analytic_validation.rs::vacuum_propagation_speed_matches_c` | error < 2 % (discrete dispersion bound stated in the test) |
| Dielectric speed equals `c/sqrt(eps_r)` | `dielectric_propagation_speed_matches_c_over_sqrt_eps` | error < 2 % |
| Operator coefficients match native | `scripts/ci/run_operator_dump_check_wsl.sh` | `vv` exact, `vi` 1.3e-13, `ii` 6e-8, `iv` 4.8e-15 |
| Non-uniform edge/face metrics | `nonuniform_mesh_edge_lengths_and_ec_coefficients` | analytic areas and ratios |
| PMC is tangential-only | `pmc_boundary_matches_the_native_magnetic_bc` | matches native |
| Mur uses the local face delta | `mur_uses_the_local_face_delta_on_a_graded_mesh` | per-face check |
| Energy formula | `engine.rs::fast_energy_matches_the_native_formula` | native formula |
| UPML reflection | `run_upml_reflection_check_wsl.sh` | probes 6.0e-8 / 1.0e-8 |
| Cylindrical r=0 regularity | `run_cylindrical_r0_check_wsl.sh`, `test_cylinder_*` | passes |
| Deterministic stopping | `--exact-endcriteria` path + `end_criteria_due` tests | same final step |
| Passive/stable decay | no dedicated free-decay energy test found | **gap** |
| Reciprocity | no dedicated test found | **gap** |
| Negative/NaN material rejection | parser rejects invalid numeric fields; no adversarial suite | **partial** |
| SAR analytic uniform field | `sar.rs::local_sar_matches_the_definition` (`0.5*sigma*|E|^2/rho`) | pass |

## Not tested (do not claim)

- No mesh-refinement convergence (see `CONVERGENCE.md`).
- No independent solver (CST/other) comparison.
- No adversarial model corpus (degenerate solids, overlapping priorities,
  source on boundary, sub-cell PEC, OOM).
- No long-run stability test beyond the recorded acceptance cases.
