# Wiki log

## [2026-09-25] ingest | Bootstrap the wiki
Added SCHEMA, index, and pages for architecture, conventions, the experiment ledger, and the BrowseComp-Plus reference, covering Phases 0 and 1 (PRs #13–#23).

## [2026-09-25] decision | Split the findings tracker
`results/PHASE0_FINDINGS.md` became `results/FINDINGS.md` (status, locks, open items) plus one file per phase under `results/findings/`. Suite rationale and published baselines moved to `docs/browsecomp-plus-reference.md`.

## [2026-09-25] decision | Storyline stays private and on BrowseComp-Plus
The Jev storyline lives in `private/jev-storyline.md` (gitignored), not in the wiki. It reads every result against its comparator. So far Jev wins only against weaker comparators: Haiku and BM25.

## [2026-09-25] decision | Per-phase results folders; compact logs
`results/` now holds `FINDINGS.md`, `findings/`, and one folder per phase (`phase0_hotpot`, `phase0_pack`, `phase0_corpus`, `phase1_rlm`). RLM trajectories are one compact line per turn; the old full-prompt logs are gzipped in `.cache/rlm_logs/`.

## [2026-09-25] decision | Public-copy checklist and experiments page
Added `wiki/docs/before-public.md` (what has to change before a public copy) and `docs/experiments.html` (locked results and the rlms client notes, with questions and answers left out). Rechecked the three rlms 0.1.3 bugs against current main: all three are still present.

## [2026-09-25] ingest | Phase 1 complete
Ledger rows 1.8 (Jev-first reader: same accuracy as the RLM at 38% of its cost, 7× faster) and 1.9 (gate loses the co-primary to Sonnet's self-confidence).

## [2026-09-25] ingest | Phase 1 run map; arm J and held-out documented
`results/findings/phase1_rlm.md` opens with a run map (arms, question ranges, n, harness, Jev's role, measures, status, cost, file). The architecture page describes arm J and the held-out set, including Jev's two roles there. The ledger has a Phase 1 at-a-glance table.

## [2026-09-25] ingest | BM25 control and held-out extension
Ledger row 1.10: BM25's top 8 holds a gold doc on 49/100 vs Jev's 94/100 (free check; arm K not run). Held-out extension (A 30, J 50) is recorded in the run map; the gate verdict is unchanged.

## [2026-09-25] decision | Glossary and cleanup
Added `docs/glossary.md`. All findings, wiki pages, and the README use its terms: qualified arm names, and Jev screen / decide / check. Removed the dead `--rlms` flag and an unused constant.

## [2026-09-25] decision | This repository is the public one
`wiki/docs/before-public.md` no longer calls for a second repository. Publishing means rewriting this history after an offline bundle, then flipping this remote public.

## [2026-09-25] decision | No upstream rlms issue
The three Claude bugs in rlms 0.1.3 stay documented, with the local workarounds. Filing an issue is not part of the public-release list.

## [2026-09-25] decision | Experiments page is Phase 1 only
`docs/experiments.html` drops Phase 0 and the rlms notes. It shows the BrowseComp-Plus Phase 1 results.

## [2026-09-25] decision | Publish from a new repo built by an export
Reverses "This repository is the public one": GitHub keeps `refs/pull/N/head` after a force-push, so a history rewrite cannot hide the fixtures. `scripts/export_public.py` builds the public tree outside the repo and `scripts/scan_public.py` fails it on benchmark text, private paths, unstripped rows, or a stray canary. Pack-dependent tests skip when the pack is absent (`needs_pack`); LICENSE is Apache-2.0. Pages: `docs/before-public.md`, `index.md`.

## [2026-09-26] decision | Jev check asks only the Choice
`verify_gate` drops the per-cited-doc Nouls and no longer returns `support`; the analysis only read p(act). Phase 1 rows keep their recorded `support`. Pages: `docs/architecture.md`, `docs/glossary.md`.

## [2026-09-26] review | The Jev check also scored declines
Declines that cite docs got a Jev check; Jev often agreed the docs support "cannot be determined", and the co-primary counted that against it. With held-out declines left out, AUROC is 0.913 vs 0.944 instead of 0.912 vs 0.958; the result of record stands. Pages: `results/findings/phase1_rlm.md`, `docs/experiments.html`.

## [2026-09-26] ingest | Answerability check
Ledger row 1.11 (plus at-a-glance rows): one Jev Choice per question over reader arm J's top 8 separates main from held-out at AUROC 0.984; at p(yes) < 0.5 it declines 50/50 held-out and loses 10/94 correct answers. Glossary row "Answerability check", distinct from the Jev check. Pages: `docs/experiments.md`, `docs/glossary.md`; `results/FINDINGS.md` status.
