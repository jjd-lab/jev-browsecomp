# jev-browsecomp

Research harness. It tests whether cheap typed decisions from Jev (Typesafe; Choice / Noul → act | review | abstain over stable doc ids) make must-cite question answering cheaper, faster, or more reliable than full-LLM pipelines, including a real Recursive Language Model. Every citation is a mechanical id→span check. The main benchmark is BrowseComp-Plus. Independent research, not affiliated with or endorsed by Typesafe.

- Status, locks, and results: [`results/FINDINGS.md`](results/FINDINGS.md)
- How it works, conventions, experiment ledger, glossary: [`wiki/index.md`](wiki/index.md)
- Phase 1 BrowseComp-Plus page, with questions and answers left out: [`docs/experiments.html`](docs/experiments.html)

The RLM method is Zhang, Kraska, and Khattab ([arXiv:2512.24601](https://arxiv.org/abs/2512.24601)). Phase 1 uses their `rlms` package (0.1.3) unmodified, with local client patches in `must_cite_rlm/rlm_jev.py`.

## Setup

```bash
pip install pytest && python3 -m pytest          # offline tests; no keys, no network
python3 -m venv .venv && .venv/bin/pip install pyarrow rlms anthropic   # for corpus and Phase 1 runs
```

Live runs read keys from `.env` (gitignored): `TYPESAFE_API_KEY` for Jev and `ANTHROPIC_API_KEY` for Claude. On macOS, Python needs a CA bundle:

```bash
set -a && . ./.env && set +a && export SSL_CERT_FILE=/etc/ssl/cert.pem
```

Don't install `typesafe-sdk` into `.venv`. Its code path drops Choice probabilities, which the Jev check needs.

## Phase 0: Hotpot slice and the BrowseComp-Plus pack

```bash
./scripts/run_scoreboard.sh                                   # Hotpot stub → results/phase0_hotpot/SCOREBOARD.md (no keys)
./scripts/run_scoreboard.sh --suite browsecomp-plus           # BC+ pack stub → results/phase0_pack/SCOREBOARD.browsecomp-plus.md
MUST_CITE_JEV_DECODE=both ./scripts/run_scoreboard.sh --live --suite browsecomp-plus \
  --live-out results/phase0_pack/SCOREBOARD.browsecomp-plus.live.md       # live pack arm C with Jev
python3 -m must_cite_rlm.risk_coverage <trace> --holdout <trace>   # precision vs coverage from live traces
```

Useful live flags: `--decider jev|chat`, `--holdout-gold` (drop gold docs, so the right call is not to act), and `--top-k N` (candidates per decide; 0 = whole pool). `MUST_CITE_JEV_DECODE` is `both` (default), `noul_only`, or `choice_per_span`.

## Phase 0: the full 100K-doc corpus

```bash
.venv/bin/python scripts/build_browsecomp_plus_corpus_run.py --download   # ~1.8 GB into .cache/, freezes BM25 top 100
.venv/bin/python scripts/build_browsecomp_plus_corpus_run.py --index      # SQLite FTS5 index, 4.5 GB, ~6 min
./scripts/run_scoreboard.sh --live --suite browsecomp-plus-corpus --arm flat|recurse|hybrid
./scripts/run_scoreboard.sh --live --suite browsecomp-plus-corpus --arm narrow --from-trace <trace>
```

## Phase 1: RLM and reader arms (1K set, 1,000 docs per question)

Needs Docker, the corpus cache and index above, and both keys.

```bash
.venv/bin/python scripts/build_browsecomp_plus_1k.py                      # questions 1–100 + held-out 101–150
.venv/bin/python scripts/run_rlm_jev.py --arm A --n 100 --budget 45 --workers 2
.venv/bin/python scripts/run_rlm_jev.py --arm B --n 100 --budget 55 --workers 2
.venv/bin/python scripts/run_rlm_jev.py --arm A --holdout --n 50 --budget 40 --max-tokens 800000 --workers 2
.venv/bin/python scripts/gate_rlm_jev.py A.jsonl B.jsonl                  # Jev check on finished answers
.venv/bin/python scripts/analyze_rlm_jev.py                               # verdicts → results/phase1_rlm/ANALYSIS.md
```

Reader arm J (Jev screen, then one Sonnet call) runs with `--arm J`; reader arm K is the same reader with BM25 ranking (`--arm K`, not run yet), and `scripts/ranker_recall.py` compares the two rankers' top 8 without any API calls. Its untested variants are `--show-jev-scores`, `--jev-reject-below X`, and `--reader-max-output N`; write each variant to its own file with `--tag`. Runs are resumable: a rerun skips finished questions, and `--budget` counts past spend. Other flags: `--ids` (specific questions), `--tag` (separate output file, e.g. `capfix`), and `analyze_rlm_jev.py --patch <tag>`. Before any live run, read the spend rules and the rule to set comparisons before running, in [`wiki/docs/conventions.md`](wiki/docs/conventions.md).

## Data

- `fixtures/corpus/`, `gold.jsonl`, `provenance.jsonl`: the 23-question Hotpot slice (34 Wikipedia articles, CC BY-SA 4.0; `scripts/build_hotpot_slice.py`). It keeps only supporting articles, and bridge rows were chosen because the stub arm split holds, so it is not a random sample.
- `fixtures/browsecomp_plus/`: the frozen 150-query pack from `Tevatron/browsecomp-plus` (pinned revision in `PACK.json`; `scripts/build_browsecomp_plus_pack.py`), plus `corpus_bm25.jsonl`.
- `fixtures/browsecomp_plus_1k/`: Phase 1 question ids and 1,000 docids each, plus the held-out set.
- BrowseComp-Plus carries a canary. Never publish its questions or answers outside this repo.
