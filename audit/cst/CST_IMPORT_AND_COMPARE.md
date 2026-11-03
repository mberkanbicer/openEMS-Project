# CST import and compare workflow

No comparison tooling exists yet. This is the smallest workflow that would
produce honest category-C evidence when real CST exports are supplied.

## 1. Required exports from CST

| Quantity | Format | Notes |
|---|---|---|
| S-parameters | Touchstone (`.sNp`) | reference impedance and reference plane stated |
| Port impedance / modes | CSV | per frequency |
| Probes / field samples | CSV or HDF5 | coordinates, component, complex value |
| Far field | CSV | theta/phi grid, `E_theta`/`E_phi`, gain/directivity normalization |
| SAR | CSV | local/max/1g/10g, density, accepted power |
| Run manifest | text | CST version, solver, mesh cells, convergence, boundary |

## 2. Match the model first

Fill `MODEL_EQUIVALENCE_TEMPLATE.md` for both solvers **before** looking at the
results. A difference is not evidence until the model and normalization match.

## 3. Compare

- Magnitude (dB) and **unwrapped phase** vs frequency; resonance/null
  frequencies; group delay; energy balance.
- Complex vectors at coincident samples (not heatmap colours).
- Far-field in the same polarization basis and angle convention.
- SAR with the same accepted-power normalization and mass averaging.

## 4. Report

Store raw data, the alignment/interpolation method (documented), per-case
acceptance limits agreed in advance, and a machine-readable diff. A result that
cannot be reproduced from the saved files is not evidence.

No script is added until real data exists; inventing a parser without a sample
would not be verifiable.
