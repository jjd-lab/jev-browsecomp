"""Arms R and H: typed-decide recursion over the corpus BM25 top 100 (Phase 0c step 5).

Every hop is Jev over ids. Code splits and slices text; the model never sees
more than one decide call's worth.

1. Screen: per-doc Noul over the first PROMPT_CHARS of each doc, BATCH ids per call.
2. Expand: the KEEP best docs are cut into PROMPT_CHARS chunks (at most
   MAX_CHUNKS per doc). Per-chunk Noul; a doc keeps its best chunk.
3. Decide: one `both` call over the KEEP docs, each shown as its best chunk.

Arm H adds search before step 2: for ROUNDS rounds, Claude sees the question
and snippets of the best screened docs and writes QUERIES keyword queries. Each
query's top PER_QUERY unseen docs are screened like the rest. Claude only writes
queries; every select and act/abstain call stays Jev.

Narrow (arm N) replays a finished run's final KEEP from its trace: the
DECIDE_DOCS docs with the highest decide Noul are re-expanded, and one more
`both` decide sees each as its DECIDE_CHUNKS best chunks in document order.

The flat baseline is step 3 alone on the BM25 top KEEP, first PROMPT_CHARS each.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from must_cite_rlm.arms import _trial
from must_cite_rlm.browsecomp import (
    CORPUS_CACHE,
    CORPUS_RUN_PATH,
    PROMPT_CHARS,
    _doc_node,
    citable_span,
    load_pack,
)
from must_cite_rlm import live
from must_cite_rlm.live import JEV_INPUT_USD_PER_MTOKEN, LiveError, Meter, _noul_questions
from must_cite_rlm.tree import Node
from must_cite_rlm.types import Gold, NodeId, Trial

BATCH = 8
KEEP = 8
MAX_CHUNKS = 10
DECIDE_DOCS = 4
DECIDE_CHUNKS = 2
ROUNDS = 3
QUERIES = 3
PER_QUERY = 20
SNIPPETS = 5
SNIPPET_CHARS = 1500

REWRITE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "queries",
        "description": "Return new keyword queries for the corpus search engine.",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"queries": {"type": "array", "items": {"type": "string"}}},
            "required": ["queries"],
        },
    },
}

Nouls = Callable[[str, list[tuple[str, str]], Meter], dict[str, float]]
Rewrite = Callable[[str, list[str], list[tuple[str, str]]], list[str]]


@dataclass(frozen=True)
class CorpusPool:
    gold: Gold
    ranked: tuple[NodeId, ...]
    nodes: Mapping[NodeId, Node]
    body: Mapping[NodeId, str]
    # Gold docids dropped by --holdout-gold, so search in arm H cannot bring them back.
    held_out: tuple[NodeId, ...] = ()


def load_corpus_pools(
    holdout: bool = False, run_path: Path = CORPUS_RUN_PATH, docs_path: Path = CORPUS_CACHE / "docs.jsonl"
) -> tuple[CorpusPool, ...]:
    """Pack golds with their corpus BM25 top 100. Docs with no citable span are dropped."""
    if not docs_path.exists():
        raise FileNotFoundError(f"{docs_path} is missing; run scripts/build_browsecomp_plus_corpus_run.py")
    _header, *rows = [json.loads(line) for line in run_path.read_text(encoding="utf-8").splitlines()]
    texts: dict[str, str] = {}
    with docs_path.open(encoding="utf-8") as handle:
        for line in handle:
            doc = json.loads(line)
            texts[doc["docid"]] = doc["text"]
    golds = {pool.gold.id: pool.gold for pool in load_pack()[0]}
    pools = []
    for row in rows:
        gold = golds[row["id"]]
        nodes: dict[NodeId, Node] = {}
        for docid, _score in row["hits"]:
            if holdout and docid in gold.node_ids:
                continue
            span = citable_span(texts[docid])
            if span is not None:
                nodes[NodeId(docid)] = _doc_node(docid, texts[docid], *span)
        held_out = gold.node_ids if holdout else ()
        if holdout:
            gold = Gold(gold.id, gold.text, "abstain", ())
        pools.append(CorpusPool(gold, tuple(nodes), nodes, {node_id: texts[node_id] for node_id in nodes}, held_out))
    return tuple(pools)


def jev_nouls(question: str, pairs: list[tuple[str, str]], meter: Meter) -> dict[str, float]:
    """One Jev call asking only the per-id Noul questions."""
    lines = [question, ""] + [f"{key}\n{text}" for key, text in pairs]
    body = {
        "model": os.environ.get("TYPESAFE_DEFAULT_MODEL", "jev-latest"),
        "state": "\n".join(lines),
        "questions": _noul_questions(pairs),
    }
    payload, latency_ms = live._jev_call(body)
    tokens = payload.get("usage", {}).get("input_tokens", 0)
    meter.add(tokens * JEV_INPUT_USD_PER_MTOKEN / 1_000_000, latency_ms)
    answers = payload.get("answers", {})
    return {key: float(answers[key]["noul"]) for key, _ in pairs if key in answers}


def _scored(nouls: Nouls, question: str, pairs: list[tuple[str, str]], meter: Meter) -> dict[str, float]:
    """Jev rejects inputs past its token cap, so a failing batch is halved and retried."""
    try:
        return nouls(question, pairs, meter)
    except LiveError:
        if len(pairs) == 1:
            raise
        half = len(pairs) // 2
        return {**_scored(nouls, question, pairs[:half], meter), **_scored(nouls, question, pairs[half:], meter)}


def _batched(items: Sequence, size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _screen(nouls: Nouls, question: str, ids: Sequence[NodeId], body: Mapping[NodeId, str], meter: Meter) -> dict[str, float]:
    scores: dict[str, float] = {}
    for batch in _batched(ids, BATCH):
        scores.update(_scored(nouls, question, [(node_id, body[node_id][:PROMPT_CHARS]) for node_id in batch], meter))
    return scores


def _expand_and_decide(
    gold: Gold,
    kept: Sequence[NodeId],
    body: Mapping[NodeId, str],
    nodes: Mapping[NodeId, Node],
    nouls: Nouls,
    meter: Meter,
    trace: dict[str, str],
    arm: str,
) -> tuple[Trial, tuple[NodeId, ...], dict[str, float]]:
    chunks = [chunk for node_id in kept for chunk in _chunks(node_id, body[node_id])]
    chunk_scores: dict[str, float] = {}
    for batch in _batched(chunks, BATCH):
        chunk_scores.update(_scored(nouls, gold.text, list(batch), meter))
    best: dict[str, tuple[float, str]] = {}
    for key, text in chunks:
        node_id = key.split("#")[0]
        score = chunk_scores.get(key, 0.0)
        if node_id not in best or score > best[node_id][0]:
            best[node_id] = (score, text)
    final = tuple(NodeId(node_id) for node_id in kept)
    decision = live.jev_decide(gold.text, [(node_id, best[node_id][1]) for node_id in final], meter, trace)
    trial = _trial(gold, arm, decision, trace.get("raw", ""), nodes)
    return trial, final, {node_id: best[node_id][0] for node_id in final}


def _decide_fitting(question: str, pairs: list[tuple[NodeId, str]], meter: Meter, trace: dict[str, str]):
    """Token-dense text can pass Jev's cap even at PROMPT_CHARS; halve what each id shows and retry."""
    for _ in range(3):
        try:
            return live.jev_decide(question, pairs, meter, trace)
        except LiveError:
            pairs = [(node_id, text[: len(text) // 2]) for node_id, text in pairs]
    return live.jev_decide(question, pairs, meter, trace)


def _chunks(node_id: NodeId, text: str) -> list[tuple[str, str]]:
    count = min(MAX_CHUNKS, -(-len(text) // PROMPT_CHARS))
    return [(f"{node_id}#{i}", text[i * PROMPT_CHARS : (i + 1) * PROMPT_CHARS]) for i in range(count)]


def narrow(
    gold: Gold,
    ranked: Sequence[NodeId],
    body: Mapping[NodeId, str],
    nodes: Mapping[NodeId, Node],
    meter: Meter,
    trace: dict[str, str],
    nouls: Nouls | None = None,
) -> tuple[Trial, tuple[NodeId, ...], dict]:
    """One more decide over the top DECIDE_DOCS of `ranked`, each shown as its best DECIDE_CHUNKS chunks."""
    nouls = nouls or jev_nouls
    final = tuple(ranked[:DECIDE_DOCS])
    chunks = [chunk for node_id in final for chunk in _chunks(node_id, body[node_id])]
    scores: dict[str, float] = {}
    for batch in _batched(chunks, BATCH):
        scores.update(_scored(nouls, gold.text, list(batch), meter))
    shown: dict[str, list[str]] = {}
    pairs = []
    for node_id in final:
        keys = [key for key, _ in _chunks(node_id, body[node_id])]
        top = sorted(keys, key=lambda key: -scores.get(key, 0.0))[:DECIDE_CHUNKS]
        shown[node_id] = sorted(top, key=lambda key: int(key.split("#")[1]))
        text = dict(_chunks(node_id, body[node_id]))
        pairs.append((node_id, "\n[...]\n".join(text[key] for key in shown[node_id])))
    decision = _decide_fitting(gold.text, pairs, meter, trace)
    return _trial(gold, "N", decision, trace.get("raw", ""), nodes), final, {"chunks": shown}


def _best(screen: Mapping[str, float], order: Sequence[NodeId], n: int) -> list[NodeId]:
    # Ties keep retrieval order.
    rank = {node_id: index for index, node_id in enumerate(order)}
    return sorted(screen, key=lambda node_id: (-screen[node_id], rank[node_id]))[:n]


Step = tuple[Trial, tuple[NodeId, ...], dict, Mapping[NodeId, Node]]


def recurse(pool: CorpusPool, meter: Meter, trace: dict[str, str], nouls: Nouls | None = None) -> Step:
    nouls = nouls or jev_nouls
    screen = _screen(nouls, pool.gold.text, pool.ranked, pool.body, meter)
    kept = _best(screen, pool.ranked, KEEP)
    trial, final, best_chunk = _expand_and_decide(pool.gold, kept, pool.body, pool.nodes, nouls, meter, trace, "R")
    detail = {"screen": {node_id: screen[node_id] for node_id in kept}, "best_chunk": best_chunk}
    return trial, final, detail, pool.nodes


def flat(pool: CorpusPool, meter: Meter, trace: dict[str, str]) -> Step:
    final = pool.ranked[:KEEP]
    pairs = [(node_id, pool.body[node_id][:PROMPT_CHARS]) for node_id in final]
    decision = live.jev_decide(pool.gold.text, pairs, meter, trace)
    return _trial(pool.gold, "F", decision, trace.get("raw", ""), pool.nodes), final, {}, pool.nodes


def claude_rewrite(meter: Meter) -> Rewrite:
    complete = live.anthropic_complete(meter)

    def rewrite(question: str, tried: list[str], snippets: list[tuple[str, str]]) -> list[str]:
        lines = [f"Question:\n{question}", "", "Queries already run:"]
        lines += [f"- {query}" for query in tried] or ["- (none)"]
        lines += ["", "Best documents found so far:"]
        lines += [f"[{docid}]\n{text}" for docid, text in snippets]
        messages = [
            {
                "role": "system",
                "content": (
                    "You search a web-document corpus with a BM25 keyword engine to find the document that answers "
                    f"the question. Write up to {QUERIES} new keyword queries: distinctive names, terms, and facts, "
                    "a few words each. Use the documents so far to follow the chain of clues. Do not repeat a query."
                ),
            },
            {"role": "user", "content": "\n".join(lines)},
        ]
        try:
            queries = json.loads(complete(messages, REWRITE_SCHEMA)).get("queries", [])
        except (json.JSONDecodeError, AttributeError):
            return []
        return [query for query in queries if isinstance(query, str) and query.strip()][:QUERIES]

    return rewrite


def hybrid(
    pool: CorpusPool,
    meter: Meter,
    trace: dict[str, str],
    search=None,
    rewrite: Rewrite | None = None,
    nouls: Nouls | None = None,
) -> Step:
    from must_cite_rlm.search import Search

    search = search or Search()
    rewrite = rewrite or claude_rewrite(meter)
    nouls = nouls or jev_nouls
    question = pool.gold.text
    body = dict(pool.body)
    nodes = dict(pool.nodes)
    order = list(pool.ranked)
    screen = _screen(nouls, question, pool.ranked, body, meter)
    tried: list[str] = []
    for _ in range(ROUNDS):
        top = _best(screen, order, SNIPPETS)
        queries = rewrite(question, list(tried), [(node_id, body[node_id][:SNIPPET_CHARS]) for node_id in top])
        added: list[NodeId] = []
        for query in queries:
            tried.append(query)
            for docid, _score in search.query(query, PER_QUERY):
                if docid in body or docid in pool.held_out:
                    continue
                text = search.text(docid)
                span = citable_span(text)
                if span is None:
                    continue
                node_id = NodeId(docid)
                body[node_id] = text
                nodes[node_id] = _doc_node(docid, text, *span)
                added.append(node_id)
        order += added
        screen.update(_screen(nouls, question, added, body, meter))
    kept = _best(screen, order, KEEP)
    trial, final, best_chunk = _expand_and_decide(pool.gold, kept, body, nodes, nouls, meter, trace, "H")
    detail = {
        "queries": tried,
        "added": len(order) - len(pool.ranked),
        "screen": {node_id: screen[node_id] for node_id in kept},
        "best_chunk": best_chunk,
    }
    return trial, final, detail, nodes


def pools_from_trace(path: Path, holdout: bool = False, search=None) -> tuple[CorpusPool, ...]:
    """A finished run's final candidates, ordered by that run's decide Noul (ties keep candidate order)."""
    from must_cite_rlm.search import Search

    search = search or Search()
    golds = {pool.gold.id: pool.gold for pool in load_pack()[0]}
    pools = []
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        gold = golds[row["id"]]
        answers = row["raw"].get("answers", {}) if isinstance(row["raw"], dict) else {}
        candidates = [NodeId(c) for c in row["candidates"] if not (holdout and c in gold.node_ids)]
        ranked = sorted(candidates, key=lambda c: -float(answers.get(c, {}).get("noul", 0.0)))
        body = {node_id: search.text(node_id) for node_id in ranked}
        nodes = {node_id: _doc_node(node_id, text, *citable_span(text)) for node_id, text in body.items()}
        held_out = gold.node_ids if holdout else ()
        if holdout:
            gold = Gold(gold.id, gold.text, "abstain", ())
        pools.append(CorpusPool(gold, tuple(ranked), nodes, body, held_out))
    return tuple(pools)
