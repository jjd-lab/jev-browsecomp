# Risk-coverage

Trace `SCOREBOARD.browsecomp-plus.live.k8.trace.jsonl`, n=150. Held-out trace `SCOREBOARD.browsecomp-plus.live.k8.holdout.trace.jsonl`, n=150.

Each question cites its argmax Noul when its score is at or above the threshold. Coverage is the share of questions that act at that threshold.
Held-out false-act is the share of held-out questions (gold dropped from the pool) whose score clears the same threshold.

As decided (route `act` and argmax Noul ≥ 0.5): coverage 0.653, precision 0.704.
Ceiling if every question acts on its argmax Noul: 0.547.
Held-out as decided: false-act 0.133.

## Ranked by route p(act)

| coverage | threshold | precision | held-out false-act |
| ---: | ---: | ---: | ---: |
| 0.100 | 0.82 | 0.867 | 0.013 |
| 0.213 | 0.77 | 0.906 | 0.020 |
| 0.313 | 0.71 | 0.809 | 0.040 |
| 0.400 | 0.66 | 0.800 | 0.067 |
| 0.500 | 0.58 | 0.787 | 0.093 |
| 0.620 | 0.51 | 0.710 | 0.107 |
| 0.807 | 0.30 | 0.636 | 0.293 |
| 1.000 | 0.05 | 0.547 | 0.913 |

## Ranked by max Noul

| coverage | threshold | precision | held-out false-act |
| ---: | ---: | ---: | ---: |
| 0.100 | 0.91 | 0.867 | 0.007 |
| 0.213 | 0.89 | 0.781 | 0.020 |
| 0.320 | 0.87 | 0.812 | 0.067 |
| 0.427 | 0.84 | 0.750 | 0.113 |
| 0.513 | 0.82 | 0.727 | 0.147 |
| 0.640 | 0.79 | 0.688 | 0.233 |
| 0.800 | 0.69 | 0.642 | 0.520 |
| 1.000 | 0.20 | 0.547 | 0.973 |
