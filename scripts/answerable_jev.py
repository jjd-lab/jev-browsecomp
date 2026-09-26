#!/usr/bin/env python3
"""Ask Jev whether reader arm J's 8 documents can answer the question at all.

One Choice per question (yes | partly | no) over the recorded shortlist, with no
Sonnet call and no change to any recorded row. Rules: results/findings/phase1_rlm.md,
"Answerability check". Writes results/phase1_rlm/J.answerable.jsonl and resumes
from it, so rerunning only fills missing ids.

    python3 scripts/answerable_jev.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from must_cite_rlm import live  # noqa: E402
from must_cite_rlm.browsecomp import PROMPT_CHARS  # noqa: E402
from must_cite_rlm.search import Search  # noqa: E402

DIR = ROOT / "results" / "phase1_rlm"
FIXTURES = ROOT / "fixtures" / "browsecomp_plus_1k"
OUT = DIR / "J.answerable.jsonl"
SETS = (("main", "J.jsonl", "queries.jsonl"), ("held-out", "J.holdout.jsonl", "holdout.jsonl"))
BUDGET_USD = 2.0

ANSWERABLE = {
    "type": "choice",
    "instructions": "Do these documents contain enough information to answer the question?",
    "criteria": {
        "yes": "The documents together contain the answer.",
        "partly": "The documents contain some of the clues but not the answer.",
        "no": "The documents do not contain the answer.",
    },
}


def ask(question: str, pairs: list[tuple[str, str]]) -> tuple[dict, int, float]:
    """Halve each document on a Jev error (input cap), as recurse._decide_fitting does."""
    for halvings in range(4):
        lines = [question, ""] + [f"{docid}\n{text}" for docid, text in pairs]
        body = {
            "model": os.environ.get("TYPESAFE_DEFAULT_MODEL", "jev-latest"),
            "state": "\n".join(lines),
            "questions": {"answerable": ANSWERABLE},
        }
        for attempt in range(4):
            try:
                payload, _ = live._jev_call(body)
                break
            except live.LiveError:
                if attempt == 3:
                    payload = None
                    break
                time.sleep(5 * 2**attempt)
        if payload is not None:
            answer = payload.get("answers", {}).get("answerable", {})
            if "probabilities" not in answer:
                raise live.LiveError("Jev returned no Choice probabilities; the typesafe_sdk path drops them")
            tokens = payload.get("usage", {}).get("input_tokens", 0)
            return answer, halvings, tokens * live.JEV_INPUT_USD_PER_MTOKEN / 1_000_000
        pairs = [(docid, text[: len(text) // 2]) for docid, text in pairs]
    raise live.LiveError("Jev failed after 3 halvings")


def main() -> int:
    done = {}
    if OUT.exists():
        done = {(r["set"], r["id"]) for r in map(json.loads, OUT.read_text(encoding="utf-8").splitlines())}
    spent = sum(json.loads(line)["cost_jev"] for line in OUT.read_text(encoding="utf-8").splitlines()) if OUT.exists() else 0.0
    search = Search()
    with OUT.open("a", encoding="utf-8") as out:
        for name, rows_file, queries_file in SETS:
            questions = {r["id"]: r["question"] for r in map(json.loads, (FIXTURES / queries_file).read_text(encoding="utf-8").splitlines())}
            for row in map(json.loads, (DIR / rows_file).read_text(encoding="utf-8").splitlines()):
                if (name, row["id"]) in done:
                    continue
                if spent >= BUDGET_USD:
                    print(f"budget ${BUDGET_USD} reached")
                    return 1
                pairs = [(docid, search.text(docid)[:PROMPT_CHARS]) for docid in row["shortlist"]]
                answer, halvings, cost = ask(questions[row["id"]], pairs)
                spent += cost
                record = {
                    "id": row["id"],
                    "set": name,
                    "p_yes": float(answer["probabilities"].get("yes", 0.0)),
                    "probabilities": answer["probabilities"],
                    "choice": answer.get("choice"),
                    "halvings": halvings,
                    "cost_jev": cost,
                }
                out.write(json.dumps(record) + "\n")
                out.flush()
    print(f"done, Jev ${spent:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
