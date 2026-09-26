"""BM25 search over the full BrowseComp-Plus corpus via SQLite FTS5.

The index lives in the gitignored corpus cache and is built from the pinned
parquet shards. rowid is the native numeric docid. FTS5's bm25() uses k1=1.2
and b=0.75 with its own unicode61 tokenizer; query terms come from the arm C
tokenizer and are OR'd, so a query is a bag of words, not a phrase.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from must_cite_rlm.arms import _term_counts
from must_cite_rlm.browsecomp import CORPUS_CACHE, CORPUS_SHARDS

INDEX_PATH = CORPUS_CACHE / "fts.sqlite"


def build_index(cache: Path = CORPUS_CACHE, path: Path = INDEX_PATH) -> Path:
    import pyarrow.parquet as pq

    partial = path.with_suffix(".part")
    partial.unlink(missing_ok=True)
    db = sqlite3.connect(partial)
    db.execute("CREATE VIRTUAL TABLE docs USING fts5(text, tokenize='unicode61')")
    for name in CORPUS_SHARDS:
        for batch in pq.ParquetFile(cache / name).iter_batches(columns=["docid", "text"], batch_size=2000):
            db.executemany(
                "INSERT INTO docs(rowid, text) VALUES (?, ?)",
                zip((int(d) for d in batch.column("docid").to_pylist()), batch.column("text").to_pylist()),
            )
        db.commit()
    db.execute("INSERT INTO docs(docs) VALUES ('optimize')")
    db.commit()
    db.close()
    partial.rename(path)
    return path


class Search:
    def __init__(self, path: Path = INDEX_PATH) -> None:
        if not path.exists():
            raise FileNotFoundError(f"{path} is missing; run scripts/build_browsecomp_plus_corpus_run.py --index")
        self._path = path

    def _db(self) -> sqlite3.Connection:
        # One connection per call keeps this safe across worker threads.
        return sqlite3.connect(f"file:{self._path}?mode=ro", uri=True)

    def query(self, text: str, n: int) -> list[tuple[str, float]]:
        terms = list(_term_counts(text))
        if not terms:
            return []
        match = " OR ".join(f'"{term}"' for term in terms)
        with self._db() as db:
            rows = db.execute(
                "SELECT rowid, bm25(docs) FROM docs WHERE docs MATCH ? ORDER BY bm25(docs) LIMIT ?", (match, n)
            ).fetchall()
        # bm25() is lower-is-better; flip it so higher is better like the rest of the repo.
        return [(str(rowid), -score) for rowid, score in rows]

    def text(self, docid: str) -> str:
        with self._db() as db:
            row = db.execute("SELECT text FROM docs WHERE rowid = ?", (int(docid),)).fetchone()
        if row is None:
            raise KeyError(docid)
        return row[0]
