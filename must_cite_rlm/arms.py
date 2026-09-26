from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping, Sequence

from must_cite_rlm.check import IllegalSpan
from must_cite_rlm.tree import Node
from must_cite_rlm.types import (
    Abstain,
    Act,
    CandidateSet,
    Cite,
    Decision,
    Gold,
    NodeId,
    Review,
    Trial,
)

MAX_DEPTH = 2
STUB_QUOTE_CHARS = 40
ARM_NAMES = ("A", "B", "C")

Decider = Callable[[CandidateSet], Decision]

_STOP = frozenset(
    """
    which what when where this that with from into over than then
    does only after before about how many much should kept keep
    marks mark the and for are was were been being have has had
    not nor any all into when does text notes note
    """.split()
)

_NODE_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*(?:/[a-z0-9-]+)+")

# Arm C ranker. BrowseComp-Plus uses the default. The Hotpot yardstick passes "overlap".
DEFAULT_RANKER = "bm25"
RANKERS = ("bm25", "overlap")

# Okapi BM25 (Robertson & Zaragoza). k1=1.2, b=0.75.
# IDF(t) = ln(1 + (N - df + 0.5) / (df + 0.5)) stays non-negative.
# N, df, and avgdl are the per-question leaf pool, not a global corpus.
# The sum is over unique query tokens. A leaf with no query token scores 0.
BM25_K1 = 1.2
BM25_B = 0.75

# Lexical shapes for one question:
#   Token: lowercase [a-z0-9]+, length >= 3, not in _STOP
#   Bag: Mapping[Token, int], counts in one text
#   Pool: sequence of (NodeId, Bag) for the depth-2 leaves
#   Query: the question Bag
#   Score: float, higher is better


def _term_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        if len(word) < 3 or word in _STOP:
            continue
        counts[word] = counts.get(word, 0) + 1
    return counts


def _tokens(text: str) -> set[str]:
    return set(_term_counts(text))


def _overlap(question: str, text: str) -> int:
    return len(_tokens(question) & _tokens(text))


def _bm25_scores(question: str, docs: Sequence[tuple[NodeId, str]]) -> list[tuple[float, NodeId]]:
    bags = [(node_id, _term_counts(text)) for node_id, text in docs]
    n = len(bags)
    if n == 0:
        return []
    lengths = [sum(bag.values()) for _, bag in bags]
    avgdl = sum(lengths) / n
    query_terms = list(_term_counts(question))
    df = {term: sum(1 for _, bag in bags if term in bag) for term in query_terms}
    scores: list[tuple[float, NodeId]] = []
    for (node_id, bag), dl in zip(bags, lengths, strict=True):
        score = 0.0
        norm = 0.0 if avgdl == 0 else dl / avgdl
        for term in query_terms:
            tf = bag.get(term, 0)
            if tf == 0:
                continue
            n_q = df[term]
            idf = math.log(1.0 + (n - n_q + 0.5) / (n_q + 0.5))
            denom = tf + BM25_K1 * (1.0 - BM25_B + BM25_B * norm)
            score += idf * (tf * (BM25_K1 + 1.0)) / denom
        scores.append((score, node_id))
    return scores


def stub_decide(
    question: str,
    nodes: Mapping[NodeId, Node],
    body: Mapping[NodeId, str] | None = None,
) -> Decider:
    def chunk(node_id: NodeId) -> str | None:
        if body is not None and node_id in body:
            return body[node_id]
        node = nodes.get(node_id)
        if node is None:
            return None
        return node.span.text

    def decide(candidates: CandidateSet) -> Decision:
        scored = []
        for node_id in candidates.node_ids:
            text = chunk(node_id)
            if text is None:
                continue
            scored.append((_overlap(question, text), node_id))
        scored = [item for item in scored if item[0] > 0]
        if not scored:
            return Abstain()
        best = max(score for score, _ in scored)
        winners = tuple(node_id for score, node_id in scored if score == best)
        if len(winners) != 1:
            return Review()
        return Act(winners)

    return decide


def _trial(
    gold: Gold,
    arm: str,
    decision: Decision,
    raw_model: str,
    nodes: Mapping[NodeId, Node],
) -> Trial:
    if isinstance(decision, Act):
        cites = tuple(Cite(node_id) for node_id in decision.node_ids)
        parts = []
        for node_id in decision.node_ids:
            node = nodes.get(node_id)
            if node is not None:
                parts.append(f'"{node.span.text}"')
        text = " ".join(parts) if parts else None
    else:
        cites = ()
        text = None
    return Trial(gold.id, arm, decision, cites, text, raw_model)


def _model_raw(trace: dict[str, str] | None, decision: Decision) -> str:
    if trace is None:
        return _raw(decision)
    raw = trace.get("raw", "")
    return raw if raw else _raw(decision)


def arm_b(
    gold: Gold,
    nodes: Mapping[NodeId, Node],
    decide: Decider | None = None,
    trace: dict[str, str] | None = None,
) -> Trial:
    choose = decide if decide is not None else stub_decide(gold.text, nodes)
    calls = 0

    def limited(candidates: CandidateSet) -> Decision:
        nonlocal calls
        calls += 1
        if calls > MAX_DEPTH:
            raise IllegalSpan(gold.id)
        return choose(candidates)

    sections = tuple(node.id for node in nodes.values() if node.depth == 1)
    first = limited(CandidateSet(sections))
    if not isinstance(first, Act):
        return _trial(gold, "B", first, _model_raw(trace, first), nodes)
    children: list[NodeId] = []
    for node_id in first.node_ids:
        node = nodes.get(node_id)
        if node is not None:
            children.extend(node.child_ids)
    if not children:
        return _trial(gold, "B", first, _model_raw(trace, first), nodes)
    second = limited(CandidateSet(tuple(children)))
    return _trial(gold, "B", second, _model_raw(trace, second), nodes)


def arm_c(
    gold: Gold,
    nodes: Mapping[NodeId, Node],
    choose: Decider | None = None,
    k: int = 1,
    trace: dict[str, str] | None = None,
    text_of: Callable[[NodeId], str] | None = None,
    ranker: str = DEFAULT_RANKER,
) -> Trial:
    ranked = tuple(item for item in ranked_leaves(gold.text, nodes, text_of, ranker) if item[0] > 0)
    if not ranked:
        decision: Decision = Abstain()
    elif choose is None:
        decision = Act((ranked[0][1],))
    else:
        top = tuple(node_id for _, node_id in ranked[:k])
        decision = choose(CandidateSet(top))
    return _trial(gold, "C", decision, _model_raw(trace, decision), nodes)


def stub_fanout(question: str, node_id: NodeId, text: str) -> str:
    if _overlap(question, text) < 1:
        return "NO"
    prefix = " ".join(text.split())[:STUB_QUOTE_CHARS]
    return f'see {node_id} "{prefix}"'


def _ids_in_prose(raw: str) -> tuple[NodeId, ...]:
    found: list[NodeId] = []
    for token in _NODE_ID.findall(raw):
        node_id = NodeId(token)
        if node_id not in found:
            found.append(node_id)
    return tuple(found)


def ranked_leaves(
    question: str,
    nodes: Mapping[NodeId, Node],
    text_of: Callable[[NodeId], str] | None = None,
    ranker: str = DEFAULT_RANKER,
) -> tuple[tuple[float, NodeId], ...]:
    if ranker not in RANKERS:
        raise ValueError(f"unknown ranker {ranker}")
    leaves = tuple(node.id for node in nodes.values() if node.depth == 2)

    def chunk(node_id: NodeId) -> str:
        if text_of is not None:
            return text_of(node_id)
        return nodes[node_id].span.text

    docs = tuple((node_id, chunk(node_id)) for node_id in leaves)
    if ranker == "overlap":
        scored: list[tuple[float, NodeId]] = [
            (float(_overlap(question, text)), node_id) for node_id, text in docs
        ]
    else:
        scored = _bm25_scores(question, docs)
    return tuple(sorted(scored, key=lambda item: (-item[0], item[1])))


def arm_a(
    gold: Gold,
    nodes: Mapping[NodeId, Node],
    fanout: Callable[[str, NodeId, str], str] | None = None,
) -> Trial:
    speak = fanout if fanout is not None else stub_fanout
    sections = [node for node in nodes.values() if node.depth == 1]
    raws = [speak(gold.text, node.id, node.span.text) for node in sections]
    raw = "\n".join(raws)
    ids = _ids_in_prose(raw)
    quotes = re.findall(r'"([^"]*)"', raw)
    if not ids:
        decision: Decision = Abstain()
        text = " ".join(f'"{quote}"' for quote in quotes) if quotes else None
        return Trial(gold.id, "A", decision, (), text, raw)
    decision = Act(ids)
    text = " ".join(f'"{quote}"' for quote in quotes) if quotes else None
    cites = tuple(Cite(node_id) for node_id in ids)
    return Trial(gold.id, "A", decision, cites, text, raw)


def _raw(decision: Decision) -> str:
    if isinstance(decision, Act):
        return "act " + " ".join(decision.node_ids)
    if isinstance(decision, Review):
        return "review"
    return "abstain"
