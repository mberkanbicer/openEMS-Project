# CST MWS comparison — status

**Status: BLOCKED — reference data unavailable.**

- No CST licence, project file, solver version or exported result exists in the
  workspace. `rg '\bCST\b'` over the tree returns **0 files**.
- No chart in this repository is labelled "CST verified"; none may be.
- The comparison is therefore **NOT RUN**, not "similar" or "approximately
  matching".

## What would unblock it

A matched case with, for both solvers: identical geometry/materials, documented
mesh and convergence, boundary/PML, excitation, port normalization/reference
plane, frequency grid and field sampling. Then export machine-readable data
(`.csv`, Touchstone, HDF5) and run the comparison script. The template is
`MODEL_EQUIVALENCE_TEMPLATE.md`.

Until then, the strongest evidence remains the analytic wave-speed tests and
the native differential harness (category A + D). CST is category C evidence
and is not a substitute for A.
