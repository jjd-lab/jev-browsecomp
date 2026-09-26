# Phase 1 analysis

Rows from `A.capfix.jsonl` / `B.capfix.jsonl` replace the original rows for those question ids.

## Overview

| arm | n | accuracy | gold cited | no answer | token stops | $/q RLM | $/q Jev | $/q total | s/q | median turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 100 | 0.910 | 0.930 | 6 | 3 | 0.3541 | 0.0000 | 0.3541 | 143 | 11 |
| B | 100 | 0.900 | 0.930 | 8 | 6 | 0.4073 | 0.0123 | 0.4196 | 152 | 14 |
| J | 100 | 0.940 | 0.940 | 1 | 0 | 0.0476 | 0.0856 | 0.1332 | 21 | 1 |
| A.holdout | 30 | 0.067 | 0.000 | 3 | 0 | 1.1856 | 0.0000 | 1.1856 | 391 | 31 |
| J.holdout | 50 | 0.040 | 0.000 | 5 | 0 | 0.0692 | 0.0856 | 0.1548 | 41 | 1 |

## Jev gate vs self-confidence

Same answers, two scorers: `jev` = post-hoc gate p(act), `self` = stated confidence. AURC is lower-better. Δ = AURC(jev) − AURC(self), 95% paired bootstrap CI.

| set | n | errors | AURC jev | AURC self | Δ | 95% CI | verdict | AUROC jev | AUROC self | acc@cov0.8 jev | acc@cov0.8 self |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |
| A (primary) | 100 | 9 | 0.023 | 0.013 | +0.011 | [+0.000, +0.034] | no clear difference | 0.872 | 0.926 | 0.988 | 0.988 |
| B | 100 | 10 | 0.017 | 0.010 | +0.006 | [+0.000, +0.017] | self-confidence wins | 0.908 | 0.956 | 0.975 | 0.988 |
| A + held-out (co-primary) | 130 | 39 | 0.082 | 0.064 | +0.019 | [+0.005, +0.039] | self-confidence wins | 0.912 | 0.958 | 0.827 | 0.846 |
| A+B | 200 | 19 | 0.020 | 0.012 | +0.008 | [+0.001, +0.019] | self-confidence wins | 0.886 | 0.939 | 0.975 | 0.988 |

Label audit: same answer, different judge label on 0 question(s).

## Arm B vs A, paired (n=100)

| endpoint | A | B | B − A | 95% CI | verdict |
| --- | ---: | ---: | ---: | --- | --- |
| accuracy | 0.910 | 0.900 | -0.010 | [-0.070, +0.050] | no clear difference |
| $/question | 0.354 | 0.420 | +0.066 | [+0.016, +0.119] | B worse |
| seconds/question | 143.117 | 151.725 | +8.607 | [-10.865, +29.293] | no clear difference |

Mean Jev $/question in B: 0.0123; items screened/question: 192.

Accuracy discordant pairs: A-only correct 5, B-only correct 4, exact McNemar p = 1.000.

## Arm J vs A, paired (n=100)

| endpoint | A | J | J − A | 95% CI | verdict |
| --- | ---: | ---: | ---: | --- | --- |
| accuracy | 0.910 | 0.940 | +0.030 | [-0.030, +0.090] | no clear difference |
| $/question | 0.354 | 0.133 | -0.221 | [-0.287, -0.158] | J better |
| seconds/question | 143.117 | 20.677 | -122.441 | [-143.835, -102.463] | J better |

Mean Jev $/question in J: 0.0856; items screened/question: 1000.

Accuracy discordant pairs: A-only correct 3, J-only correct 6, exact McNemar p = 0.508.


## Arm J vs A, paired (n=62, fresh questions only (not in the 38-question probe))

| endpoint | A | J | J − A | 95% CI | verdict |
| --- | ---: | ---: | ---: | --- | --- |
| accuracy | 0.903 | 0.968 | +0.065 | [+0.000, +0.145] | no clear difference |
| $/question | 0.354 | 0.136 | -0.219 | [-0.306, -0.139] | J better |
| seconds/question | 142.081 | 21.410 | -120.671 | [-149.371, -95.715] | J better |

Mean Jev $/question in J: 0.0855; items screened/question: 1000.


## Held-out answers (no supporting document)

| arm | n | no answer | declined in words | gave an answer | median stated confidence | median Jev p(act) | answers with self ≥ 0.5 | answers with Jev ≥ 0.5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A.holdout | 30 | 3 | 19 | 8 | 0.25 | 0.10 | 0 | 0 |
| J.holdout | 50 | 5 | 37 | 8 | 0.35 | 0.10 | 3 | 1 |
