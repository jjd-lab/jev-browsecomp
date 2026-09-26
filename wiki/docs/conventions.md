---
type: convention
title: Running and recording experiments
description: Rules set before runs, spend control, live-run operations, and the rlms patches, each learned from a run that went wrong.
tags: [conventions, rules, cost, operations]
timestamp: 2026-09-25
---

# Running and recording experiments

## Decide the verdict before the data

- Before the run, write the endpoints, question sets, and verdict rule into `results/findings/<phase>.md` and into the analysis code (`scripts/analyze_rlm_jev.py`).
- A verdict needs the whole 95% paired-bootstrap CI on one side of 0. Anything else reads "no clear difference".
- Record any mid-run change as a deviation, noting what had been seen at that point. Don't move the stopping point once interim results are visible. In Phase 1, the cut from 150 to 100 questions came before any comparison was computed, and a later cut to 80 was declined for this reason.
- A follow-up that changes an arm is a new arm (B2, harness v2), not a re-score. The old result stays on record.

## Labels you can trust

- The Haiku judge flipped an identical answer between arms. Use a `claude-sonnet-5` judge, store its raw verdict, and run the label audit (same normalized answer, different label) before quoting results.
- A row with no answer is an abstention and scores 0 under every confidence scorer.
- On a held-out set (gold and evidence removed), every answer counts as should-not-act when scoring the Jev check, even when the judge accepts it from the model's own memory: no document supports it.

## Spend control

- Every live run gets a per-arm dollar cap (`--budget`) and per-question limits (turns, tokens, minutes). The cap is checked between questions, so spend can overshoot by one question per worker. Keep workers at 2 for expensive arms.
- Estimate cost from a smoke run, then check spend after the first ~15 questions. The Haiku-root pilot passed its cap by ~$10 because a single stuck question could cost up to $7.
- Raising a turn cap moves the binding limit to tokens. Change the limits together.
- Runs are resumable: results append per question and finished ids are skipped. Stop and restart instead of editing a running job.
- `gate_rlm_jev.py` (the Jev check) rewrites a results file in place. Run it only after the run writing that file has finished, or appended rows can be lost.

## Live-run operations (macOS host)

- Load keys with `set -a && . ./.env && set +a`. `.env` is gitignored.
- System and venv Python lack a CA bundle: export `SSL_CERT_FILE=/etc/ssl/cert.pem`.
- `.venv` has `pyarrow`, `rlms`, and `anthropic`, but not `typesafe-sdk`. Keep it that way: the SDK path in `live._jev_call` drops Choice probabilities, and the Jev check refuses to run without them.
- Jev sometimes returns a transient 500. `scripts/gate_rlm_jev.py` retries with backoff. A 402 means the Typesafe account needs credit.
- Killing a runner leaves `python:3.11-slim` containers and `.rlm_workspace/` folders behind. Stop only those containers; other containers on the host belong to other projects.
- Trajectories: `RLMLogger` on disk wrote the full prompt every turn, about 1 GB per question (280 GB across Phase 1, since gzipped in place). New runs keep the logger in memory and write one compact line per turn (code, trimmed output, timing) to `.cache/rlm_logs/<arm>/q<id>.jsonl`.

## rlms 0.1.3 patches (`must_cite_rlm/rlm_jev.py`)

- It read `content[0].text`, which fails when the first block is a thinking block or the content is empty. Patched to join text blocks.
- Its out-of-iterations step sent a trailing assistant message (rejected by Claude 4.6+) and got code back. Patched to an explicit no-code final turn.
- It drops usage when a run raises. Cost is read from the LM clients instead.
- A token-limit stop has no final-answer step, so it ends with no answer. Accepted as "no answer" for both arms.

Rechecked 2026-09-25 against PyPI `rlms` 0.1.3, still the latest release, and against `alexzhang13/rlm` main, which is still version 0.1.3. All three are still there. On main, `return response.content[0].text` is `rlm/clients/anthropic.py` lines 47 and 64. `_default_answer` still appends an assistant message (`rlm/core/rlm.py` line 672). `TimeoutExceededError` (line 501) and `TokenLimitExceededError` (line 576) still carry only `partial_answer`, and both abort before `_default_answer`. `max_budget` still reads `total_cost`, which the Anthropic client never sets. No upstream issue. The workarounds stay in this harness. `docs/experiments.html` is the Phase 1 BrowseComp-Plus page and does not carry these notes.
