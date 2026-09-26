#!/usr/bin/env python3
"""Rank the full BrowseComp-Plus corpus with BM25 for every pack query.

Reads the pinned Tevatron/browsecomp-plus-corpus shards (~100K documents,
1.76 GB parquet) from a gitignored cache and writes two things:

- fixtures/browsecomp_plus/corpus_bm25.jsonl: the top CORPUS_TOP_N docids and
  scores per query. Small, frozen, in git.
- .cache/browsecomp_plus_corpus/docs.jsonl: the text of every docid in that
  run. Not in git.

BM25 is the arm C formula and tokenizer, with N, df, and avgdl taken over the
whole corpus. Only the pack's query terms are counted, so no index is built.
Needs pyarrow. Pytest does not run this script.

    python3 scripts/build_browsecomp_plus_corpus_run.py --download
"""

from __future__ import annotations

import argparse
import heapq
from array import array
import json
import math
import sys
import urllib.request
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from must_cite_rlm.arms import BM25_B, BM25_K1, _term_counts
from must_cite_rlm.browsecomp import (
    CORPUS_CACHE,
    CORPUS_REVISION,
    CORPUS_RUN_PATH,
    CORPUS_SHARDS,
    CORPUS_SOURCE,
    CORPUS_TOP_N,
    load_pack,
)


def _download(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    for name in CORPUS_SHARDS:
        path = cache / name
        if path.exists():
            continue
        url = f"https://huggingface.co/datasets/{CORPUS_SOURCE}/resolve/{CORPUS_REVISION}/data/{name}"
        print(f"download {name}", file=sys.stderr)
        partial = path.with_suffix(".part")
        urllib.request.urlretrieve(url, partial)
        partial.rename(path)


Postings = dict[str, tuple[array, array]]


def _count_shard(args: tuple[Path, frozenset[str]]) -> tuple[list[str], array, Postings]:
    """Doc ids, doc lengths, and query-term postings (row indexes, tfs) for one shard."""
    import pyarrow.parquet as pq

    path, vocab = args
    docids: list[str] = []
    lengths = array("i")
    postings: Postings = {}
    parquet = pq.ParquetFile(path)
    for batch in parquet.iter_batches(columns=["docid", "text"], batch_size=2000):
        for docid, text in zip(batch.column("docid").to_pylist(), batch.column("text").to_pylist(), strict=True):
            row = len(docids)
            counts = _term_counts(text or "")
            docids.append(docid)
            lengths.append(sum(counts.values()))
            for term in vocab.intersection(counts):
                rows, tfs = postings.setdefault(term, (array("i"), array("i")))
                rows.append(row)
                tfs.append(counts[term])
    return docids, lengths, postings


def _texts(args: tuple[Path, frozenset[str]]) -> dict[str, str]:
    import pyarrow.parquet as pq

    path, wanted = args
    found: dict[str, str] = {}
    for batch in pq.ParquetFile(path).iter_batches(columns=["docid", "text"], batch_size=2000):
        for docid, text in zip(batch.column("docid").to_pylist(), batch.column("text").to_pylist(), strict=True):
            if docid in wanted:
                found[docid] = text
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--download", action="store_true", help="Fetch missing corpus shards into the cache.")
    parser.add_argument("--cache", type=Path, default=CORPUS_CACHE)
    parser.add_argument("--index", action="store_true", help="Build only the SQLite FTS5 search index in the cache.")
    args = parser.parse_args(argv)
    if args.download:
        _download(args.cache)
    if args.index:
        from must_cite_rlm.search import build_index

        print(build_index(args.cache, args.cache / "fts.sqlite"))
        return 0
    paths = [args.cache / name for name in CORPUS_SHARDS]
    missing = [path.name for path in paths if not path.exists()]
    if missing:
        parser.error(f"missing shards {missing}; pass --download")

    pools, _ = load_pack()
    queries = {pool.gold.id: list(_term_counts(pool.gold.text)) for pool in pools}
    vocab = frozenset(term for terms in queries.values() for term in terms)

    with ProcessPoolExecutor(max_workers=len(paths)) as pool:
        shards = list(pool.map(_count_shard, [(path, vocab) for path in paths]))

    docids: list[str] = []
    lengths = array("i")
    postings: Postings = {}
    for shard_ids, shard_lengths, shard_postings in shards:
        offset = len(docids)
        docids += shard_ids
        lengths.extend(shard_lengths)
        for term, (rows, tfs) in shard_postings.items():
            merged_rows, merged_tfs = postings.setdefault(term, (array("i"), array("i")))
            merged_rows.extend(row + offset for row in rows)
            merged_tfs.extend(tfs)
    if len(set(docids)) != len(docids):
        raise SystemExit("duplicate docids in corpus")
    n = len(docids)
    avgdl = sum(lengths) / n

    rows = []
    for pool in pools:
        scores: dict[int, float] = {}
        for term in queries[pool.gold.id]:
            hit_rows, hit_tfs = postings.get(term, (array("i"), array("i")))
            idf = math.log(1.0 + (n - len(hit_rows) + 0.5) / (len(hit_rows) + 0.5))
            for row, tf in zip(hit_rows, hit_tfs):
                denom = tf + BM25_K1 * (1.0 - BM25_B + BM25_B * lengths[row] / avgdl)
                scores[row] = scores.get(row, 0.0) + idf * (tf * (BM25_K1 + 1.0)) / denom
        top = heapq.nsmallest(CORPUS_TOP_N, scores.items(), key=lambda item: (-item[1], docids[item[0]]))
        rows.append({"id": pool.gold.id, "hits": [[docids[row], round(score, 4)] for row, score in top]})

    header = {
        "source": CORPUS_SOURCE,
        "revision": CORPUS_REVISION,
        "n_docs": n,
        "avgdl": round(avgdl, 2),
        "k1": BM25_K1,
        "b": BM25_B,
        "top_n": CORPUS_TOP_N,
    }
    CORPUS_RUN_PATH.write_text(
        json.dumps(header) + "\n" + "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    print(CORPUS_RUN_PATH)

    wanted = frozenset(docid for row in rows for docid, _ in row["hits"])
    with ProcessPoolExecutor(max_workers=len(paths)) as pool:
        texts: dict[str, str] = {}
        for found in pool.map(_texts, [(path, wanted) for path in paths]):
            texts.update(found)
    out = args.cache / "docs.jsonl"
    with out.open("w", encoding="utf-8") as handle:
        for docid in sorted(texts, key=int):
            handle.write(json.dumps({"docid": docid, "text": texts[docid]}) + "\n")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
