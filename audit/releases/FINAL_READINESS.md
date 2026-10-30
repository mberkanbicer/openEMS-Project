# Final readiness

Decision: **CONDITIONAL_RESEARCH_RELEASE**

The default CPU solver path is evidence-backed against the pinned native
implementation and two analytic wave-speed cases, and the two silently ignored
physics options found by this audit are now rejected explicitly. The port is
not a complete equivalent of every upstream feature and lacks independent
(CST) and convergence evidence, so it must not be described as a complete,
CST-validated or production-ready replacement.

## 1. What is proven

- Workspace builds and the crate/Python/Octave tests run on this host:
  **acceptance 13/13 PASS** at `ff95333` + the audit changes
  (`docs/migration/ACCEPTANCE.md`; 804 crate tests, 504 HDF5, 459 Python with
  2 GPU skips, Octave 10/10, 51 differential cases).
- 51-case native differential harness, operator dump, UPML reflection, SAR and
  curve-excitation gates.
- Analytic vacuum and dielectric propagation speed (2 % discrete bound).
- 405 native Python tests (2 GPU tests skipped), Octave 10/10, install layout.
- GUI editor workflow with real-click tree → inspector → status evidence.
- P0 guards: `CellConstantMaterial` and `MultiGrid` fail loudly (E-007/E-008)
  instead of changing the physics silently.

## 2. What is not proven

| Item | Status |
|---|---|
| Mesh/time convergence | **partly measured**: cavity TE101 order 2.05/2.03; slab/MSL/dt not run (`numerics/CONVERGENCE.md`) |
| CST MWS comparison | **blocked**, no data (`cst/`) |
| GPU compute | **not implemented** (scope, ADR 0002) |
| macOS/FreeBSD/Windows run at this HEAD | **blocked** (E-005; no hosted CI) |
| Windows installer | workflow present, no run at this HEAD |
| Performance threshold | refreshed baseline; proposed 4.0x/3.25x gate passes; approval pending (`PERF-001`) |
| Analytic SAR | missing (`VAL-002`) |
| MATLAB (as opposed to Octave) | not run |
| Fuzzing/Miri/sanitizers | not run |
| GUI layout persistence | open P2 (`GUI-002`); colour management fixed (RM-171) |

## 3. Checklist (protocol §13)

| Criterion | Verdict |
|---|---|
| Seven-component matrix with traceability | Met (`component_matrix.csv`) |
| Existing port audited before changes | Met (`00_inventory.md`, dashboard) |
| No verified module rewritten without cause | Met; changes are guards + bindings |
| Missing/partial high-priority paths completed | Partly: Python façade and P0 guards fixed; multi-grid/GPU remain out of scope |
| No unreported C++ runtime | Met (`legacy_dependency_register.md`) |
| CPU reference passes analytic/regression | Met for the recorded corpus |
| Mesh/time convergence | **Partly met**: cavity only |
| Physical conventions validated | Partly: wave speed, ports, SAR gate; no analytic SAR |
| Immutable reference provenance | Met (`GOLD_REGISTRY.json`), no self-generation |
| SIMD/thread backends compared | Not met (no SIMD variant) |
| GPU parity | N/A (no backend) |
| CST comparison | **Blocked** |
| Python/MATLAB/Octave compatibility | Python/Octave met; MATLAB unverified |
| GUI edit/validate/export | Met; no solver run by design |
| Security/unsafe/fuzz review | Partly: source review; no fuzz/Miri |
| Cross-platform builds | **Blocked at HEAD** |
| Final report links evidence | Met (this tree) |

## 4. Conditions to move to READY_FOR_RELEASE

1. ~~A clean 13/13 acceptance run at the release commit.~~ Met for this
   working tree; re-run at the final tagged commit.
2. Convergence study for the dielectric slab, MSL notch, SAR and dt refinement (the cavity is recorded).
3. Hosted or local macOS/FreeBSD/Windows runs at the release commit.
4. Owner approval of the proposed performance gate (the release-tree run already passes it).
5. ~~The sRGB material-colour fix.~~ Met (RM-171).
6. A decision on multi-grid and cell-constant materials: implement, or keep the
   explicit rejection in the release notes.
7. A MATLAB run if MATLAB support is advertised.

## 5. Honest limitations for the release note

- No GPU acceleration.
- No cylindrical multi-grid; models that request it stop at setup.
- `CellConstantMaterial` models stop at setup.
- No CST validation; no convergence claim.
- macOS/FreeBSD/Windows verification predates this HEAD.
- Performance is 2-4x native on the recorded cases, not faster.
