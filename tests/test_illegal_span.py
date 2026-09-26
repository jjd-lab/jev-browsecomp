from __future__ import annotations

from pathlib import Path

import pytest

from must_cite_rlm.arms import arm_a, arm_b, arm_c
from must_cite_rlm.check import IllegalSpan, assert_cites, cites_ok
from must_cite_rlm.tree import ROOT, load_gold, load_nodes, parse_artifact
from must_cite_rlm.types import Act, Cite, NodeId, Trial


def test_missing_id_is_illegal() -> None:
    nodes = load_nodes()
    trial = Trial("q", "B", Act((NodeId("missing/node"),)), (Cite(NodeId("missing/node")),), None, "act missing/node")
    with pytest.raises(IllegalSpan):
        assert_cites(trial, nodes)


def test_exact_quote_is_legal_and_paraphrase_is_illegal() -> None:
    nodes = load_nodes()
    node_id = NodeId("howell-conant/howell-conant/0")
    span = nodes[node_id].span
    legal = Trial("q", "C", Act((node_id,)), (Cite(node_id),), f'"{span.text}"', "act howell-conant/howell-conant/0")
    assert_cites(legal, nodes)
    paraphrase = Trial("q", "A", Act((node_id,)), (Cite(node_id),), '"a fashion photographer"', "act howell-conant/howell-conant/0")
    with pytest.raises(IllegalSpan):
        assert_cites(paraphrase, nodes)


def test_model_offsets_are_illegal() -> None:
    nodes = load_nodes()
    node_id = NodeId("howell-conant/howell-conant/0")
    span = nodes[node_id].span
    trial = Trial(
        "q",
        "A",
        Act((node_id,)),
        (Cite(node_id),),
        f'"{span.text}"',
        "start_char=12 end_char=40",
    )
    with pytest.raises(IllegalSpan):
        assert_cites(trial, nodes)


def test_span_text_is_the_char_slice() -> None:
    path = ROOT / "fixtures" / "corpus" / "howell-conant.md"
    text = path.read_text(encoding="utf-8")
    nodes = parse_artifact(path)
    span = nodes[NodeId("howell-conant/howell-conant/0")].span
    assert span.text == text[span.start_char : span.end_char]
    assert span.text.startswith("Howell T. Conant, Senior")
    assert "photographer" in span.text
    assert "start_char" not in span.text
    assert '"' not in span.text


def test_gold_ids_are_leaves() -> None:
    nodes = load_nodes()
    golds = load_gold()
    assert len(golds) == 23
    assert sum(gold.decision == "abstain" for gold in golds) == 6
    assert len(list((ROOT / "fixtures" / "corpus").glob("*.md"))) == 34
    for gold in golds:
        for node_id in gold.node_ids:
            assert nodes[node_id].depth == 2
            assert '"' not in nodes[node_id].span.text


def test_b_walks_at_most_two_plies(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "demo-note.md").write_text(
        "# Demo\n\n## Alpha\n\nAlpha holds the cedar token.\n\n## Beta\n\nBeta holds the maple token.\n",
        encoding="utf-8",
    )
    nodes = {}
    for path in corpus.glob("*.md"):
        nodes.update(parse_artifact(path))
    calls: list[int] = []

    def decide(candidates):
        calls.append(len(candidates.node_ids))
        return Act((candidates.node_ids[0],))

    from must_cite_rlm.types import Gold

    gold = Gold("q", "Where is the cedar token?", "act", (NodeId("demo-note/alpha/0"),))
    trial = arm_b(gold, nodes, decide)
    assert len(calls) == 2
    assert cites_ok(trial, nodes) is True
    assert trial.raw_model.startswith("act ")
    assert "start_char" not in trial.raw_model


def test_b_and_c_pass_assert_cites_and_a_prefix_fails() -> None:
    nodes = load_nodes()
    golds = load_gold()
    for gold in golds:
        assert cites_ok(arm_b(gold, nodes), nodes) is True
        assert cites_ok(arm_c(gold, nodes), nodes) is True
    answered = next(gold for gold in golds if gold.decision == "act")
    assert cites_ok(arm_a(answered, nodes), nodes) is False
