# CST cross-validation preparation (E-009)

**Date:** 2026-10-31
**Scope:** prepare the CST side of `CST-001`; the exception stays open until a
real CST export is compared.

## Delivered

| item | path | state |
| --- | --- | --- |
| CST model macro (MSL notch, 1-7 GHz) | `docs/migration/cst/msl_notch.bas` | not executed against a live CST installation |
| Manual build + export recipe | `docs/migration/cst/README.md` | complete |
| Comparison harness (Touchstone parsing, gates, report) | `scripts/ci/run_cst_comparison.py` | self-tested on synthetic Touchstone |
| Acceptance check | `run_full_acceptance_wsl.sh` → "CST comparison harness self-test" | passes |

The harness **refuses to claim a comparison without data**: `--cst` is required
and a missing file exits 2. `--self-test` exercises the parser (`RI`, `MA`,
`DB`; Hz…GHz), the notch fit and all four gates on the recorded reference curve
with 0 %, 0.2 % and 3 % frequency shifts.

## Self-test evidence (2026-10-31)

```
self-test identical: True rms=0.000 dB
self-test 0.2% shift: True notch=0.200%
self-test 3% shift: True notch=3.000%
self-test MA format: True
self-test: PASS
python scripts/ci/run_cst_comparison.py   # no --cst
CST data missing: pass --cst <export.s2p>; see docs/migration/cst/README.md   (exit 2)
```

## What still blocks E-009

A CST export from the model in `docs/migration/cst/README.md`: the Touchstone
S-parameter sweep (1-7 GHz) plus the CST version and solver settings. CST is not
installed in the migration environment, so this cannot be produced here; the
project owner runs it locally.

## Closing procedure

1. Place `msl_notch.s2p` in `docs/migration/cst/`.
2. `python scripts/ci/run_cst_comparison.py --cst docs/migration/cst/msl_notch.s2p --out docs/migration/cst/msl_notch_comparison.md`
3. If the gates pass, record the numbers in `docs/migration/VALIDATION.md`,
   close `E-009` in `docs/migration/EXCEPTIONS.md`, and mark the matrix row
   `CST MWS cross-validation` as `VERIFIED_COMPLETE`.
4. If a gate fails, keep the exception open and investigate the model
   difference (strip thickness, port span, mesh) before touching a limit.
