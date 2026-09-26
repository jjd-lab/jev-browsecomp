#!/usr/bin/env python3
"""Add the post-hoc Jev verification gate to every result row that lacks one.

Same gate for every arm: the question, the row's exact answer, and the cited
docs (each shown as the window around the answer's first mention). Rewrites
results/phase1_rlm/<file>.jsonl in place; rows that already have `gate_post` are kept.

    python3 scripts/gate_rlm_jev.py A.jsonl B.jsonl
    python3 scripts/gate_rlm_jev.py --rejudge A.jsonl   # also relabel rows judged by another model
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from must_cite_rlm.live import LiveError, Meter  # noqa: E402
from must_cite_rlm.rlm_jev import JUDGE_MODEL, judge, verify_gate  # noqa: E402
from must_cite_rlm.search import Search  # noqa: E402

DIR = ROOT / "results" / "phase1_rlm"
QUERIES = ROOT / "fixtures" / "browsecomp_plus_1k" / "queries.jsonl"


def _gate(question: str, answer: str | None, cited: dict[str, str], meter: Meter) -> dict:
    """Jev occasionally returns a transient 500; retry before giving up."""
    for attempt in range(4):
        try:
            return verify_gate(question, answer, cited, meter)
        except LiveError:
            if attempt == 3:
                raise
            time.sleep(5 * 2**attempt)


def main(argv: list[str]) -> int:
    rejudge = "--rejudge" in argv
    queries = {r["id"]: r for r in map(json.loads, QUERIES.read_text(encoding="utf-8").splitlines())}
    search = Search()
    for name in (a for a in argv if a != "--rejudge"):
        path = DIR / name
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        meter = Meter()
        judge_cost = 0.0
        for row in rows:
            query = queries[row["id"]]
            if rejudge and row["response"] and row.get("judge_model") != JUDGE_MODEL:
                row_meter = Meter()
                verdict = judge(query["question"], row["response"], query["answer"], row_meter)
                judge_cost += row_meter.cost_usd
                row.update(
                    {
                        "correct": verdict["correct"],
                        "judge_parsed": verdict["parsed"],
                        "judge_model": verdict["model"],
                        "judge_raw": verdict["raw"],
                        "cost_judge": row["cost_judge"] + row_meter.cost_usd,
                    }
                )
            if "gate_post" not in row:
                cited = {docid: search.text(docid) for docid in row["cited"]}
                row["gate_post"] = _gate(query["question"], row["exact_answer"], cited, meter)
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        print(f"{name}: {len(rows)} rows, gate Jev ${meter.cost_usd:.4f}, judge ${judge_cost:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
