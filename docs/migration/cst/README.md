# CST cross-validation fixture (E-009 / CST-001)

The migration has analytic and native-differential evidence but no independent
third-party solver comparison. This directory holds the CST side of that check:
the same microstrip notch filter as
`openEMS/.github/smoketests/python/MSL_NotchFilter.py`, plus the export recipe
and the comparison harness.

**Status:** **completed 2026-10-31, PASS.** CST Studio Suite 2026 ran the model
(160 steps/wavelength, fixed mesh); the notch is 3.6425 GHz vs the openEMS
3.6700 GHz (**0.749 %**), |S11| 0.9981, |S21| -29.8 dB and the 1-7 GHz |S11|
shape RMS 1.42 dB. All four gates pass; evidence and the mesh-convergence table
are in `PREPARATION.md` and `run_wg160/`.

## What is compared

The shunt open stub reflects at its quarter-wave resonance, so the observable is
the **|S11| maximum** (and the |S21| minimum). The converged openEMS result is
`docs/migration/reference-data/convergence/msl_notch.json`:

| quantity | openEMS (finest mesh) |
| --- | --- |
| notch frequency | 3.6700 GHz |
| \|S11\| at notch | 0.9921 |
| \|S21\| at notch | 0.0031 (-50 dB absent) |
| quarter-wave estimate | 3.6871 GHz (+0.46 %) |

## Model (all dimensions in um)

| item | value |
| --- | --- |
| substrate | 100 000 x 30 000 x 254, y = -9 000 … 21 000, eps_r = 3.66, tan_d = 0 |
| microstrip | 100 000 x 600 x 35 PEC at z = 254 … 289 |
| stub | 600 x 12 000 x 35 PEC at x = -300 … 300, y = 300 … 12 300, z = 254 … 289 |
| air | full 100 x 30 mm column from z = 289 to 3 000 (vacuum), matching the openEMS domain height |
| ports | waveguide ports at x = ±50 000, y = -3 000 … 3 000, z = 0 … 1 000 (the plane must contain the strip) |
| boundaries | x/y open, zmin electric (ground), zmax open |
| frequencies | 1 … 7 GHz |
| mesh | hexahedral, 160 steps per wavelength at 7 GHz, fixed (no adaptation) |

CST cannot create a zero-thickness PEC sheet as a brick, so the strip is 35 um
thick copper-equivalent PEC. A 5 um control run moved the notch by 0.3 % in the
wrong direction, so the physical 35 um is kept.

## Option A - run the Python script (recommended)

`run_msl_notch_cst.py` drives CST through `cstControlApi.py`: builds the model,
runs the time-domain solver, exports the Touchstone file, compares the notch
with the converged openEMS curve and writes a report.

```powershell
# CST's Python libraries support CPython 3.8-3.13 (CST 2026 rejects 3.14).
python docs\migration\cst\run_msl_notch_cst.py
```

Outputs (default `docs/migration/cst/run/`):

| file | content |
| --- | --- |
| `msl_notch.cst` | CST project |
| `msl_notch.s2p` | Touchstone export (Hz, RI, 50 ohm) |
| `msl_notch_cst.json` | notch, gates and metadata |
| `msl_notch_comparison.md` | comparison report |
| `cst_messages.txt` | CST solver messages (mesh, passes, timing) |

The script defaults reproduce the validated run: waveguide ports, 1 mm port
plane, 160 steps/wavelength, fixed mesh. Runtime is about 12 minutes on 8
threads. `--no-run` builds and saves the model only; `--adapt` enables adaptive
refinement; `--port-type discrete` and `--open-margin` are diagnostic options.

## Option B - run the macro

1. Open CST Studio Suite, create a new **Microwave & RF / Time Domain** project.
2. Open `msl_notch.bas` and edit `ProjectPath` and `ExportDir` at the top.
3. **Home > Macros > Run Macro…** and select the file.
4. The macro builds the model, runs the solver and saves the project.

The macro is a fallback for environments where the Python libraries are not
available; the Python script above is the tested path. If a CST release names
an object differently, the macro stops on that line; send the line number and
CST version.

## Option C - build it manually

1. **Units:** Home > Units > Geometry `um`, Frequency `GHz`, Time `ns`.
2. **Background:** Epsilon 1, Mu 1, normal.
3. **Boundaries:** Xmin/Xmax `open`, Ymin/Ymax `open`, Zmin `electric`,
   Zmax `open`.
4. **Material:** new normal material `RO4350B`, Epsilon 3.66, Mu 1, TanD 0.
5. **Bricks** (Modeling > Brick), in this order:
   - `substrate`: X -50000 … 50000, Y -9000 … 21000, Z 0 … 254, material RO4350B;
   - `strip`: X -50000 … 50000, Y -300 … 300, Z 254 … 289, material PEC;
   - `stub`: X -300 … 300, Y 300 … 12300, Z 254 … 289, material PEC;
   - `air`: X -50000 … 50000, Y -9000 … 21000, Z 289 … 3000, material Vacuum
     (gives the 3 mm openEMS domain height).
6. **Ports** (Simulation > Waveguide Port), orientation `x`, one mode each,
   plane z = 0 … 500 (must contain the strip at z = 254 … 289):
   - port 1 at X = -50000, X range -50000 … -50000, Y -3000 … 3000;
   - port 2 at X = +50000, X range 50000 … 50000, Y -3000 … 3000.
7. **Solver:** Time Domain, hexahedral, ports 1 and 2, steady-state limit
   -40 dB, fixed mesh with 160 steps per wavelength. Set the frequency range
   to 1 … 7 GHz.
8. **Run.** Expect roughly 10-20 minutes on a laptop.

If CST is not in the default location, set `CST_INSTALL_DIR` (or
`CST_PYTHON_LIBRARIES`) before running Option A.

## Export (what to send back)

Option A writes the Touchstone file and the report automatically. For the macro
or manual path:

1. In the Navigation Tree open **1D Results > S-Parameters**.
2. Right-click **S-Parameters > Export > Touchstone…**.
3. Export the 1…7 GHz sweep with at least 601 points as `msl_notch.s2p`.
4. Optional but useful: **S-Parameters > Export > ASCII** as `msl_notch_s.txt`,
   and a screenshot of the S11 curve with the marker at the notch.
5. Put the files in `docs/migration/cst/` (or send them) together with the CST
   version and solver settings.

Then run:

```bash
python scripts/ci/run_cst_comparison.py \
  --cst docs/migration/cst/msl_notch.s2p \
  --out docs/migration/cst/msl_notch_comparison.md
```

The harness reads Touchstone (`RI`, `MA`, `DB`; Hz…GHz). It does not parse CST's
own ASCII 1D export, so always send the Touchstone file.

## Acceptance gates and why

| gate | limit | rationale |
| --- | --- | --- |
| notch frequency | within 1.0 % | openEMS mesh spread is 3.0e-4; a 35 um strip and a different mesh/port discretisation can move the resonance by a few tenths of a percent, but 1 % still catches a wrong model |
| \|S11\| at notch | >= 0.8 on both sides | the stub is a near-total reflector; a lower value means the port or stub is not modelled |
| \|S21\| at notch | <= -20 dB on both sides | same physical statement as rejection |
| \|S11\| RMS over the band | <= 3 dB, floored at -40 dB | phase-sensitive deep nulls are excluded by the floor; above the floor the magnitude shape must agree |

The limits were proposed before the first CST fixture and **all four pass** on
the recorded 160-step run (notch 0.749 %, RMS 1.42 dB). They are not widened;
if a later model shows a justified offset, record the cause first.

## After a successful run

Done 2026-10-31: the CST export, report and version are stored in `run_wg160/`
and the numbers are recorded in `VALIDATION.md`. `E-009` is closed in
`EXCEPTIONS.md`.
3. Close `E-009` in `docs/migration/EXCEPTIONS.md` (the change rule requires the
   decision record to be updated with it) and update the component matrix.
