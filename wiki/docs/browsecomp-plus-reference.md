---
type: reference
title: BrowseComp-Plus reference
description: Why BrowseComp-Plus is the suite, the published baselines our numbers are read against, and how comparable they are.
tags: [browsecomp-plus, baselines, reference]
timestamp: 2026-09-25
---

# BrowseComp-Plus reference

## Why this suite

BrowseComp-Plus (HF `Tevatron/browsecomp-plus` plus its corpus) is the main suite for four reasons:

- It has native doc ids with gold and evidence labels, so citations can be checked mechanically.
- Its corpus is large enough to need recursion or search: millions of tokens per question.
- There are published results to compare against, including the RLM paper's 1K-doc setting (Table 1: CodeAct + BM25 51, compaction 70.5, RLM depth=1 91.3, OpenCode + offload 94).
- It supports two kinds of score: answer accuracy under the paper's judge protocol, and gold cited with mechanical cite checks, cost, and latency.

Phase 0 started with a 150-question pack (gold, evidence, and negatives) instead of the full corpus. The Hotpot slice checks citing by id only.

Other suites considered:

- LongBench-v2 CodeQA (multiple-choice accuracy: RLM depth 1 62, OpenCode offload 64, RLM depth 2 66). A weak must-cite fit, since it publishes no span or file ids; useful only as a recursion stress test.
- Qasper, for span and evidence-paragraph fidelity. Short documents, so it says nothing about long context.
- OOLONG and OOLONG-Pairs: skipped. They test aggregation and have no spans.

## Published results (read 2026-09-25)

Sources: Chen et al., arXiv 2508.06600 (Tables 1–3); leaderboard data `Tevatron/BrowseComp-Plus-results` (last commit 2026-09-24); Zhang, Kraska, Khattab, arXiv 2512.24601 v3 (Table 1).

- The published metric is answer accuracy from an LLM judge (gpt-4.1 in the paper, Qwen3-32B on the leaderboard). Agent recall and citation precision and recall are measured against evidence docs. No source reports a gold-doc cite rate for agents, so our gold cited (exact_id) has no published counterpart.
- Paper baselines, 830 queries, 100K corpus, accuracy (gpt-4.1 judge) / evidence recall / search calls: gpt-5 + BM25 55.90 / 61.70 / 23.2; gpt-5 + Qwen3-Embed-8B 70.12 / 78.98 / 21.7; Sonnet 4 + BM25 14.34 / 21.31 / 10.0; Opus 4 + BM25 15.54 / 22.96 / 11.2.
- Leaderboard top (Qwen3 judge): GPT-5 AI21 multi-agent 95.18 (209 search calls); GLM-5.1 90.72; GPT-5 with Mixedbread Search v3 90.48; GPT-5.5 with BM25 90.48. No Claude model newer than Sonnet 4 or Opus 4 is listed.
- Retriever only, full question as the query: BM25 gold R@100 6.1, R@1000 17.3; Qwen3-Embed-8B gold R@100 55.8.
- RLM paper, BrowseComp-Plus (1K docs): 150 queries, each given 1,000 docs that always include its gold and evidence docs, no retriever. GPT-5 RLM depth=1 91.3 ($0.99/q), CodeAct + BM25 51.0, compaction 70.5.

## How comparable our numbers are

- BC+ pack (Phase 0): 150 queries with a single gold doc each. Our BM25 reaches gold R@100 0.220 there, against the paper's 6.1 over all 830, so the pack is easier for lexical retrieval than the full set. Corpus arm H's 0.273 is gold cited, not answer accuracy.
- 1K set (Phase 1): same construction as the RLM paper's 1K setting, but our own seeded draw of 150 questions, a `claude-sonnet-5` judge instead of gpt-4.1, and Sonnet 5 in place of GPT-5. RLM arm A's 0.91–0.94 and reader arm J's 0.94 sit near the paper's 91.3 but are not the same measurement.
