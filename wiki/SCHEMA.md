# Wiki schema

The maintenance contract for `wiki/`. Read this before adding or editing pages.

## What goes where

| Layer | Holds | Changes when |
| --- | --- | --- |
| `wiki/docs/` | Durable knowledge: how the harness works, conventions, what each experiment concluded and why, benchmark reference | Architecture, a convention, or a locked conclusion changes |
| `results/FINDINGS.md` + `results/findings/*.md` | The living tracker: status and locks, then run-by-run numbers, pre-registrations, and deviations per phase | Every scored run |
| `results/**` | Generated boards, traces, analyses | Every run (never hand-edited) |

The wiki never copies a generated board or live run state. It links to `results/` for numbers that move, and it records a number only when it is a locked conclusion (a finished, scored run).

## Page types (OKF `type:`)

- `architecture`: how the code fits together.
- `convention`: rules for running and recording experiments.
- `experiment`: the ledger of finished experiments and their verdicts.
- `reference`: facts the results are read against: published baselines and the glossary.
- `review`: dated code or result reviews under `wiki/reviews/`.

Every page under `docs/` or `reviews/` has YAML frontmatter with `type`, `title`, `description`, `tags`, and `timestamp`. The nav files (`SCHEMA.md`, `index.md`, `log.md`) have none.

## Operations

- **Ingest.** After a scored run or a locked decision: update `results/FINDINGS.md` and the phase file first. Then update the matching wiki page (the source→doc map below), `index.md` if a page is added, and append to `log.md`.
- **Query.** Start at `index.md`. For current behavior, read the code paths in the map below, which win over the wiki. The wiki wins for *why* and history.
- **Lint.** Check that every `docs/` page is in `index.md`, that frontmatter is complete, that the experiment ledger matches the findings file's locked results, and that no page copies a generated board. The Jev storyline is private (`private/`, gitignored) and is not a wiki page.

## Log format

Append-only. One entry per change:

```
## [YYYY-MM-DD] {ingest|decision|review} | Title
One to three lines: what changed and which pages.
```

## Source → doc map

| Source | Page |
| --- | --- |
| `must_cite_rlm/arms.py`, `tree.py`, `scoreboard.py`, `browsecomp.py` | `docs/architecture.md` (Phase 0 arms) |
| `must_cite_rlm/recurse.py`, `search.py`, `scripts/build_browsecomp_plus_corpus_run.py` | `docs/architecture.md` (corpus arms R/H/N) |
| `must_cite_rlm/rlm_jev.py`, `scripts/*rlm_jev*.py`, `scripts/build_browsecomp_plus_1k.py` | `docs/architecture.md` (Phase 1 RLM) |
| `must_cite_rlm/live.py` | `docs/architecture.md` (providers, Jev decode), `docs/conventions.md` (live-run ops) |
| `results/findings/*.md` (locked results) | `docs/experiments.md` |
