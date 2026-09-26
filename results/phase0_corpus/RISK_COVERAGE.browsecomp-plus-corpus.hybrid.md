# Risk-coverage

Trace `SCOREBOARD.browsecomp-plus-corpus.live.hybrid.trace.jsonl`, n=150. Held-out trace `SCOREBOARD.browsecomp-plus-corpus.live.hybrid.holdout.trace.jsonl`, n=150.

Each question cites its argmax Noul when its score is at or above the threshold. Coverage is the share of questions that act at that threshold.
Held-out false-act is the share of held-out questions (gold dropped from the pool) whose score clears the same threshold.

As decided (route `act` and argmax Noul ≥ 0.5): coverage 0.407, precision 0.672.
Ceiling if every question acts on its argmax Noul: 0.360.
Held-out as decided: false-act 0.047.

## Ranked by route p(act)

| coverage | threshold | precision | held-out false-act |
| ---: | ---: | ---: | ---: |
| 0.100 | 0.77 | 0.867 | 0.007 |
| 0.200 | 0.68 | 0.833 | 0.020 |
| 0.307 | 0.56 | 0.739 | 0.027 |
| 0.400 | 0.46 | 0.683 | 0.053 |
| 0.513 | 0.34 | 0.636 | 0.100 |
| 0.607 | 0.21 | 0.571 | 0.240 |
| 0.813 | 0.08 | 0.434 | 0.627 |
| 1.000 | 0.02 | 0.360 | 1.000 |

## Ranked by max Noul

| coverage | threshold | precision | held-out false-act |
| ---: | ---: | ---: | ---: |
| 0.113 | 0.87 | 0.941 | 0.033 |
| 0.200 | 0.83 | 0.733 | 0.047 |
| 0.313 | 0.78 | 0.681 | 0.060 |
| 0.407 | 0.72 | 0.639 | 0.140 |
| 0.500 | 0.67 | 0.613 | 0.220 |
| 0.607 | 0.61 | 0.538 | 0.340 |
| 0.800 | 0.47 | 0.433 | 0.607 |
| 1.000 | 0.20 | 0.360 | 0.993 |
