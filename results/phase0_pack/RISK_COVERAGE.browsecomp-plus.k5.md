# Risk-coverage

Trace `SCOREBOARD.browsecomp-plus.live.k5.trace.jsonl`, n=150. Held-out trace `SCOREBOARD.browsecomp-plus.live.k5.holdout.trace.jsonl`, n=150.

Each question cites its argmax Noul when its score is at or above the threshold. Coverage is the share of questions that act at that threshold.
Held-out false-act is the share of held-out questions (gold dropped from the pool) whose score clears the same threshold.

As decided (route `act` and argmax Noul ≥ 0.5): coverage 0.487, precision 0.767.
Ceiling if every question acts on its argmax Noul: 0.493.
Held-out as decided: false-act 0.100.

## Ranked by route p(act)

| coverage | threshold | precision | held-out false-act |
| ---: | ---: | ---: | ---: |
| 0.100 | 0.83 | 0.733 | 0.007 |
| 0.207 | 0.74 | 0.774 | 0.027 |
| 0.313 | 0.68 | 0.766 | 0.040 |
| 0.400 | 0.60 | 0.783 | 0.073 |
| 0.507 | 0.46 | 0.776 | 0.107 |
| 0.600 | 0.33 | 0.733 | 0.187 |
| 0.800 | 0.12 | 0.575 | 0.560 |
| 1.000 | 0.04 | 0.493 | 0.960 |

## Ranked by max Noul

| coverage | threshold | precision | held-out false-act |
| ---: | ---: | ---: | ---: |
| 0.113 | 0.91 | 0.706 | 0.013 |
| 0.233 | 0.87 | 0.800 | 0.040 |
| 0.327 | 0.85 | 0.755 | 0.080 |
| 0.400 | 0.82 | 0.733 | 0.100 |
| 0.513 | 0.77 | 0.675 | 0.227 |
| 0.607 | 0.73 | 0.659 | 0.313 |
| 0.800 | 0.57 | 0.575 | 0.687 |
| 1.000 | 0.22 | 0.493 | 0.953 |
