"""Arms J and K: single-call readers on BrowseComp-Plus (1K documents).

J: Jev screens every document once (a Noul per doc, first PROMPT_CHARS each).
K: BM25 ranks the documents instead (the control for J). Either way the top
READ_DOCS go to a single Sonnet call, and there is no RLM loop. The result
row has the same fields as `rlm_jev.run_question`, so the judge, the post-hoc
gate, and the analysis read it unchanged.

`ReaderConfig` holds the untested variants; its defaults reproduce the recorded
runs (scores hidden from Sonnet, no reject, 16k output tokens).
"""

from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass

from must_cite_rlm import live
from must_cite_rlm.arms import _bm25_scores
from must_cite_rlm.browsecomp import PROMPT_CHARS
from must_cite_rlm.rlm_jev import ROOT_MODEL, JevProxy, parse_response

READ_DOCS = 8
MAX_OUTPUT_TOKENS = 16_000

READER_TEMPLATE = """
You are a deep research agent. Answer the question using only the documents below. Each starts with its docid in square brackets.{score_note}

Question: {question}

Documents:
{documents}

Your final answer must be in the following format:
Explanation: {{your explanation for your final answer. For this explanation section only, you should cite your evidence documents inline by enclosing their docids in square brackets [] at the end of sentences. For example, [20].}}
Exact Answer: {{your succinct, final answer}}
Confidence: {{your confidence score between 0% and 100% for your answer}}
""".strip()

SCORE_NOTE = (
    " Each also shows a relevance score between 0 and 1 from a screening model; "
    "it can be wrong, so judge each document by its text."
)


@dataclass(frozen=True)
class ReaderConfig:
    # "jev" (arm J) or "bm25" (arm K, BM25 over full document text within the question's pool).
    ranker: str = "jev"
    # Label each document with its Jev screen score in Sonnet's prompt.
    show_scores: bool = False
    # Skip Sonnet and abstain when Jev's best screen score is below this.
    reject_below: float | None = None
    # Sonnet's output cap; adaptive thinking counts against it. 16k ran out on 5 of 50 held-out questions.
    max_output_tokens: int = MAX_OUTPUT_TOKENS


def rank(scores: dict[str, float], context: dict[str, str]) -> list[str]:
    """Top READ_DOCS by score; ties keep the context order."""
    order = {docid: position for position, docid in enumerate(context)}
    return sorted(scores, key=lambda docid: (-scores[docid], order[docid]))[:READ_DOCS]


def bm25_scores(question: str, context: dict[str, str]) -> dict[str, float]:
    return {str(docid): score for score, docid in _bm25_scores(question, list(context.items()))}


def build_prompt(question: str, shortlist: list[str], scores: dict[str, float], context: dict[str, str], config: ReaderConfig) -> str:
    def header(docid: str) -> str:
        return f"[{docid}] (relevance {scores[docid]:.2f})" if config.show_scores else f"[{docid}]"

    documents = "\n\n".join(f"{header(docid)}\n{context[docid][:PROMPT_CHARS]}" for docid in shortlist)
    return READER_TEMPLATE.format(
        question=question, documents=documents, score_note=SCORE_NOTE if config.show_scores else ""
    )


def run_reader(row: dict, context: dict[str, str], config: ReaderConfig = ReaderConfig()) -> dict:
    import anthropic

    if config.ranker not in ("jev", "bm25"):
        raise ValueError(f"unknown ranker {config.ranker!r}")
    if config.ranker == "bm25" and (config.show_scores or config.reject_below is not None):
        raise ValueError("show_scores and reject_below need Jev's 0–1 scores; BM25 scores are unbounded")
    started = time.perf_counter()
    proxy = JevProxy()
    if config.ranker == "jev":
        scores = proxy.screen(row["question"], context)
    else:
        scores = bm25_scores(row["question"], context)
    shortlist = rank(scores, context)
    rejected = config.reject_below is not None and (not shortlist or scores[shortlist[0]] < config.reject_below)
    response, error, cost_rlm, tokens = "", None, 0.0, {}
    if not rejected:
        prompt = build_prompt(row["question"], shortlist, scores, context, config)
        try:
            # Streaming: the SDK refuses non-streaming requests with a large max_tokens. Sonnet 5 runs
            # adaptive thinking when `thinking` is omitted, and thinking tokens bill as output.
            client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
            with client.messages.stream(
                model=ROOT_MODEL, max_tokens=config.max_output_tokens, messages=[{"role": "user", "content": prompt}]
            ) as stream:
                message = stream.get_final_message()
            response = "".join(block.text for block in message.content if block.type == "text")
            usage = {"input_tokens": message.usage.input_tokens, "output_tokens": message.usage.output_tokens}
            cost_rlm = live.anthropic_cost(ROOT_MODEL, usage) or 0.0
            tokens = {ROOT_MODEL: {**usage, "calls": 1}}
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
    return {
        "id": row["id"],
        "arm": "J" if config.ranker == "jev" else "K",
        "response": response,
        **parse_response(response),
        "shortlist": shortlist,
        "shortlist_scores": [round(scores[docid], 4) for docid in shortlist],
        "gold_in_shortlist": bool(set(shortlist) & set(row["gold_docids"])),
        "jev_rejected": rejected,
        "reader_config": asdict(config),
        "gate": None,
        "jev_decides": 0,
        "jev_screened": proxy.screened,
        "cost_rlm": cost_rlm,
        "cost_jev": proxy.meter.cost_usd,
        "tokens_rlm": tokens,
        "seconds": time.perf_counter() - started,
        "error": error,
    }
