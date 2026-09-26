from __future__ import annotations

import json
from pathlib import Path

import pytest

from must_cite_rlm.arms import arm_b, arm_c, ranked_leaves
from must_cite_rlm.live import LiveError
from must_cite_rlm.scoreboard import is_exact, main
from must_cite_rlm.tree import ROOT, load_gold, load_nodes


def test_stub_scoreboard_labels_mode_and_keeps_b_and_c_cite_ok(tmp_path: Path) -> None:
    out = tmp_path / "SCOREBOARD.md"
    assert main(["--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "Mode `stub`." in text
    rows = {}
    for line in text.splitlines():
        if line.startswith("| A |") or line.startswith("| B |") or line.startswith("| C |"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            rows[cells[0]] = cells
    assert set(rows) == {"A", "B", "C"}
    assert float(rows["A"][2]) < 1.0
    assert float(rows["B"][2]) == 1.0
    assert float(rows["C"][2]) == 1.0
    assert float(rows["B"][3]) == 0.0
    assert float(rows["C"][3]) == 0.0
    assert float(rows["B"][1]) > float(rows["C"][1])
    assert f"Stub B exact_id_acc is {float(rows['B'][1]):.3f}" in text
    assert f"stub C exact_id_acc is {float(rows['C'][1]):.3f}" in text
    assert "HotpotQA dev distractor v1" in text
    assert "CC BY-SA 4.0" in text
    assert "not a random HotpotQA sample" in text


def test_hotpot_slice_separates_stub_b_from_stub_c() -> None:
    nodes = load_nodes()
    golds = load_gold()
    by_id = {gold.id: gold for gold in golds}
    provenance = [
        json.loads(line)
        for line in (ROOT / "fixtures" / "provenance.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [row["id"] for row in provenance] == [gold.id for gold in golds]
    license_text = (ROOT / "fixtures" / "LICENSE.txt").read_text(encoding="utf-8")
    assert "CC BY-SA 4.0" in license_text
    assert "e3da074df24e8369009918aa5cdbdd254dadcde4c63f7569d36afd6f2268caa8" in license_text
    strict = 0
    for row in provenance:
        gold = by_id[row["id"]]
        if row["role"] == "abstain":
            assert gold.decision == "abstain"
            assert row["hotpot_id"] is None
            assert is_exact(arm_b(gold, nodes), gold) is True
            assert is_exact(arm_c(gold, nodes, ranker="overlap"), gold) is True
            continue
        assert row["hotpot_id"]
        assert gold.decision == "act"
        if row["role"] == "bridge":
            assert is_exact(arm_b(gold, nodes), gold) is True
            assert is_exact(arm_c(gold, nodes, ranker="overlap"), gold) is False
            ranked = ranked_leaves(gold.text, nodes, ranker="overlap")
            assert ranked[0][1] != gold.node_ids[0]
            scores = {node_id: score for score, node_id in ranked}
            if ranked[0][0] > scores[gold.node_ids[0]]:
                strict += 1
        elif row["role"] == "easy":
            assert is_exact(arm_b(gold, nodes), gold) is True
            assert is_exact(arm_c(gold, nodes, ranker="overlap"), gold) is True
            assert ranked_leaves(gold.text, nodes, ranker="overlap")[0][1] == gold.node_ids[0]
        else:
            assert row["role"] == "multi"
            assert len(gold.node_ids) == 2
            assert is_exact(arm_b(gold, nodes), gold) is False
            assert is_exact(arm_c(gold, nodes, ranker="overlap"), gold) is False
    assert strict >= 5


def test_live_without_keys_writes_skip_note(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    live = tmp_path / "SCOREBOARD.live.md"
    stub = tmp_path / "SCOREBOARD.md"
    assert main(["--live", "--live-out", str(live), "--out", str(stub)]) == 0
    text = live.read_text(encoding="utf-8")
    assert "Live run skipped." in text
    assert "OPENAI_API_KEY" in text
    assert "ANTHROPIC_API_KEY" in text
    assert "TYPESAFE_API_KEY" in text
    assert "When both `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` are set, OpenAI is used." in text
    assert stub.exists() is False


def test_live_rejects_a_bad_jev_decode_before_provider_calls(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("TYPESAFE_API_KEY", "jev")
    monkeypatch.setenv("MUST_CITE_JEV_DECODE", "argmax")

    def fake_post(url, headers, body):
        raise AssertionError(url)

    monkeypatch.setattr("must_cite_rlm.live.post_json", fake_post)
    live = tmp_path / "SCOREBOARD.live.md"
    with pytest.raises(LiveError):
        main(["--live", "--live-out", str(live)])
    assert live.exists() is False


def test_live_with_only_anthropic_key_is_not_a_skip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    urls: list[str] = []

    def fake_post(url, headers, body):
        urls.append(url)
        assert headers["x-api-key"] == "sk-ant-test"
        assert headers["anthropic-version"] == "2023-06-01"
        usage = {"input_tokens": 100, "output_tokens": 20}
        if "tools" in body:
            payload = {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "decision",
                        "input": {"decision": "abstain", "node_ids": ["missing/nope/0"]},
                    }
                ],
                "usage": usage,
            }
        else:
            assert body["model"] == "claude-haiku-4-5"
            payload = {"content": [{"type": "text", "text": "NO"}], "usage": usage}
        return payload, 1.0

    monkeypatch.setattr("must_cite_rlm.live.post_json", fake_post)
    live = tmp_path / "SCOREBOARD.live.md"
    stub = tmp_path / "SCOREBOARD.md"
    assert main(["--live", "--live-out", str(live), "--out", str(stub)]) == 0
    text = live.read_text(encoding="utf-8")
    assert "Live run skipped." not in text
    assert "Mode `live`." in text
    assert "claude-haiku-4-5" in text
    assert "1.00" in text
    assert urls
    assert set(urls) == {"https://api.anthropic.com/v1/messages"}
    assert stub.exists() is False
