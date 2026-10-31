# CST cross-validation fixture (E-009 / CST-001)

The migration has analytic and native-differential evidence but no independent
third-party solver comparison. This directory holds the CST side of that check:
the same microstrip notch filter as
`openEMS/.github/smoketests/python/MSL_NotchFilter.py`, plus the export recipe
and the comparison harness.

**Status:** prepared 2026-10-31, **not yet run** (no CST installation in the
migration environment). `E-009` stays open until a real CST export is compared
and recorded in `VALIDATION.md`.

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
| ports | waveguide ports at x = ±50 000, y = -3 000 … 3 000, z = 0 … 254 |
| boundaries | x/y open, zmin electric (ground), zmax open |
| frequencies | 1 … 7 GHz |
| mesh | hexahedral, adaptive, ~20 lines per wavelength at 7 GHz |

CST cannot create a zero-thickness PEC sheet as a brick, so the strip is 35 um
thick copper-equivalent PEC. The 35 um does not move the notch measurably
(0.1 % scale), but record it in the result.

## Option A - run the macro

1. Open CST Studio Suite, create a new **Microwave & RF / Time Domain** project.
2. Open `msl_notch.bas` and edit `ProjectPath` and `ExportDir` at the top.
3. **Home > Macros > Run Macro…** and select the file.
4. The macro builds the model, runs the solver and saves the project.

The macro is untested against a live CST installation: if your release names an
object or property differently it stops on that line. Send the line number and
CST version, or use the manual recipe below, which is authoritative.

## Option B - build it manually

1. **Units:** Home > Units > Geometry `um`, Frequency `GHz`, Time `ns`.
2. **Background:** Epsilon 1, Mu 1, normal.
3. **Boundaries:** Xmin/Xmax `open`, Ymin/Ymax `open`, Zmin `electric`,
   Zmax `open`.
4. **Material:** new normal material `RO4350B`, Epsilon 3.66, Mu 1, TanD 0.
5. **Bricks** (Modeling > Brick), in this order:
   - `substrate`: X -50000 … 50000, Y -9000 … 21000, Z 0 … 254, material RO4350B;
   - `strip`: X -50000 … 50000, Y -300 … 300, Z 254 … 289, material PEC;
   - `stub`: X -300 … 300, Y 300 … 12300, Z 254 … 289, material PEC.
6. **Ports** (Simulation > Waveguide Port), orientation `x`, one mode each:
   - port 1 at X = -50000, X range -50000 … -50000, Y -3000 … 3000, Z 0 … 254;
   - port 2 at X = +50000, X range 50000 … 50000, Y -3000 … 3000, Z 0 … 254.
7. **Solver:** Time Domain, hexahedral, ports 1 and 2, steady-state limit
   -40 dB, adaptive mesh on. Set the frequency range to 1 … 7 GHz.
8. **Run.** Expect roughly 5-20 minutes on a laptop.

## Export (what to send back)

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

The harness also accepts CST ASCII exports if you rename the extension; it
parses Touchstone (`RI`, `MA`, `DB`; Hz…GHz) and reports the notch frequency,
depth, rejection and the |S11| RMS difference.

## Acceptance gates and why

| gate | limit | rationale |
| --- | --- | --- |
| notch frequency | within 1.0 % | openEMS mesh spread is 3.0e-4; a 35 um strip and a different mesh/port discretisation can move the resonance by a few tenths of a percent, but 1 % still catches a wrong model |
| \|S11\| at notch | >= 0.8 on both sides | the stub is a near-total reflector; a lower value means the port or stub is not modelled |
| \|S21\| at notch | <= -20 dB on both sides | same physical statement as rejection |
| \|S11\| RMS over the band | <= 3 dB, floored at -40 dB | phase-sensitive deep nulls are excluded by the floor; above the floor the magnitude shape must agree |

The limits are proposed for the first CST fixture. If the first real comparison
shows a justified systematic offset (for example the 35 um strip), record the
cause and only then adjust a limit - never widen one merely to pass.

## After a successful run

1. Store the CST export, the comparison report and the CST version here.
2. Add the measured numbers to `docs/migration/VALIDATION.md`.
3. Close `E-009` in `docs/migration/EXCEPTIONS.md` (the change rule requires the
   decision record to be updated with it) and update the component matrix.
