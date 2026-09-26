# RLM + Jev on BrowseComp-Plus (1K documents)

Questions finished by both arms: 10. Root `claude-sonnet-5`, llm_query sub-calls `claude-haiku-4-5`, depth 1, Docker REPL. Accuracy uses the BrowseComp-Plus judge template with Haiku as the judge.

| arm | accuracy | gold cited | $/q RLM | $/q Jev | $/q total | s/q | errors | acc @ cov 0.25 / 0.50 / 0.75 / 1.00 (by confidence) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 0.900 | 1.000 | 0.2544 | 0.0000 | 0.2544 | 120 | 0 | 1.00 / 1.00 / 1.00 / 0.90 |
| B | 0.800 | 0.900 | 0.2799 | 0.0190 | 0.2989 | 143 | 0 | 1.00 / 1.00 / 1.00 / 0.80 |

Arm B made a jev_decide call on 8/10 questions and screened 212 items per question on average.
Arm B gated by its last jev_decide (route act): coverage 0.80, accuracy 1.00.
Arm B accuracy @ coverage 0.25 / 0.50 / 0.75 / 1.00 by jev p_act: 1.00 / 1.00 / 1.00 / 0.80.
