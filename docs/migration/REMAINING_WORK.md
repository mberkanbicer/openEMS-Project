# Remaining work: tasks, decisions and grey areas

**Date:** 2026-10-28, updated 2026-10-29
**Scope:** no rows remain open in `REMEDIATION_TASKS.md` at snapshot
**153 `Verified` — 0 `Implemented` — 0 `Analyzed` — 0 `Blocked`.**
**Method:** each row was re-checked against the pinned native sources under
`openEMS/`, `CSXCAD/` and `QCSXCAD/`; the original implementation is the
authority wherever the port could be read either way. The findings below are
source-level facts unless a measurement is quoted.

This document decides *what is left and what must be chosen*; it does not
change any status. Every close still needs the evidence rule from
`REMEDIATION_PLAN.md` Section 0.

## Status update 2026-10-29 (final)

The register is closed: `RM-152` (GUI CAD workflow) and `RM-153`
(native icons and metrics) are `Verified`, so the list below is a
historical record of how each row was closed. The remaining
limitations are the recorded exceptions E-005 (hosted platform
matrix/nightly) and E-006 (no native Qt side-by-side or macOS/Linux-X11
desktop session), both environment-bound rather than unimplemented.

## Status update 2026-10-29

`RM-076` and `RM-151` are now `Verified`.

* `RM-076`: the native `nf2ff` reads a Rust dump and every far-field dataset
  matches within `1.6e-5` of the peak. The missing factor was the native DFT
  weight `2 * recorded_interval`; the writer now also matches the native `f64`
  datasets and the `float32` `Frequency` attribute.
* `RM-151`: bare `Operator::new()` defaults to Var3 like native; the Debye
  identity is asserted on the f32-rounded coefficients (bit-exact) so no bound
  changed.
* `RM-042`/`RM-054`: the operator dump fixture now carries `Kappa=0.05`, so
  `EC_G` is compared against native for the first time (vv `9.8e-15`,
  vi `4.3e-13`). A parallel-plate TEM test with `Kappa` attenuates, but its
  ~4% lossless standing-wave residue is too large for the 3% analytic bound;
  the fixture still needs tightening, so `RM-054` stays `Implemented`.

Decision `D-R4`, `D-R7` and `D-R8(a)` are therefore applied: `RM-144` is now
`Implemented` and no row is `Blocked`.

`RM-006`, `RM-043` and `RM-054` were closed later the same day:

* `RM-006`: `STATUS_POLICY.md` with the closed vocabulary and the owner
  acknowledgement.
* `RM-043`: the UPML probes match native to `6.0e-8` / `1.0e-8` and the tail is
  -141 dB natively, -142 dB in the port.
* `RM-054`: the lossy guide probes match native to `7.5e-6` / `1.1e-5` with
  the same `0.6802` attenuation, and `EC_G` matches in the operator dump.

`RM-106` and `RM-124` were closed the same day: a real-display Windows
session with a maximized screenshot, and a daily 03:00 Windows task running
`scripts/ci/run_nightly_wsl.sh` with a dated artifact. The register now has
**151 `Verified`, 0 `Implemented`, 0 `Blocked`**; the remaining step is a
fresh `FINAL_AUDIT.md` against the current revision.

---

## 1. What this pass changed in the picture

Five findings move the eight rows from "unclear" to "bounded work". Two of them
are defects the register did not name.

### F1. `RM-076` is a missing `2 * dt`, not a reader problem

The native reader accepts the Rust dump since the `uint8` attribute fix, and
the native `nf2ff` runs to completion. The far field is low by a constant
factor, not wrong in shape: every `E_*` dataset has the same ratio
**1.083e10**, and `P_rad` the square of it (**1.17e20**).

That factor is the DFT weight. Native `HDF5_File_Reader::CalcFDVectorData`
integrates the sum with the recorded sample interval
(`openEMS/tools/hdf5_file_reader.cpp:938-945`):

```cpp
time_diff *= 2;
field_fd[n] *= time_diff;      // trapezoidal weight over the dump interval
```

The Rust `discrete_fourier_transform` (`openEMS/rust/src/nf2ff_hdf5.rs:547-594`)
returns the bare sum. The dump interval is `4.6188022e-11 s` (dumps every 8
steps at `5.7735e-12 s`), and `1 / (2 * 4.6188022e-11) = 1.0825e10`, which is
the measured ratio. So the value path is understood: multiply by `2 * dt`,
with `dt` the recorded sample interval, exactly as native does.

Consequence: the Rust `nf2ff` absolute fields are currently 10 orders of
magnitude too small. Directivity and normalised patterns hide this, which is
why the Octave `nf2ff_dipole` case passes.

### F2. `RM-151` is a one-line default, and the Debye bound is f32 storage

Native `Operator::Operator()` sets `m_TimeStepVar = 3`
(`openEMS/FDTD/operator.cpp:57`); the Rust `OperatorBaseImpl::new()` sets
`m_time_step_var: 1` (`openEMS/rust/src/operator_base.rs:254`). The engine and
the XML path already force 3, so only direct library users see the difference.

The Debye identity fails at `1.07e-6` once Var3 is used because the coefficients
are stored as `FDTD_FLOAT` (f32) in both stacks: native computes in `double`
and stores into `FDTD_FLOAT` arrays (`operator_ext_debyematerial.cpp:199-202`),
and so does Rust (`extensions.rs:1034-1036`). This is a test-bound question, not
a model question.

### F3. `RM-054` most likely used the wrong conductivity

openEMS defines `Kappa` as **electric** conductivity and `Sigma` as **magnetic**
conductivity (`doc-src/.../dispersive.rst:137-142`); `Calc_ECPos` uses
`EffMat[1] = kappa` for `EC_G` and `EffMat[3] = sigma` for `EC_R`
(`openEMS/FDTD/operator.cpp:1221-1247`). The register's failing attempt used
`sigma = 0.05`, whose magnetic loss is `sigma / (2 Z0) ~ 6.6e-5 Np/m`, i.e.
unmeasurable over 40 mm -- which is exactly the observed ratio `1.007`.

The analytic `0.692` it was compared against is the low-loss value for
`kappa = 0.05` (`exp(-kappa Z0 d / 2) = 0.686`). So the code path is probably
right and the fixture was wrong. The exact attenuation at `1 GHz`,
`kappa = 0.05` (`tan(delta) ~ 0.9`, so the low-loss form is not valid) is
`alpha = 8.70 Np/m`, i.e. `exp(-alpha d) = 0.706` over 40 mm.

Also: the `RM-042` operator dump used `eps = 4` and `sigma = 0.01` only, so
`EC_G` has never been compared against native. The coefficient half of
`RM-054` still needs a `kappa` fixture.

### F4. `RM-124` is an account restriction plus a default-branch rule

`gh api repos/.../actions/permissions` returns `enabled: true`, but a dispatch
fails with **HTTP 422 "Actions has been disabled for this repository"** -- the
account-level/billing form of the restriction, not the repository switch.
Independently, `schedule:` only runs from the default branch and `master`
contains only `ci.yml` and `windows-package.yml`; `reference.yml` exists only on
`mberkanbicer-rust-migration-audit`. A nightly therefore cannot fire until the
workflow is on `master` **and** the account restriction is lifted.

### F5. `RM-144` is implementable now and is not an external blocker

(a) **Cylindrical `SnapBox2Mesh` is missing.** Native
`Operator_Cylinder::SnapBox2Mesh` (`openEMS/FDTD/operator_cylinder.cpp:283-304`)
re-centres the azimuth span on `FitToAlphaRange(midpoint)`, clamps it to the
mesh range and only then snaps. Rust `snap_box_to_mesh_native`
(`openEMS/rust/src/operator.rs:1615`) snaps each endpoint independently, so a
box across the seam or a full-circle box folds to an empty or inverted span.
`processing.rs:3402` snaps dump boxes the same per-axis way.

(b) **`--nativeFieldDumps` only changes cylindrical vector rotation.**
`VTK_File_Writer::AddVectorField` branches on
`(m_MeshType == 0) or m_NativeDump` (`openEMS/tools/vtk_file_writer.cpp:173-181`);
a Cartesian mesh is byte-identical either way. The Rust writers
(`write_structured_grid_cylindrical`, `write_structured_vts_cylindrical`)
always rotate into `(x, y, z)`. The work is a bool threaded into `ProcessFields`
and `ProcessFieldsFD` plus two conditionals, and removal of the CLI warning at
`openEMS/rust-cli/src/main.rs:199`.

Neither piece waits on anything external. `Blocked` is the wrong status under
the Section 0 vocabulary; the row is `Implemented` with two named sub-tasks.

### F6. Records are stale and one row was silently unparsed

* `MIGRATION_STATUS.md` says `142 Verified, 8 Implemented` and
  `FINAL_AUDIT.md` says `96 Verified, 53 Implemented` and names
  RM-097..RM-106 as `Implemented` -- all older than the register.
* `gui-qa.md` says "only then can RM-015, RM-097...RM-106 move to `Verified`";
  those rows are already verified.
* The `RM-144` row still calls RM-078 `Implemented`; RM-078 is `Verified`.
* The `RM-054` row records the failing attempt without naming the fixture's
  `Sigma`-vs-`Kappa` mix-up.
* The `RM-054` row is long enough that it was one of the rows a stray `|`
  could split; the same class of defect hit `RM-057` earlier. Any rewrite of
  these rows must keep the cell free of bare pipes.

---

## 2. Per-task register

Legend: **Owner** = needs a human decision/signature; **Agent** = code and
measurement work; **Blocked on** = the real prerequisite.

### RM-006 -- status/evidence policy and closed vocabulary

| | |
| --- | --- |
| Current | The policy text exists in `REMEDIATION_PLAN.md` Section 0 and is summarised in `MIGRATION_STATUS.md`; the open item is "team acknowledgement" |
| Remaining | One canonical policy document plus a recorded acknowledgement |
| Evidence | Signed table (name, role, date, scope) linked from the plan and the status page |
| Grey area | Who "the team" is for a single-owner fork; whether one signature is enough; whether `Blocked` may be used for "not implemented" (RM-144 shows it currently is) |
| Decision | **D-R1** |
| Owner | yes |
| Effort | 1 hour, no code |

### RM-043 -- UPML reflection against native

| | |
| --- | --- |
| Current | Extension wiring (`RM-041`) and coefficients (`RM-042`) verified; the library test `upml_absorbs_a_gaussian_pulse` measures tail/peak `1.36e-6` (-117 dB) against PEC `1.28e-3` |
| Remaining | The same case measured natively, and an approved reflection bound |
| Plan | (1) Fix a fixture: 41x21x21 at 1 mm, `PML_8` on all six faces, Ez Gaussian `f0 = 6 GHz`, `fc = 3 GHz` at the centre, 900 steps, two E probes (centre and 6 mm off-centre), full-domain dump every 10 steps. (2) Run the pinned native binary and the Rust CLI on it. (3) Compare probe traces with the reference harness; derive the reflection ratio from the incident and the late-window peak in both. (4) Record both ratios and the bound |
| Evidence | Case under `reference-data/upml-wsl/`, a `VALIDATION.md` section, a harness case |
| Grey area | The library test sums the whole operator voltage array including PML auxiliary edges -- that is not a physical observable and cannot be compared with native. The comparison must use probes or dumps. The bound itself is a choice: -117 dB is not a sensible acceptance limit |
| Decision | **D-R2** |
| Owner | bound only |
| Effort | 1-2 days, mostly the native run and the harness case |

### RM-054 -- lossy medium (`EC_G`/`EC_R`)

| | |
| --- | --- |
| Current | `EC_G = kappa * area / delta`, `EC_R = sigma * area / delta`, matching native `Calc_ECPos`; the propagation attempt showed no attenuation |
| Remaining | (a) a `kappa != 0` operator-dump comparison (the `RM-042` fixture only had `sigma`), (b) a lossy-medium propagation test with `kappa` |
| Plan | (a) add `Kappa = 0.05` to the operator dump fixture and compare `vv`/`vi` node by node against native (bound: 1e-12 relative on the peak, the same class as the `vi` 1.29e-13 already recorded). (b) add `lossy_medium_attenuates_a_tem_wave` to `analytic_validation.rs`: parallel-plate guide, `kappa = 0.05 S/m`, 40 mm probe spacing, compare against the exact `alpha = omega sqrt(mu eps / 2) sqrt(sqrt(1 + (kappa / (omega eps))^2) - 1)`, bound 3 % like the existing propagation cases |
| Evidence | The dump comparison plus the analytic test with its measured ratio |
| Grey area | Which conductivity; whether the analytic formula is the exact one (at `tan(delta) ~ 0.9` the low-loss `kappa Z0 / 2` is 8 % off); whether to also cover magnetic loss (`sigma`) with its own analytic case |
| Decision | **D-R3** |
| Owner | new bound only |
| Effort | 0.5 day |

### RM-076 -- HDF5 writer / native readers

**Closed 2026-10-29** -- see the status update above.

| | |
| --- | --- |
| Current | Layout, attributes and dtypes match native; native `nf2ff` parses the dump; values differ by one constant |
| Remaining | Apply the native DFT normalisation and re-measure |
| Plan | multiply the DFT sum by `2 * dt` (recorded sample interval; native uses the last interval) in `nf2ff_hdf5.rs`, add a unit test with a known sine and a non-trivial interval, rebuild, rerun the native `nf2ff` on the Rust dump and compare every `/nf2ff/E_*` and `/nf2ff/P_rad` dataset (target: 1e-5 relative, the HDF5 bound in `REFERENCE_TOLERANCES.md`), then record the native-reader and value evidence in one place |
| Evidence | Native `nf2ff` output file, comparison numbers, updated `VALIDATION.md` |
| Grey area | This changes the absolute far-field numbers of the Rust `nf2ff`; normalised results do not move. The Python/Octave `nf2ff` helpers are not affected, but any downstream comparison that assumed unnormalised sums would be |
| Decision | **D-R4** |
| Owner | no (parity fix), but record it as a behaviour change |
| Effort | 0.5 day |

### RM-106 -- manual GUI QA

| | |
| --- | --- |
| Current | 18 automated/offscreen checks pass, including a real 1280x800 wgpu frame; seven interactive items (A-G) are open |
| Remaining | A, B, C, D, E on a real display; F native side-by-side; G platform matrix |
| Plan | prepare a fixture project and a launch script; the owner runs A-E in one Windows session and records PASS/FAIL per item; F and G need a scope decision first |
| Evidence | Signed checklist rows and screenshots in `audits/gui-qa.md` |
| Grey area | F requires the native Qt AppCSXCAD, which is not built in this environment (`~/openems-exact/bin` has no GUI; `~/opt/openEMS/bin/AppCSXCAD` is the Rust port) and has no image-export CLI. Pixel parity is also a weak criterion. G needs macOS, which this host cannot provide |
| Decision | **D-R5** (scope of F and G, and who signs) |
| Owner | yes |
| Effort | 1 hour owner time after the fixture exists |

### RM-124 -- nightly reference run

| | |
| --- | --- |
| Current | `reference.yml` has `schedule` and `workflow_dispatch`; push runs are green up to `f69ed4d`; dispatch now fails 422; `master` does not carry the workflow |
| Remaining | A real scheduled run, or an approved substitute |
| Plan | owner lifts the account restriction and the branch is merged (or the workflow is added to `master`); then wait for one 03:00 UTC run and record its id and artifact. Interim: a dated local nightly under `reference-data/nightly/` proves the job is runnable |
| Evidence | Run id, date, duration, artifact path |
| Grey area | Whether a dispatched run counts as "nightly"; whether a local cron artifact counts; whether the row can close before the merge |
| Decision | **D-R6** |
| Owner | yes (account) |
| Effort | minutes once access exists |

### RM-144 -- cylindrical box snapping and `--nativeFieldDumps`

| | |
| --- | --- |
| Current | Marked `Blocked`, but both blockers are ordinary code |
| Remaining | (a) port `Operator_Cylinder::SnapBox2Mesh` (re-centre, clamp, then snap) and use it for cylindrical boxes in the operator and in `processing.rs`; (b) thread `nativeFieldDumps` into `ProcessFields`/`ProcessFieldsFD` and skip the cylindrical rotation in the TD and FD writers; (c) a differential case with a seam-crossing dump box and a cylindrical native-vector dump |
| Evidence | Unit tests for the fold/clamp, plus a `coax_cylindrical` VTK/HDF5 comparison against native with and without the flag |
| Grey area | Whether the flag should also affect Cartesian output (native: no) and whether the seam-crossing box case belongs in `coax_cylindrical` or a new fixture |
| Decision | **D-R7** (re-classify the row, confirm the scope) |
| Owner | no |
| Effort | 1-2 days |

### RM-151 -- default timestep and Var3 parity

**Closed 2026-10-29** -- see the status update above.

| | |
| --- | --- |
| Current | Engine and XML path use Var3; bare `Operator::new()` uses Var1 (native: 3); the Debye identity test is the only casualty |
| Remaining | Flip the default, settle the Debye bound, re-run `openems-core` |
| Plan | set `m_time_step_var: 3` in `operator_base.rs`, then either compare the stored f32 coefficient with `analytic as f32 as f64` (exact, no bound change) or approve `2e-6` for the identity |
| Evidence | `openems-core` suite green with the default flipped; the Debye test's measured residual recorded |
| Grey area | Whether the test should assert f32-rounded equality (strictly correct) or a slightly wider bound (simpler, needs approval); whether any other bare-`Operator::new()` test silently depended on Var1 |
| Decision | **D-R8** |
| Owner | yes for the bound |
| Effort | 0.5 day |

---

## 3. Decision register

Each decision is written so that a one-line answer closes it. The recommended
option is first.

| ID | Question | Options | Recommendation | If deferred |
| --- | --- | --- | --- | --- |
| D-R1 | Who acknowledges the status/evidence policy, and in what form? | (a) one owner signature in `docs/migration/STATUS_POLICY.md`, mirrored from Section 0; (b) owner plus one named reviewer; (c) an issue/PR approval instead of a file | (a) -- the repository has a single owner and the file is the durable record | RM-006 stays `Implemented` |
| D-R2 | What is the UPML acceptance? | (a) probe-based reflection: native and port ratios within 3 dB and port ratio <= -60 dB; (b) only the port bound, native run recorded without a bound; (c) full-domain energy tail like the library test, compared with native dumps | (a) -- it is a physical observable, comparable in both stacks, and -60 dB is far above the measured -117 dB, so it cannot hide a regression | RM-043 stays `Implemented` |
| D-R3 | Which conductivity defines the lossy test, and which analytic formula? | (a) `kappa` with the exact `alpha`, 3 % bound; (b) `kappa` with the low-loss `kappa Z0 / 2` (8 % off at 0.05 S/m); (c) add both `kappa` and `sigma` cases | (a); add (c) later if a magnetic-loss case is wanted | RM-054 stays `Implemented` |
| D-R4 | Adopt the native `2 * dt` DFT weight in `nf2ff`? | (a) yes, match native; (b) keep the bare sum and document a different convention | (a) -- the row exists to be native-compatible; directivity is unchanged | RM-076 stays `Implemented` and the native `nf2ff` keeps returning ~1e-17 |
| D-R5 | Scope of the manual GUI QA | (a) A-E on Windows, F as a visual sanity check only if a native build exists, G limited to Windows + Linux; (b) all seven items including macOS and native pixel comparison; (c) A-E only, F/G as recorded exceptions | (a), with F/G as exceptions if no native build or macOS host is available | RM-106 stays `Implemented` |
| D-R6 | How does the nightly get proven? | (a) fix the Actions restriction + merge to `master`, record one scheduled run; (b) local nightly artifact, close with an exception; (c) dispatched run counts as nightly | (a); (b) only as an interim artifact | RM-124 stays `Implemented` |
| D-R7 | Is RM-144 still `Blocked`? | (a) re-classify to `Implemented` and do the two code items; (b) keep `Blocked` and name the missing owner decision | (a) -- no external dependency exists | The row misrepresents the state and inflates the "blocked" count |
| D-R8 | Debye identity bound under Var3 | (a) assert f32-rounded equality, no bound change; (b) approve `2e-6`; (c) keep Var1 | (a); (b) only if the test still fails for accumulation reasons | RM-151 stays `Implemented`, and the library default stays different from native |

---

## 4. Execution order

1. **D-R1, D-R7, D-R4** are cheap and unblock the rest: sign the policy, fix the
   row classification, apply the DFT weight.
2. **RM-076** then closes with one native run; it is the only P0 that needs no
   new fixture beyond the existing `nf2ff_dipole` case.
3. **RM-054** is the next code-only P0: extend the operator dump with `kappa`,
   then the analytic lossy test.
4. **RM-151** is one line plus the chosen assertion; run the full
   `openems-core` suite after it.
5. **RM-043** needs the new fixture and a native run; schedule it with the
   native harness work, not alone.
6. **RM-144** is the largest code item; do it after the P0 rows so a regression
   is attributable.
7. **RM-106, RM-124, RM-006** are owner actions; the agent can prepare the
   fixture, the script and the signature table, but cannot produce the
   evidence.

## 5. Definition of done for this register

* Every row above has either an executed measurement or an owner decision ID
  referenced from `REMEDIATION_TASKS.md`.
* `python scripts/ci/check_migration_docs.py` passes.
* `MIGRATION_STATUS.md`, `FINAL_AUDIT.md` and `REMEDIATION_PLAN.md` carry the
  same counts as the register; the stale sentences listed in F6 are gone.
* `FINAL_AUDIT.md` is re-run against the current revision, not the revision it
  was written at.
* The final full acceptance run is repeated after the last code change.

## 6. What cannot be produced from this host

| Item | Why | Who |
| --- | --- | --- |
| Real-display GUI QA (A-E) | WSLg cannot present a frame (`Io error: Broken pipe`); no Xvfb installed | owner on Windows |
| Native GUI side-by-side | no native Qt AppCSXCAD build and no image-export CLI | owner or a new build task |
| macOS build | no macOS host; Actions is restricted | owner / CI |
| Nightly cron | account restriction + workflow not on `master` | owner |
| Policy acknowledgement | a human signature | owner |
