# Jev gate vs self-confidence (pre-registered)

Same answers, two scorers: `jev` = post-hoc gate p(act), `self` = stated confidence. AURC is lower-better. Δ = AURC(jev) − AURC(self), 95% paired bootstrap CI.

| set | n | errors | AURC jev | AURC self | Δ | 95% CI | verdict | AUROC jev | AUROC self | acc@cov0.8 jev | acc@cov0.8 self |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |
| A (primary) | 10 | 1 | 0.010 | 0.010 | +0.000 | [+0.000, +0.000] | no clear difference | 1.000 | 1.000 | 1.000 | 1.000 |
| B | 10 | 2 | 0.031 | 0.031 | +0.000 | [+0.000, +0.000] | no clear difference | 1.000 | 1.000 | 1.000 | 1.000 |
| A + held-out (co-primary) | 10 | 1 | 0.010 | 0.010 | +0.000 | [+0.000, +0.000] | no clear difference | 1.000 | 1.000 | 1.000 | 1.000 |
| A+B | 20 | 3 | 0.018 | 0.016 | +0.003 | [+0.000, +0.018] | no clear difference | 0.980 | 1.000 | 1.000 | 1.000 |

Label audit: same answer, different judge label on 0 question(s).

## Arm B vs A, paired (n=10)

| endpoint | A | B | B − A | 95% CI | verdict |
| --- | ---: | ---: | ---: | --- | --- |
| accuracy | 0.900 | 0.800 | -0.100 | [-0.300, +0.000] | no clear difference |
| $/question | 0.254 | 0.299 | +0.044 | [-0.010, +0.101] | no clear difference |
| seconds/question | 119.593 | 143.471 | +23.878 | [+6.660, +43.092] | B worse |

Accuracy discordant pairs: A-only correct 1, B-only correct 0, exact McNemar p = 1.000.
Mean Jev $/question in B: 0.0190; items screened/question: 212.
