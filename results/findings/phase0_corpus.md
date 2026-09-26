# Phase 0: the full 100K-doc corpus (Phase 0c steps 5–7)

This file runs the 150 BC+ pack questions against all 100,195 docs in the full corpus. Jev is compared against flat BM25. In corpus arm H, Haiku writes the search queries. The metric is gold cited (`exact_id`), not answer accuracy. The step plan and bars are in [`phase0_pack.md`](phase0_pack.md). Status is in [`../FINDINGS.md`](../FINDINGS.md).

## Timeline (SHA to result)

| when | SHA / PR | finding |
| --- | --- | --- |
| Phase 0c step 5 corpus run | — | `scripts/build_browsecomp_plus_corpus_run.py` ranks all 100,195 docs of `Tevatron/browsecomp-plus-corpus` @ `b27b02b` with pack arm C's BM25 (corpus-level N, df, avgdl; the raw question is the query). The top 100 per query are frozen in `fixtures/browsecomp_plus/corpus_bm25.jsonl`. Texts stay in the gitignored `.cache/`. Gold recall@8 0.087, @100 0.220. |
| Phase 0c step 5 corpus arm R | — | `--suite browsecomp-plus-corpus`, Jev `both`. Corpus arm flat (one Jev decide over the corpus BM25 top 8): gold cited 0.033, $0.000987/q. Corpus arm R (Jev screen of the top 100 → chunk expand of the best 8 → one Jev decide): gold cited 0.120; as decided, coverage 0.153 / precision 0.783 / held-out false-act 0.027; $0.018483/q; 14.8 s of Jev calls per question. Files: `results/phase0_corpus/RISK_COVERAGE.browsecomp-plus-corpus.{flat,recurse}.md`, `results/phase0_corpus/SCOREBOARD.browsecomp-plus-corpus.live.{flat,recurse}{,.holdout}.md` and traces. |
| Phase 0c step 6 corpus arm H | — | `--arm hybrid`: corpus arm R plus 3 search rounds. In each round, `claude-haiku-4-5` reads snippets (1500 chars) of the 5 best screened docs and writes up to 3 keyword queries. Each query's top 20 unseen docs, from a SQLite FTS5 BM25 index of the full corpus (`.cache/`, 4.5 GB), join the Jev screen. Gold cited 0.273; as decided, coverage 0.407 / precision 0.672 / held-out false-act 0.047; $0.038298/q; 28.5 s of calls per question. Files: `results/phase0_corpus/RISK_COVERAGE.browsecomp-plus-corpus.hybrid.md`, `results/phase0_corpus/SCOREBOARD.browsecomp-plus-corpus.live.hybrid{,.holdout}.md` and traces. |
| Phase 0c step 7 corpus arm N | — | `--arm narrow --from-trace <H trace>` replays corpus arm H's final 8. The top 4 by H's Jev decide Noul are re-expanded, and one more `both` Jev decide sees each doc's best 2 chunks in document order. A decide that Jev rejects is retried with each id's text halved. Gold cited 0.287 (H 0.273); as decided, coverage 0.433 / precision 0.662 / held-out false-act 0.060; +$0.001889/q. Files: `results/phase0_corpus/RISK_COVERAGE.browsecomp-plus-corpus.narrow.md`, `results/phase0_corpus/SCOREBOARD.browsecomp-plus-corpus.live.narrow{,.holdout}.md` and traces. |

## Step 5: corpus ranking (no decide yet)

| k | 1 | 3 | 8 | 10 | 20 | 50 | 100 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| gold recall@k | 0.033 | 0.053 | 0.087 | 0.093 | 0.113 | 0.153 | 0.220 |

Evidence recall@100 averages 0.161. Top-100 docs are long (median 62k chars, mean 124k), so one question's top 100 is ~12M chars, far past Jev's input cap. A flat k=8 Jev decide over this ranking can reach at most 0.087 gold cited. Recursing over the top 100 lifts that ceiling to 0.220.

The raw BrowseComp question is an obfuscated multi-hop puzzle, so a single lexical query misses most gold. The larger lever is searching with reformulated queries. That is a generative hop, not typed ID-select.

## Step 5: corpus arm R

| arm | exact_id | as decided cov / prec / held-out false-act | argmax ceiling | $/q |
| --- | ---: | ---: | ---: | ---: |
| flat top 8 | 0.033 | 0.047 / 0.714 / 0.013 | 0.067 | 0.000987 |
| R over top 100 | 0.120 | 0.153 / 0.783 / 0.027 | 0.180 | 0.018483 |

- Bar: the accuracy part is met (+8.7 pts gold cited over corpus arm flat). The cost part is missed: 19× flat, against a bar of ≤ 5×. In absolute terms corpus arm R costs $0.018/q. The same ~20-call recursion with Haiku sub-calls would cost roughly $0.50/q at ~25k input tokens per call. That is an estimate, not a run.
- Where gold is lost: gold is in the BM25 top 100 on 33/150. The Jev screen kept it in the final 8 on 33/33. The final Jev decide cited it on 18/33, made 5 wrong acts overall, and sent the rest to review or abstain.
- Screening is not the bottleneck. Retrieval is the first limit (0.220 recall@100 from one raw-question query). The final Jev decide's 18/33 is the second.
- Calibration holds under recursion: with gold removed, false-act is 0.027 as decided.

## Step 6: corpus arm H

| arm | exact_id | gold in final 8 | cited gold | wrong acts | as decided cov / prec / false-act | prec @ cov ~0.20 / ~0.30 | $/q |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| flat top 8 | 0.033 | — | 5 | — | 0.047 / 0.714 / 0.013 | — | 0.000987 |
| R | 0.120 | 33 | 18 | 5 | 0.153 / 0.783 / 0.027 | 0.700 / 0.556 | 0.018483 |
| H | 0.273 | 83 | 41 | 20 | 0.407 / 0.672 / 0.047 | 0.833 / 0.739 | 0.038298 |

- Search is the lever. Corpus arm H averages 9 queries and 104 added docs per question. Gold reaches the final 8 on 83/150 (corpus arm R: 33). The queries follow the clue chain: on question 6 they move from the raw clues to "Jesuit … Asia" to "Sogang … principal".
- H's curve dominates R's at every coverage R reaches, at about 2× R's cost.
- The as-decided gate is now too loose: 20 wrong acts, precision 0.672. A route p(act) threshold of 0.56 gives precision 0.739 at coverage 0.307, with held-out false-act 0.027.
- The two losses are now about even. Gold is never found on 67/150. On 42/83, gold was in the final 8 and the final Jev decide missed it.
- Claude could put answer entities from its own knowledge into the queries. Search agents work that way, but it means corpus arm H's retrieval gain is not Jev's.

## Step 7: corpus arm N

Result: null. Of the 83 questions where corpus arm H's final 8 held gold, H routed 13 to review with gold as the argmax Noul. On another 29, H ranked a different doc first (gold second on 16). Corpus arm N re-decides with 2 chunks for the top 4; gold is still in that top 4 on 78. Versus H, N gains 12 cites and loses 10, so gold cited moves 0.273 → 0.287. That is inside run variance. Precision at coverage 0.20 drops from 0.833 to 0.633. At 0.30 it is flat (0.739 vs 0.733). More text per doc does not fix the pick.

The gate fix is free and holds on H's traces: acting only when route p(act) ≥ 0.56 gives coverage 0.307, precision 0.739, held-out false-act 0.027 (as decided: 0.407 / 0.672 / 0.047). The threshold was read off the same traces, so it needs a fresh run before it is locked.
