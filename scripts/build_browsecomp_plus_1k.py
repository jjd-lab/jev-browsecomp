#!/usr/bin/env python3
"""Freeze a BrowseComp-Plus (1K documents) set, the RLM paper's long-context setting.

Zhang, Kraska, Khattab (arXiv 2512.24601, §3.1) sample 150 queries and give
each 1,000 corpus documents that always include its gold and evidence docs.
Their exact draw is not published, so this one is seeded here: 150 of the 830
queries, then per query its gold and evidence docids plus a random fill from
the full corpus, in a shuffled order.

Writes fixtures/browsecomp_plus_1k/queries.jsonl (ids only; texts come from the
corpus FTS index) and PACK.json. The main run uses the first N_MAIN queries.
holdout.jsonl is the last N_HOLDOUT, disjoint from those, with their gold and
evidence docids swapped for more random fill, so no document answers them. Needs pyarrow, the six query shards in
.cache/browsecomp_plus_queries/, and the FTS index from
scripts/build_browsecomp_plus_corpus_run.py --index. Pytest does not run this.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import build_browsecomp_plus_pack as pack  # noqa: E402

from must_cite_rlm.browsecomp import CORPUS_REVISION, REVISION, SOURCE, select_query_ids  # noqa: E402
from must_cite_rlm.search import INDEX_PATH  # noqa: E402

OUT_DIR = ROOT / "fixtures" / "browsecomp_plus_1k"
SHARD_DIR = ROOT / ".cache" / "browsecomp_plus_queries"
SHARDS = [f"test-0000{i}-of-00006.parquet" for i in range(6)]
N_QUERIES = 150
N_DOCS = 1000
N_MAIN = 100
N_HOLDOUT = 50
SEED = 20260925


def main() -> int:
    seen: set[str] = set()
    rows = []
    for name in SHARDS:
        rows += pack._read_shard(SHARD_DIR / name, seen)
    by_id = {row["query_id"]: row for row in rows}
    chosen = select_query_ids(sorted(by_id, key=int), N_QUERIES, SEED)

    with sqlite3.connect(f"file:{INDEX_PATH}?mode=ro", uri=True) as db:
        corpus = [str(rowid) for (rowid,) in db.execute("SELECT rowid FROM docs ORDER BY rowid")]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    held = []
    with (OUT_DIR / "queries.jsonl").open("w", encoding="utf-8") as out:
        for position, qid in enumerate(chosen):
            row = by_id[qid]
            gold = [doc["docid"] for doc in row["gold_docs"]]
            evidence = [doc["docid"] for doc in row["evidence_docs"]]
            needed = list(dict.fromkeys(gold + evidence))
            taken = set(needed)
            fill = select_query_ids([d for d in corpus if d not in taken], N_DOCS - len(needed), SEED + int(qid))
            docids = select_query_ids(needed + fill, N_DOCS, SEED - int(qid))
            if position >= N_QUERIES - N_HOLDOUT:
                spare = select_query_ids([d for d in corpus if d not in taken and d not in fill], len(needed), SEED * 2 + int(qid))
                swap = dict(zip(needed, spare))
                held.append((qid, row, gold, evidence, [swap.get(d, d) for d in docids]))
            out.write(
                json.dumps(
                    {
                        "id": qid,
                        "question": row["query"],
                        "answer": row["answer"],
                        "gold_docids": gold,
                        "evidence_docids": evidence,
                        "docids": docids,
                    }
                )
                + "\n"
            )
    with (OUT_DIR / "holdout.jsonl").open("w", encoding="utf-8") as out:
        for qid, row, gold, evidence, docids in held:
            out.write(
                json.dumps(
                    {
                        "id": qid,
                        "question": row["query"],
                        "answer": row["answer"],
                        "gold_docids": gold,
                        "evidence_docids": evidence,
                        "docids": docids,
                        "held_out": True,
                    }
                )
                + "\n"
            )
    (OUT_DIR / "PACK.json").write_text(
        json.dumps(
            {
                "source": SOURCE,
                "revision": REVISION,
                "corpus_revision": CORPUS_REVISION,
                "n": N_QUERIES,
                "docs_per_query": N_DOCS,
                "main": N_MAIN,
                "holdout": N_HOLDOUT,
                "seed": SEED,
                "draw": "select_query_ids over the 830 query ids sorted numerically; fill and order seeded per query",
                "canary": pack.CANARY,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(OUT_DIR / "queries.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
