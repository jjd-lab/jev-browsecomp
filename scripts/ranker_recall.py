#!/usr/bin/env python3
"""How often each ranker's top 8 holds a gold doc on the Phase 1 main questions.

Jev's top 8 comes from the recorded arm J rows (`shortlist`). BM25's top 8 is
recomputed locally over the same 1,000 docs per question, with the same ranking
arm K would use. No API calls. Writes results/phase1_rlm/RANKER_RECALL.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from must_cite_rlm.reader import bm25_scores, rank  # noqa: E402
from must_cite_rlm.search import Search  # noqa: E402

DIR = ROOT / "results" / "phase1_rlm"
QUERIES = ROOT / "fixtures" / "browsecomp_plus_1k" / "queries.jsonl"


def main() -> int:
    jev = {r["id"]: r for r in map(json.loads, (DIR / "J.jsonl").read_text(encoding="utf-8").splitlines())}
    capped = set()
    for name in ("A.capfix.jsonl", "B.capfix.jsonl"):
        capped |= {r["id"] for r in map(json.loads, (DIR / name).read_text(encoding="utf-8").splitlines())}
    rows = [json.loads(line) for line in QUERIES.read_text(encoding="utf-8").splitlines()][:100]
    search = Search()
    hits = {}
    for row in rows:
        context = {docid: search.text(docid) for docid in row["docids"]}
        gold = set(row["gold_docids"])
        hits[row["id"]] = (bool(gold & set(rank(bm25_scores(row["question"], context), context))), jev[row["id"]]["gold_in_shortlist"])
    lines = [
        "# Ranker recall: does the top 8 hold a gold doc?",
        "",
        f"Phase 1 main questions 1–100, each with 1,000 docs. Jev's top 8 is from the recorded arm J rows; BM25's top 8 is recomputed over full document text. \"Hard\" = a question where arm A or B hit the v1 turn cap ({len(capped)} of 100).",
        "",
        "| Set | n | BM25 | Jev |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name, ids in (
        ("All", list(hits)),
        ("Hard", [i for i in hits if i in capped]),
        ("Easy", [i for i in hits if i not in capped]),
    ):
        lines.append(f"| {name} | {len(ids)} | {sum(hits[i][0] for i in ids)} | {sum(hits[i][1] for i in ids)} |")
    lines += [
        "",
        f"Both {sum(b and j for b, j in hits.values())}, Jev only {sum(j and not b for b, j in hits.values())}, "
        f"BM25 only {sum(b and not j for b, j in hits.values())}, neither {sum(not b and not j for b, j in hits.values())}.",
        "",
    ]
    (DIR / "RANKER_RECALL.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
