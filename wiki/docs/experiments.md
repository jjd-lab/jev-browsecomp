---
type: experiment
title: Experiment ledger
description: Every finished experiment, with its size, what Jev was compared against, the result, and the lesson.
tags: [experiments, browsecomp-plus, jev, rlm]
timestamp: 2026-09-25
---

# Experiment ledger

Finished results only. [`results/FINDINGS.md`](../../results/FINDINGS.md) and its per-phase files hold the full numbers, the rules set before each run, and every deviation. Terms follow the [glossary](glossary.md).

## How to read a result

Check two things before reading a result as evidence about Jev: how large the run was, and what Jev was compared against.

| Setting | Rows | Size per question | Metric | Jev compared against | Outcome |
| --- | --- | --- | --- | --- | --- |
| Hotpot slice and BC+ pack | 0.1–0.5 | 23 q; 150 q × ~9 docs | gold cited | Haiku as the decider; BM25 or overlap ranking | Jev beats Haiku (0.4) |
| Full corpus | 0.6–0.8 | 150 q × 100,195 docs (BM25 top 100 ≈ 3M tokens) | gold cited | flat BM25; Haiku writing searches | Jev beats flat BM25 (0.6) |
| 1K set, Jev inside the RLM | 1.3, 1.6 | 100 q × 1,000 docs (≈ 8M tokens) | accuracy | RLM arm A (Sonnet 5 alone) | Accuracy tie; RLM arm B costs more |
| 1K set, Jev check | 1.4, 1.9 | 100 main + 20–30 held-out q | error ranking | Sonnet's stated confidence | Stated confidence wins |
| 1K set, Jev in front of one call | 1.7, 1.8, 1.10 | 100 main + 50 held-out q | accuracy, $, time; gold in top 8 | RLM arm A; BM25 ranking | Same accuracy at 38% of the cost and 1/7 of the time; Jev's top 8 holds gold on 94/100 vs BM25's 49/100 |
| Pilots and probes | 1.1, 1.2, 1.5 | 10–22 q | mixed | — | Direction only |

Until reader arm J (1.7, 1.8), every Jev win was against a weaker comparator. Scale does not separate wins from losses: the Jev screen held up on the full corpus (0.6). What matters is the comparator and where Jev sits. Inside the RLM loop, Jev adds cost without adding accuracy (1.3, 1.6). In front of a single Sonnet call, it holds accuracy at a fraction of the cost (1.8), and the Jev screen is why (1.10). Phase 0 wins measure gold cited; Phase 1 results measure accuracy.

Stated confidence is the number Sonnet writes after "Confidence:", not a logprob. Every answered row has one (94/94 in RLM arm A, 92/92 in RLM arm B; median 85%). Most wrong answers already say 45% or lower, and each arm has only 5–6 answered-but-wrong main questions. So the Jev check has little to gain on main questions, and the held-out questions carry that test.

## Phase 0: Hotpot slice and BC+ pack

| # | Tested | Result | Verdict | Lesson |
| --- | --- | --- | --- | --- |
| 0.1 | Pack arm B (tree walk) vs pack arm C (flat), Hotpot slice | Both ~0.74 gold cited; C 12× cheaper | Tie | Citing by id works. A tree adds nothing on small inputs. |
| 0.2 | Ranker for pack arm C, BC+ pack | Gold cited 0.23 (overlap) → 0.31 (BM25); repeat 0.30 | Ranker was the bottleneck | Fix what feeds the decider first. |
| 0.3 | Jev decide, precision vs coverage, gold removed | Precision ~0.83 at 36% coverage; acts on 6% of questions with gold removed | Jev refuses well | Report precision vs coverage, not exact match alone. |
| 0.4 | Jev decide vs Haiku making the same decision | Precision 0.79 vs 0.59 at matched coverage; 28× cheaper, 3× faster | Jev wins | The gap is calibration: Haiku gives p(act) ≥ 0.95 on half of questions. |
| 0.5 | Candidates per Jev decide (k = 3, 5, 8) | Gold cited 0.30 → 0.46; precision ~0.80 | More candidates help | Jev's input cap is about 32–42k tokens. |

## Phase 0: full corpus

| # | Tested | Result | Verdict | Lesson |
| --- | --- | --- | --- | --- |
| 0.6 | Corpus arm R (Jev screen of the BM25 top 100) vs corpus arm flat (top 8) | Gold cited 0.12 vs 0.03; the Jev screen kept gold in the final 8 on 33/33 | Jev screens without loss | BM25 recall@100 from the raw question (0.22) is the ceiling. |
| 0.7 | Corpus arm H (Haiku writes searches, Jev decides) | Gold cited 0.27; precision 0.83 at 20% coverage; $0.04/q | Search is the lever | Rewriting queries needs a generative model; Jev can't write queries. |
| 0.8 | Corpus arm N (two-chunk re-decide) | 0.29 vs 0.27, within run variance | Null | More text per doc doesn't fix the pick. |

## Phase 1: 1K set with Sonnet 5

| # | Tested | Result | Verdict | Lesson |
| --- | --- | --- | --- | --- |
| 1.1 | Haiku as the RLM root (pilot) | Most runs hit 30 turns or 15 min | Haiku can't drive the RLM | The root model has to be strong. |
| 1.2 | Sonnet 5 RLM (pilot, 10 q) | RLM arms A and B both 9/10 at ~$0.25–0.30/q | Works | The paper's GPT-5 RLM: 91.3% at $0.99/q on its own sample. |
| 1.3 | RLM arm B vs A, 100 main q, harness v1 | Accuracy 0.84 vs 0.94 (p = 0.002); $0.34 vs $0.30/q | B worse | Jev tool calls use root turns. Arm B hit the 20-turn cap more often and lost answers there. |
| 1.4 | Jev check vs stated confidence, main q | RLM arm A AUROC 0.87 vs 0.93 (v2 rows); A+B pooled favors stated confidence | Jev check does not win | Sonnet 5 is already calibrated when the answer exists. |
| 1.5 | RLM arm B2 (one-call shortlist), probe on B's 22 capped q | 13/22 vs B 7/22 vs A 17/22 | Partial fix | Spending fewer turns helps, but not enough to beat plain search. |
| 1.6 | Harness v2 (30 turns, no-code final turn), capped reruns | Accuracy 0.91 vs 0.90; $0.35 vs $0.42/q | Accuracy tie, arm B costs more | Most of the v1 gap was the harness. Jev tools add cost, not accuracy. |
| 1.7 | Reader arm J vs RLM arm A, probe on 30 random + 8 hard q | Random 30: accuracy 0.87 vs 0.90 (no clear difference), $0.13 vs $0.33/q, 19 vs 139 s. Hard 15: 0.80 vs 0.80, $0.13 vs $0.57, 23 vs 214 s | Cheaper and faster, no detected accuracy loss | Worth a full run; at n=30 the accuracy CI still allowed a ~17-point loss. |
| 1.8 | Reader arm J vs RLM arm A, full run on 100 main q; J on 50 held-out q | Accuracy 0.94 vs 0.91 with harness v2 (+3 points, 95% CI −3 to +9) or 0.94 with v1 (tie); $0.13 vs $0.35/q; 21 vs 143 s; the same on the 62 questions outside the probe. Held-out: J declined on 37 of 50 | Arm J wins on cost and time; accuracy the same | The Jev screen in front of one Sonnet call replaces the RLM's search loop. |
| 1.9 | Jev check vs stated confidence, RLM arm A's 100 main + held-out answers | 20 held-out: AUROC 0.910 vs 0.955, Δ AURC +0.016 [+0.003, +0.037]. 30 held-out (extension): 0.912 vs 0.958 | Stated confidence wins | Sonnet 5 doesn't answer confidently when no document supports an answer, so the Jev check has little to catch. |
| 1.10 | BM25 control: does BM25's top 8 hold a gold doc? (free, no API calls; reader arm K not run) | BM25 49/100 vs Jev 94/100 (hard 10 vs 23, easy 39 vs 71); Jev only 46, BM25 only 1 | The Jev screen is what makes reader arm J work | BrowseComp questions are indirect clues, and keyword ranking misses them even in the 1K set. This is retrieval, not accuracy; an embedding retriever is the untested control. |

### Phase 1 runs at a glance

| Run | Arms | Questions | Jev's role | Result |
| --- | --- | --- | --- | --- |
| Main run + capped reruns | RLM arm A vs RLM arm B | main 1–100 | tools inside the RLM loop | accuracy tie once the harness was fixed; arm B costs more (1.3, 1.6) |
| Reader | reader arm J vs RLM arm A | main 1–100 | Jev screen in front of one Sonnet call | same accuracy, 38% of the cost, 1/7 of the time (1.8) |
| BM25 control | reader arm K (not run) | main 1–100 | none | free recall check: BM25's top 8 holds gold on 49/100 vs Jev's 94/100 (1.10) |
| Held-out | RLM arm A (30) and reader arm J (50) | held-out 101–150 | A: Jev check only; J: Jev screen plus Jev check | both mostly abstain (same 30: A declined 19 and gave no answer on 3, J declined 25); J costs ~1/8; the Jev check does not beat stated confidence (1.9) |

The full run map (question ranges, n, harness, cost, files) is at the top of [`results/findings/phase1_rlm.md`](../../results/findings/phase1_rlm.md).

### Phase 1 across harness versions (100 main q)

| Version | RLM arm | Accuracy | No answer | Hit turn cap | Token-limit stops | $/q | s/q |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| v1 (20 turns) | A | 0.94 | 7 | 17 | 0 | 0.30 | 132 |
| v1 (20 turns) | B | 0.84 | 14 | 22 | 0 | 0.34 | 142 |
| v2 (capped reruns) | A | 0.91 | 6 | 8 | 3 | 0.35 | 143 |
| v2 (capped reruns) | B | 0.90 | 8 | 9 | 6 | 0.42 | 152 |

On B's 22 capped questions: A v1 17/22, B v1 7/22, B2 13/22 ($0.66/q), B v2 13/22 ($1.01/q). On A's 17 capped questions: A v1 12/17 ($0.57/q), A v2 9/17 ($0.88/q). Each rerun is a fresh attempt, so these subsets move by about ±3 questions. The true B − A accuracy gap lies between −10 (v1) and −1 (v2). Either way, Jev tools don't raise accuracy, and they do raise cost.

Phase 1 spend: $208, of which Jev is $18 (9%).
