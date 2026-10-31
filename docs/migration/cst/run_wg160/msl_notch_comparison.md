# CST cross-validation (E-009 / CST-001)

Notch reference: 3.6700 GHz
Notch CST:       3.6425 GHz
Relative difference: 0.749 %

| observable | reference | CST |
| --- | --- | --- |
| \|S11\| at notch | 0.9921 | 0.9981 |
| \|S21\| at notch | -50.07 dB | -29.76 dB |
| \|S11\| RMS difference | - | 1.42 dB |

Band: 1.000-7.000 GHz

| gate | result |
| --- | --- |
| notch_frequency | PASS |
| reflection_at_notch | PASS |
| rejection_at_notch | PASS |
| shape_rms | PASS |

VERDICT: PASS
