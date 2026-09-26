# Risk-coverage

Trace `SCOREBOARD.browsecomp-plus-corpus.live.flat.trace.jsonl`, n=150. Held-out trace `SCOREBOARD.browsecomp-plus-corpus.live.flat.holdout.trace.jsonl`, n=150.

Each question cites its argmax Noul when its score is at or above the threshold. Coverage is the share of questions that act at that threshold.
Held-out false-act is the share of held-out questions (gold dropped from the pool) whose score clears the same threshold.

As decided (route `act` and argmax Noul ≥ 0.5): coverage 0.047, precision 0.714.
Ceiling if every question acts on its argmax Noul: 0.067.
Held-out as decided: false-act 0.013.

## Ranked by route p(act)

| coverage | threshold | precision | held-out false-act |
| ---: | ---: | ---: | ---: |
| 0.113 | 0.20 | 0.471 | 0.047 |
| 0.220 | 0.09 | 0.273 | 0.173 |
| 0.313 | 0.06 | 0.191 | 0.280 |
| 0.513 | 0.04 | 0.130 | 0.480 |
| 0.680 | 0.03 | 0.098 | 0.700 |
| 0.920 | 0.02 | 0.072 | 0.907 |
| 1.000 | 0.01 | 0.067 | 1.000 |

## Ranked by max Noul

| coverage | threshold | precision | held-out false-act |
| ---: | ---: | ---: | ---: |
| 0.100 | 0.64 | 0.600 | 0.053 |
| 0.207 | 0.48 | 0.290 | 0.147 |
| 0.313 | 0.40 | 0.191 | 0.247 |
| 0.407 | 0.35 | 0.148 | 0.353 |
| 0.507 | 0.28 | 0.118 | 0.473 |
| 0.600 | 0.24 | 0.111 | 0.567 |
| 0.847 | 0.17 | 0.079 | 0.827 |
| 1.000 | 0.09 | 0.067 | 0.993 |
