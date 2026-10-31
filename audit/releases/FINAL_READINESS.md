# Final readiness

Decision: **CONDITIONAL_RESEARCH_RELEASE**

The default CPU solver path is evidence-backed against the pinned native
implementation and two analytic wave-speed cases, and the two silently ignored
physics options found by this audit are now rejected explicitly. Convergence is
measured for the cavity (mesh and time step), the dielectric speed and the MSL
notch, and SAR is validated against the exact lossy-medium solution. An
independent (CST) comparison is still missing. The port is not a complete
equivalent of every upstream feature, so it must not be described as a complete,
CST-validated or production-ready replacement.

## 1. What is proven

- Workspace builds and the crate/Python/Octave tests run on this host:
  **acceptance 13/13 PASS** on a clean worktree; `docs/migration/ACCEPTANCE.md`
  pins the tested SHA and counts (506 HDF5, 459 Python with 2 GPU skips, Octave
  10/10, 51 differential cases; Windows workspace separately 897 tests / 33
  binaries).
- 51-case native differential harness, operator dump, UPML reflection, SAR and
  curve-excitation gates.
- Analytic vacuum and dielectric propagation speed (2 % discrete bound).
- 459 native Python tests (2 GPU tests skipped), Octave 10/10, install layout.
- GUI editor workflow with real-click tree → inspector → status evidence;
  arrow-key tree navigation with focus rings and a Ctrl+K command palette.
- P0 guards: `CellConstantMaterial` and `MultiGrid` fail loudly (E-007/E-008)
  instead of changing the physics silently.

## 2. What is not proven

| Item | Status |
|---|---|
| Mesh/time convergence | **measured**: cavity TE101 2.05/2.03; dt 2.32 vs the fixed-mesh limit; dielectric monotone 0.90/0.31; MSL notch 3.6700 GHz with 3.0e-4 mesh spread (`numerics/CONVERGENCE.md`) |
| CST MWS comparison | **blocked**, no data (`cst/`) |
| GPU compute | **not implemented** (scope, ADR 0002) |
| macOS/FreeBSD/Windows run at this HEAD | **blocked** (E-005; no hosted CI) |
| Windows installer | workflow present, no run at this HEAD (`PKG-001`) |
| GUI drag-docking | **PASS** (ADR 0010 implemented): egui_tiles 0.18 tree, drag grips, tab groups, persisted in `settings.json`; no floating windows |
| Performance threshold | refreshed baseline; proposed 4.0x/3.25x gate passes; approval pending (`PERF-001`) |
| Analytic SAR | **PASS** (`VAL-002`): lossy line alpha 9.3513 vs 9.3601 Np/m, beta 84.3651 vs 84.3547 rad/m, SAR slope rel 9.4e-4 |
| MATLAB (as opposed to Octave) | smoke PASS (R2025b: XML write, setup, 50-step run) |
| Fuzzing/Miri/sanitizers | **Miri PASS**: 21 parser + 3 operator tests, 0 UB; 32 optimizer exact-FP tests excluded (Miri float emulation); no fuzz/sanitizer run |

## 3. Checklist (protocol §13)

| Criterion | Verdict |
|---|---|
| Seven-component matrix with traceability | Met (`component_matrix.csv`) |
| Existing port audited before changes | Met (`00_inventory.md`, dashboard) |
| No verified module rewritten without cause | Met; changes are guards + bindings |
| Missing/partial high-priority paths completed | Partly: Python façade and P0 guards fixed; multi-grid/GPU remain out of scope |
| No unreported C++ runtime | Met (`legacy_dependency_register.md`) |
| CPU reference passes analytic/regression | Met for the recorded corpus |
| Mesh/time convergence | **Met for the recorded studies**: cavity mesh/time, dielectric speed, MSL notch; no CST or SAR-averaging convergence claim |
| Physical conventions validated | Met for wave speed, ports, and SAR (analytic lossy line); absolute SAR scale follows the validated DFT convention |
| Immutable reference provenance | Met (`GOLD_REGISTRY.json`), no self-generation |
| SIMD/thread backends compared | Not met (no SIMD variant) |
| GPU parity | N/A (no backend) |
| CST comparison | **Blocked** |
| Python/MATLAB/Octave compatibility | Python/Octave met; MATLAB smoke PASS (R2025b) |
| GUI edit/validate/export | Met; dock layout (tabs/splits) is draggable and persisted; no solver run by design |
| Security/unsafe/fuzz review | Partly: source review + a Miri pass on parser/operator; no fuzz or sanitizer run |
| Cross-platform builds | **Blocked at HEAD** |
| Final report links evidence | Met (this tree) |

## 4. Conditions to move to READY_FOR_RELEASE

1. ~~A clean 13/13 acceptance run at the release commit.~~ Met at `cf3d226`;
   re-run at the final tagged commit.
2. ~~A converged MSL notch model.~~ Met (RM-179): notch 3.6700 GHz, 3.0e-4 mesh spread.
3. Hosted or local macOS/FreeBSD/Windows runs at the release commit.
4. Owner approval of the proposed performance gate (the release-tree run already passes it).
5. ~~The sRGB material-colour fix.~~ Met (RM-171).
6. A decision on multi-grid and cell-constant materials: implement, or keep the
   explicit rejection in the release notes.
7. ~~A MATLAB run if MATLAB support is advertised.~~ Smoke met (full suite still open).

## 5. Honest limitations for the release note

- No GPU acceleration.
- No cylindrical multi-grid; models that request it stop at setup.
- `CellConstantMaterial` models stop at setup.
- No CST validation. Convergence is measured for the cavity (mesh/time), the
  dielectric speed and the MSL notch, and SAR is validated on a lossy line; no
  SAR-averaging convergence claim.
- macOS/FreeBSD/Windows verification predates this HEAD.
- Performance is 2-4x native on the recorded cases, not faster.
