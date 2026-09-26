"""BrowseComp-Plus smoke pack.

Flat leaves keyed by native docids. Arm C ranks the per-question pool and
calls decide(CandidateSet). Arm B's depth-1 walk is not built here.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from must_cite_rlm.arms import arm_c, stub_decide
from must_cite_rlm.tree import ROOT, Node
from must_cite_rlm.types import ArtifactId, Gold, NodeId, Span, Trial

PACK_DIR = ROOT / "fixtures" / "browsecomp_plus"
GOLD_PATH = PACK_DIR / "gold.jsonl"
PROVENANCE_PATH = PACK_DIR / "provenance.jsonl"
PACK_PATH = PACK_DIR / "PACK.json"

SOURCE = "Tevatron/browsecomp-plus"
REVISION = "144cff8e35b5eaef7e526346aa60774a9deb941f"
# Queries release only. The first file is the documented pin. The frozen pack
# also reads the next three shards of this revision: shard 0 has 43
# singleton-gold queries, and filename order through shard 3 is the first
# prefix with an eligible pool of at least 150. Shards 4 and 5 are not used.
SHARD_FILES: tuple[tuple[str, str], ...] = (
    ("test-00000-of-00006.parquet", "4ff9e93054eaee61b8d079a89b7ec4d02f16c9d05fa6e2fef7185b0786427a3a"),
    ("test-00001-of-00006.parquet", "70cc3a6781693bb013c6855f231d15159222dddf826eb19947f6f85fcabccd4e"),
    ("test-00002-of-00006.parquet", "f4fab28dcd293231da1b9da48680a19c7cdcb831df889d0691304de66016d194"),
    ("test-00003-of-00006.parquet", "e738eb7a2e76feebe60632fc279a99773586d75ce5344e205c9c53fc3071c126"),
)
SHARD = "data/" + SHARD_FILES[0][0]
SHARD_SHA256 = SHARD_FILES[0][1]
SEED = 20260924
SMOKE_N = 150
TARGET_N = 150
NEGATIVE_CAP = 4
MIN_SPAN = 40
MAX_SPAN = 400
PROMPT_CHARS = 12000

# Full corpus, for pools larger than one decide call. Shards and extracted text
# live in the gitignored cache. Only the BM25 run file is in git.
CORPUS_SOURCE = "Tevatron/browsecomp-plus-corpus"
CORPUS_REVISION = "b27b02bc3e45511b8b82a13e6f90ce761df726f6"
CORPUS_SHARDS = tuple(f"train-0000{i}-of-00007.parquet" for i in range(7))
CORPUS_TOP_N = 100
CORPUS_CACHE = ROOT / ".cache" / "browsecomp_plus_corpus"
CORPUS_RUN_PATH = PACK_DIR / "corpus_bm25.jsonl"

# Numerical Recipes LCG. select_query_ids does not use random.Random.
_LCG_A = 1664525
_LCG_C = 1013904223
_LCG_M = 0x100000000


@dataclass(frozen=True)
class Pool:
    gold: Gold
    nodes: Mapping[NodeId, Node]
    body: Mapping[NodeId, str]
    evidence_docids: tuple[str, ...]
    negative_docids: tuple[str, ...]


def citable_span(text: str, min_chars: int = MIN_SPAN, max_chars: int = MAX_SPAN) -> tuple[int, int] | None:
    """Longest double-quote-free slice, capped, as offsets into `text`."""
    best: tuple[int, int] | None = None
    start = 0
    while start <= len(text):
        mark = text.find('"', start)
        end = len(text) if mark == -1 else mark
        if best is None or end - start > best[1] - best[0]:
            best = (start, end)
        if mark == -1:
            break
        start = mark + 1
    if best is None:
        return None
    span_start, span_end = best
    span_end = min(span_end, span_start + max_chars)
    while span_end > span_start and text[span_end - 1] in " \n\r\t":
        span_end -= 1
    if span_end - span_start < min_chars:
        return None
    return span_start, span_end


def select_query_ids(ids: Sequence[str], n: int, seed: int) -> list[str]:
    """Take `n` ids from a Fisher-Yates shuffle driven by a fixed LCG."""
    if n < 1 or n > len(ids):
        raise ValueError(f"cannot select {n} ids from {len(ids)}")
    pool = list(ids)
    state = seed & 0xFFFFFFFF

    def draw(limit: int) -> int:
        nonlocal state
        state = (state * _LCG_A + _LCG_C) % _LCG_M
        return state % limit

    for i in range(len(pool) - 1, len(pool) - 1 - n, -1):
        j = draw(i + 1)
        pool[i], pool[j] = pool[j], pool[i]
    return pool[-n:]


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise ValueError(f"{path.name} row is not an object")
        rows.append(obj)
    return rows


def _doc_node(docid: str, text: str, span_start: int, span_end: int) -> Node:
    node_id = NodeId(docid)
    piece = text[span_start:span_end]
    if '"' in piece or len(piece) < MIN_SPAN or piece not in text:
        raise ValueError(f"{docid} span is not a quote-free slice")
    return Node(
        node_id,
        ArtifactId(docid),
        2,
        (),
        Span(node_id, span_start, span_end, piece),
    )


def load_pack(directory: Path = PACK_DIR) -> tuple[tuple[Pool, ...], dict[NodeId, Node]]:
    gold_rows = _load_jsonl(directory / "gold.jsonl")
    provenance_rows = _load_jsonl(directory / "provenance.jsonl")
    documents = _load_jsonl(directory / "documents.jsonl")
    pack = json.loads((directory / "PACK.json").read_text(encoding="utf-8"))
    if pack.get("source") != SOURCE or pack.get("revision") != REVISION:
        raise ValueError("PACK.json does not match the pinned BrowseComp-Plus revision")
    if pack.get("n") != len(gold_rows):
        raise ValueError("PACK.json n does not match gold.jsonl")
    negative_cap = pack.get("negative_cap", NEGATIVE_CAP)
    if not isinstance(negative_cap, int) or negative_cap < 1:
        raise ValueError("PACK.json negative_cap is missing")
    if [row["id"] for row in provenance_rows] != [row["id"] for row in gold_rows]:
        raise ValueError("provenance ids do not match gold ids")
    by_doc: dict[str, dict] = {}
    for doc in documents:
        docid = doc["docid"]
        if not isinstance(docid, str) or not docid.isdigit():
            raise ValueError(f"docid {docid!r} is not a native numeric id")
        if docid in by_doc:
            raise ValueError(f"duplicate docid {docid}")
        text = doc["text"]
        if not isinstance(text, str):
            raise ValueError(f"{docid} text is not a string")
        start = doc["span_start"]
        end = doc["span_end"]
        if not isinstance(start, int) or not isinstance(end, int):
            raise ValueError(f"{docid} span offsets are not ints")
        piece = text[start:end]
        if '"' in piece or len(piece) < MIN_SPAN:
            raise ValueError(f"{docid} span is not a quote-free slice of the document")
        if not isinstance(doc.get("url"), str) or not doc["url"]:
            raise ValueError(f"{docid} is missing a url")
        by_doc[docid] = doc
    pools: list[Pool] = []
    nodes: dict[NodeId, Node] = {}
    for gold_row, prov in zip(gold_rows, provenance_rows, strict=True):
        qid = gold_row["id"]
        if qid != prov["id"] or not isinstance(qid, str):
            raise ValueError("gold and provenance ids disagree")
        question = gold_row["question"]
        decision = gold_row["gold_decision"]
        raw_ids = gold_row["gold_node_ids"]
        if not isinstance(question, str) or not question:
            raise ValueError(f"{qid} question is empty")
        if not isinstance(prov.get("answer"), str):
            raise ValueError(f"{qid} answer is missing")
        if decision != "act" or not isinstance(raw_ids, list) or len(raw_ids) < 1:
            raise ValueError(f"{qid} gold must be act with at least one docid")
        if not all(isinstance(item, str) and item.isdigit() for item in raw_ids):
            raise ValueError(f"{qid} gold id is not a native docid")
        evidence = prov["evidence_docids"]
        negatives = prov["negative_docids"]
        if not isinstance(evidence, list) or not isinstance(negatives, list):
            raise ValueError(f"{qid} candidate lists are missing")
        if any(item not in evidence for item in raw_ids):
            raise ValueError(f"{qid} gold docid is not in evidence_docids")
        if len(negatives) != negative_cap:
            raise ValueError(f"{qid} expected {negative_cap} negatives, found {len(negatives)}")
        if set(negatives) & set(evidence):
            raise ValueError(f"{qid} negatives overlap evidence")
        pool_nodes: dict[NodeId, Node] = {}
        body: dict[NodeId, str] = {}
        for docid in [*evidence, *negatives]:
            if not isinstance(docid, str) or docid not in by_doc:
                raise ValueError(f"{qid} missing document {docid}")
            doc = by_doc[docid]
            node = _doc_node(docid, doc["text"], doc["span_start"], doc["span_end"])
            prior = nodes.get(node.id)
            if prior is not None and prior.span != node.span:
                raise ValueError(f"docid {docid} span disagrees across questions")
            nodes[node.id] = node
            pool_nodes[node.id] = node
            body[node.id] = doc["text"]
        pools.append(
            Pool(
                Gold(qid, question, "act", tuple(NodeId(item) for item in raw_ids)),
                pool_nodes,
                body,
                tuple(evidence),
                tuple(negatives),
            )
        )
    if len(pools) != pack["n"]:
        raise ValueError("pool count does not match PACK.json")
    return tuple(pools), nodes


def holdout_gold(pool: Pool) -> Pool:
    """The same pool without its gold docids. No candidate is gold, so the right call is not to act."""
    held = set(pool.gold.node_ids)
    return Pool(
        Gold(pool.gold.id, pool.gold.text, "abstain", ()),
        {node_id: node for node_id, node in pool.nodes.items() if node_id not in held},
        {node_id: text for node_id, text in pool.body.items() if node_id not in held},
        tuple(docid for docid in pool.evidence_docids if docid not in held),
        pool.negative_docids,
    )


def text_of_body(body: Mapping[NodeId, str]):
    def text_of(node_id: NodeId) -> str:
        return body[node_id]

    return text_of


def stub_trials(pools: Sequence[Pool], k: int) -> list[Trial]:
    trials: list[Trial] = []
    for pool in pools:
        decide = stub_decide(pool.gold.text, pool.nodes, body=pool.body)
        trials.append(
            arm_c(
                pool.gold,
                pool.nodes,
                choose=decide,
                k=k,
                text_of=text_of_body(pool.body),
            )
        )
    return trials


def prompt_text(body: Mapping[NodeId, str]) -> dict[NodeId, str]:
    return {node_id: text[:PROMPT_CHARS] for node_id, text in body.items()}
