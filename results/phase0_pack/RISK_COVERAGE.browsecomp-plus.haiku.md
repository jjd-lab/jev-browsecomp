# Risk-coverage

Trace `SCOREBOARD.browsecomp-plus.live.haiku.trace.jsonl`, n=150. Held-out trace `SCOREBOARD.browsecomp-plus.live.haiku.holdout.trace.jsonl`, n=150.

Each question cites its argmax Noul when its score is at or above the threshold. Coverage is the share of questions that act at that threshold.
Held-out false-act is the share of held-out questions (gold dropped from the pool) whose score clears the same threshold.

As decided (route `act` and argmax Noul ≥ 0.5): coverage 0.607, precision 0.560.
Ceiling if every question acts on its argmax Noul: 0.380.
Held-out as decided: false-act 0.340.

## Ranked by route p(act)

| coverage | threshold | precision | held-out false-act |
| ---: | ---: | ---: | ---: |
| 0.533 | 0.95 | 0.562 | 0.293 |
| 0.607 | 0.85 | 0.560 | 0.340 |
| 0.880 | 0.15 | 0.432 | 0.747 |
| 0.887 | 0.05 | 0.429 | 0.760 |

## Ranked by max Noul

| coverage | threshold | precision | held-out false-act |
| ---: | ---: | ---: | ---: |
| 0.407 | 0.98 | 0.590 | 0.167 |
| 0.567 | 0.95 | 0.588 | 0.293 |
| 0.640 | 0.90 | 0.542 | 0.367 |
| 0.800 | 0.75 | 0.467 | 0.613 |
| 0.887 | 0.10 | 0.429 | 0.760 |
