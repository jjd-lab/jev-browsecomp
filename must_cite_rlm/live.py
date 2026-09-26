from __future__ import annotations

import json
import os
import time
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from must_cite_rlm.tree import Node
from must_cite_rlm.types import Abstain, Act, CandidateSet, Decision, NodeId, Review

JEV_INPUT_USD_PER_MTOKEN = 0.042
GPT4O_MINI_INPUT_USD_PER_MTOKEN = 0.15
GPT4O_MINI_OUTPUT_USD_PER_MTOKEN = 0.60
HAIKU_45_INPUT_USD_PER_MTOKEN = 1.00
HAIKU_45_OUTPUT_USD_PER_MTOKEN = 5.00
HAIKU_35_INPUT_USD_PER_MTOKEN = 0.80
HAIKU_35_OUTPUT_USD_PER_MTOKEN = 4.00
ACT_NOUL = 0.5
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5"
JEV_URL = "https://api.typesafe.ai/v1/systemone"
TOP_K = 3
ANTHROPIC_MAX_TOKENS = 1024
JEV_DECODE_ENV = "MUST_CITE_JEV_DECODE"
JEV_DECODES = ("both", "noul_only", "choice_per_span")

# Haiku 4.5 is the current cheap Claude id. Haiku 3.5 is retired on the Claude API;
# those ids stay priced at the published 3.5 list rate when ANTHROPIC_MODEL names them.
ANTHROPIC_TOKEN_USD: dict[str, tuple[float, float]] = {
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-4-5": (HAIKU_45_INPUT_USD_PER_MTOKEN, HAIKU_45_OUTPUT_USD_PER_MTOKEN),
    "claude-haiku-4-5-20251001": (HAIKU_45_INPUT_USD_PER_MTOKEN, HAIKU_45_OUTPUT_USD_PER_MTOKEN),
    "claude-3-5-haiku-latest": (HAIKU_35_INPUT_USD_PER_MTOKEN, HAIKU_35_OUTPUT_USD_PER_MTOKEN),
    "claude-3-5-haiku-20241022": (HAIKU_35_INPUT_USD_PER_MTOKEN, HAIKU_35_OUTPUT_USD_PER_MTOKEN),
}

NO_SAMPLING_MODELS = frozenset({"claude-sonnet-5"})

DECISION_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "decision",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "decision": {"type": "string", "enum": ["act", "review", "abstain"]},
                "node_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["decision", "node_ids"],
        },
    },
}

# The chat side of the Jev `both` decode: one route with a probability that act
# is right, and one support probability per candidate id.
SCORED_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "scored_decision",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "route": {"type": "string", "enum": ["act", "review", "abstain"]},
                "act_probability": {"type": "number"},
                "support": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "node_id": {"type": "string"},
                            "probability": {"type": "number"},
                        },
                        "required": ["node_id", "probability"],
                    },
                },
            },
            "required": ["route", "act_probability", "support"],
        },
    },
}

Transport = Callable[[str, dict[str, str], dict], tuple[dict, float]]
Complete = Callable[[list[dict[str, str]], dict | None], str]


class LiveError(Exception):
    pass


@dataclass
class Meter:
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    cost_known: bool = True

    def add(self, cost_usd: float | None, latency_ms: float) -> None:
        self.latency_ms += latency_ms
        if cost_usd is None:
            self.cost_known = False
            return
        self.cost_usd += cost_usd


def _chat_provider() -> str | None:
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None


def live_status() -> str:
    chat = _chat_provider()
    if chat is not None:
        return chat
    if os.environ.get("TYPESAFE_API_KEY"):
        return "jev-only"
    return "missing"


def skip_note(status: str) -> str:
    if status == "jev-only":
        reason = (
            "Live run skipped. `TYPESAFE_API_KEY` is set and neither `OPENAI_API_KEY` nor `ANTHROPIC_API_KEY` is set. "
            "Arm B can call Jev, but arm A and arm C need `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`."
        )
    else:
        reason = (
            "Live run skipped. This process has no `OPENAI_API_KEY`, no `ANTHROPIC_API_KEY`, and no `TYPESAFE_API_KEY`."
        )
    return "\n".join(
        [
            "# Scoreboard live",
            "",
            reason,
            "",
            "Set `OPENAI_API_KEY` to run arm A, arm C, and arm B when `TYPESAFE_API_KEY` is absent. "
            "If `OPENAI_API_KEY` is absent and `ANTHROPIC_API_KEY` is set, those arms use the Anthropic Messages API. "
            "When both `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` are set, OpenAI is used. "
            "Set `TYPESAFE_API_KEY` to send arm B through Jev. "
            "The Jev client uses `typesafe-sdk` when that package imports, and otherwise `POST https://api.typesafe.ai/v1/systemone`. "
            "Anthropic is `POST https://api.anthropic.com/v1/messages`.",
            "",
            "`OPENAI_MODEL` defaults to `gpt-4o-mini`. "
            "That model's list price is 0.15 dollars per million input tokens and 0.60 dollars per million output tokens. "
            "`ANTHROPIC_MODEL` defaults to `claude-haiku-4-5` "
            "(the Claude API alias of `claude-haiku-4-5-20251001`). "
            "That model's list price is 1.00 dollars per million input tokens and 5.00 dollars per million output tokens. "
            "Claude 3.5 Haiku (`claude-3-5-haiku-latest` and `claude-3-5-haiku-20241022`) is retired on the Claude API. "
            "Its published list price is 0.80 dollars per million input tokens and 4.00 dollars per million output tokens, "
            "and those ids are still priced if `ANTHROPIC_MODEL` names them. "
            "Jev's published input price is 0.042 dollars per million input tokens. "
            "Any other `OPENAI_MODEL` or `ANTHROPIC_MODEL`, including Opus, leaves `cost_usd` unknown.",
            "",
            "The stub table is `results/phase0_hotpot/SCOREBOARD.md`. `./scripts/run_scoreboard.sh` without `--live` does not call a provider.",
            "",
            "Risk-coverage is not computed. This run did not call a provider. Stub abstain is zero token overlap. There is no score threshold.",
            "",
        ]
    )


def meter_cost_note(unknown: list[str]) -> str:
    if live_status() == "anthropic":
        model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)
        rates = ANTHROPIC_TOKEN_USD.get(model)
        if unknown or rates is None:
            arms = ", ".join(unknown) if unknown else "this run"
            return (
                "`cost_usd` is an estimate at the priced Claude Haiku list rate, "
                "and it is incomplete for " + arms + " because `ANTHROPIC_MODEL` is not a priced Haiku id."
            )
        return (
            "`cost_usd` is the mean per question. "
            f"Anthropic model `{model}` is priced at {rates[0]:.2f} dollars per million input tokens "
            f"and {rates[1]:.2f} dollars per million output tokens. "
            "Jev uses 0.042 dollars per million input tokens."
        )
    if unknown:
        return (
            "`cost_usd` is an estimate at the gpt-4o-mini list price, "
            "and it is incomplete for " + ", ".join(unknown) + " because `OPENAI_MODEL` is not gpt-4o-mini."
        )
    return (
        "`cost_usd` is the mean per question. "
        "OpenAI uses the gpt-4o-mini list price when the payload has no dollar field. "
        "Jev uses 0.042 dollars per million input tokens."
    )


def post_json(url: str, headers: dict[str, str], body: dict) -> tuple[dict, float]:
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise LiveError(str(exc)) from exc
    latency_ms = (time.perf_counter() - started) * 1000
    if not isinstance(payload, dict):
        raise LiveError("provider response was not an object")
    return payload, latency_ms


def openai_cost(model: str, usage: Mapping[str, object]) -> float | None:
    if model != "gpt-4o-mini":
        return None
    prompt = usage.get("prompt_tokens", 0)
    completion = usage.get("completion_tokens", 0)
    if not isinstance(prompt, int) or not isinstance(completion, int):
        return None
    return (
        prompt * GPT4O_MINI_INPUT_USD_PER_MTOKEN + completion * GPT4O_MINI_OUTPUT_USD_PER_MTOKEN
    ) / 1_000_000


def anthropic_cost(model: str, usage: Mapping[str, object]) -> float | None:
    rates = ANTHROPIC_TOKEN_USD.get(model)
    if rates is None:
        return None
    prompt = usage.get("input_tokens", 0)
    completion = usage.get("output_tokens", 0)
    if not isinstance(prompt, int) or not isinstance(completion, int):
        return None
    return (prompt * rates[0] + completion * rates[1]) / 1_000_000


def jev_cost(input_tokens: int) -> float:
    return input_tokens * JEV_INPUT_USD_PER_MTOKEN / 1_000_000


def parse_llm_decision(raw: str, allowed: set[NodeId]) -> Decision:
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return Abstain()
    if not isinstance(obj, dict):
        return Abstain()
    kind = obj.get("decision")
    raw_ids = obj.get("node_ids", [])
    if kind == "review":
        return Review()
    if kind != "act" or not isinstance(raw_ids, list):
        return Abstain()
    ids = tuple(NodeId(item) for item in raw_ids if isinstance(item, str) and NodeId(item) in allowed)
    if not ids:
        return Abstain()
    return Act(ids)


def jev_decode_mode() -> str:
    mode = os.environ.get(JEV_DECODE_ENV, "both")
    if mode not in JEV_DECODES:
        raise LiveError("MUST_CITE_JEV_DECODE must be both, noul_only, or choice_per_span")
    return mode


def jev_decode_clause() -> str:
    if not os.environ.get("TYPESAFE_API_KEY"):
        return ""
    return f" Jev decode is `{jev_decode_mode()}`."


def _argmax_noul(answers: Mapping[str, object], allowed: tuple[NodeId, ...]) -> NodeId | None:
    best: tuple[float, NodeId] | None = None
    for node_id in allowed:
        answer = answers.get(node_id)
        if not isinstance(answer, dict):
            continue
        score = answer.get("noul")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            continue
        value = float(score)
        if value < ACT_NOUL:
            continue
        # A tie keeps the earliest id in allowed. A later equal noul does not replace it.
        if best is None or value > best[0]:
            best = (value, node_id)
    if best is None:
        return None
    return best[1]


def _decision_both(answers: Mapping[str, object], allowed: tuple[NodeId, ...]) -> Decision:
    route = answers.get("route")
    if not isinstance(route, dict) or route.get("choice") == "abstain":
        return Abstain()
    if route.get("choice") == "review":
        return Review()
    if route.get("choice") != "act":
        return Abstain()
    winner = _argmax_noul(answers, allowed)
    if winner is None:
        return Abstain()
    return Act((winner,))


def _decision_noul_only(answers: Mapping[str, object], allowed: tuple[NodeId, ...]) -> Decision:
    winner = _argmax_noul(answers, allowed)
    if winner is None:
        return Abstain()
    return Act((winner,))


def _decision_choice_per_span(answers: Mapping[str, object], allowed: tuple[NodeId, ...]) -> Decision:
    # Several acts cite the earliest id in allowed, so exact_id stays a singleton.
    reviewed = False
    for node_id in allowed:
        answer = answers.get(node_id)
        if not isinstance(answer, dict):
            continue
        choice = answer.get("choice")
        if choice == "act":
            return Act((node_id,))
        if choice == "review":
            reviewed = True
    if reviewed:
        return Review()
    return Abstain()


def decision_from_jev(payload: Mapping[str, object], allowed: tuple[NodeId, ...]) -> Decision:
    mode = jev_decode_mode()
    answers = payload.get("answers")
    if not isinstance(answers, dict):
        return Abstain()
    if mode == "noul_only":
        return _decision_noul_only(answers, allowed)
    if mode == "choice_per_span":
        return _decision_choice_per_span(answers, allowed)
    return _decision_both(answers, allowed)


def _route_question() -> dict:
    return {
        "type": "choice",
        "instructions": "Should these spans be cited, reviewed by a person, or refused?",
        "criteria": {
            "act": "At least one span supports the question.",
            "review": "A person should check these spans.",
            "abstain": "No span supports the question.",
        },
    }


def _noul_questions(pairs: list[tuple[NodeId, str]]) -> dict[str, dict]:
    return {
        str(node_id): {
            "type": "noul",
            "instructions": f"Does span {node_id} support the question?",
        }
        for node_id, _text in pairs
    }


def _choice_per_span_questions(pairs: list[tuple[NodeId, str]]) -> dict[str, dict]:
    return {
        str(node_id): {
            "type": "choice",
            "instructions": f"Should span {node_id} be cited, reviewed by a person, or refused?",
            "criteria": {
                "act": "This span supports the question.",
                "review": "A person should check this span.",
                "abstain": "This span does not support the question.",
            },
        }
        for node_id, _text in pairs
    }


def build_jev_body(question: str, pairs: list[tuple[NodeId, str]]) -> dict:
    mode = jev_decode_mode()
    if mode == "noul_only":
        questions: dict[str, dict] = _noul_questions(pairs)
    elif mode == "choice_per_span":
        questions = _choice_per_span_questions(pairs)
    else:
        questions = {"route": _route_question()}
        questions.update(_noul_questions(pairs))
    lines = [question, ""]
    for node_id, text in pairs:
        lines.append(f"{node_id}\n{text}")
    model = os.environ.get("TYPESAFE_DEFAULT_MODEL", "jev-latest")
    return {"model": model, "state": "\n".join(lines), "questions": questions}


def _append_raw(trace: dict[str, str], raw: str) -> None:
    prior = trace.get("raw", "")
    trace["raw"] = raw if not prior else prior + "\n" + raw


def openai_decide(
    question: str,
    pairs: list[tuple[NodeId, str]],
    meter: Meter,
    trace: dict[str, str],
    complete: Complete,
) -> Decision:
    allowed = {node_id for node_id, _ in pairs}
    lines = [question, ""]
    for node_id, text in pairs:
        lines.append(f"{node_id}\n{text}")
    messages = [
        {
            "role": "system",
            "content": (
                "Choose act, review, or abstain. "
                "For act, copy node ids from the list. "
                "Do not write character offsets."
            ),
        },
        {"role": "user", "content": "\n".join(lines)},
    ]
    raw = complete(messages, DECISION_SCHEMA)
    _append_raw(trace, raw)
    return parse_llm_decision(raw, allowed)


def _probability(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return min(1.0, max(0.0, float(value)))


def jev_payload_from_chat(raw: str, allowed: tuple[NodeId, ...]) -> dict:
    """Recast a scored chat reply as Jev `both` answers, so the same decode and trace read it."""
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return {"answers": {}}
    if not isinstance(obj, dict):
        return {"answers": {}}
    route = obj.get("route")
    p_act = _probability(obj.get("act_probability"))
    answers: dict[str, dict] = {}
    if route in ("act", "review", "abstain"):
        answers["route"] = {"type": "choice", "choice": route, "probabilities": {"act": p_act or 0.0}}
    support = obj.get("support")
    for item in support if isinstance(support, list) else []:
        if not isinstance(item, dict):
            continue
        node_id = item.get("node_id")
        score = _probability(item.get("probability"))
        if node_id in allowed and score is not None and node_id not in answers:
            answers[node_id] = {"type": "noul", "noul": score}
    return {"answers": answers}


def scored_chat_decide(
    question: str,
    pairs: list[tuple[NodeId, str]],
    meter: Meter,
    trace: dict[str, str],
    complete: Complete,
) -> Decision:
    allowed = tuple(node_id for node_id, _ in pairs)
    route = _route_question()
    lines = [question, ""]
    for node_id, text in pairs:
        lines.append(f"{node_id}\n{text}")
    messages = [
        {
            "role": "system",
            "content": " ".join(
                [
                    route["instructions"],
                    *(f"{name}: {meaning}" for name, meaning in route["criteria"].items()),
                    "Give act_probability, the probability that act is the right route.",
                    "For every span id in the list, give the probability that the span supports the question.",
                    "Copy node ids from the list. Do not write character offsets.",
                ]
            ),
        },
        {"role": "user", "content": "\n".join(lines)},
    ]
    raw = complete(messages, SCORED_SCHEMA)
    payload = jev_payload_from_chat(raw, allowed)
    _append_raw(trace, json.dumps(payload))
    return _decision_both(payload["answers"], allowed)


def text_messages(question: str, node_id: NodeId, text: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "Answer from the section only. "
                "If it is relevant, name the node id and quote the section. "
                "If it is not relevant, say NO."
            ),
        },
        {"role": "user", "content": f"Question: {question}\nNode {node_id}\n{text}"},
    ]


def chat_complete(meter: Meter, transport: Transport | None = None) -> Complete:
    send = transport if transport is not None else post_json
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    key = os.environ.get("OPENAI_API_KEY", "")

    def complete(messages: list[dict[str, str]], schema: dict | None) -> str:
        body: dict = {"model": model, "messages": messages, "temperature": 0}
        if schema is not None:
            body["response_format"] = schema
        payload, latency_ms = send(
            OPENAI_URL,
            {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            body,
        )
        usage = payload.get("usage")
        cost = openai_cost(model, usage) if isinstance(usage, dict) else None
        meter.add(cost, latency_ms)
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LiveError("chat response had no choices")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise LiveError("chat response had no content")
        return content

    return complete


def _unwrap_json(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    body = lines[1:]
    if body and body[-1].strip().startswith("```"):
        body = body[:-1]
    return "\n".join(body).strip()


def anthropic_message_text(payload: Mapping[str, object], *, json_text: bool = False) -> str:
    content = payload.get("content")
    if not isinstance(content, list) or not content:
        raise LiveError("anthropic response had no content")
    texts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_use":
            tool_input = block.get("input")
            if isinstance(tool_input, str):
                return tool_input
            if isinstance(tool_input, dict):
                return json.dumps(tool_input)
        if block.get("type") == "text" and isinstance(block.get("text"), str):
            texts.append(block["text"])
    if not texts:
        raise LiveError("anthropic response had no content")
    raw = "\n".join(texts)
    return _unwrap_json(raw) if json_text else raw


def anthropic_complete(meter: Meter, transport: Transport | None = None, model: str | None = None) -> Complete:
    send = transport if transport is not None else post_json
    model = model or os.environ.get("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)
    key = os.environ.get("ANTHROPIC_API_KEY", "")

    def complete(messages: list[dict[str, str]], schema: dict | None) -> str:
        system = "\n".join(message["content"] for message in messages if message.get("role") == "system")
        dialog = [
            {"role": message["role"], "content": message["content"]}
            for message in messages
            if message.get("role") != "system"
        ]
        body: dict = {
            "model": model,
            "max_tokens": ANTHROPIC_MAX_TOKENS,
            "temperature": 0,
            "messages": dialog,
        }
        if model in NO_SAMPLING_MODELS:
            # These reject sampling params, and default thinking would eat ANTHROPIC_MAX_TOKENS.
            del body["temperature"]
            body["thinking"] = {"type": "disabled"}
        if system:
            body["system"] = system
        if schema is not None:
            spec = schema.get("json_schema")
            if not isinstance(spec, dict):
                raise LiveError("decision schema was not json_schema")
            name = spec.get("name")
            inner = spec.get("schema")
            if not isinstance(name, str) or not isinstance(inner, dict):
                raise LiveError("decision schema was incomplete")
            body["tools"] = [
                {
                    "name": name,
                    "description": spec.get(
                        "description", "Choose act, review, or abstain. For act, copy node ids from the list."
                    ),
                    "input_schema": inner,
                }
            ]
            body["tool_choice"] = {"type": "tool", "name": name}
        payload, latency_ms = send(
            ANTHROPIC_URL,
            {
                "x-api-key": key,
                "anthropic-version": ANTHROPIC_VERSION,
                "Content-Type": "application/json",
            },
            body,
        )
        usage = payload.get("usage")
        cost = anthropic_cost(model, usage) if isinstance(usage, dict) else None
        meter.add(cost, latency_ms)
        return anthropic_message_text(payload, json_text=schema is not None)

    return complete


def provider_complete(meter: Meter, transport: Transport | None = None) -> Complete:
    chat = _chat_provider()
    if chat == "openai":
        return chat_complete(meter, transport)
    if chat == "anthropic":
        return anthropic_complete(meter, transport)
    raise LiveError("missing chat provider")


def jev_decide(
    question: str,
    pairs: list[tuple[NodeId, str]],
    meter: Meter,
    trace: dict[str, str],
    transport: Transport | None = None,
) -> Decision:
    body = build_jev_body(question, pairs)
    allowed = tuple(node_id for node_id, _ in pairs)
    if transport is None:
        payload, latency_ms = _jev_call(body)
    else:
        payload, latency_ms = transport(JEV_URL, {}, body)
    usage = payload.get("usage")
    tokens = usage.get("input_tokens", 0) if isinstance(usage, dict) else 0
    cost = jev_cost(tokens) if isinstance(tokens, int) else None
    meter.add(cost, latency_ms)
    raw = json.dumps(payload)
    _append_raw(trace, raw)
    return decision_from_jev(payload, allowed)


def _jev_call(body: dict) -> tuple[dict, float]:
    try:
        from typesafe_sdk import Choice, Noul, TypeSafeClient
    except ImportError:
        key = os.environ.get("TYPESAFE_API_KEY", "")
        return post_json(
            JEV_URL,
            {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            body,
        )
    questions = {}
    for key, spec in body["questions"].items():
        if spec["type"] == "choice":
            questions[key] = Choice(instructions=spec["instructions"], criteria=spec["criteria"])
        else:
            questions[key] = Noul(instructions=spec["instructions"])
    started = time.perf_counter()
    try:
        response = TypeSafeClient(model=body["model"]).system_one(state=body["state"], questions=questions)
    except Exception as exc:
        raise LiveError(str(exc)) from exc
    latency_ms = (time.perf_counter() - started) * 1000
    answers: dict[str, dict] = {}
    for key, spec in body["questions"].items():
        answer = response.answers[key]
        if spec["type"] == "choice":
            answers[key] = {"type": "choice", "choice": answer.choice}
        else:
            answers[key] = {"type": "noul", "noul": float(answer.noul)}
    usage = getattr(response, "usage", None)
    input_tokens = 0 if usage is None else int(getattr(usage, "input_tokens", 0) or 0)
    return {"answers": answers, "usage": {"input_tokens": input_tokens}}, latency_ms


def make_text_fanout(meter: Meter, complete: Complete | None = None):
    speak = complete if complete is not None else provider_complete(meter)

    def fanout(question: str, node_id: NodeId, text: str) -> str:
        return speak(text_messages(question, node_id, text), None)

    return fanout


def make_id_choose(
    question: str,
    nodes: Mapping[NodeId, Node],
    meter: Meter,
    trace: dict[str, str],
    complete: Complete | None = None,
    prompt_text: Mapping[NodeId, str] | None = None,
    decider: str | None = None,
):
    """`decider` None keeps the key rule. "jev" forces Jev. "chat" forces the scored chat decide."""
    use_jev = decider == "jev" or (decider is None and bool(os.environ.get("TYPESAFE_API_KEY")))
    chat = None if use_jev else (complete if complete is not None else provider_complete(meter))

    def choose(candidates: CandidateSet) -> Decision:
        pairs: list[tuple[NodeId, str]] = []
        for node_id in candidates.node_ids:
            if prompt_text is not None and node_id in prompt_text:
                pairs.append((node_id, prompt_text[node_id]))
                continue
            node = nodes.get(node_id)
            if node is not None:
                pairs.append((node_id, node.span.text))
        if use_jev:
            return jev_decide(question, pairs, meter, trace)
        if chat is None:
            raise LiveError("missing chat provider")
        if decider == "chat":
            return scored_chat_decide(question, pairs, meter, trace, chat)
        return openai_decide(question, pairs, meter, trace, chat)

    return choose
