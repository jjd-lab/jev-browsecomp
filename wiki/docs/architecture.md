---
type: architecture
title: Harness architecture
description: How the must-cite harness is built, from the Phase 0 arms to the Phase 1 RLM with Jev tools.
tags: [architecture, jev, rlm, browsecomp-plus]
timestamp: 2026-09-26
---

# Harness architecture

Every arm follows one rule: code lists stable ids, and a model only chooses among them. Code copies the cited text, so a citation is an id→span check, never text the model wrote.

Arm letters are reused across phases, so always name the family: pack arm C, corpus arm R, RLM arm A, reader arm J. The [glossary](glossary.md) lists every arm and term.

## Jev, the decide layer

Jev (Typesafe) answers typed questions about a set of texts:

- Noul: one probability per id ("does text X support the question?"), used to screen and rank.
- Choice: one categorical answer with probabilities. Here it is the route `act | review | abstain`, and p(act) is the confidence score.

`MUST_CITE_JEV_DECODE=both` (the default since PR6) asks the route Choice plus one Noul per id. On `act`, the cite is the highest Noul at or above 0.5. The route decides whether to act; the Nouls decide which id to cite. Across the pack runs, ranking by route p(act) beat ranking by max Noul.

Jev costs about $0.042 per million input tokens. Each call is capped at roughly 32–42k input tokens (it returns 400 `max_tokens_exceeded` past that), so large inputs go in batches of 8 ids. Jev reads text. It cannot write search queries or code.

## Pack arms (Phase 0): decide over candidate ids (`must_cite_rlm/arms.py`, `browsecomp.py`, `scoreboard.py`)

- Pack arm A: free-form LLM quotes per section. It fails the exact-span check by construction.
- Pack arm B: tree walk (section → paragraph) with a Jev decide at each level.
- Pack arm C: flat ranker (BM25 by default, token overlap on Hotpot) → top k → one Jev decide.

The suites are a 23-question Hotpot slice (the cite yardstick) and a frozen 150-query BrowseComp-Plus pack of about 9 docs per question (`fixtures/browsecomp_plus/`). Live boards write a `.trace.jsonl` with each question's candidates, route probabilities, and Nouls. `must_cite_rlm/risk_coverage.py` turns a trace, plus a gold-held-out trace, into precision-vs-coverage tables.

## Corpus arms (Phase 0): the full corpus (`recurse.py`, `search.py`)

- `scripts/build_browsecomp_plus_corpus_run.py` downloads the pinned corpus into gitignored `.cache/`, freezes a BM25 top-100 per pack query, and with `--index` builds a SQLite FTS5 BM25 index of all 100,195 docs.
- Flat: one decide over the BM25 top 8.
- R: Jev Noul screen of the top 100 → chunk the best 8 → one decide.
- H: R plus three rounds of Haiku-written keyword searches against FTS5. Haiku only writes searches; Jev makes every select and act/abstain call.
- N: replays a finished run's final candidates with a two-chunk re-decide.

## RLM and reader arms (Phase 1): the 1K set (`must_cite_rlm/rlm_jev.py`, `reader.py`)

The setting follows the RLM paper (Zhang, Kraska, Khattab, arXiv 2512.24601): each question gets 1,000 corpus docs that always include its gold and evidence docs, about 7–9M tokens (`fixtures/browsecomp_plus_1k/`, seeded draw). The main run uses questions 1–100. The held-out set is questions 101–150 with their gold and evidence docs swapped for random ones, so no document answers them. `rlms` 0.1.3 runs in a Docker REPL where `context = {docid: text}`.

- Root `claude-sonnet-5`; `llm_query` sub-calls go to `claude-haiku-4-5`.
- RLM arm A: `llm_query` and plain Python only.
- RLM arm B: adds the Jev screen (`jev_screen`) and the Jev decide (`jev_decide`) as tools; `jev_decide` must be called before answering.
- RLM arm B2: replaces `jev_screen` with `jev_shortlist`, which screens and returns the top k with snippets in one call.
- Reader arm J, the Jev-first reader (`must_cite_rlm/reader.py`): no RLM and no Docker. Jev screens all 1,000 docs (a Noul per doc, first 12,000 chars each), and the top 8 go to one `claude-sonnet-5` call (adaptive thinking) in the same answer format. The row records Jev's top 8, their screen scores, and whether a gold doc is among them. `ReaderConfig` holds three untested variants, all off by default: `show_scores` (label each doc with its Jev score in Sonnet's prompt), `reject_below` (abstain without calling Sonnet when Jev's best score is below a threshold), and `max_output_tokens` (Sonnet's output cap, thinking included; the recorded runs used 16k). Sonnet is called with streaming so a larger cap is allowed. In the recorded runs Sonnet never saw Jev's scores, only which 8 docs were picked and their order. Reader arm K is the same reader with BM25 ranking (`ranker="bm25"`), the control for J. It has not been run; `scripts/ranker_recall.py` compares the two rankers' top 8 for free.
- Jev tools run as code in the container and POST to a host proxy bound to `127.0.0.1`, so the Typesafe key never enters the container. Screens run 8 batches at a time (1,000 docs in about 12 s).
- The answer uses BrowseComp-Plus's format (Explanation with `[docid]` cites / Exact Answer / Confidence). A `claude-sonnet-5` judge grades it with the benchmark's template.
- Held-out set: questions 101–150 with their gold and evidence docs swapped for random corpus docs, so nothing in the 1,000 supports an answer. The right behavior is to decline, and every answer counts as should-not-act. RLM arm A and reader arm J both run on it. For arm A, Jev only runs the Jev check. For arm J, the Jev screen also decides what Sonnet reads.
- The Jev check (code: `verify_gate`, stored as `gate_post`) runs the same way on every arm after the answer exists: a Choice on "do the cited docs support this proposed answer?", whose p(act) is the score. Each doc is shown as the window around the answer. The Phase 1 runs also asked a Noul per cited doc (stored as `support`); nothing read it, so the check no longer asks it.
- Harness v2: a 30-turn cap, a per-question token cap (`--max-tokens`), and a no-code final turn.
- The local patches to rlms 0.1.3 are listed in [conventions](conventions.md).

Scripts: `build_browsecomp_plus_1k.py` (set + held-out), `run_rlm_jev.py` (resumable, $ cap, `--ids`, `--tag`), `gate_rlm_jev.py`, `analyze_rlm_jev.py` (per-arm overview and verdicts).
