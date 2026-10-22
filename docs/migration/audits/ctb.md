# CTB Audit

**Status:** Source and MATLAB smoke audit complete for the pinned submodule.
Numerical defects and compatibility gaps are recorded below; no CTB source
was changed.

## Scope and interface map

All 21 tracked M-files in `CTB/` were inventoried and reviewed. There is no
matching test file or test directory. The repository's `Makefile` only
installs the M-files under `$(PREFIX)/share/CTB/matlab` (default prefix
`/usr/local`) and copies the license and README. MATLAB R2025b was available;
Octave was not found on this host.

| Function group | Public functions | Contract |
| --- | --- | --- |
| Network-parameter transforms | `s2z`, `s2y`, `z2s`, `y2s`, `z2y`, `y2z`, `s_renorm` | Convert complex n-port matrices shaped `n x n x nfreq`; conversion functions default to a 50-ohm reference. `z2y` and `y2z` invert each frequency slice. Renormalization composes S-to-Z and Z-to-S. |
| ABCD transforms and composition | `s2a`, `a2s`, `a_T`, `a_PI`, `a_series`, `a_shunt`, `a_mul` | `s2a`/`a2s` are limited to `2 x 2 x nfreq`; helpers construct T/PI, series, and shunt matrices; `a_mul` multiplies matrices frequency-by-frequency. |
| Touchstone I/O | `read_touchstone`, `write_touchstone` | Reader infers port count from extension and supports Hz/kHz/MHz/GHz plus RI/MA/DB data. Writer emits RI and supports S/Z/Y parameter types; defaults reference impedance to 50 ohms for S and 1 for Z/Y. |
| Network operations | `InitNetwork`, `AddElement2Port`, `SetPortTermination`, `ApplyCurrent2Port`, `ApplyRFPower2Port` | Network struct stores frequency, S/Z/Y matrices, reference impedances, per-port ABCD networks, original S, port count, and frequency count. Element updates support series/shunt C/L/R and direct Z/Y loads; current and RF-power helpers return port-by-frequency current matrices. |

Inputs are treated as complex-valued Matlab arrays; frequencies are documented
in Hz and power in watts. The implementation relies on Matlab/Octave matrix
operations and implicit expansion patterns, with no explicit type, dimension,
or finite-value validation beyond selected checks.

## Confirmed findings

1. **PI helper fails for numeric inputs.** `a_PI.m:14` contains
   `Y1.Y2./Y3`, which MATLAB interprets as dot indexing. MATLAB R2025b
   confirmed `a_PI(1,2,3)` fails with “Dot indexing is not supported for
   variables of this type.” The intended product is not asserted here; resolve
   the formula with the component owner before porting.
2. **Three-or-more-port Touchstone ordering is transposed.** A 3-port,
   two-frequency S-matrix round trip through `write_touchstone` and
   `read_touchstone` had maximum element error `0.0203961`; comparing the
   result to `permute(input,[2 1 3])` produced zero error. One- and two-port
   round trips were exact. The writer's n-port loop and reader's source/dest
   assignment use different ordering for three or more ports. The reader's
   own source comment warns that higher-than-two-port files need validation.
3. **Malformed Touchstone extensions are accepted.** The reader rejects an
   extension only when its first character is not `s` *and* its last character
   is not `p`. MATLAB accepted a valid two-port S file named `.x2p` and read it
   as a two-port S file. The extension check does not enforce the documented
   `.sNp` form.
4. **Element type documentation differs from the implementation.**
   `AddElement2Port.m` documents `Y_se` as the shunt-admittance option, while
   the implementation accepts `Y_sh`. Determine whether callers rely on
   either spelling before setting the compatibility contract.
5. **Touchstone parse errors leave the input file open.** The invalid-unit
   probe raises before the function reaches its trailing `fclose(fid)`.
   MATLAB R2025b's `openedFiles` confirmed the input path remained open after
   the exception. Callers repeating failed reads can retain file handles.

## Executed reference probes

All commands used MATLAB R2025b with `addpath('CTB')`.

| Probe | Result |
| --- | --- |
| Touchstone S round trip, 1 port, 2 frequencies | Frequency and matrix max errors `0`; reference `50`; one comment returned. |
| Touchstone S round trip, 2 ports, 2 frequencies | Frequency and matrix max errors `0`; reference `50`; one comment returned. |
| Touchstone Z/Y round trips, 2 ports, 2 frequencies | Both parameter types round-tripped exactly; omitted reference defaulted to `1`. |
| Touchstone S round trip, 3 ports, 2 frequencies | Matrix max error `0.0203961`; transpose-order error `0`. |
| `s2z(z2s(Z,50),50)` for a nonsingular 2-port matrix at two frequencies | Maximum absolute error `1.42109e-14`. |
| `s_renorm(S,50,50)` | Maximum absolute error `1.38778e-16`. |
| `InitNetwork` → `AddElement2Port` → `SetPortTermination` → current and RF-power excitation | Both current outputs had shape `2 x 2` and finite values. |
| `a_PI(1,2,3)` | Runtime failure at line 14 due to dot indexing. |
| Read a valid file with extension `.x2p` | Accepted as a 2-port S file. |

## Extended edge probes

Additional probes used MATLAB R2025b and temporary files removed after each
read:

| Probe | Observed result |
| --- | --- |
| `s2z(eye(2))` | Emits `MATLAB:singularMatrix`; all returned values are NaN. |
| `z2s(-50*eye(2),50)` | Emits `MATLAB:singularMatrix`; returns non-finite values. |
| `z2s(25*eye(2),0)` / `z2s(25*eye(2),-50)` | Zero reference is accepted and returns NaNs; negative reference is accepted and returns finite values. Neither is validated. |
| `s2z(zeros(2,3))` | Raises a MATLAB array-size mismatch. |
| `s2a(zeros(3,3))` | Silently returns a 2-by-2 result using the first two rows/columns despite the documented 2-port-only contract. |
| `s2a(zeros(2,2))` | `S21=0` produces non-finite values without a validation error. |
| Touchstone S1P with 0 and negative frequency and `R 0` | Accepted; frequencies are retained and the returned reference is zero. |
| Touchstone record with a nonnumeric field | Accepted with `NaN` data. |
| Touchstone file without a parameter header | Errors on the undefined `freq_mul` variable. |
| Comment line inside a wrapped data record | Accepted as record content; creates non-finite data, then parsing continues. |
| Truncated Touchstone record at EOF | Accepted with a non-finite datum rather than a truncation error. |
| `InitNetwork([0 1e9],S)` plus a series capacitor | DC impedance is infinite; updates emit singular-matrix warnings and the derived S/Z data are non-finite. |
| `SetPortTermination(net,1,0)` | Accepted; recalculated S data are non-finite. |
| `ApplyCurrent2Port(net,1,NaN)` | Accepted and propagates NaNs to the current result. |
| `ApplyRFPower2Port(net,1,-1)` | Accepted; the negative real power is treated as magnitude plus a phase of π. |
| `AddElement2Port(net,0,'R_se',50)` | Raises `invalid port number`. |
| Touchstone Hz/kHz/MHz/GHz headers | All accepted; returned frequencies use Hz with the expected scale. |
| Touchstone RI/MA/DB data | All accepted; the sample encodings yielded `0.5+0.25i`, `0+0.5i`, and `0.5+0i`, respectively. |
| Blank line in a wrapped record and trailing comment | Blank continuation parsed correctly; trailing comment was returned. |
| Invalid Touchstone unit | Raises `wrong unit: "THZ"` and leaves the input file open; `openedFiles` confirmed the leaked handle. |
| Three-frequency, asymmetric-reference transform corpus | For a nonsingular 2-port S matrix and reference impedances `[50;75]`, `s2y`/`y2s`, `s2z`/`y2z`, and `s2z`/`z2y` round trips passed with maximum absolute errors `2.22e-16`, `4.26e-14`, and `1.39e-17`; `s2a`/`a2s` at 50 ohms passed with error `2.22e-16`. |
| Three-frequency, 3-port S/Z/Y round trips | With asymmetric references `[50;75;60]`, `s2z`/`z2s` and `s2y`/`y2s` both passed; maximum absolute errors were `1.25e-16` and `7.08e-17`. |
| Three-port renormalization between unequal references | Renormalizing from `[50;75;60]` to `[75;60;50]` and back passed with maximum absolute S-matrix error `1.39e-16`. |
| 3-port S-to-Z/Y against direct equations | With asymmetric positive references `[50;75;60]`, `s2z` and `s2y` matched independently assembled matrix equations over three frequencies; maximum absolute differences were `2.84e-14` and `5.21e-18`. |
| Renormalization impedance invariant | The Z matrix before and after renormalizing a 3-port S matrix from `[50;75;60]` to `[75;60;50]` agreed within `7.12e-15`. |
| Single-frequency 2-port S/ABCD round trip | `s2a` and `a2s` preserved a `2 x 2 x 1` S matrix with maximum absolute error `1.25e-16`. |

The source has limited explicit validation: invalid port indices and unknown
element names are rejected, while matrix singularities, non-finite values,
nonphysical references, malformed Touchstone rows, and invalid physical
frequencies commonly propagate through MATLAB operations.

## Remaining validation limits

- Extend singularity, reference, non-finite, and dimension probes to every
  transform and each network-operation branch; the probes above are
  representative, not exhaustive.
- Validate Touchstone port-count variants and 3+ port files against
  independent reference implementations, including edge-case comments and
  malformed records.
- Resolve the confirmed defects and type-name mismatch in the CTB source
  repository before treating those behaviors as stable migration references.
