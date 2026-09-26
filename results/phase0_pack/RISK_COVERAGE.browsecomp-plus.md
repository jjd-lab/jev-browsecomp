# Risk-coverage

Trace `SCOREBOARD.browsecomp-plus.live.repeat.trace.jsonl`, n=150. Held-out trace `SCOREBOARD.browsecomp-plus.live.holdout.trace.jsonl`, n=150.

Each question cites its argmax Noul when its score is at or above the threshold. Coverage is the share of questions that act at that threshold.
Held-out false-act is the share of held-out questions (gold dropped from the pool) whose score clears the same threshold.

As decided (route `act` and argmax Noul ≥ 0.5): coverage 0.360, precision 0.833.
Ceiling if every question acts on its argmax Noul: 0.400.
Held-out as decided: false-act 0.060.

## Ranked by route p(act)

| coverage | threshold | precision | held-out false-act |
| ---: | ---: | ---: | ---: |
| 0.100 | 0.76 | 0.800 | 0.007 |
| 0.213 | 0.68 | 0.844 | 0.027 |
| 0.300 | 0.56 | 0.800 | 0.033 |
| 0.407 | 0.43 | 0.787 | 0.087 |
| 0.500 | 0.26 | 0.680 | 0.173 |
| 0.613 | 0.15 | 0.598 | 0.347 |
| 0.813 | 0.06 | 0.475 | 0.700 |
| 1.000 | 0.02 | 0.400 | 1.000 |

## Ranked by max Noul

| coverage | threshold | precision | held-out false-act |
| ---: | ---: | ---: | ---: |
| 0.107 | 0.88 | 0.938 | 0.020 |
| 0.207 | 0.85 | 0.774 | 0.060 |
| 0.307 | 0.81 | 0.739 | 0.087 |
| 0.407 | 0.76 | 0.689 | 0.140 |
| 0.500 | 0.70 | 0.680 | 0.253 |
| 0.600 | 0.57 | 0.578 | 0.413 |
| 0.800 | 0.38 | 0.483 | 0.720 |
| 1.000 | 0.11 | 0.400 | 0.980 |
