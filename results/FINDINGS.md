# Findings (living)

This is the live tracker: status, locks, and where each result is recorded. Update it when a run finishes or a locked decision changes. Durable knowledge lives in [`wiki/`](../wiki/index.md): how the harness works, conventions, the experiment ledger, and the [glossary](../wiki/docs/glossary.md).

## Status (2026-09-25)

Nothing is running. All planned Phase 1 runs are finished.

- Reader arm J (Jev screen, then one Sonnet call) vs RLM arm A (Sonnet 5 RLM), 100 main questions: accuracy 0.94 vs 0.91 with harness v2 (+3 points, 95% CI −3 to +9), or 0.94 with harness v1 (a tie). Cost $0.13 vs $0.35 per question, time 21 s vs 143 s. The same pattern holds on the 62 questions outside the earlier probe.
- The Jev screen is why arm J works: its top 8 holds a gold doc on 94 of 100 main questions, BM25's on 49 (free check; reader arm K not run).
- On held-out questions (no supporting document), both arms mostly abstain. On the same 30: RLM arm A declined 19 and gave no answer on 3; reader arm J declined 25. Arm J declined on 37 of all 50.
- RLM arm B (Jev tools inside the loop) vs arm A: accuracy 0.90 vs 0.91, no clear difference; cost $0.42 vs $0.35 per question, arm B worse.
- The Jev check does not beat Sonnet's stated confidence at ranking errors: AUROC 0.910 vs 0.955 with 20 held-out questions, 0.912 vs 0.958 with 30.

The Phase 1 page is [`docs/experiments.html`](../docs/experiments.html). Untested options: an embedding-retriever control, reader arm K, the reader variants (`--show-jev-scores`, `--jev-reject-below`, `--reader-max-output`), and Jev-ranked context under the RLM.

## Results by phase

| File | Setting | Compared against | Holds |
| --- | --- | --- | --- |
| [`findings/phase0_pack.md`](findings/phase0_pack.md) | Hotpot slice; BC+ pack (150 q × ~9 docs) | Haiku as decider; BM25 | Pack arms, suite, timeline, decode ablation, steps 1–4 |
| [`findings/phase0_corpus.md`](findings/phase0_corpus.md) | Full corpus (100,195 docs) | Flat BM25; Haiku writing searches | Steps 5–7: corpus read, corpus arms R, H, N |
| [`findings/phase1_rlm.md`](findings/phase1_rlm.md) | 1K set (100 main + 50 held-out q) | Sonnet 5 RLM; BM25 ranking | Run map, pilots, rules, main run, probes, harness v2, reader arms, held-out, extensions |

Published baselines and the reason for choosing BrowseComp-Plus: [`wiki/docs/browsecomp-plus-reference.md`](../wiki/docs/browsecomp-plus-reference.md).

## Locks

| Lock | Value |
| --- | --- |
| Suite | BrowseComp-Plus. The Hotpot slice checks citing by id only. |
| Default Jev decide | `both` (route Choice plus one Noul per id), since the PR6 ablation. |
| Phase 0 ranking rule | Gold cited first, then mean $/q; cite checks must stay at 1.0 on typed arms. |
| Phase 1 comparison rule | Set in `scripts/analyze_rlm_jev.py` before the runs: 95% paired-bootstrap CI on one side of 0, otherwise "no clear difference". |
| Models | RLM root `claude-sonnet-5`, `llm_query` sub-calls `claude-haiku-4-5`, judge `claude-sonnet-5`. A Haiku root did not converge. |
| RLM harness | v2: 30 turns, no-code final turn, 500k tokens per question (800k on held-out). |

## Open

- Embedding-retriever control (e.g. Qwen3-Embed-8B) for reader arm J: not run.
- Reader arm K (BM25 reader): built, not run.
- Reader variants: built, not run.
- RLM arm B on held-out questions: not run; not needed for the Jev-check question.
- Multi-id gold handling beyond a single cite: optional.
