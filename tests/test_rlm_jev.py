from __future__ import annotations

import json
import urllib.request

import pytest

from must_cite_rlm.rlm_jev import JEV_TOOL_CODE, JEV_TOOL_HELP, JevProxy, parse_response
from must_cite_rlm.types import Act, NodeId


def test_parse_response_reads_the_browsecomp_plus_format() -> None:
    text = (
        "Explanation: The school was founded in 1948 [123]. Its principal died in 1999 [45][123].\n"
        "Exact Answer: 4:15 PM\n"
        "Confidence: 72%"
    )
    assert parse_response(text) == {"exact_answer": "4:15 PM", "confidence": 0.72, "cited": ["123", "45"]}
    assert parse_response("no format") == {"exact_answer": None, "confidence": None, "cited": []}
    assert parse_response("Exact Answer: x\nConfidence: 85")["confidence"] == 0.85
    assert parse_response("Exact Answer: x\nConfidence: 0.4")["confidence"] == 0.4


def test_jev_tool_code_defines_one_function_per_tool() -> None:
    for name in JEV_TOOL_HELP:
        code = JEV_TOOL_CODE.format(name=name, url="http://h:1", path=name.split("_")[1])
        namespace: dict = {}
        exec(code, namespace)
        assert callable(namespace[name])
        assert f"http://h:1/{name.split('_')[1]}" in code


def _post(port: int, path: str, body: dict) -> dict:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/{path}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    return json.loads(urllib.request.urlopen(request, timeout=10).read())


def test_proxy_screens_in_batches_and_logs_decides(monkeypatch) -> None:
    batches: list[int] = []

    def nouls(question, pairs, meter):
        batches.append(len(pairs))
        assert all(len(text) <= 12000 for _, text in pairs)
        return {key: 0.5 for key, _ in pairs}

    def decide(question, pairs, meter, trace, transport=None):
        answers = {"route": {"choice": "act", "probabilities": {"act": 0.8}}}
        answers.update({key: {"noul": 0.9 if key == "b" else 0.1} for key, _ in pairs})
        trace["raw"] = json.dumps({"answers": answers})
        return Act((NodeId("b"),))

    monkeypatch.setattr("must_cite_rlm.rlm_jev.jev_nouls", nouls)
    monkeypatch.setattr("must_cite_rlm.live.jev_decide", decide)
    proxy = JevProxy()
    with proxy as url:
        port = int(url.rsplit(":", 1)[1])
        scores = _post(port, "screen", {"question": "q", "items": {str(i): "x" * 20000 for i in range(20)}})
        gate = _post(port, "decide", {"question": "q", "items": {"a": "A", "b": "B"}})
    assert len(scores) == 20 and sorted(batches) == [4, 8, 8]
    assert gate == {"route": "act", "p_act": 0.8, "cite": "b", "support": {"a": 0.1, "b": 0.9}}
    assert proxy.decides == [gate] and proxy.screened == 20


def _analysis():
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("analyze", Path(__file__).parents[1] / "scripts" / "analyze_rlm_jev.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_aurc_and_auroc_match_hand_values() -> None:
    m = _analysis()
    # Scores rank the one wrong answer last: risks 0, 0, 1/3 over coverage 1/3..3/3.
    assert m.aurc([0.9, 0.8, 0.1], [False, False, True]) == pytest.approx((0 + 0 + 1 / 3) / 3)
    # Ranked first: risks 1, 1/2, 1/3.
    assert m.aurc([0.1, 0.8, 0.9], [False, False, True]) == pytest.approx((1 + 1 / 2 + 1 / 3) / 3)
    # All tied: every coverage has the expected risk 1/3.
    assert m.aurc([0.5, 0.5, 0.5], [False, False, True]) == pytest.approx(1 / 3)
    assert m.auroc([0.9, 0.8, 0.1], [False, False, True]) == 1.0
    assert m.auroc([0.5, 0.5], [False, True]) == 0.5
    assert m.auroc([0.5, 0.5], [False, False]) is None
    assert m._topk_error([0.9, 0.5, 0.5, 0.1], [False, True, False, True], 2) == pytest.approx(0.25)


def test_compare_calls_a_clear_winner() -> None:
    m = _analysis()
    rows = [
        {"correct": i % 5 != 0, "exact_answer": "x", "gate_post": {"p_act": 0.1 if i % 5 == 0 else 0.9}, "confidence": 0.9}
        for i in range(60)
    ]
    result = m.compare(rows)
    assert result["delta"] < 0 and result["ci"][1] < 0 and result["verdict"] == "Jev gate wins"


def test_answer_window_centers_on_the_answer() -> None:
    from must_cite_rlm.rlm_jev import _answer_window

    text = "a" * 30000 + "Ada Lovelace" + "b" * 30000
    window = _answer_window(text, "ada lovelace")
    assert "Ada Lovelace" in window and len(window) == 12000
    assert _answer_window("short text", "missing") == "short text"


def test_jev_shortlist_returns_top_k_with_snippets_through_the_proxy(monkeypatch) -> None:
    pytest.importorskip("requests")
    from must_cite_rlm.rlm_jev import JEV_SHORTLIST_CODE

    def nouls(question, pairs, meter):
        assert all(len(text) <= 12000 for _, text in pairs)
        return {key: int(key) / 100 for key, _ in pairs}

    monkeypatch.setattr("must_cite_rlm.rlm_jev.jev_nouls", nouls)
    docs = {str(i): f"doc {i} " + "x" * 20000 for i in range(20)}
    with JevProxy() as url:
        namespace: dict = {}
        exec(JEV_SHORTLIST_CODE.format(url=url.replace("host.docker.internal", "127.0.0.1")), namespace)
        top = namespace["jev_shortlist"]("q", docs, k=3, snippet=10)
    assert [row["docid"] for row in top] == ["19", "18", "17"]
    assert top[0] == {"docid": "19", "score": 0.19, "snippet": "doc 19 xxx"}


def test_out_of_iterations_prefill_becomes_a_no_code_final_turn() -> None:
    from must_cite_rlm.rlm_jev import FINAL_TURN, RLMS_OUT_OF_ITERATIONS, _no_trailing_assistant

    history = [{"role": "user", "content": "q"}, {"role": "assistant", "content": RLMS_OUT_OF_ITERATIONS}]
    assert _no_trailing_assistant(history)[-1] == {"role": "user", "content": FINAL_TURN}
    other = [{"role": "user", "content": "q"}, {"role": "assistant", "content": "partial"}]
    assert _no_trailing_assistant(other)[-1] == {"role": "user", "content": "partial"}
    assert _no_trailing_assistant([{"role": "user", "content": "q"}]) == [{"role": "user", "content": "q"}]


def _fake_anthropic(monkeypatch, sent: list[str], text: str) -> None:
    import sys
    import types

    class _Stream:
        def __init__(self, messages):
            self.messages = messages

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get_final_message(self):
            block = types.SimpleNamespace(type="text", text=text)
            return types.SimpleNamespace(content=[block], usage=types.SimpleNamespace(input_tokens=1000, output_tokens=100))

    class _Messages:
        def stream(self, model, max_tokens, messages):
            sent.append((messages[0]["content"], max_tokens))
            return _Stream(messages)

    fake = types.SimpleNamespace(Anthropic=lambda api_key: types.SimpleNamespace(messages=_Messages()))
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")


def _reader_setup(monkeypatch):
    from must_cite_rlm import reader

    monkeypatch.setattr("must_cite_rlm.rlm_jev.jev_nouls", lambda question, pairs, meter: {key: int(key) / 100 for key, _ in pairs})
    context = {str(i): f"doc {i} text" for i in range(20)}
    row = {"id": "q", "question": "Q?", "gold_docids": ["19"]}
    return reader, context, row


def test_reader_sends_jev_top_docs_to_one_call(monkeypatch) -> None:
    reader, context, row = _reader_setup(monkeypatch)
    sent: list = []
    _fake_anthropic(monkeypatch, sent, "Explanation: x [19].\nExact Answer: y\nConfidence: 70%")
    result = reader.run_reader(row, context)
    assert result["shortlist"] == [str(i) for i in range(19, 11, -1)]
    assert result["shortlist_scores"][0] == 0.19 and result["jev_rejected"] is False
    assert result["gold_in_shortlist"] and result["cited"] == ["19"] and result["confidence"] == 0.7
    prompt, max_tokens = sent[0]
    assert "[19]\ndoc 19 text" in prompt and "[11]" not in prompt and "relevance" not in prompt
    assert max_tokens == reader.MAX_OUTPUT_TOKENS and result["reader_config"]["show_scores"] is False
    assert result["cost_rlm"] == pytest.approx((1000 * 2 + 100 * 10) / 1_000_000)


def test_reader_variants_show_scores_reject_and_output_cap(monkeypatch) -> None:
    reader, context, row = _reader_setup(monkeypatch)
    sent: list = []
    _fake_anthropic(monkeypatch, sent, "Exact Answer: y\nConfidence: 50%")
    shown = reader.run_reader(row, context, reader.ReaderConfig(show_scores=True, max_output_tokens=32_000))
    assert "[19] (relevance 0.19)" in sent[0][0] and "relevance score between 0 and 1" in sent[0][0]
    assert sent[0][1] == 32_000 and shown["reader_config"]["max_output_tokens"] == 32_000
    rejected = reader.run_reader(row, context, reader.ReaderConfig(reject_below=0.5))
    assert rejected["jev_rejected"] is True and rejected["response"] == "" and rejected["exact_answer"] is None
    assert len(sent) == 1 and rejected["cost_rlm"] == 0.0 and rejected["cost_jev"] >= 0.0
    kept = reader.run_reader(row, context, reader.ReaderConfig(reject_below=0.1))
    assert kept["jev_rejected"] is False and len(sent) == 2


def test_paired_block_reports_paired_differences() -> None:
    m = _analysis()
    base = {str(i): {"correct": True, "cost_rlm": 0.3, "cost_jev": 0.0, "cost_judge": 0.0, "seconds": 100.0} for i in range(40)}
    other = {str(i): {"correct": True, "cost_rlm": 0.04, "cost_jev": 0.09, "cost_judge": 0.0, "seconds": 20.0, "jev_screened": 1000} for i in range(40)}
    lines = "\n".join(m.paired_block("J", base, other, sorted(base, key=int)))
    assert "## Arm J vs A, paired (n=40)" in lines
    assert "| accuracy | 1.000 | 1.000 | +0.000 |" in lines
    assert "| $/question | 0.300 | 0.130 | -0.170 |" in lines and "J better" in lines


def test_compact_log_keeps_code_and_trims_output(tmp_path) -> None:
    import types

    from must_cite_rlm.rlm_jev import _write_compact_log

    iteration = {
        "iteration": 1,
        "iteration_time": 2.5,
        "prompt": "x" * 100_000,
        "final_answer": None,
        "code_blocks": [{"code": "print(1)", "result": {"stdout": "y" * 5000, "stderr": ""}}],
    }
    logger = types.SimpleNamespace(get_trajectory=lambda: {"run_metadata": {}, "iterations": [iteration]})
    path = tmp_path / "A" / "q1.jsonl"
    _write_compact_log(path, logger)
    row = json.loads(path.read_text(encoding="utf-8"))
    assert row["blocks"][0]["code"] == "print(1)" and len(row["blocks"][0]["stdout"]) == 2000
    assert "prompt" not in row and row["seconds"] == 2.5
    _write_compact_log(tmp_path / "none.jsonl", types.SimpleNamespace(get_trajectory=lambda: None))
    assert not (tmp_path / "none.jsonl").exists()


def test_bm25_reader_ranks_without_jev(monkeypatch) -> None:
    from must_cite_rlm import reader

    def no_jev(*args, **kwargs):
        raise AssertionError("arm K must not call Jev")

    monkeypatch.setattr("must_cite_rlm.rlm_jev.jev_nouls", no_jev)
    sent: list = []
    _fake_anthropic(monkeypatch, sent, "Explanation: x [7].\nExact Answer: granite\nConfidence: 80%")
    context = {str(i): "filler text about rivers" for i in range(20)}
    context["7"] = "granite quarry granite quarry near the old mill"
    row = {"id": "q", "question": "Which granite quarry?", "gold_docids": ["7"]}
    result = reader.run_reader(row, context, reader.ReaderConfig(ranker="bm25"))
    assert result["arm"] == "K" and result["shortlist"][0] == "7" and result["gold_in_shortlist"]
    assert result["cost_jev"] == 0.0 and result["jev_screened"] == 0 and len(result["shortlist"]) == 8
    assert "[7]\ngranite quarry" in sent[0][0]
    with pytest.raises(ValueError):
        reader.run_reader(row, context, reader.ReaderConfig(ranker="bm25", show_scores=True))
