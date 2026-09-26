# Phase 1: an RLM with Jev tools on BrowseComp-Plus (1K documents)

This phase tests Jev at big-corpus scale with a frontier model. Each of 100 questions comes with 1,000 docs (~8M tokens). The metric is answer accuracy, and the comparator is Sonnet 5. The status is in [`../FINDINGS.md`](../FINDINGS.md). The raw data is in `results/phase1_rlm/`.

## Run map

Every Phase 1 run. All questions come from the 1K set (`fixtures/browsecomp_plus_1k/`). The main questions are 1–100, where the answer docs are present. The held-out questions are 101–150, where they are removed. Raw rows are in `results/phase1_rlm/`.

"Jev check" is the post-hoc question "do the cited docs support this answer?", asked after every answer. The code calls it the gate (`verify_gate`, `gate_post`).

| Run | Arm(s) | Questions | n | Harness | Jev's role | Measures | Status | Cost | File |
| --- | --- | --- | ---: | --- | --- | --- | --- | ---: | --- |
| Haiku pilot | RLM arms A, B | main | 9, 11 | v1, Haiku root | RLM arm B: in-loop tools | does it run | failed (no convergence) | $28.57 | `haiku_pilot/` |
| Sonnet smoke + pilot | RLM arms A, B | main 1–10 | 10, 10 | v1 | RLM arm B: in-loop tools | does it run | done | $5.84 | `sonnet_pilot/` |
| Main full run | RLM arms A, B | main 1–100 | 100, 100 | v1 (20 turns) | RLM arm B: in-loop tools (`jev_screen`, `jev_decide`) | accuracy, $, time (B vs A) | done | $64.85 | `A.jsonl`, `B.jsonl` |
| RLM arm B2 probe | RLM arm B2 | RLM arm B's 22 capped | 22 | v1 | one-call `jev_shortlist` tool | recovers capped questions? | done | $14.62 | `B2.jsonl` |
| Capped reruns | RLM arms A, B | questions that hit the v1 cap | 17, 22 | v2 (30 turns, no-code final turn) | RLM arm B: in-loop tools | B vs A with the harness fixed | done | $37.18 | `A.capfix.jsonl`, `B.capfix.jsonl` |
| Jev check (post-hoc) | all arms | every answered row | — | — | Choice "do the cited docs support this answer?" + Noul per cited doc | Jev check vs the model's stated confidence | done for all finished rows | ~$0.1 | `gate_post` field |
| Reader arm J probe | reader arm J | main: first 30 + 8 hard | 38 | reader | the Jev screen that picks Sonnet's 8 docs | J vs A, exploratory | done | $4.9 | first 38 rows of `J.jsonl` |
| Reader arm J full run | reader arm J | main 1–100 | 100 | reader | the Jev screen | J vs A: accuracy, $, time | done | $13.62 | `J.jsonl` |
| RLM arm A held-out | RLM arm A | held-out 101–120, extension to 101–130 | 20 → 30 | v2, 800k tokens | Jev check only | declines vs guesses; Jev check vs stated confidence | done (30) | $35.7 | `A.holdout.jsonl` |
| Reader arm J held-out | reader arm J | held-out 101–120, extension to 101–150 | 20 → 50 | reader | the Jev screen, plus the Jev check | declines vs guesses | done (50) | $7.88 | `J.holdout.jsonl` |
| BM25 control | reader arm K (BM25 reader) | main 1–100 | 100 | reader | none (BM25 ranks) | does the Jev screen matter? | replaced by a free recall check: BM25 top 8 holds gold on 49/100 vs Jev 94/100; reader arm K not run | $0 | `RANKER_RECALL.md` |

## Setting and pilots

The setting follows the RLM paper §3.1: 150 of the 830 queries, each with 1,000 corpus docs that always include its gold and evidence docs (~7–9M tokens). The draw is seeded here (`scripts/build_browsecomp_plus_1k.py`, `fixtures/browsecomp_plus_1k/`). It is not the paper's sample.

The root LM writes Python in a Docker REPL where `context` is {docid: text}. RLM arm A has `llm_query` only. RLM arm B adds `jev_screen` and `jev_decide`. These call a host-side proxy so the Typesafe key stays out of the container. Answers use the BrowseComp-Plus response format and its judge template. Haiku was the judge in the pilots; Sonnet 5 is the judge from the main full run on. Pilot limits per question: at most 20 iterations, 500k tokens, 15 min.

`must_cite_rlm/rlm_jev.py` patches two rlms 0.1.3 Anthropic-client bugs. It read `content[0].text`, which breaks on thinking blocks and empty content. It also sent a trailing assistant message on the out-of-iterations step.

| run | arm | n | accuracy | gold cited | $/q | s/q | note |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Haiku root pilot | RLM arm A | 9 | 1/9 | — | 1.97 | — | most runs hit 30 iterations or 15 min; rlms IndexError on the final step |
| Haiku root pilot | RLM arm B | 11 | 4/11 | — | 0.98 | — | same failures; ran past the $8 per-arm cap (checked only between questions) |
| Sonnet root pilot | RLM arm A | 10 | 0.900 | 1.000 | 0.254 | 120 | no errors |
| Sonnet root pilot | RLM arm B | 10 | 0.900 | 0.900 | 0.299 | 143 | Jev $0.019/q; 212 items screened/q |

Sonnet pilot read. Both RLM arms reach 9/10 at ~$0.25–0.30/q. For reference, the paper's GPT-5 RLM depth-1 reached 91.3% at $0.99/q on its own 150. In RLM arm B, `jev_decide` ran on 8/10, said act on 8, and all 8 were correct. By stated confidence, RLM arm A is 0.88 at coverage 0.75 and RLM arm B is 1.00. With one miss per arm, none of this separates the arms. Sonnet uses Jev as a first-pass filter, then plain string search, and rarely calls `llm_query`. Files: `results/phase1_rlm/sonnet_pilot/` and `results/phase1_rlm/haiku_pilot/`.

## Rules set before the main full run (2026-09-25)

Runs: RLM arms A and B on the first 100 questions (the main questions), then RLM arm A (and RLM arm B if chosen) on the 50 held-out questions (`fixtures/browsecomp_plus_1k/holdout.jsonl`). The held-out questions are 101–150 with their gold and evidence docids swapped for random corpus docs, so no question is in both sets.

Deviation, 2026-09-25, during the run: the plan was 150 main questions, with the held-out set drawn from the first 50. the project owner cut the main questions to 100 to save spend and moved the held-out set to the disjoint last 50. At that point only per-arm progress counts had been seen (RLM arm A 35 done, RLM arm B 27 done). No A-vs-B or Jev check comparison had been computed.

Setup: Sonnet 5 root, Haiku sub-calls, and a Sonnet 5 judge (`claude-sonnet-5`, thinking off). The switch from the Haiku judge is because it flipped an identical answer between arms in the pilot. The Jev check runs on every row. RLM arm B's prompt no longer tells the model to lower its confidence when jev_decide does not act. Jev screen batches run 8 at a time (1,000 docs in 11.9 s, was ~90 s).

The analysis is `scripts/analyze_rlm_jev.py`, and its docstring is the rule:

1. Does Jev in the loop help (RLM arm B vs A)? Paired over questions: B − A in accuracy, $/question, and wall seconds/question, each with a 95% paired bootstrap CI (10,000 resamples, seed 20260925). The verdict is "B better" or "B worse" only when the whole CI is on one side of 0. Accuracy also gets the exact McNemar test. Pilot (n=10, sequential screen): accuracy −0.10 [−0.30, 0], $ +0.044 [−0.010, +0.101], seconds +23.9 [+6.7, +43.1] (B worse).
2. Does the Jev check beat stated confidence? On the same answers: AURC(Jev check p(act)) − AURC(stated confidence), with a 95% paired bootstrap CI. Primary: RLM arm A, which never saw Jev. Co-primary: RLM arm A on the main questions plus RLM arm A on the held-out questions. Every held-out row counts as should-not-act even when the judge marks it correct, because no document supports it. This co-primary rule was added before any full-run data. An abstained row scores 0 under both scorers. On the pilot, both scorers ranked its 1–2 errors perfectly.
3. Label audit. Any question where both arms gave the same normalized answer but got different labels is listed and reviewed by hand before the verdicts are quoted.

Power: at ~90–95% accuracy, 100 questions give ~5–10 errors per arm. Accuracy differences under ~10 points will likely read "no clear difference". Cost and time differences are per-question and measurable at this n.

## Main full run result, harness v1 (100 questions per arm, 2026-09-25)

Verdicts under the rules above (`results/phase1_rlm/ANALYSIS.md`). The label audit found 0 flips. A = RLM arm A, B = RLM arm B.

| endpoint | A | B | B − A | 95% CI | verdict |
| --- | ---: | ---: | ---: | --- | --- |
| accuracy | 0.940 | 0.840 | −0.100 | [−0.160, −0.050] | B worse (A-only correct 10, B-only 0, McNemar p = 0.002) |
| $/question | 0.301 | 0.341 | +0.041 | [+0.008, +0.074] | B worse |
| seconds/question | 132 | 142 | +9.7 | [−2.0, +21.3] | no clear difference |

Jev check vs stated confidence, same answers:

| set | AURC jev | AURC self | Δ | 95% CI | verdict | AUROC jev / self |
| --- | ---: | ---: | ---: | --- | --- | --- |
| A (primary) | 0.019 | 0.009 | +0.010 | [+0.000, +0.032] | no clear difference | 0.839 / 0.906 |
| A+B | 0.021 | 0.013 | +0.008 | [+0.000, +0.018] | stated confidence wins | 0.910 / 0.950 |

The co-primary (RLM arm A plus held-out) waits for the held-out run. Total spend ≈ $60.

Exploratory read (not one of the planned tests). RLM arm B's accuracy loss is mostly the 20-iteration cap. RLM arm B takes more Sonnet turns (median 13.5 vs 11) because the Jev tools and the required jev_decide add steps. RLM arm B hit the cap on 22 questions (RLM arm A 17) and salvaged a correct answer on 7 of them (RLM arm A 12). That left 14 rows with no answer (RLM arm A 7). Among questions RLM arm B answered, almost all were right. Of RLM arm B's 10 B-only misses, 9 have no answer, and in 6 of those RLM arm B never called Jev.

So this run measures "Jev tools as prompted, under a 20-iteration budget", not the quality of the Jev screen. jev_screen ranked the gold docs near the top (6 of 7 in the top 6 on the timing check). A test with a larger iteration budget or an optional jev_decide would be a new run with its rules set in advance, not a re-read of this one.

## Probe: RLM arm B2 on RLM arm B's capped questions (exploratory, 2026-09-25)

RLM arm B2 is RLM arm B with `jev_screen` replaced by `jev_shortlist(question, context, k)`. One call screens every document and returns the top k with docid, score, and an 800-char snippet. Everything else matches RLM arm B, including the 20-iteration cap and the required jev_decide. It ran on the 22 questions where RLM arm B hit the cap (`results/phase1_rlm/B2.jsonl`, $14.62).

| RLM arm | correct | no answer | capped | $/q | s/q |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 17/22 | 4 | 12 | 0.521 | 195 |
| B | 7/22 | 12 | 22 | 0.649 | 239 |
| B2 | 13/22 | 7 | 15 | 0.662 | 199 |

RLM arm B2 vs B: 7 B2-only correct, 1 B-only. Part of that gain is selection. These questions were picked because RLM arm B failed on them, so a plain RLM arm B rerun would also improve. RLM arm B2 still trails RLM arm A (13 vs 17) at a higher cost ($0.66 vs $0.52). These are hard questions for both arms (RLM arm A also capped on 12), and RLM arm A salvages more of its capped runs. RLM arm B2 used jev_shortlist on 15 of 22 and jev_decide on 14.

Read: the one-call shortlist removes part of the turn cost, but not enough to beat RLM arm A on these questions. The untested lever is the cap-salvage and turn-budget fixes, for both arms.

## Harness v2 and capped reruns (recorded before running, 2026-09-25)

Harness v2 applies to both RLM arms. The turn cap goes from 20 to 30. The 500k-token and 15-min limits stay. rlms' out-of-iterations prompt becomes an explicit no-code final turn (`FINAL_TURN` in `must_cite_rlm/rlm_jev.py`). On the capped questions, the v1 prompt often got code back instead of an answer.

v2 only changes a run that reaches 20 turns, so only the capped questions are rerun: RLM arm A's 17 and RLM arm B's 22 (original RLM arm B, not B2). Results go to `A.capfix.jsonl` / `B.capfix.jsonl`. `scripts/analyze_rlm_jev.py --patch capfix` writes `ANALYSIS.capfix.md` with the same verdict rules. The v1 result above stays the record of the main full run.

Caveat: a capped rerun is a fresh draw, so a capped question can now finish under 20 turns by chance. Both arms get the same treatment.

On harness v2, the 500k-token limit binds before 30 turns on the hardest questions. rlms stops those runs with no final-answer step (a TokenLimitExceededError row with no answer). the project owner accepted that as "no answer" for both arms.

RLM arm A on the held-out questions then runs on harness v2 with an 800k-token limit (`--max-tokens 800000`, recorded per row) and a $40 cap. With no supported answer to find, a token-limit stop would be an uninformative no-answer row, and the Jev check test needs the run to finish with an answer.

## Harness v2 result: capped reruns patched in (2026-09-25)

Capped reruns: RLM arm A 17/17 and RLM arm B 22/22 capped questions on harness v2 ($14.99 and $22.19). Paired over 100 questions with those rows swapped in, using the same endpoints and rules as the main full run. A = RLM arm A, B = RLM arm B.

| endpoint | A | B | B − A | 95% CI | verdict |
| --- | ---: | ---: | ---: | --- | --- |
| accuracy | 0.910 | 0.900 | −0.010 | [−0.070, +0.050] | no clear difference (A-only 5, B-only 4, McNemar p = 1.000) |
| $/question | 0.354 | 0.420 | +0.066 | [+0.016, +0.119] | B worse |
| seconds/question | 143 | 152 | +8.6 | [−10.9, +29.3] | no clear difference |

On the capped questions, RLM arm B went from 7/22 to 13/22 correct and RLM arm A from 12/17 to 9/17. Token-limit stops ended with no answer on RLM arm A 3 and RLM arm B 6.

Read: most of the v1 accuracy gap was the harness (the 20-turn cap plus a final step that returned code), not Jev. With the harness fixed, Jev tools neither raise nor lower accuracy and cost ~19% more. A capped rerun is a fresh draw, so the capped-question numbers carry extra variance.

After Typesafe credit was restored, the Jev check was run on these rows (`ANALYSIS.capfix.md`). The Jev check result holds under v2. RLM arm A (primary): AUROC jev 0.872 vs self 0.926, Δ AURC +0.011 [+0.000, +0.034], no clear difference. RLM arms A+B: stated confidence wins. Label audit: 0 flips.

## Held-out run (RLM arm A, harness v2, 800k tokens)

Results go to `results/phase1_rlm/A.holdout.jsonl`.

Deviation, 2026-09-25, during the run: the project owner cut the held-out run from 50 to the first 20 questions because it cost ~$1.17/q. The $40 cap would have stopped it near question 34. At that point 7 questions were done and all 7 had an answer. None had been through the Jev check, so nothing about the Jev check vs stated confidence comparison had been seen. Resumed with `--n 20 --budget 25`. The co-primary set becomes RLM arm A's 100 main answers plus 20 held-out answers, each held-out answer counting as should-not-act.

## Probe: reader arm J, Jev-first reader (recorded before running, 2026-09-25)

Reader arm J (`must_cite_rlm/reader.py`): the Jev screen scores all 1,000 docs (a Noul per doc, first 12,000 chars each). The top 8 go to a single `claude-sonnet-5` call (adaptive thinking, the same answer format). No RLM loop, no Docker.

It runs on the first 30 of the 100 main questions (a random draw). It is compared paired against RLM arm A's harness-v2 rows on the same 30. Same judge, same Jev check. Each row records the Jev screen's top-8 list and whether it holds a gold doc. This is exploratory: B − A style differences with 95% paired CIs are reported, but at n=30 they are not a verdict. Cap $10. Question: does the Jev screen plus one call get near the RLM's accuracy at a fraction of its cost and time?

Stratification, added 2026-09-25 after 23 of the 30 reader arm J rows had finished (only row counts seen, no reader arm J correctness). "Hard" means the 27 main questions where RLM arm A or B hit the v1 20-turn cap. "Easy" means the other 73. The first 30 hold 7 hard and 23 easy. The hard stratum is topped up to 15 with the next 8 hard questions in the same random order (356, 1226, 592, 254, 928, 371, 470, 1193), for 38 reader arm J rows in total. Report J − A per stratum (RLM arm A uses its harness-v2 rows). The overall estimate uses only the random first 30.

### Reader arm J probe result (exploratory, 38 questions, $4.9)

J − A, paired. A = RLM arm A, using its harness-v2 rows. J = reader arm J. Bracketed ranges are 95% paired-bootstrap CIs.

| Stratum | n | Accuracy A / J | J − A | $/q A / J | Seconds A / J | Gold in Jev top 8 |
| --- | ---: | --- | --- | --- | --- | ---: |
| Random first 30 (overall) | 30 | 0.900 / 0.867 | −0.033 [−0.167, +0.067] | 0.327 / 0.129 (J better) | 139 / 19 (J better) | 28/30 |
| Easy | 23 | 1.000 / 0.957 | −0.043 [−0.130, 0.000] | 0.212 / 0.127 (J better) | 100 / 17 (J better) | 23/23 |
| Hard (RLM arm A or B hit the v1 cap) | 15 | 0.800 / 0.800 | 0.000 [−0.200, +0.200] | 0.572 / 0.133 (J better) | 214 / 23 (J better) | 11/15 |

- No errors. Reader arm J answered every question. Overall, A-only correct 2 and J-only correct 1. Of reader arm J's 4 misses in the first 30, 2 had no gold doc in the Jev top 8 (screening misses) and 2 had one (reading misses).
- About two-thirds of reader arm J's cost is the Jev screen ($0.087 of $0.13/q). The single Sonnet call is ~$0.04.
- Read: the Jev screen plus one Sonnet call shows no accuracy loss we can detect against the Sonnet RLM, at ~40% of its cost and ~1/7 of its time. The gap is largest on hard questions (4.4× cheaper, 9× faster, same 0.80). At n=30 the accuracy CI still allows a loss of up to ~17 points, so this calls for a full run, not a claim.

## Reader arm J full run and held-out (rules set before the run, 2026-09-25)

Decided after the 38-question probe above looked promising. Rules:

1. Main comparison: reader arm J vs RLM arm A (harness-v2 rows) on all 100 main questions. Same paired endpoints and verdict rules as RLM arm B vs A: accuracy, $/question, seconds; 95% paired-bootstrap CI; exact McNemar for accuracy.
2. The 38 probe questions were seen before the decision to run the full set. The estimate on only the 62 fresh questions is reported alongside. If a conclusion holds only with the probe included, it is flagged.
3. Accuracy is reported as the J − A difference with its 95% CI. A 5-point margin was also planned. It was dropped from the reporting on 2026-09-25 in favor of the plain CI, which is unchanged.
4. Held-out: reader arm J on the same first 20 held-out questions as RLM arm A (`J.holdout.jsonl`). Report how often reader arm J answers, its stated confidence, and the Jev check p(act) on those answers, next to RLM arm A's held-out results.

Caps: reader arm J main $15 (including the probe's $4.9), reader arm J held-out $4.

### Reader arm J full run result (2026-09-25)

100 main questions ($13.62 total for reader arm J main) plus 20 held-out ($2.89). No errors. A = RLM arm A (harness-v2 rows), J = reader arm J.

| Set | n | Accuracy A / J | J − A [95% CI] | $/q A / J | Seconds A / J |
| --- | ---: | --- | --- | --- | --- |
| All 100 | 100 | 0.910 / 0.940 | +0.030 [−0.030, +0.090] | 0.354 / 0.133 (J better) | 143 / 21 (J better) |
| Fresh 62 (not in the probe) | 62 | 0.903 / 0.968 | +0.065 [0.000, +0.145] | 0.354 / 0.136 (J better) | 142 / 21 (J better) |

A-only correct 3, J-only correct 6 (McNemar p = 0.508). The result holds on the fresh questions alone, so it doesn't depend on the probe that motivated the full run. The Jev top 8 held a gold doc on 94/100. Of reader arm J's 6 misses, 3 were screening misses (no gold in the top 8) and 1 had no answer. Jev is $0.086 of reader arm J's $0.133/q. Against RLM arm A's harness-v1 accuracy (0.94), reader arm J ties.

Held-out (20 questions, no supporting doc): reader arm J declined on 18 ("Cannot be determined from the provided documents", 0% confidence). It gave an answer on 2 (stated confidence 0.15 and 0.55; Jev check p(act) 0.06 and 0.26). The judge accepted 1 from model memory.

### Held-out and Jev check co-primary result (2026-09-25)

RLM arm A held-out: 20 questions, $24.25 (≈$1.21/q), harness v2, 800k tokens. Scored with the same Jev check. From `ANALYSIS.capfix.md`, which uses RLM arm A's v2 rows:

| Set | n | Errors | AUROC Jev / self | Δ AURC [95% CI] | Verdict |
| --- | ---: | ---: | --- | --- | --- |
| RLM arm A (primary) | 100 | 9 | 0.872 / 0.926 | +0.011 [0.000, +0.034] | no clear difference |
| RLM arm A + held-out (co-primary) | 120 | 29 | 0.910 / 0.955 | +0.016 [+0.003, +0.037] | stated confidence wins |
| RLM arms A + B | 200 | 19 | 0.886 / 0.939 | +0.008 [+0.001, +0.019] | stated confidence wins |

Held-out behavior, no supporting document:

| Arm | n | No answer | Declined | Gave an answer | Answers with self ≥ 0.5 | Answers with Jev ≥ 0.5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| RLM arm A (Sonnet RLM) | 20 | 2 | 13 | 5 | 0 | 0 |
| Reader arm J (Jev-first reader) | 20 | 0 | 18 | 2 | 1 | 0 |

Read: the Jev check claim fails. On this benchmark Sonnet 5 does not make confident unsupported guesses. It declines or answers at low stated confidence. A post-hoc Jev check has nothing to add, and Sonnet's stated confidence ranks errors better. Label audit: 0 flips.

## Held-out extension (decided 2026-09-25, after the 20-question results)

Extension: the project owner extended the held-out runs after seeing the 20-question results. Reader arm J goes to all 50 held-out questions and RLM arm A to the first 30. The 20-question Jev check verdict above stays the result of record. The larger sets are reported next to it as an extension decided after seeing results. Caps: RLM arm A held-out $38 total (was $24.25 spent), reader arm J held-out $8 total (was $2.89 spent). Same harness v2, 800k-token limit for RLM arm A, same judge and Jev check.

### Reader arm J held-out, all 50 questions (extension, 2026-09-25)

Reader arm J declined on 37 of 50 and gave an answer on 8 (stated confidence 0.15–0.78; the Jev check scored 1 of the 8 at ≥ 0.5). The judge accepted 2 from model memory, with no supporting document.

The other 5 have no answer. Sonnet spent its whole 16,000-token output budget on reasoning and wrote no text (questions 270, 718, 126, 1085, 895). The same limit hit 1 main question (884, already a reader arm J miss with no gold in the top 8).

Cost $7.88 (≈$0.16/q), median 16 s. In these runs Sonnet saw only which 8 docs the Jev screen picked and their order, never the Jev scores. The reader now saves the top-8 scores and has three options, all off by default and not yet run: `--show-jev-scores`, `--jev-reject-below`, `--reader-max-output`.

### Held-out extension result (2026-09-25; decided after the 20-question results)

Jev check co-primary, RLM arm A's 100 main answers plus held-out:

- With 20 held-out (result of record): AUROC Jev 0.910 vs self 0.955, Δ AURC +0.016 [+0.003, +0.037].
- With 30 held-out: AUROC 0.912 vs 0.958, Δ +0.019 [+0.005, +0.039].

Stated confidence wins both ways.

Held-out behavior on the same 30 questions, plus reader arm J on all 50:

| Arm | n | Declined | No answer | Gave an answer | Answers with self ≥ 0.5 | Answers with Jev ≥ 0.5 | Judged correct from memory | $/q | Median s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| RLM arm A (Sonnet RLM) | 30 | 19 | 3 | 8 | 0 | 0 | 2 | 1.19 | 276 |
| Reader arm J (Jev-first reader) | 30 | 25 | 0 | 5 | 2 | 1 | 1 | 0.14 | 16 |
| Reader arm J, all 50 | 50 | 37 | 5 | 8 | 3 | 1 | 2 | 0.15 | 16 |

Both arms mostly decline. Reader arm J declines more often and costs ~1/8 as much. But on 2 of 30 it answered at ≥ 50% stated confidence, where RLM arm A never did. RLM arm A spent ~4.6 min per question searching before declining.

## Reader arm K: BM25 reader control (rules set before the run, 2026-09-25)

Why: in the 1K set, the ~9 gold and evidence docs sit among ~990 random corpus docs, so plain lexical retrieval may already find them. If BM25 top 8 plus one Sonnet call matches reader arm J, the reader arm J result means "skip the RLM", not "use Jev". Jev is two-thirds of reader arm J's cost.

Reader arm K is identical to reader arm J except the ranking. BM25 (`arms._bm25_scores`, k1 1.2, b 0.75, statistics within the question's 1,000 docs, full document text) picks the top 8 in place of the Jev screen. Same prompt (first 12,000 chars per doc), same `claude-sonnet-5` call and 16k output cap, same judge, same Jev check. No Jev during the run. Runs: main 1–100 (`K.jsonl`) and held-out 101–150 (`K.holdout.jsonl`). Caps: $8 main, $4 held-out.

Rules:
1. Primary: reader arm J vs K on the 100 main questions (accuracy, $/question, seconds), same paired 95% CI rules. "Jev adds value over BM25 on accuracy" only if the whole J − K accuracy CI is above 0.
2. Held-out: declined / no answer / answered counts for reader arms J and K on the same 50. "Jev declines better" is reported descriptively (n=50 is small).
3. Secondary: reader arm K vs RLM arm A on the 100 main questions, and how often each ranker's top 8 holds a gold doc.

### Reader arm K outcome: replaced by a free retrieval check (2026-09-25)

Before any reader arm K run, the project owner chose not to run it and to use a free, no-API check as the control. `scripts/ranker_recall.py` recomputes BM25's top 8 over each main question's 1,000 docs and compares it with the recorded Jev screen top 8 (`RANKER_RECALL.md`):

| Set | n | Top 8 holds a gold doc: BM25 | Jev |
| --- | ---: | ---: | ---: |
| All | 100 | 49 | 94 |
| Hard | 27 | 10 | 23 |
| Easy | 73 | 39 | 71 |

Both 48, Jev only 46, BM25 only 1, neither 5. Even in the 1K set, where the gold and evidence docs sit among ~990 random docs, keyword ranking misses the answer doc on half the questions, and Jev finds 45 more. So the reader arm J result comes from the Jev screen, not only from dropping the RLM loop.

Caveat: this is retrieval, not answer accuracy. Sonnet can sometimes answer from non-gold evidence docs, so reader arm K's accuracy would be somewhat above 49%. It was not measured. A modern embedding retriever (the BrowseComp-Plus paper's Qwen3-Embed-8B) is the stronger untested control. Reader arm K stays in the code (`--arm K`), not run.
