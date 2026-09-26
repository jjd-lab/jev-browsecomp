from __future__ import annotations

import json

import pytest

from must_cite_rlm.live import (
    SCORED_SCHEMA,
    jev_payload_from_chat,
    scored_chat_decide,
    ACT_NOUL,
    ANTHROPIC_URL,
    DECISION_SCHEMA,
    LiveError,
    Meter,
    _jev_call,
    anthropic_complete,
    anthropic_cost,
    build_jev_body,
    decision_from_jev,
    jev_decode_clause,
    jev_decide,
    live_status,
    make_id_choose,
    make_text_fanout,
    meter_cost_note,
    openai_cost,
    openai_decide,
    parse_llm_decision,
    text_messages,
)
from must_cite_rlm.tree import Node
from must_cite_rlm.types import Abstain, Act, ArtifactId, CandidateSet, NodeId, Review, Span

SEAL = NodeId("loft-mill/seal/1")
SIBLING = NodeId("loft-mill/seal/0")
ALLOWED = {SEAL, SIBLING}


def test_parse_llm_decision_keeps_only_allowed_ids() -> None:
    raw = json.dumps({"decision": "act", "node_ids": [SEAL, "missing/nope/0"]})
    assert parse_llm_decision(raw, ALLOWED) == Act((SEAL,))
    assert isinstance(parse_llm_decision('{"decision":"review","node_ids":["missing/nope/0"]}', ALLOWED), Review)
    assert isinstance(parse_llm_decision("not json", ALLOWED), Abstain)
    assert isinstance(
        parse_llm_decision(json.dumps({"decision": "act", "node_ids": ["missing/nope/0"]}), ALLOWED),
        Abstain,
    )


def test_decision_from_jev_act_cites_only_the_argmax_noul(monkeypatch) -> None:
    """route=act cites the one highest noul at or above ACT_NOUL.

    A tie keeps the earliest id in `allowed`. Review and abstain ignore scores.
    """
    monkeypatch.delenv("MUST_CITE_JEV_DECODE", raising=False)
    allowed = (SIBLING, SEAL)
    act = {
        "answers": {
            "route": {"choice": "act"},
            SIBLING: {"noul": ACT_NOUL - 0.01},
            SEAL: {"noul": ACT_NOUL},
        }
    }
    assert decision_from_jev(act, allowed) == Act((SEAL,))
    both = {
        "answers": {
            "route": {"choice": "act"},
            SIBLING: {"noul": 0.8},
            SEAL: {"noul": 0.9},
        }
    }
    assert decision_from_jev(both, allowed) == Act((SEAL,))
    earlier = {
        "answers": {
            "route": {"choice": "act"},
            SIBLING: {"noul": 0.95},
            SEAL: {"noul": 0.7},
        }
    }
    assert decision_from_jev(earlier, allowed) == Act((SIBLING,))
    # Equal noul: the earliest id in allowed wins, not both and not the later id.
    tie = {
        "answers": {
            "route": {"choice": "act"},
            SIBLING: {"noul": 0.8},
            SEAL: {"noul": 0.8},
        }
    }
    assert decision_from_jev(tie, allowed) == Act((SIBLING,))
    assert decision_from_jev(tie, (SEAL, SIBLING)) == Act((SEAL,))
    below = {
        "answers": {
            "route": {"choice": "act"},
            SIBLING: {"noul": 0.4},
            SEAL: {"noul": ACT_NOUL - 0.01},
        }
    }
    assert isinstance(decision_from_jev(below, allowed), Abstain)
    review = {
        "answers": {
            "route": {"choice": "review"},
            SEAL: {"noul": 0.99},
        }
    }
    assert isinstance(decision_from_jev(review, allowed), Review)
    assert isinstance(decision_from_jev({"answers": {"route": {"choice": "abstain"}}}, allowed), Abstain)


def test_openai_decide_drops_unknown_ids_and_omits_offsets() -> None:
    seen: dict[str, object] = {}

    def complete(messages, schema):
        seen["messages"] = messages
        seen["schema"] = schema
        return json.dumps({"decision": "act", "node_ids": [SEAL, "missing/nope/0"]})

    meter = Meter()
    trace: dict[str, str] = {}
    decision = openai_decide("Which seal closes the chalk crate?", [(SEAL, "The chalk crate in the loft has a slate seal.")], meter, trace, complete)
    assert decision == Act((SEAL,))
    blob = json.dumps(seen)
    assert "start_char" not in blob
    assert "end_char" not in blob
    assert "start_char" not in trace["raw"]


def test_text_fanout_prompt_names_the_node_and_not_offsets() -> None:
    messages = text_messages("Which seal?", SEAL, "The chalk crate in the loft has a slate seal.")
    blob = json.dumps(messages)
    assert "loft-mill/seal/1" in blob
    assert "start_char" not in blob
    assert "end_char" not in blob


def test_jev_body_asks_choice_and_one_noul_per_span(monkeypatch) -> None:
    monkeypatch.delenv("MUST_CITE_JEV_DECODE", raising=False)
    body = build_jev_body("Which seal?", [(SEAL, "The chalk crate in the loft has a slate seal.")])
    assert body["questions"]["route"]["type"] == "choice"
    assert set(body["questions"]["route"]["criteria"]) == {"act", "review", "abstain"}
    assert body["questions"][SEAL]["type"] == "noul"
    assert "start_char" not in json.dumps(body)


def test_noul_only_cites_argmax_and_abstains_without_review(monkeypatch) -> None:
    monkeypatch.setenv("MUST_CITE_JEV_DECODE", "noul_only")
    allowed = (SIBLING, SEAL)
    body = build_jev_body("Which seal?", [(SIBLING, "sibling"), (SEAL, "seal")])
    assert "route" not in body["questions"]
    assert body["questions"][SIBLING]["type"] == "noul"
    assert body["questions"][SEAL]["type"] == "noul"
    assert all(spec["type"] == "noul" for spec in body["questions"].values())
    high = {
        "answers": {
            "route": {"choice": "review"},
            SIBLING: {"noul": 0.8},
            SEAL: {"noul": 0.9},
        }
    }
    assert decision_from_jev(high, allowed) == Act((SEAL,))
    tie = {"answers": {SIBLING: {"noul": ACT_NOUL}, SEAL: {"noul": ACT_NOUL}}}
    assert decision_from_jev(tie, allowed) == Act((SIBLING,))
    assert decision_from_jev(tie, (SEAL, SIBLING)) == Act((SEAL,))
    low = {"answers": {"route": {"choice": "act"}, SIBLING: {"noul": 0.49}, SEAL: {"noul": True}}}
    assert isinstance(decision_from_jev(low, allowed), Abstain)
    assert isinstance(decision_from_jev({"answers": {}}, allowed), Abstain)


def test_choice_per_span_cites_the_first_act_in_allowed_order(monkeypatch) -> None:
    monkeypatch.setenv("MUST_CITE_JEV_DECODE", "choice_per_span")
    allowed = (SIBLING, SEAL)
    body = build_jev_body("Which seal?", [(SIBLING, "sibling"), (SEAL, "seal")])
    assert "route" not in body["questions"]
    assert list(body["questions"]) == [SIBLING, SEAL]
    spec = body["questions"][SEAL]
    assert spec["type"] == "choice"
    assert set(spec["criteria"]) == {"act", "review", "abstain"}
    assert "noul" not in json.dumps(body["questions"])
    both_act = {"answers": {SIBLING: {"choice": "act"}, SEAL: {"choice": "act"}}}
    assert decision_from_jev(both_act, allowed) == Act((SIBLING,))
    assert decision_from_jev(both_act, (SEAL, SIBLING)) == Act((SEAL,))
    later = {"answers": {SIBLING: {"choice": "abstain"}, SEAL: {"choice": "act"}}}
    assert decision_from_jev(later, allowed) == Act((SEAL,))
    review_then_act = {"answers": {SIBLING: {"choice": "review"}, SEAL: {"choice": "act"}}}
    assert decision_from_jev(review_then_act, allowed) == Act((SEAL,))
    review_only = {"answers": {SIBLING: {"choice": "review"}, SEAL: {"choice": "abstain"}}}
    assert isinstance(decision_from_jev(review_only, allowed), Review)
    # A route act and a high noul do not cite when the span choice is abstain.
    ignored = {"answers": {"route": {"choice": "act"}, SEAL: {"noul": 0.99, "choice": "abstain"}}}
    assert isinstance(decision_from_jev(ignored, (SEAL,)), Abstain)
    assert isinstance(decision_from_jev({"answers": {SIBLING: {"choice": "nope"}}}, allowed), Abstain)


def test_jev_decide_follows_the_decode_flag(monkeypatch) -> None:
    monkeypatch.setenv("MUST_CITE_JEV_DECODE", "noul_only")

    def noul_transport(url, headers, body):
        assert "route" not in body["questions"]
        assert body["questions"][SEAL]["type"] == "noul"
        return {"answers": {SIBLING: {"noul": 0.4}, SEAL: {"noul": 0.7}}, "usage": {"input_tokens": 0}}, 1.0

    meter = Meter()
    decision = jev_decide("Which seal?", [(SIBLING, "a"), (SEAL, "b")], meter, {}, noul_transport)
    assert decision == Act((SEAL,))

    monkeypatch.setenv("MUST_CITE_JEV_DECODE", "choice_per_span")

    def choice_transport(url, headers, body):
        assert body["questions"][SIBLING]["type"] == "choice"
        assert body["questions"][SEAL]["type"] == "choice"
        return {
            "answers": {SIBLING: {"choice": "act"}, SEAL: {"choice": "act"}},
            "usage": {"input_tokens": 0},
        }, 1.0

    decision = jev_decide("Which seal?", [(SIBLING, "a"), (SEAL, "b")], Meter(), {}, choice_transport)
    assert decision == Act((SIBLING,))


def test_unknown_jev_decode_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("MUST_CITE_JEV_DECODE", "argmax")
    with pytest.raises(LiveError):
        build_jev_body("Which seal?", [(SEAL, "slate seal")])
    with pytest.raises(LiveError):
        decision_from_jev({"answers": {SEAL: {"noul": 0.9}}}, (SEAL,))


def test_jev_decode_clause_names_the_mode_only_when_jev_is_on(monkeypatch) -> None:
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setenv("MUST_CITE_JEV_DECODE", "noul_only")
    assert jev_decode_clause() == ""
    monkeypatch.setenv("TYPESAFE_API_KEY", "jev")
    assert jev_decode_clause() == " Jev decode is `noul_only`."
    monkeypatch.delenv("MUST_CITE_JEV_DECODE", raising=False)
    assert jev_decode_clause() == " Jev decode is `both`."
    monkeypatch.setenv("MUST_CITE_JEV_DECODE", "nope")
    with pytest.raises(LiveError):
        jev_decode_clause()


def test_sdk_call_reads_every_choice_and_noul(monkeypatch) -> None:
    class _Choice:
        def __init__(self, instructions, criteria):
            self.instructions = instructions
            self.criteria = criteria

    class _Noul:
        def __init__(self, instructions):
            self.instructions = instructions

    class _Answer:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class _Usage:
        input_tokens = 4

    class _Client:
        def __init__(self, model):
            self.model = model

        def system_one(self, state, questions):
            answers = {}
            for key, question in questions.items():
                if isinstance(question, _Choice):
                    answers[key] = _Answer(choice="act")
                else:
                    answers[key] = _Answer(noul=0.8)
            return type("Response", (), {"answers": answers, "usage": _Usage()})()

    import sys
    import types

    module = types.ModuleType("typesafe_sdk")
    module.Choice = _Choice
    module.Noul = _Noul
    module.TypeSafeClient = _Client
    monkeypatch.setitem(sys.modules, "typesafe_sdk", module)

    monkeypatch.setenv("MUST_CITE_JEV_DECODE", "choice_per_span")
    payload, _latency = _jev_call(build_jev_body("Which seal?", [(SIBLING, "a"), (SEAL, "b")]))
    assert payload["answers"][SIBLING] == {"type": "choice", "choice": "act"}
    assert "route" not in payload["answers"]
    assert decision_from_jev(payload, (SIBLING, SEAL)) == Act((SIBLING,))

    monkeypatch.setenv("MUST_CITE_JEV_DECODE", "noul_only")
    payload, _latency = _jev_call(build_jev_body("Which seal?", [(SEAL, "b")]))
    assert payload["answers"][SEAL] == {"type": "noul", "noul": 0.8}
    assert decision_from_jev(payload, (SEAL,)) == Act((SEAL,))


def test_jev_decide_reads_the_transport_payload() -> None:
    def transport(url, headers, body):
        assert body["questions"]["route"]["type"] == "choice"
        return {
            "answers": {"route": {"choice": "act"}, SEAL: {"noul": 0.7}},
            "usage": {"input_tokens": 1_000_000},
        }, 12.0

    meter = Meter()
    trace: dict[str, str] = {}
    decision = jev_decide("Which seal?", [(SEAL, "slate seal")], meter, trace, transport)
    assert decision == Act((SEAL,))
    assert meter.cost_usd == pytest.approx(0.042)
    assert meter.latency_ms == 12.0


def test_openai_cost_uses_both_token_sides_for_gpt4o_mini() -> None:
    meter_cost = openai_cost(
        "gpt-4o-mini",
        {"prompt_tokens": 2_000_000, "completion_tokens": 1_000_000},
    )
    assert meter_cost == pytest.approx(0.15 * 2 + 0.60)
    assert openai_cost("gpt-4o", {"prompt_tokens": 10, "completion_tokens": 10}) is None


def _seal_nodes() -> dict[NodeId, Node]:
    return {
        SEAL: Node(
            SEAL,
            ArtifactId("loft-mill"),
            2,
            (),
            Span(SEAL, 0, 10, "slate seal"),
        )
    }


def test_live_status_prefers_openai_then_anthropic(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    assert live_status() == "missing"
    monkeypatch.setenv("TYPESAFE_API_KEY", "jev")
    assert live_status() == "jev-only"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    assert live_status() == "anthropic"
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    assert live_status() == "openai"


def test_anthropic_cost_prices_haiku_and_leaves_sonnet_unknown() -> None:
    haiku = anthropic_cost(
        "claude-haiku-4-5",
        {"input_tokens": 1_000_000, "output_tokens": 1_000_000},
    )
    assert haiku == pytest.approx(1.00 + 5.00)
    snapshot = anthropic_cost(
        "claude-haiku-4-5-20251001",
        {"input_tokens": 2_000_000, "output_tokens": 500_000},
    )
    assert snapshot == pytest.approx(1.00 * 2 + 5.00 * 0.5)
    haiku35 = anthropic_cost(
        "claude-3-5-haiku-20241022",
        {"input_tokens": 1_000_000, "output_tokens": 1_000_000},
    )
    assert haiku35 == pytest.approx(0.80 + 4.00)
    assert anthropic_cost("claude-opus-5", {"input_tokens": 10, "output_tokens": 10}) is None


def test_anthropic_tool_use_drops_unknown_ids(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    seen: dict[str, object] = {}

    def transport(url, headers, body):
        seen["url"] = url
        seen["headers"] = headers
        seen["body"] = body
        return {
            "content": [
                {
                    "type": "tool_use",
                    "name": "decision",
                    "input": {"decision": "act", "node_ids": [SEAL, "missing/nope/0"]},
                }
            ],
            "usage": {"input_tokens": 1_000_000, "output_tokens": 1_000_000},
        }, 7.0

    meter = Meter()
    trace: dict[str, str] = {}
    choose = make_id_choose("Which seal?", _seal_nodes(), meter, trace, anthropic_complete(meter, transport))
    decision = choose(CandidateSet((SEAL, SIBLING)))
    assert decision == Act((SEAL,))
    assert seen["url"] == ANTHROPIC_URL
    headers = seen["headers"]
    assert isinstance(headers, dict)
    assert headers["x-api-key"] == "sk-ant-test"
    assert headers["anthropic-version"] == "2023-06-01"
    body = seen["body"]
    assert isinstance(body, dict)
    assert body["model"] == "claude-haiku-4-5"
    assert body["tool_choice"] == {"type": "tool", "name": "decision"}
    assert body["tools"][0]["input_schema"] == DECISION_SCHEMA["json_schema"]["schema"]
    blob = json.dumps(body)
    assert "start_char" not in blob
    assert "end_char" not in blob
    assert "slate seal" in blob
    assert meter.cost_usd == pytest.approx(6.0)
    assert meter.latency_ms == 7.0
    assert meter.cost_known is True


def test_anthropic_json_in_content_abstains_on_unknown_ids(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")

    def transport(url, headers, body):
        raw = json.dumps({"decision": "act", "node_ids": ["missing/nope/0"]})
        return {
            "content": [{"type": "text", "text": "```json\n" + raw + "\n```"}],
            "usage": {"input_tokens": 1_000_000, "output_tokens": 0},
        }, 1.0

    meter = Meter()
    trace: dict[str, str] = {}
    choose = make_id_choose("Which seal?", _seal_nodes(), meter, trace, anthropic_complete(meter, transport))
    assert isinstance(choose(CandidateSet((SEAL,))), Abstain)
    assert meter.cost_usd == pytest.approx(0.80)
    assert meter.cost_known is True


def test_anthropic_unknown_model_leaves_cost_unknown(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-5")

    def transport(url, headers, body):
        assert body["model"] == "claude-opus-5"
        return {"content": [{"type": "text", "text": "NO"}], "usage": {"input_tokens": 10, "output_tokens": 2}}, 1.0

    meter = Meter()
    assert make_text_fanout(meter, anthropic_complete(meter, transport))("Which seal?", SEAL, "slate seal") == "NO"
    assert meter.cost_known is False
    assert meter.cost_usd == 0.0
    note = meter_cost_note(["A"])
    assert "A" in note
    assert "ANTHROPIC_MODEL" in note


def test_text_fanout_posts_to_anthropic_when_that_is_the_only_chat_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    seen: dict[str, object] = {}

    def fake_post(url, headers, body):
        seen["url"] = url
        seen["body"] = body
        return {"content": [{"type": "text", "text": "NO"}], "usage": {"input_tokens": 1_000, "output_tokens": 10}}, 4.0

    monkeypatch.setattr("must_cite_rlm.live.post_json", fake_post)
    meter = Meter()
    assert make_text_fanout(meter)("Which seal?", SEAL, "slate seal") == "NO"
    assert seen["url"] == ANTHROPIC_URL
    body = seen["body"]
    assert isinstance(body, dict)
    assert "tools" not in body
    assert body["messages"][0]["role"] == "user"
    assert meter.cost_usd == pytest.approx((1_000 * 1.00 + 10 * 5.00) / 1_000_000)


def test_both_chat_keys_prefer_openai(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    seen: dict[str, object] = {}

    def fake_post(url, headers, body):
        seen["url"] = url
        seen["authorization"] = headers.get("Authorization")
        return {
            "choices": [{"message": {"content": "NO"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2},
        }, 1.0

    monkeypatch.setattr("must_cite_rlm.live.post_json", fake_post)
    assert live_status() == "openai"
    meter = Meter()
    assert make_text_fanout(meter)("Which seal?", SEAL, "slate seal") == "NO"
    assert seen["url"] == "https://api.openai.com/v1/chat/completions"
    assert seen["authorization"] == "Bearer sk-openai"
    note = meter_cost_note([])
    assert "gpt-4o-mini" in note
    assert "claude-haiku-4-5" not in note


def test_jev_payload_from_chat_keeps_allowed_ids_and_clamps() -> None:
    raw = json.dumps(
        {
            "route": "act",
            "act_probability": 1.4,
            "support": [
                {"node_id": "a", "probability": 0.7},
                {"node_id": "zz", "probability": 0.9},
                {"node_id": "b", "probability": -0.2},
                {"node_id": "a", "probability": 0.1},
            ],
        }
    )
    payload = jev_payload_from_chat(raw, (NodeId("a"), NodeId("b")))
    assert payload["answers"] == {
        "route": {"type": "choice", "choice": "act", "probabilities": {"act": 1.0}},
        "a": {"type": "noul", "noul": 0.7},
        "b": {"type": "noul", "noul": 0.0},
    }
    assert jev_payload_from_chat("not json", (NodeId("a"),)) == {"answers": {}}


@pytest.mark.parametrize(
    ("route", "support", "expected"),
    [
        ("act", [0.3, 0.8], Act((NodeId("b"),))),
        ("act", [0.3, 0.4], Abstain()),
        ("review", [0.9, 0.9], Review()),
        ("abstain", [0.9, 0.9], Abstain()),
    ],
)
def test_scored_chat_decide_uses_the_both_rule(route, support, expected) -> None:
    sent: list[dict | None] = []

    def complete(messages, schema):
        sent.append(schema)
        assert "character offsets" in messages[0]["content"]
        return json.dumps(
            {
                "route": route,
                "act_probability": 0.6,
                "support": [{"node_id": i, "probability": p} for i, p in zip(("a", "b"), support)],
            }
        )

    trace: dict[str, str] = {}
    decision = scored_chat_decide("q?", [(NodeId("a"), "A"), (NodeId("b"), "B")], Meter(), trace, complete)
    assert decision == expected
    assert sent == [SCORED_SCHEMA]
    assert json.loads(trace["raw"])["answers"]["route"]["probabilities"] == {"act": 0.6}


def test_anthropic_sonnet_5_sends_no_sampling_params_and_no_thinking(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
    seen: list[dict] = []

    def transport(url, headers, body):
        seen.append(body)
        return {"content": [{"type": "text", "text": "ok"}], "usage": {"input_tokens": 10, "output_tokens": 2}}, 1.0

    meter = Meter()
    assert anthropic_complete(meter, transport, model="claude-sonnet-5")([{"role": "user", "content": "hi"}], None) == "ok"
    assert seen[0]["model"] == "claude-sonnet-5"
    assert "temperature" not in seen[0] and seen[0]["thinking"] == {"type": "disabled"}
    assert meter.cost_usd == pytest.approx((10 * 2.00 + 2 * 10.00) / 1_000_000)
    anthropic_complete(meter, transport)([{"role": "user", "content": "hi"}], None)
    assert seen[1]["model"] == "claude-haiku-4-5" and seen[1]["temperature"] == 0
