# Risk-coverage

Trace `SCOREBOARD.browsecomp-plus-corpus.live.recurse.trace.jsonl`, n=150. Held-out trace `SCOREBOARD.browsecomp-plus-corpus.live.recurse.holdout.trace.jsonl`, n=150.

Each question cites its argmax Noul when its score is at or above the threshold. Coverage is the share of questions that act at that threshold.
Held-out false-act is the share of held-out questions (gold dropped from the pool) whose score clears the same threshold.

As decided (route `act` and argmax Noul ≥ 0.5): coverage 0.153, precision 0.783.
Ceiling if every question acts on its argmax Noul: 0.180.
Held-out as decided: false-act 0.027.

## Ranked by route p(act)

| coverage | threshold | precision | held-out false-act |
| ---: | ---: | ---: | ---: |
| 0.100 | 0.57 | 0.667 | 0.007 |
| 0.200 | 0.32 | 0.700 | 0.053 |
| 0.300 | 0.15 | 0.556 | 0.167 |
| 0.413 | 0.09 | 0.403 | 0.313 |
| 0.553 | 0.07 | 0.313 | 0.453 |
| 0.627 | 0.06 | 0.277 | 0.540 |
| 0.893 | 0.03 | 0.201 | 0.913 |
| 1.000 | 0.01 | 0.180 | 1.000 |

## Ranked by max Noul

| coverage | threshold | precision | held-out false-act |
| ---: | ---: | ---: | ---: |
| 0.100 | 0.79 | 0.733 | 0.020 |
| 0.200 | 0.64 | 0.667 | 0.100 |
| 0.320 | 0.52 | 0.542 | 0.207 |
| 0.427 | 0.45 | 0.406 | 0.307 |
| 0.500 | 0.41 | 0.360 | 0.407 |
| 0.627 | 0.36 | 0.287 | 0.540 |
| 0.800 | 0.28 | 0.225 | 0.747 |
| 1.000 | 0.13 | 0.180 | 1.000 |
