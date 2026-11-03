# CST cross-validation result (E-009 / CST-001)

**Status:** completed 2026-10-31, **PASS**.
**CST:** Studio Suite 2026 (Windows), driven by
`docs/migration/cst/run_msl_notch_cst.py` through `cstControlApi.py`.

## Definitive model

| setting | value |
| --- | --- |
| geometry | MSL notch: 100 x 30 mm substrate (RO4350B, 254 um), 600 um line, 12 mm shunt stub, 35 um PEC |
| air | vacuum column from the strip to z = 3 mm (openEMS domain height) |
| ports | waveguide ports at x = +/-50 mm, y = -3 … 3 mm, plane z = 0 … 1 mm (contains the strip) |
| boundaries | x open, y open, zmin electric, zmax open |
| solver | HF time domain, hexahedral, 160 steps/wavelength, fixed mesh (no adaptation) |
| sweep | 1-7 GHz, 1201 samples |
| runtime | 692.6 s (8 threads) |

The earlier low-frequency "notch" (1.04 GHz) was a port plane that did not
contain the strip (parallel-plate cutoff); the coarse-mesh attempts (3.545 GHz)
used a `Mesh.LinesPerWavelength` property that this CST release silently ignores.
The model above uses `MeshSettings.Set "StepsPerWaveNear/Far"`, which does apply.

## Result

`docs/migration/cst/run_wg160/msl_notch_comparison.md`:

| observable | openEMS | CST 2026 | difference |
| --- | --- | --- | --- |
| notch frequency | 3.6700 GHz | 3.6425 GHz | **0.749 %** (gate 1 %) |
| \|S11\| at notch | 0.9921 | 0.9981 | gate >= 0.8 PASS |
| \|S21\| at notch | -50.07 dB | -29.76 dB | gate <= -20 dB PASS |
| \|S11\| RMS, 1-7 GHz | - | 1.42 dB | gate <= 3 dB PASS |

All four gates pass. The Touchstone export (`run_wg160/msl_notch.s2p`),
metadata, CST messages and the report are committed; the CST project folder
(69 MB) is reproducible and ignored.

## Mesh convergence

Waveguide ports, fixed mesh, same geometry:

| steps/wavelength | notch | vs openEMS |
| ---: | ---: | ---: |
| 80 | 3.6327 GHz | 1.018 % |
| 160 | 3.6425 GHz | 0.749 % |

The notch moves monotonically toward the openEMS/quarter-wave value with mesh
refinement; the 160-step result is inside the 1 % gate. The convergence is the
reason the single 160 run is treated as the reference, not a cherry-picked one.

## Known limitation (not gated)

The CST power balance (\|S11\|² + \|S21\|²) is 0.68 at 1 GHz, rising to 0.95 at
7 GHz. The low-frequency deficit is the band-edge excitation/port behaviour of
the open-boundary waveguide port; both codes are weakly excited there. The
comparison therefore gates the notch region observables and the broadband
\|S11\| shape, not the absolute low-frequency power balance. This is recorded,
not hidden.

## Reproduce

```powershell
python docs\migration\cst\run_msl_notch_cst.py
```

The script defaults to the validated model (waveguide ports, 1 mm port plane,
160 steps/lambda, fixed mesh), writes `run/msl_notch.s2p` and runs the
comparison. `--no-run` builds the project only; `--adapt` enables adaptive
refinement; `--port-type discrete` is available for experiments.

## Evidence files

| file | content |
| --- | --- |
| `run_wg160/msl_notch.s2p` | CST Touchstone export (185 004 bytes) |
| `run_wg160/msl_notch_comparison.md` | gate report, VERDICT PASS |
| `run_wg160/msl_notch_cst.json` | notch, gates, paths |
| `run_wg160/cst_messages.txt` | solver passes, 160-step mesh, timing |
