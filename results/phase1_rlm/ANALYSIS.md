# Phase 1 analysis

## Overview

| arm | n | accuracy | gold cited | no answer | token stops | $/q RLM | $/q Jev | $/q total | s/q | median turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 100 | 0.940 | 0.960 | 7 | 0 | 0.3008 | 0.0000 | 0.3008 | 132 | 11 |
| B | 100 | 0.840 | 0.870 | 14 | 0 | 0.3250 | 0.0163 | 0.3414 | 142 | 14 |
| J | 100 | 0.940 | 0.940 | 1 | 0 | 0.0476 | 0.0856 | 0.1332 | 21 | 1 |
| A.holdout | 30 | 0.067 | 0.000 | 3 | 0 | 1.1856 | 0.0000 | 1.1856 | 391 | 31 |
| J.holdout | 50 | 0.040 | 0.000 | 5 | 0 | 0.0692 | 0.0856 | 0.1548 | 41 | 1 |

## Jev gate vs self-confidence

Same answers, two scorers: `jev` = post-hoc gate p(act), `self` = stated confidence. AURC is lower-better. Δ = AURC(jev) − AURC(self), 95% paired bootstrap CI.

| set | n | errors | AURC jev | AURC self | Δ | 95% CI | verdict | AUROC jev | AUROC self | acc@cov0.8 jev | acc@cov0.8 self |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |
| A (primary) | 100 | 6 | 0.019 | 0.009 | +0.010 | [+0.000, +0.032] | no clear difference | 0.839 | 0.906 | 0.988 | 0.988 |
| B | 100 | 16 | 0.026 | 0.019 | +0.007 | [-0.000, +0.019] | no clear difference | 0.942 | 0.972 | 0.975 | 0.988 |
| A + held-out (co-primary) | 130 | 36 | 0.075 | 0.055 | +0.020 | [+0.006, +0.039] | self-confidence wins | 0.905 | 0.958 | 0.846 | 0.875 |
| A+B | 200 | 22 | 0.021 | 0.013 | +0.008 | [+0.000, +0.018] | self-confidence wins | 0.910 | 0.950 | 0.981 | 0.988 |

Label audit: same answer, different judge label on 0 question(s).

## Arm B vs A, paired (n=100)

| endpoint | A | B | B − A | 95% CI | verdict |
| --- | ---: | ---: | ---: | --- | --- |
| accuracy | 0.940 | 0.840 | -0.100 | [-0.160, -0.050] | B worse |
| $/question | 0.301 | 0.341 | +0.041 | [+0.008, +0.074] | B worse |
| seconds/question | 132.340 | 142.015 | +9.674 | [-1.977, +21.323] | no clear difference |

Mean Jev $/question in B: 0.0163; items screened/question: 209.

Accuracy discordant pairs: A-only correct 10, B-only correct 0, exact McNemar p = 0.002.

## Arm J vs A, paired (n=100)

| endpoint | A | J | J − A | 95% CI | verdict |
| --- | ---: | ---: | ---: | --- | --- |
| accuracy | 0.940 | 0.940 | +0.000 | [-0.050, +0.060] | no clear difference |
| $/question | 0.301 | 0.133 | -0.168 | [-0.211, -0.126] | J better |
| seconds/question | 132.340 | 20.677 | -111.664 | [-127.080, -96.572] | J better |

Mean Jev $/question in J: 0.0856; items screened/question: 1000.

Accuracy discordant pairs: A-only correct 4, J-only correct 4, exact McNemar p = 1.000.


## Arm J vs A, paired (n=62, fresh questions only (not in the 38-question probe))

| endpoint | A | J | J − A | 95% CI | verdict |
| --- | ---: | ---: | ---: | --- | --- |
| accuracy | 0.935 | 0.968 | +0.032 | [-0.032, +0.097] | no clear difference |
| $/question | 0.295 | 0.136 | -0.159 | [-0.214, -0.108] | J better |
| seconds/question | 130.460 | 21.410 | -109.050 | [-130.474, -89.642] | J better |

Mean Jev $/question in J: 0.0855; items screened/question: 1000.


## Held-out answers (no supporting document)

| arm | n | no answer | declined in words | gave an answer | median stated confidence | median Jev p(act) | answers with self ≥ 0.5 | answers with Jev ≥ 0.5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A.holdout | 30 | 3 | 19 | 8 | 0.25 | 0.10 | 0 | 0 |
| J.holdout | 50 | 5 | 37 | 8 | 0.35 | 0.10 | 3 | 1 |
