# Phase 0: Hotpot slice and the BC+ pack

This file covers two small question sets: the 23-question Hotpot slice and the 150-question BC+ pack, with about 9 docs per question. Jev is compared against Haiku as the decider and against BM25 ranking. Status and index are in [`../FINDINGS.md`](../FINDINGS.md).

## Pack arms (live, Typesafe on)

| arm | what runs |
| --- | --- |
| pack arm A | Claude quotes free-form per depth-1 section. Quotes must equal `Span.text`. |
| pack arm B | Tree walk plus the same Jev decide. |
| pack arm C | Flat top-3 leaves plus the same Jev decide. |

When `TYPESAFE_API_KEY` is set, Jev decides pack arms B and C, not Claude. The Choice is the global route. Each Noul scores support for one id. On `act`, the cite is the argmax Noul at or above 0.5 (PR5).

## Suite

| suite | role |
| --- | --- |
| Hotpot slice | Cite/id yardstick only. Do not grow it as a long-context substitute. |
| BrowseComp-Plus | Primary suite. The smoke pack is 150 queries from `Tevatron/browsecomp-plus` revision `144cff8e35b5eaef7e526346aa60774a9deb941f`. Pinned shard `data/test-00000-of-00006.parquet`, sha256 `4ff9e93054eaee61b8d079a89b7ec4d02f16c9d05fa6e2fef7185b0786427a3a`. The draw also uses shards `test-00001` through `test-00003` of that revision (eligible pool 165; shard 0 alone has 43 singleton-gold queries). Native docids. |

Smoke scoring (implemented):

- `exact_id` (gold cited): set equality on the one gold docid.
- `cite_ok`: the indexed span equals the quote, and that span is a verbatim slice of the document.
- $/q and latency.

Answer accuracy under the paper protocol is not scored yet. The answer string is recorded in provenance.

Each question's flat pool is every evidence doc plus the first 4 usable negatives in release order. The gold doc is one of the evidence docs. The full ~100K corpus is not in git.

## Timeline (SHA to result)

| when | SHA / PR | finding |
| --- | --- | --- |
| stub, harder gold | PR2 `9fa0940` | Stub pack arm B ≫ pack arm C on planted near-copies. |
| Claude live (old gold) | PR3 `6cea8a3` | Pack arms B ≈ C at ~0.30 gold cited. Pack arm A produced illegal spans. |
| Typesafe rematch (old gold) | — | Jev pack arm B 0.967 vs Claude pack arm C 0.867. |
| Hotpot slice stub | PR4 `496b34d` | Stub pack arm B 0.913 vs pack arm C 0.435 (23-question Hotpot slice). |
| Hotpot live, multi-cite | `496b34d` | Pack arms B = C at 0.391. `cite_ok` 1.0. Pack arm C is ~12× cheaper than pack arm B. |
| autopsy | — | `exact_id` is set equality. Most misses were over-cites (gold ⊂ pred). The stub gap came from singletons. |
| singleton act | PR5 `2ca8b47` | Rematch: pack arm B 0.739, pack arm C 0.826. `cite_ok` 1.0. |
| decode ablation | PR6 `60f638e` | See the table below. Keep `both`. |
| BC+ smoke stub | PR9 `60918bb` | Pack arm C on the 20-query pack: `exact_id_acc` 0.200, `cite_ok` 1.000. Live not run. |
| BC+ pack 150 stub | — | Pack grown to 150 from the pinned revision, shards `test-00000` through `test-00003` (eligible pool 165; Fisher-Yates seed 20260924). Stub pack arm C `exact_id_acc` 0.213, `cite_ok` 1.000. |
| live pack arm C @150, overlap | `eae3f30` | Board produced at that main. Typesafe on, decode `both`, pack arm C, n=150, token-overlap ranker. `exact_id_acc` 0.227, `cite_ok` 1.000, `illegal_span_rate` 0.000, `abstain_rate` 0.167, `cost_usd` 0.000335, `latency_ms` 536.4. Baseline for the BM25 rematch. |
| Phase 0b R1 BM25 stub | — | Pack arm C's default ranker is now Okapi BM25 (k1=1.2, b=0.75) on the same per-question pool (evidence + 4 negatives), full document text. Stub pack arm C `exact_id_acc` 0.207 (31/150), `cite_ok` 1.000, `illegal_span_rate` 0.000, `abstain_rate` 0.000. The prior overlap stub was 0.213 (32/150). The stub decide still picks the unique best token overlap inside the top 3, so this stub under-credits BM25. |
| live pack arm C @150, BM25 | `a6bec4a` | Board produced at that main. Typesafe on, decode `both`, pack arm C, n=150, Okapi BM25 (k1=1.2, b=0.75). `exact_id_acc` 0.313, `cite_ok` 1.000, `illegal_span_rate` 0.000, `abstain_rate` 0.147, `cost_usd` 0.000311, `latency_ms` 531.3. Primary gate (≥ 0.30) met. The stub under-credited BM25 because its decide still picks by overlap inside the top 3. File: `results/phase0_pack/SCOREBOARD.browsecomp-plus.live.md`. |
| Phase 0c step 1 repeat | — | Same BM25 config, rerun with the per-question trace. `exact_id_acc` 0.300, `cite_ok` 1.000, `illegal_span_rate` 0.000, `abstain_rate` 0.160, `cost_usd` 0.000311, `latency_ms` 528.1. Within ±0.03 of 0.313. Files: `results/phase0_pack/SCOREBOARD.browsecomp-plus.live.repeat.md` and `.trace.jsonl`. |
| Phase 0c step 2 risk-coverage | — | Held-out live board (gold dropped from every pool): `abstain_rate` 0.247, $0.000296/q. As decided: coverage 0.360, precision 0.833, held-out false-act 0.060. At coverage 0.40: precision 0.787 / false-act 0.087 ranked by route p(act), 0.689 / 0.140 ranked by max Noul. Files: `results/phase0_pack/RISK_COVERAGE.browsecomp-plus.md`, `results/phase0_pack/SCOREBOARD.browsecomp-plus.live.holdout.md` and `.trace.jsonl`. |
| Phase 0c step 3 Haiku decide | — | `--decider chat`, `claude-haiku-4-5`, same BM25 top 3 and 12000-char prompts. Haiku answers the Jev `both` questions in one structured call. `exact_id_acc` 0.340, `cite_ok` 1.000, `abstain_rate` 0.120, $0.008626/q (28× Jev), latency 1559.8 ms (3× Jev). As decided: coverage 0.607, precision 0.560, held-out false-act 0.340. At coverage 0.407, ranked by max Noul (Haiku's better score): precision 0.590, false-act 0.167. Files: `results/phase0_pack/RISK_COVERAGE.browsecomp-plus.haiku.md`, `results/phase0_pack/SCOREBOARD.browsecomp-plus.live.haiku{,.holdout}.md` and traces. |
| Phase 0c step 4 top-k | — | Jev `both`, BM25, `--top-k` 5 and 8. k=all failed: Jev returns 400 `max_tokens_exceeded` on question 342 (15 docs, ~156k chars), while 17 docs at ~119k chars / 31.7k input tokens passed. k=5: gold cited 0.373, recall@5 109/150, $0.000464/q. k=8: gold cited 0.460, recall@8 142/150, $0.000614/q, 652 ms. Files: `results/phase0_pack/RISK_COVERAGE.browsecomp-plus.k{5,8}.md`, `results/phase0_pack/SCOREBOARD.browsecomp-plus.live.k{5,8}{,.holdout}.md` and traces. |

## Decode ablation (`60f638e`, ~15 min/board)

Artifacts: `results/phase0_hotpot/SCOREBOARD.live.{both,noul_only,choice_per_span}.md`

B and C are pack arms.

| decode | B exact | B $/q | C exact | C $/q | note |
| --- | ---: | ---: | ---: | ---: | --- |
| both | 0.739 | 0.000239 | 0.739 | 0.000019 | Default. |
| noul_only | 0.739 | 0.000233 | 0.696 | 0.000016 | Tiny saving on B. C drops. Reject. |
| choice_per_span | 0.652 | 0.000345 | 0.522 | 0.000023 | Worse, and costlier on B. Reject. |

Pack arm A stays at ~0.174 gold cited, `cite_ok` 0, and illegal_span 1.0 under all three decodes. The decode choice only matters for pack arms B and C.

The earlier rematch on `both` had pack arm C at 0.826. This ablation has it at 0.739. Treat the difference as run variance. Do not chase the higher number without a repeat.

## Cost vs accuracy (locked read)

- Do not trade gold cited for pennies (`noul_only` on pack arm C).
- Within a decode, pack arm C ≪ pack arm B on $/q. The gap comes from flat versus tree, not from the decode flag.
- Pack arm A costs ~$0.016/q and fails `cite_ok`. It is off the Pareto front.

## BrowseComp-Plus smoke

Stub run (no key, no network):

```bash
./scripts/run_scoreboard.sh --suite browsecomp-plus
```

This writes `results/phase0_pack/SCOREBOARD.browsecomp-plus.md`. On this pack, stub pack arm C has `exact_id_acc` 0.207 and `cite_ok` 1.000. Thirty-one questions cite the gold docid, twelve ties go to Review, and one hundred seven cite a different docid. The ranker is Okapi BM25 (k1=1.2, b=0.75), with IDF and average length computed inside the per-question pool. The stub decide is unchanged: it picks the unique best token overlap among the top 3. So the stub's gold cited is not the BM25 argmax. The overlap stub on this pack was 0.213.

Ranker hits on the same pool, before any decide: overlap top-1 33/150 and top-3 74/150; BM25 top-1 37/150 and top-3 81/150. On a score tie, top-1 counts the lowest id. These are retrieval counts, not a live board.

Both live boards (overlap on `eae3f30`, BM25 on `a6bec4a`) are in the timeline above. `results/phase0_pack/SCOREBOARD.browsecomp-plus.live.md` is the BM25 board, and it meets the primary gate (gold cited ≥ 0.30). The stub's 0.207 under-credits BM25. Do not refill the live board from the stub.

Live run:

```bash
MUST_CITE_JEV_DECODE=both ./scripts/run_scoreboard.sh --live --suite browsecomp-plus --live-out results/phase0_pack/SCOREBOARD.browsecomp-plus.live.md
```

With `TYPESAFE_API_KEY` set, pack arm C runs through Jev. Decode `both` is the Choice route plus one Noul per docid. On act, it cites the argmax Noul at or above 0.5. The prompt holds the first 12000 characters of each top-3 doc. With `TYPESAFE_API_KEY` unset, a chat key runs the chat decide instead. Pack arms A and B are not called.

Rebuild (pytest does not download from Hugging Face). Shard 0 is still the pin but has only 43 singleton-gold queries, so the 150-query pack passes shards 0–3 in filename order:

```bash
python3 scripts/build_browsecomp_plus_pack.py \
  --shard test-00000-of-00006.parquet \
  --shard test-00001-of-00006.parquet \
  --shard test-00002-of-00006.parquet \
  --shard test-00003-of-00006.parquet
```

`--download` fetches the pinned shard only and cannot fill `--n` 150. Shards 4 and 5 are not in the draw. License, canary, and the web-page urls are in `fixtures/browsecomp_plus/LICENSE.txt`.

## Phase 0b R1 bars

- Must, on the scored board: `cite_ok` 1.0 and `illegal_span_rate` 0. The BM25 live board meets both.
- Primary gate: gold cited ≥ 0.30. The live rematch on `a6bec4a` scored 0.313, so the gate is met.
- Soft bar was ≥ 0.27. Kill was below 0.25.

Decode stays `both`. Pack arm C only. No pack rebuild. The Hotpot cite yardstick still passes `ranker="overlap"`, and Phase 0b R1 does not rescore it.

## Phase 0c plan

Each step has a bar and a stop rule. Pack arm C only until step 5.

| step | what | bar | if it fails |
| --- | --- | --- | --- |
| 1 | Live BC+ writes `<live-out>.trace.jsonl`: candidates, route probabilities, Noul per id, decision. Repeat BM25 live. | Repeat within ±0.03 of 0.313. | Investigate variance before scoring. |
| 2 | `python -m must_cite_rlm.risk_coverage <trace> --holdout <trace>`: precision vs coverage over route p(act) and max Noul. `--holdout-gold` runs the live pool with gold dropped, where the right call is not to act. No new pack. | Precision ≥ 0.85 at coverage 0.40; false-act ≤ 0.10 on held-out. | Report gold cited only; tune the act gate before step 3. |
| 3 | Claude Haiku decide on the same BM25 top 3, same act/review/abstain schema. Compare the step 2 curves and $/q. | Jev within 10 pts precision at matched coverage. | Haiku becomes the default decider; Jev is a cost-only story. |
| 4 | Decide over k = 3, 5, 8 (`--top-k`; all exceeds Jev's input cap). | Separates ranker misses from decide misses. | — |
| 5 | Pack arm B / RLM recurse on BC+ with the step 3 decider. Docs split into sections and paragraphs so the walk reaches text past `PROMPT_CHARS` (16 gold answers sit only there). | Pack arm B ≥ BM25 pack arm C + 8 pts gold cited, or equal precision at higher coverage, at ≤ 5× pack arm C $/q. | Recurse is demoted to research. Calibrated cite over retrieval is the product. |

### Step results

Step 1 (trace read of the repeat board, not a scored bar): gold is in the BM25 top 3 on 81/150. Citing the argmax Noul on every question would give 60/150 = 0.40 gold cited, versus 0.300 scored. So the review gate drops correct cites. Precision at coverage 0.40 is 0.78 ranked by route p(act) and 0.68 ranked by max Noul. Both are below the step 2 bar as-is.

Step 2: the false-act bar is met (0.060 as decided, 0.087 at coverage 0.40). The precision bar is missed (0.787 at coverage 0.40). No threshold on route p(act) or max Noul reaches 0.85 at 0.40. The as-decided gate (0.833 at 0.360) already sits on the route p(act) curve, so tuning the gate does not close the gap. Route p(act) dominates max Noul as the act score at every coverage above 0.1.

Step 3: bar passed. At matched coverage 0.407, Jev scores 0.787 precision / 0.087 false-act and Haiku scores 0.590 / 0.167. Jev leads by 20 pts at 1/28 the cost. Argmax pick quality is close (ceiling 0.400 Jev vs 0.380 Haiku), so the gap is calibration. Haiku's route p(act) is ≥ 0.95 on 53% of questions, so it cannot operate below ~0.40 coverage. Its higher gold cited (0.340) comes from acting on 61% of questions at 0.560 precision, with 34% false-act when gold is absent.

Caveats for step 3: one run each. Verbalized probabilities are the plain LLM baseline, not logprobs or self-consistency. When Haiku abstains it often omits support scores (17 main, 36 held-out rows). Those rows cannot act and sit at p(act) 0.05.

Step 4, ranked by route p(act):

| k | recall@k | argmax ceiling | prec / false-act @ ~0.40 | prec / false-act @ ~0.50 | as decided cov / prec / false-act |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 3 | 0.540 | 0.400 | 0.787 / 0.087 | 0.680 / 0.173 | 0.360 / 0.833 / 0.060 |
| 5 | 0.727 | 0.493 | 0.783 / 0.073 | 0.776 / 0.107 | 0.487 / 0.767 / 0.100 |
| 8 | 0.947 | 0.547 | 0.800 / 0.067 | 0.787 / 0.093 | 0.653 / 0.704 / 0.133 |

More candidates move the whole curve up. On this pack the ranker is the bottleneck, not the Jev decide. Jev's argmax is right on 74% of questions whose gold is in the top 3, and on 58% at top 8. The recall gain outweighs that drop. The as-decided gate (route `act`, Noul ≥ 0.5) loosens as k grows, so false-act rises from 0.060 to 0.133. At k ≥ 5 the act rule should be a route p(act) threshold (~0.6 at k=8), not the Choice alone. Default `TOP_K` stays 3.

Consequence for step 5: pools here hold 5–17 docs, and flat k=8 already reaches 0.947 recall in one Jev call. A tree walk has little to win. Recurse only has room where the candidate text exceeds Jev's input cap (between ~32k and ~42k tokens). Step 5 needs larger pools, e.g. BM25 top-100 from the ~100K corpus, or long docs split past `PROMPT_CHARS`.
