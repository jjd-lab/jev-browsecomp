# Risk-coverage

Trace `SCOREBOARD.browsecomp-plus-corpus.live.narrow.trace.jsonl`, n=150. Held-out trace `SCOREBOARD.browsecomp-plus-corpus.live.narrow.holdout.trace.jsonl`, n=150.

Each question cites its argmax Noul when its score is at or above the threshold. Coverage is the share of questions that act at that threshold.
Held-out false-act is the share of held-out questions (gold dropped from the pool) whose score clears the same threshold.

As decided (route `act` and argmax Noul ≥ 0.5): coverage 0.433, precision 0.662.
Ceiling if every question acts on its argmax Noul: 0.353.
Held-out as decided: false-act 0.060.

## Ranked by route p(act)

| coverage | threshold | precision | held-out false-act |
| ---: | ---: | ---: | ---: |
| 0.120 | 0.82 | 0.667 | 0.007 |
| 0.200 | 0.73 | 0.633 | 0.020 |
| 0.300 | 0.65 | 0.733 | 0.020 |
| 0.400 | 0.51 | 0.667 | 0.053 |
| 0.500 | 0.39 | 0.613 | 0.087 |
| 0.607 | 0.26 | 0.549 | 0.200 |
| 0.827 | 0.08 | 0.427 | 0.680 |
| 1.000 | 0.02 | 0.353 | 1.000 |

## Ranked by max Noul

| coverage | threshold | precision | held-out false-act |
| ---: | ---: | ---: | ---: |
| 0.107 | 0.88 | 0.688 | 0.027 |
| 0.213 | 0.85 | 0.625 | 0.040 |
| 0.313 | 0.81 | 0.617 | 0.053 |
| 0.413 | 0.76 | 0.597 | 0.120 |
| 0.507 | 0.69 | 0.579 | 0.213 |
| 0.613 | 0.59 | 0.533 | 0.413 |
| 0.807 | 0.44 | 0.430 | 0.707 |
| 1.000 | 0.23 | 0.353 | 0.987 |
