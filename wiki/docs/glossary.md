---
type: reference
title: Glossary
description: One name per thing. Use these terms in findings, wiki pages, commits, and the storyline.
tags: [glossary, terms, conventions]
timestamp: 2026-09-26
---

# Glossary

## Phases

| Term | Meaning |
| --- | --- |
| Phase 0 | Jev as the decide step over candidate ids: the Hotpot slice, the BC+ pack, and the full corpus. Metric: gold cited. |
| Phase 1 | Jev with a frontier model on the 1K set: the RLM arms, the reader arms, and the held-out set. Metric: accuracy. |

## Question sets

| Term | Meaning |
| --- | --- |
| Hotpot slice | 23 HotpotQA questions over 34 Wikipedia articles. Tests citing by id, nothing else. |
| BC+ pack | 150 BrowseComp-Plus questions, each with its evidence docs plus 4 negatives (~9 docs). |
| Full corpus | All 100,195 BrowseComp-Plus docs, searched per question. |
| 1K set | 150 BrowseComp-Plus questions, each with 1,000 docs (the RLM paper's setting). |
| Main questions | 1K-set questions 1–100, whose 1,000 docs include the gold and evidence docs. |
| Held-out questions | 1K-set questions 101–150, with the gold and evidence docs swapped for random docs, so no document supports an answer. |
| Hard questions | The 27 main questions where RLM arm A or B hit the 20-turn cap under harness v1. The other 73 are easy. |

## Arms

Letters repeat across phases, so always name the family: "pack arm C", "RLM arm A", "reader arm J".

| Family | Arm | What runs |
| --- | --- | --- |
| Pack arms (Phase 0) | A | Free-form LLM quotes per section (fails the exact-span check by construction). |
| | B | Tree walk with a Jev decide at each level. |
| | C | Ranker → top k → one Jev decide. |
| Corpus arms (Phase 0) | flat | One Jev decide over the BM25 top 8. |
| | R | Jev screen of the BM25 top 100 → best 8 → one Jev decide. |
| | H | R plus three rounds of Haiku-written searches. |
| | N | Replays H's final 8 with a two-chunk re-decide. |
| RLM arms (Phase 1) | A | Sonnet 5 RLM with `llm_query` and plain Python. No Jev during the run. |
| | B | RLM arm A plus the Jev screen and Jev decide as tools. |
| | B2 | RLM arm B with a one-call shortlist tool. |
| Reader arms (Phase 1) | J | Jev-first reader: the Jev screen picks 8 docs, then one Sonnet 5 call. No RLM loop. |
| | K | BM25 reader: BM25 picks the 8 docs, then the same Sonnet call. Built, not run. |

## Jev

| Term | Meaning |
| --- | --- |
| Noul | A Jev question with a probability answer, e.g. "does doc X support the question?" |
| Choice | A Jev question with a categorical answer and its probabilities. |
| Jev screen | One Noul per doc, used to rank docs. Arms R, H, B (as a tool), and J. |
| Jev decide | A route Choice (act / review / abstain) plus one Noul per candidate; on act, cite the top Noul. Pack arms, corpus arms, and RLM arm B (as a tool). |
| Jev check | After an answer exists: "do the cited docs support this proposed answer?" (a Choice; its p(act) is the score. The Phase 1 runs also asked one Noul per cited doc, since dropped as unused). Applied the same way to every Phase 1 arm; never shown to the model. The code calls it the gate (`verify_gate`, `gate_post`). |
| p(act) | The probability of the act route in a Choice. The Jev check's score. |

## Outcomes and metrics

| Term | Meaning |
| --- | --- |
| Gold doc / evidence doc | Gold: contains the answer. Evidence: needed to answer. Gold docs are evidence docs. |
| Gold cited | The answer cites a gold doc (Phase 0's exact_id). |
| Accuracy | The judge (`claude-sonnet-5`, BrowseComp-Plus template) marks the final answer correct. |
| Stated confidence | The number the model writes after "Confidence:". Not a logprob. |
| Declined | The answer line says the documents don't settle it ("cannot be determined"). |
| No answer | The run ended without an answer line (turn, token, or time limit). |
| Abstained | Declined or no answer. Scores 0 on every confidence measure. |
| AUROC / AURC | How well a score ranks wrong answers below right ones. AUROC is higher-better; AURC (area under the risk–coverage curve) is lower-better. |

## Run types

| Term | Meaning |
| --- | --- |
| Pilot | A few questions to check that a setup runs. Never a result. |
| Probe | A small exploratory run to decide whether a full run is worth it. Reported with CIs, not as a verdict. |
| Full run | A run whose comparison rules were written down before it started. |
| Harness v1 / v2 | RLM limits. v1: 20 turns, and the final step could return code. v2: 30 turns and a no-code final turn. The public page calls them the "first setup" and the "fixed setup". |
| Capped rerun | A question that hit the v1 turn cap, rerun under v2 (`*.capfix.jsonl`). |
| Extension | More questions added to a finished run after its results were seen. Reported next to the original, never in place of it. |
