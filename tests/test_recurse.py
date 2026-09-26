from __future__ import annotations

import json

import pytest

from must_cite_rlm.browsecomp import PACK_DIR, PROMPT_CHARS, _doc_node, citable_span, load_pack
from must_cite_rlm.live import LiveError, Meter
from must_cite_rlm.recurse import BATCH, KEEP, MAX_CHUNKS, CorpusPool, _scored, flat, load_corpus_pools, recurse
from must_cite_rlm.types import Act, Gold, NodeId

# The BrowseComp-Plus pack is not in the public copy (its questions and answers stay
# unpublished); scripts/build_browsecomp_plus_pack.py regenerates it.
needs_pack = pytest.mark.skipif(
    not (PACK_DIR / "gold.jsonl").exists(), reason="BrowseComp-Plus pack not built; run scripts/build_browsecomp_plus_pack.py"
)


def _pool(n_docs: int, gold: str, long_doc: str | None = None) -> CorpusPool:
    body = {}
    for i in range(n_docs):
        docid = str(100 + i)
        body[NodeId(docid)] = f"Document {docid} has a plain sentence long enough to cite here. " * 20
    if long_doc is not None:
        body[NodeId(long_doc)] = "x" * (PROMPT_CHARS * (MAX_CHUNKS + 3))
        body[NodeId(long_doc)] = "Long document opening sentence that is citable text. " + body[NodeId(long_doc)]
    nodes = {node_id: _doc_node(node_id, text, *citable_span(text)) for node_id, text in body.items()}
    return CorpusPool(Gold("q1", "Which doc?", "act", (NodeId(gold),)), tuple(body), nodes, body)


def test_recurse_screens_expands_and_decides_on_best_chunks(monkeypatch) -> None:
    pool = _pool(20, gold="117", long_doc="119")
    calls: list[list[str]] = []

    def nouls(question, pairs, meter):
        calls.append([key for key, _ in pairs])
        assert len(pairs) <= BATCH
        # Higher docid scores higher at screen; chunk 1 of each doc beats chunk 0.
        return {key: (0.9 if key.endswith("#1") else 0.5) if "#" in key else int(key) / 1000 for key, _ in pairs}

    seen: list[list[tuple[str, str]]] = []

    def decide(question, pairs, meter, trace, transport=None):
        seen.append(pairs)
        trace["raw"] = "{}"
        return Act((NodeId("117"),))

    monkeypatch.setattr("must_cite_rlm.live.jev_decide", decide)
    trial, final, detail, _ = recurse(pool, Meter(), {}, nouls=nouls)
    screen_calls = -(-20 // BATCH)
    assert [key for call in calls[:screen_calls] for key in call] == list(pool.ranked)
    assert list(final) == [str(119 - i) for i in range(KEEP)]
    long_chunks = [key for call in calls[screen_calls:] for key in call if key.startswith("119#")]
    assert len(long_chunks) == MAX_CHUNKS
    assert [node_id for node_id, _ in seen[0]] == list(final)
    assert seen[0][0][1] == pool.body["119"][PROMPT_CHARS : 2 * PROMPT_CHARS]
    assert detail["best_chunk"]["119"] == 0.9
    assert [cite.node_id for cite in trial.cites] == ["117"]


def test_flat_decides_on_bm25_top_keep(monkeypatch) -> None:
    pool = _pool(12, gold="100")
    seen: list[list[str]] = []

    def decide(question, pairs, meter, trace, transport=None):
        seen.append([node_id for node_id, _ in pairs])
        assert all(len(text) <= PROMPT_CHARS for _, text in pairs)
        trace["raw"] = "{}"
        return Act((NodeId("100"),))

    monkeypatch.setattr("must_cite_rlm.live.jev_decide", decide)
    trial, final, _, _ = flat(pool, Meter(), {})
    assert seen == [list(pool.ranked[:KEEP])] and list(final) == list(pool.ranked[:KEEP])


@needs_pack
def test_load_corpus_pools_holdout_drops_gold(tmp_path) -> None:
    pools, _ = load_pack()
    first = pools[0]
    gold = first.gold.node_ids[0]
    other = "999999"
    run = tmp_path / "run.jsonl"
    rows = [{"id": pool.gold.id, "hits": [[gold, 2.0], [other, 1.0]]} for pool in pools]
    run.write_text(json.dumps({"top_n": 2}) + "\n" + "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    docs = tmp_path / "docs.jsonl"
    docs.write_text(
        json.dumps({"docid": gold, "text": first.body[gold]}) + "\n"
        + json.dumps({"docid": other, "text": "Another plain document with enough text to cite in full."}) + "\n",
        encoding="utf-8",
    )
    kept = load_corpus_pools(run_path=run, docs_path=docs)
    held = load_corpus_pools(holdout=True, run_path=run, docs_path=docs)
    assert kept[0].ranked == (gold, other)
    assert held[0].ranked == (other,)
    assert held[0].gold.decision == "abstain" and held[0].gold.node_ids == ()


def test_scored_halves_a_batch_jev_rejects() -> None:
    sizes: list[int] = []

    def nouls(question, pairs, meter):
        sizes.append(len(pairs))
        if len(pairs) > 2:
            raise LiveError("HTTP Error 400: Bad Request")
        return {key: 0.5 for key, _ in pairs}

    pairs = [(str(i), "t") for i in range(8)]
    assert _scored(nouls, "q", pairs, Meter()) == {str(i): 0.5 for i in range(8)}
    assert sizes == [8, 4, 2, 2, 4, 2, 2]


class _FakeSearch:
    def __init__(self, docs: dict[str, str]) -> None:
        self.docs = docs
        self.queries: list[str] = []

    def query(self, text: str, n: int) -> list[tuple[str, float]]:
        self.queries.append(text)
        return [(docid, 1.0) for docid in self.docs][:n]

    def text(self, docid: str) -> str:
        return self.docs[docid]


def test_hybrid_searches_screens_new_docs_and_skips_held_out(monkeypatch) -> None:
    from dataclasses import replace

    from must_cite_rlm.recurse import ROUNDS, hybrid

    pool = replace(_pool(10, gold="100"), held_out=(NodeId("555"),))
    plain = "A found document with a plain citable sentence in it. " * 10
    search = _FakeSearch({"555": plain, "777": plain, "100": plain})
    rewrites: list[tuple[list[str], list[str]]] = []

    def rewrite(question, tried, snippets):
        rewrites.append((tried, [docid for docid, _ in snippets]))
        return [f"query {len(tried)}"]

    screened: list[str] = []

    def nouls(question, pairs, meter):
        screened.extend(key for key, _ in pairs if "#" not in key)
        return {key: 0.99 if key.startswith("777") else 0.1 for key, _ in pairs}

    def decide(question, pairs, meter, trace, transport=None):
        trace["raw"] = "{}"
        return Act((NodeId("777"),))

    monkeypatch.setattr("must_cite_rlm.live.jev_decide", decide)
    trial, final, detail, nodes = hybrid(pool, Meter(), {}, search=search, rewrite=rewrite, nouls=nouls)
    assert len(rewrites) == ROUNDS
    assert rewrites[0][0] == [] and rewrites[1][0] == ["query 0"]
    assert screened.count("777") == 1 and "555" not in screened
    assert detail["added"] == 1 and final[0] == "777"
    assert "777" in nodes and [cite.node_id for cite in trial.cites] == ["777"]


def test_search_ranks_by_fts5_bm25(tmp_path) -> None:
    import sqlite3

    from must_cite_rlm.search import Search

    path = tmp_path / "fts.sqlite"
    db = sqlite3.connect(path)
    db.execute("CREATE VIRTUAL TABLE docs USING fts5(text, tokenize='unicode61')")
    db.executemany(
        "INSERT INTO docs(rowid, text) VALUES (?, ?)",
        [(1, "granite quarry near the river"), (2, "granite granite quarry"), (3, "nothing relevant")],
    )
    db.commit()
    db.close()
    search = Search(path)
    hits = search.query("Which granite quarry?", 5)
    assert [docid for docid, _ in hits] == ["2", "1"]
    assert hits[0][1] > hits[1][1]
    assert search.text("3") == "nothing relevant"
    assert search.query("the and for", 5) == []


def test_narrow_decides_on_top_docs_with_their_best_chunks_in_order(monkeypatch) -> None:
    from must_cite_rlm.recurse import DECIDE_CHUNKS, DECIDE_DOCS, narrow

    pool = _pool(6, gold="102", long_doc="199")
    ranked = (NodeId("199"),) + tuple(node_id for node_id in pool.ranked if node_id != "199")

    def nouls(question, pairs, meter):
        # Chunks 4 and 1 of the long doc score highest, in that order.
        return {key: {"199#4": 0.9, "199#1": 0.8}.get(key, 0.1) for key, _ in pairs}

    seen: list[list[tuple[str, str]]] = []

    def decide(question, pairs, meter, trace, transport=None):
        seen.append(pairs)
        trace["raw"] = "{}"
        return Act((NodeId("102"),))

    monkeypatch.setattr("must_cite_rlm.live.jev_decide", decide)
    trial, final, detail = narrow(pool.gold, ranked, pool.body, pool.nodes, Meter(), {}, nouls=nouls)
    assert final == ranked[:DECIDE_DOCS]
    assert [node_id for node_id, _ in seen[0]] == list(final)
    assert detail["chunks"]["199"] == ["199#1", "199#4"]
    text = pool.body["199"]
    assert seen[0][0][1] == text[PROMPT_CHARS : 2 * PROMPT_CHARS] + "\n[...]\n" + text[4 * PROMPT_CHARS : 5 * PROMPT_CHARS]
    assert all(len(detail["chunks"][node_id]) <= DECIDE_CHUNKS for node_id in final)
    assert [cite.node_id for cite in trial.cites] == ["102"]


@needs_pack
def test_pools_from_trace_orders_by_decide_noul_and_holds_out_gold(tmp_path) -> None:
    from must_cite_rlm.recurse import pools_from_trace

    pools, _ = load_pack()
    gold = pools[0].gold
    plain = "A plain replayed document with enough text to cite it here."
    docids = ["11", gold.node_ids[0], "13"]
    answers = {"11": {"noul": 0.2}, gold.node_ids[0]: {"noul": 0.9}, "13": {"noul": 0.5}}
    trace = tmp_path / "t.jsonl"
    trace.write_text(json.dumps({"id": gold.id, "candidates": docids, "raw": {"answers": answers}}) + "\n", encoding="utf-8")
    search = _FakeSearch({docid: plain for docid in docids})
    kept = pools_from_trace(trace, search=search)
    held = pools_from_trace(trace, holdout=True, search=search)
    assert kept[0].ranked == (gold.node_ids[0], "13", "11")
    assert held[0].ranked == ("13", "11") and held[0].gold.decision == "abstain"


def test_decide_fitting_halves_text_until_jev_accepts(monkeypatch) -> None:
    from must_cite_rlm.recurse import _decide_fitting

    lengths: list[int] = []

    def decide(question, pairs, meter, trace, transport=None):
        lengths.append(len(pairs[0][1]))
        if lengths[-1] > 100:
            raise LiveError("HTTP Error 400: Bad Request")
        return Act((NodeId("a"),))

    monkeypatch.setattr("must_cite_rlm.live.jev_decide", decide)
    assert _decide_fitting("q", [(NodeId("a"), "x" * 400)], Meter(), {}) == Act((NodeId("a"),))
    assert lengths == [400, 200, 100]
