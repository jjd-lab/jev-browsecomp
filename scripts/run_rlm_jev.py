#!/usr/bin/env python3
"""Run an arm on BrowseComp-Plus (1K documents): RLM arm A (llm_query only), B or B2
(+ Jev tools), J (Jev-first reader: Jev screen, then one Sonnet call, no RLM), or
K (the same reader with BM25 ranking in place of Jev).

Each RLM question runs in its own Docker REPL; arm J needs no Docker. Results append to
results/phase1_rlm/<arm>.jsonl one line per question, so a rerun skips finished ids.
Stops starting questions once the arm's spend passes --budget dollars; questions
already running finish, so spend can pass the cap by up to --workers questions.
Needs Docker, ANTHROPIC_API_KEY, TYPESAFE_API_KEY (arm B), the FTS index, and
fixtures/browsecomp_plus_1k/queries.jsonl.

    python3 scripts/run_rlm_jev.py --arm B --n 20 --budget 15
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from must_cite_rlm.live import Meter  # noqa: E402
from must_cite_rlm.reader import MAX_OUTPUT_TOKENS, ReaderConfig, run_reader  # noqa: E402
from must_cite_rlm.rlm_jev import MAX_TOKENS_PER_QUESTION, judge, run_question  # noqa: E402
from must_cite_rlm.search import Search  # noqa: E402

PACK = ROOT / "fixtures" / "browsecomp_plus_1k"
OUT_DIR = ROOT / "results" / "phase1_rlm"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--arm", choices=("A", "B", "B2", "J", "K"), required=True)
    parser.add_argument("--n", type=int, default=150)
    parser.add_argument("--budget", type=float, required=True, help="Dollar cap for this arm, finished questions included.")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--holdout", action="store_true", help="Run the held-out set (gold and evidence removed).")
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS_PER_QUESTION, help="Per-question RLM token limit.")
    parser.add_argument("--tag", default=None, help="Suffix for the output file, e.g. capfix -> A.capfix.jsonl.")
    parser.add_argument("--show-jev-scores", action="store_true", help="Arm J: show Jev screen scores to Sonnet.")
    parser.add_argument("--jev-reject-below", type=float, default=None, help="Arm J: abstain without Sonnet when Jev's best score is below this.")
    parser.add_argument("--reader-max-output", type=int, default=MAX_OUTPUT_TOKENS, help="Arm J: Sonnet output-token cap (thinking included).")
    parser.add_argument("--ids", default=None, help="Comma-separated question ids to run; --n is ignored when set.")
    args = parser.parse_args(argv)
    reader_config = ReaderConfig("jev", args.show_jev_scores, args.jev_reject_below, args.reader_max_output)
    if args.arm not in ("J", "K") and reader_config != ReaderConfig():
        parser.error("--show-jev-scores, --jev-reject-below, and --reader-max-output apply to reader arms (J, K) only")
    if args.arm == "K":
        if args.show_jev_scores or args.jev_reject_below is not None:
            parser.error("--show-jev-scores and --jev-reject-below need Jev scores; arm K ranks with BM25")
        reader_config = ReaderConfig("bm25", max_output_tokens=args.reader_max_output)

    source = PACK / ("holdout.jsonl" if args.holdout else "queries.jsonl")
    rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
    if args.ids:
        wanted = set(args.ids.split(","))
        rows = [row for row in rows if row["id"] in wanted]
    else:
        rows = rows[: args.n]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{args.arm}{'.holdout' if args.holdout else ''}{'.' + args.tag if args.tag else ''}.jsonl"
    done = {}
    if out.exists():
        done = {r["id"]: r for r in map(json.loads, out.read_text(encoding="utf-8").splitlines())}
    spent = sum((r["cost_rlm"] or 0) + r["cost_jev"] + r["cost_judge"] for r in done.values())
    lock = threading.Lock()
    search = Search()

    def one(row: dict) -> None:
        nonlocal spent
        with lock:
            if spent >= args.budget:
                return
        context = {docid: search.text(docid) for docid in row["docids"]}
        if args.arm in ("J", "K"):
            result = run_reader(row, context, reader_config)
        else:
            result = run_question(row, context, args.arm, args.max_tokens)
        meter = Meter()
        verdict = None
        if result["response"]:
            try:
                verdict = judge(row["question"], result["response"], row["answer"], meter)
            except Exception as exc:
                result["error"] = (result["error"] or "") + f" judge: {type(exc).__name__}: {exc}"
        result.update(
            {
                "answer": row["answer"],
                "correct": bool(verdict and verdict["correct"]),
                "judge_parsed": bool(verdict and verdict["parsed"]),
                "judge_model": verdict["model"] if verdict else None,
                "judge_raw": verdict["raw"] if verdict else None,
                "cost_judge": meter.cost_usd,
                "gold_cited": bool(set(result["cited"]) & set(row["gold_docids"])),
                "evidence_cited": len(set(result["cited"]) & set(row["evidence_docids"])),
            }
        )
        with lock:
            spent += (result["cost_rlm"] or 0) + result["cost_jev"] + result["cost_judge"]
            with out.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(result) + "\n")
            print(
                f"{row['id']} correct={result['correct']} gold_cited={result['gold_cited']} "
                f"${(result['cost_rlm'] or 0) + result['cost_jev']:.3f} {result['seconds']:.0f}s spent=${spent:.2f}"
                + (f" error={result['error'][:80]}" if result["error"] else ""),
                flush=True,
            )

    todo = [row for row in rows if row["id"] not in done]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(one, todo))
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
