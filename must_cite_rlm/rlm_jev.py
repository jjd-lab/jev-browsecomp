"""RLM (Zhang, Kraska, Khattab; `rlms`) with Jev as REPL tools, on BrowseComp-Plus (1K documents).

The root LM writes Python in a Docker REPL where `context` is {docid: text}
for the question's 1,000 documents. Both arms get the library's `llm_query`
sub-calls. Arm B also gets two Jev tools, defined in the container as code
that calls a host-side proxy, so the Typesafe key never enters the container:

- jev_screen(question, items) -> {key: support probability}, any number of items.
- jev_decide(question, items) -> route act|review|abstain, p_act, cite, support; at most 8 items.

Arm B's gate is the last jev_decide the RLM made; arm A's confidence is its own.
Answers use the BrowseComp-Plus response format and its judge template.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from must_cite_rlm import live
from must_cite_rlm.browsecomp import CORPUS_CACHE, PROMPT_CHARS
from must_cite_rlm.live import Meter
from must_cite_rlm.recurse import BATCH, _batched, _scored, jev_nouls
from must_cite_rlm.types import Act, NodeId

ROOT_MODEL = "claude-sonnet-5"
SUB_MODEL = "claude-haiku-4-5"
# A Haiku judge flipped identical answers between arms in the pilot.
JUDGE_MODEL = "claude-sonnet-5"
MAX_TOKENS_PER_QUESTION = 500_000
LOG_DIR = CORPUS_CACHE.parent / "rlm_logs"
# Harness v2: 30 (was 20) plus the FINAL_TURN rewrite; see results/findings/phase1_rlm.md.
MAX_ITERATIONS = 30
MAX_TIMEOUT_S = 900
# Jev batches for one jev_screen call run this many at a time.
SCREEN_WORKERS = 8

# From texttron/BrowseComp-Plus search_agent/prompts.py, with the search tools replaced by `context`.
QUERY_TEMPLATE = """
You are a deep research agent. Answer the question using the documents in the REPL variable `context`, a dict mapping docid (str) to document text. There are 1,000 documents; most are irrelevant.

Question: {question}

Your final answer must be in the following format:
Explanation: {{your explanation for your final answer. For this explanation section only, you should cite your evidence documents inline by enclosing their docids in square brackets [] at the end of sentences. For example, [20].}}
Exact Answer: {{your succinct, final answer}}
Confidence: {{your confidence score between 0% and 100% for your answer}}

The string you put in answer["content"] is graded as-is, so it must contain all three lines above: "Explanation:" with [docid] citations, "Exact Answer:", and "Confidence:".
""".strip()

ARM_B_NOTE = """

Two cheap typed-decision tools are available in the REPL. They cost far less than llm_query, so prefer them for filtering:
- jev_screen(question, items) takes a dict {key: text} of any size (each text is cut to 12,000 chars) and returns {key: probability that the text supports answering the question}. Use it to filter many documents or chunks before reading any closely.
- jev_decide(question, items) takes at most 8 {key: text} items and returns {"route": "act"|"review"|"abstain", "p_act": float, "cite": key or None, "support": {key: float}}.
Before you give the final answer, you must call jev_decide on your best evidence (up to 8 items) and cite its "cite" key's docid."""

# Arm B2 differs from B only in the screening tool: one call returns a readable shortlist.
ARM_B2_NOTE = """

Two cheap typed-decision tools are available in the REPL. They cost far less than llm_query, so prefer them for filtering:
- jev_shortlist(question, context, k=10) screens every document with Jev in one call (each text is cut to 12,000 chars) and returns the top k as a list of {"docid", "score", "snippet"} sorted by score, where snippet is the document's first 800 characters. Print it in the same code block you call it from.
- jev_decide(question, items) takes at most 8 {key: text} items and returns {"route": "act"|"review"|"abstain", "p_act": float, "cite": key or None, "support": {key: float}}.
Before you give the final answer, you must call jev_decide on your best evidence (up to 8 items) and cite its "cite" key's docid."""

# From texttron/BrowseComp-Plus scripts_evaluation/evaluate_run.py (the Qwen3-32B judge path).
GRADER_TEMPLATE = """
Judge whether the following [response] to [question] is correct or not based on the precise and unambiguous [correct_answer] below.

[question]: {question}

[response]: {response}

[correct_answer]: {correct_answer}

Your judgement must be in the format and criteria specified below:

extracted_final_answer: The final exact answer extracted from the [response].

[correct_answer]: Repeat the [correct_answer] given above.

reasoning: Explain why the extracted_final_answer is correct or incorrect based on [correct_answer], in the context of this [question]. You should judge whether the extracted_final_answer is semantically equivalent to [correct_answer], allowing the extracted_final_answer to be string variations of [correct_answer]. You should also allow the extracted_final_answer to be more precise or verbose than [correct_answer], as long as its additional details are correct. Do not comment on any background to the problem, do not attempt to solve the problem, do not argue for any answer different than [correct_answer], focus only on whether the answers are semantically equivalent.

correct: Answer 'yes' if extracted_final_answer matches the [correct_answer] given above, or is within a small margin of error for numerical problems. Answer 'no' otherwise, i.e. if there if there is any inconsistency, ambiguity, non-equivalency, or if the extracted answer is incorrect.


confidence: The extracted confidence score between 0|\\%| and 100|\\%| from [response]. Put 100 if there is no confidence score available.
""".strip()

JEV_TOOL_CODE = '''
def {name}(question, items):
    import requests
    r = requests.post("{url}/{path}", json={{"question": question, "items": items}}, timeout=600)
    r.raise_for_status()
    return r.json()
'''
JEV_SHORTLIST_CODE = '''
def jev_shortlist(question, docs, k=10, snippet=800):
    import requests
    items = {{str(key): str(text)[:12000] for key, text in docs.items()}}
    r = requests.post("{url}/screen", json={{"question": question, "items": items}}, timeout=600)
    r.raise_for_status()
    scores = r.json()
    top = sorted(scores, key=lambda key: -scores[key])[:k]
    return [{{"docid": key, "score": scores[key], "snippet": str(docs[key])[:snippet]}} for key in top]
'''
JEV_TOOL_HELP = {
    "jev_screen": "jev_screen(question, items: dict[str, str]) -> {key: support probability}. Cheap bulk filter; any size.",
    "jev_decide": "jev_decide(question, items: dict[str, str], at most 8) -> {route, p_act, cite, support}. Required final gate.",
}


@dataclass
class JevProxy:
    """Host-side HTTP proxy the container's Jev tools call. One per question, so cost and calls stay per question."""

    meter: Meter = field(default_factory=Meter)
    decides: list[dict] = field(default_factory=list)
    screened: int = 0

    def screen(self, question: str, items: dict[str, str]) -> dict[str, float]:
        pairs = [(str(key), str(text)[:PROMPT_CHARS]) for key, text in items.items()]
        self.screened += len(pairs)

        def one(batch: list[tuple[str, str]]) -> tuple[dict[str, float], Meter]:
            meter = Meter()
            return _scored(jev_nouls, question, batch, meter), meter

        scores: dict[str, float] = {}
        with ThreadPoolExecutor(max_workers=SCREEN_WORKERS) as pool:
            for part, meter in pool.map(one, [list(b) for b in _batched(pairs, BATCH)]):
                scores.update(part)
                self.meter.add(meter.cost_usd, meter.latency_ms)
        return scores

    def decide(self, question: str, items: dict[str, str]) -> dict:
        pairs = [(NodeId(str(key)), str(text)[:PROMPT_CHARS]) for key, text in list(items.items())[:BATCH]]
        trace: dict[str, str] = {}
        decision = live.jev_decide(question, pairs, self.meter, trace)
        answers = json.loads(trace["raw"].splitlines()[-1]).get("answers", {})
        route = answers.get("route", {})
        result = {
            "route": route.get("choice", "abstain"),
            "p_act": float(route.get("probabilities", {}).get("act", 0.0)),
            "cite": decision.node_ids[0] if isinstance(decision, Act) and decision.node_ids else None,
            "support": {key: float(answers[key]["noul"]) for key, _ in pairs if key in answers},
        }
        self.decides.append(result)
        return result

    def __enter__(self) -> str:
        proxy = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 - http.server API
                try:
                    body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                    handler = proxy.screen if self.path == "/screen" else proxy.decide
                    out = json.dumps(handler(body["question"], body["items"])).encode()
                    self.send_response(200)
                except Exception as exc:  # the RLM sees the error text and can retry
                    out = json.dumps({"error": str(exc)}).encode()
                    self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(out)

            def log_message(self, *args) -> None:
                pass

        # Docker Desktop on macOS routes host.docker.internal to the host's loopback.
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return f"http://host.docker.internal:{self._server.server_address[1]}"

    def __exit__(self, *exc) -> None:
        self._server.shutdown()
        self._server.server_close()


def _confidence(match: re.Match | None) -> float | None:
    if match is None:
        return None
    value = float(match.group(1))
    return value / 100 if match.group(2) or value > 1 else value


def parse_response(text: str) -> dict:
    answer = re.search(r"Exact Answer:\s*(.+)", text)
    confidence = re.search(r"Confidence:\s*([\d.]+)\s*(%?)", text)
    explanation = text.split("Exact Answer:")[0]
    return {
        "exact_answer": answer.group(1).strip() if answer else None,
        "confidence": _confidence(confidence),
        "cited": list(dict.fromkeys(re.findall(r"\[(\d+)\]", explanation))),
    }


def judge(question: str, response: str, correct_answer: str, meter: Meter) -> dict:
    complete = live.anthropic_complete(meter, model=JUDGE_MODEL)
    prompt = GRADER_TEMPLATE.format(question=question, response=response, correct_answer=correct_answer)
    text = complete([{"role": "user", "content": prompt}], None)
    correct = re.search(r"correct:\**\s*(yes|no)", text, re.IGNORECASE)
    return {
        "correct": bool(correct) and correct.group(1).lower() == "yes",
        "parsed": bool(correct),
        "raw": text,
        "model": JUDGE_MODEL,
    }


_tap = threading.local()


def _text(response) -> str:
    return "".join(block.text for block in response.content if block.type == "text")


RLMS_OUT_OF_ITERATIONS = "Please provide a final answer to the user's question based on the information provided."
FINAL_TURN = (
    "You have no REPL turns left. Do not write code. Using only what you have found so far, reply now with "
    "exactly these three lines: \"Explanation:\" with [docid] citations, \"Exact Answer:\", and \"Confidence:\"."
)


def _no_trailing_assistant(messages: list) -> list:
    """Claude 4.6+ rejects assistant prefill, and rlms ends its out-of-iterations prompt with one.

    That prompt also got code back instead of an answer, so it becomes an explicit no-code final turn.
    """
    if messages and messages[-1].get("role") == "assistant":
        content = messages[-1]["content"]
        return messages[:-1] + [{"role": "user", "content": FINAL_TURN if content == RLMS_OUT_OF_ITERATIONS else content}]
    return messages


def _install_client_tap() -> None:
    """Record each LM client an RLM builds in this thread, and patch rlms' Anthropic client.

    rlms drops its usage summary when a run ends in an exception (timeouts
    included), so cost is read off the clients themselves. rlms 0.1.3 also
    returns content[0].text, which fails when the first block is thinking or
    the content is empty, and sends a trailing assistant message.
    """
    import rlm.core.rlm as core
    from rlm.clients.anthropic import AnthropicClient

    if getattr(core.get_client, "_must_cite_tap", False):
        return

    def completion(self, prompt, model=None):
        messages, system = self._prepare_messages(prompt)
        model = model or self.model_name
        kwargs = {"model": model, "max_tokens": self.max_tokens, "messages": _no_trailing_assistant(messages)}
        if system:
            kwargs["system"] = system
        response = self.client.messages.create(**kwargs)
        self._track_cost(response, model)
        return _text(response)

    async def acompletion(self, prompt, model=None):
        messages, system = self._prepare_messages(prompt)
        model = model or self.model_name
        kwargs = {"model": model, "max_tokens": self.max_tokens, "messages": _no_trailing_assistant(messages)}
        if system:
            kwargs["system"] = system
        response = await self.async_client.messages.create(**kwargs)
        self._track_cost(response, model)
        return _text(response)

    AnthropicClient.completion = completion
    AnthropicClient.acompletion = acompletion
    original = core.get_client

    def tapped(*args, **kwargs):
        client = original(*args, **kwargs)
        getattr(_tap, "clients", []).append(client)
        return client

    tapped._must_cite_tap = True
    core.get_client = tapped


def _client_usage(clients: list) -> tuple[float, dict[str, dict[str, int]]]:
    cost = 0.0
    tokens: dict[str, dict[str, int]] = {}
    for client in clients:
        for model, count in client.model_input_tokens.items():
            usage = {"input_tokens": count, "output_tokens": client.model_output_tokens[model]}
            cost += live.anthropic_cost(model, usage) or 0.0
            entry = tokens.setdefault(model, {"input_tokens": 0, "output_tokens": 0, "calls": 0})
            entry["input_tokens"] += usage["input_tokens"]
            entry["output_tokens"] += usage["output_tokens"]
            entry["calls"] += client.model_call_counts[model]
    return cost, tokens


def _write_compact_log(path, logger) -> None:
    """Per turn: the code, trimmed stdout and stderr, and timing. Enough to diagnose a run, ~1 MB not ~1 GB."""
    trajectory = logger.get_trajectory()
    if trajectory is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for turn in trajectory["iterations"]:
            blocks = [
                {
                    "code": block.get("code", ""),
                    "stdout": (block.get("result") or {}).get("stdout", "")[:2000],
                    "stderr": (block.get("result") or {}).get("stderr", "")[:1000],
                }
                for block in turn.get("code_blocks") or []
            ]
            handle.write(
                json.dumps(
                    {
                        "iteration": turn.get("iteration"),
                        "seconds": turn.get("iteration_time"),
                        "final_answer": turn.get("final_answer"),
                        "blocks": blocks,
                    }
                )
                + "\n"
            )


def run_question(row: dict, context: dict[str, str], arm: str, max_tokens: int = MAX_TOKENS_PER_QUESTION) -> dict:
    from rlm import RLM
    from rlm.logger import RLMLogger

    _install_client_tap()
    _tap.clients = []
    started = time.perf_counter()
    root_prompt = QUERY_TEMPLATE.format(question=row["question"]) + {"B": ARM_B_NOTE, "B2": ARM_B2_NOTE}.get(arm, "")
    backend_kwargs = {"model_name": ROOT_MODEL, "api_key": os.environ["ANTHROPIC_API_KEY"]}
    proxy = JevProxy()
    # In memory only: the on-disk RLMLogger writes the full prompt every turn (~1 GB/question).
    logger = RLMLogger()
    with proxy as url:
        tools = None
        if arm in ("B", "B2"):
            tools = {
                name: {"tool": JEV_TOOL_CODE.format(name=name, url=url, path=name.split("_")[1]), "description": help_}
                for name, help_ in JEV_TOOL_HELP.items()
            }
        if arm == "B2":
            del tools["jev_screen"]
            tools["jev_shortlist"] = {
                "tool": JEV_SHORTLIST_CODE.format(url=url),
                "description": "jev_shortlist(question, context, k=10) -> top-k [{docid, score, snippet}] in one call.",
            }
        try:
            rlm = RLM(
                backend="anthropic",
                backend_kwargs=backend_kwargs,
                other_backends=["anthropic"],
                other_backend_kwargs=[{"model_name": SUB_MODEL, "api_key": os.environ["ANTHROPIC_API_KEY"]}],
                environment="docker",
                max_depth=1,
                max_iterations=MAX_ITERATIONS,
                max_timeout=MAX_TIMEOUT_S,
                max_tokens=max_tokens,
                custom_tools=tools,
                custom_sub_tools={},
                logger=logger,
            )
            result = rlm.completion(context, root_prompt=root_prompt)
            response, error = result.response, None
        except Exception as exc:
            response, error = getattr(exc, "partial_answer", None) or "", f"{type(exc).__name__}: {exc}"
    _write_compact_log(LOG_DIR / arm / f"q{row['id']}.jsonl", logger)
    cost_rlm, tokens_rlm = _client_usage(_tap.clients)
    parsed = parse_response(response)
    return {
        "id": row["id"],
        "arm": arm,
        "response": response,
        **parsed,
        "gate": proxy.decides[-1] if proxy.decides else None,
        "jev_decides": len(proxy.decides),
        "jev_screened": proxy.screened,
        "cost_rlm": cost_rlm,
        "cost_jev": proxy.meter.cost_usd,
        "tokens_rlm": tokens_rlm,
        "seconds": time.perf_counter() - started,
        "max_iterations": MAX_ITERATIONS,
        "max_tokens": max_tokens,
        "capped": tokens_rlm.get(ROOT_MODEL, {}).get("calls", 0) > MAX_ITERATIONS,
        "error": error,
    }


def _answer_window(text: str, answer: str | None) -> str:
    """The PROMPT_CHARS window around the answer's first mention, else the start of the doc."""
    at = text.lower().find(answer.lower()) if answer else -1
    if at < 0:
        return text[:PROMPT_CHARS]
    start = max(0, min(at - PROMPT_CHARS // 2, len(text) - PROMPT_CHARS))
    return text[start : start + PROMPT_CHARS]


def verify_gate(question: str, answer: str | None, cited: dict[str, str], meter: Meter) -> dict:
    """Post-hoc Jev gate, same for both arms: does the cited evidence support this proposed answer?

    One Choice (act|review|abstain) whose p(act) is the gate score. No answer or
    no cited doc scores p_act 0 without a call.
    """
    if not answer or not cited:
        return {"route": "abstain", "p_act": 0.0, "called": False}
    pairs = [(docid, _answer_window(text, answer)) for docid, text in list(cited.items())[:BATCH]]
    lines = [f"Question: {question}", f"Proposed answer: {answer}", ""] + [f"{docid}\n{text}" for docid, text in pairs]
    questions = {
        "verify": {
            "type": "choice",
            "instructions": "Do these documents support the proposed answer to the question?",
            "criteria": {
                "act": "The documents support the proposed answer.",
                "review": "A person should check the proposed answer against the documents.",
                "abstain": "The documents do not support the proposed answer.",
            },
        },
    }
    body = {"model": os.environ.get("TYPESAFE_DEFAULT_MODEL", "jev-latest"), "state": "\n".join(lines), "questions": questions}
    payload, latency_ms = live._jev_call(body)
    tokens = payload.get("usage", {}).get("input_tokens", 0)
    meter.add(tokens * live.JEV_INPUT_USD_PER_MTOKEN / 1_000_000, latency_ms)
    verify = payload.get("answers", {}).get("verify", {})
    if "probabilities" not in verify:
        raise live.LiveError("Jev returned no Choice probabilities; the typesafe_sdk path drops them")
    return {
        "route": verify.get("choice"),
        "p_act": float(verify["probabilities"].get("act", 0.0)),
        "called": True,
    }
