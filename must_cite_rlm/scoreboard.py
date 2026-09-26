from __future__ import annotations

import argparse
import json
import os
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

from must_cite_rlm.arms import ARM_NAMES, BM25_B, BM25_K1, arm_a, arm_b, arm_c
from must_cite_rlm.browsecomp import (
    NEGATIVE_CAP,
    PACK_PATH,
    PROMPT_CHARS,
    REVISION,
    SHARD,
    SHARD_SHA256,
    SOURCE,
    holdout_gold,
    load_pack,
    prompt_text,
    stub_trials,
    text_of_body,
)
from must_cite_rlm.check import cites_ok
from must_cite_rlm.live import (
    TOP_K,
    Meter,
    jev_decode_clause,
    live_status,
    make_id_choose,
    make_text_fanout,
    meter_cost_note,
    skip_note,
)
from must_cite_rlm.tree import Node, ROOT, load_gold, load_nodes
from must_cite_rlm.types import Abstain, Act, Gold, Metrics, NodeId, Review, Trial

DEFAULT_OUT = ROOT / "results" / "phase0_hotpot" / "SCOREBOARD.md"
DEFAULT_LIVE_OUT = ROOT / "results" / "phase0_hotpot" / "SCOREBOARD.live.md"
BCPLUS_OUT = ROOT / "results" / "phase0_pack" / "SCOREBOARD.browsecomp-plus.md"
BCPLUS_LIVE_OUT = ROOT / "results" / "phase0_pack" / "SCOREBOARD.browsecomp-plus.live.md"
CORPUS_LIVE_OUT = ROOT / "results" / "phase0_corpus" / "SCOREBOARD.browsecomp-plus-corpus.live.md"


def is_exact(trial: Trial, gold: Gold) -> bool:
    got = tuple(cite.node_id for cite in trial.cites)
    if gold.decision == "abstain":
        return isinstance(trial.decision, Abstain) and got == ()
    if gold.decision == "review":
        return isinstance(trial.decision, Review) and got == ()
    return isinstance(trial.decision, Act) and set(got) == set(gold.node_ids)


def score_trials(
    golds: Sequence[Gold],
    trials: Sequence[Trial],
    nodes: Mapping[NodeId, Node],
    latency_ms: float,
    cost_usd: float = 0.0,
) -> Metrics:
    n = len(golds)
    if n == 0 or len(trials) != n:
        raise ValueError("golds and trials differ in length")
    exact = sum(is_exact(trial, gold) for trial, gold in zip(trials, golds, strict=True))
    ok = sum(cites_ok(trial, nodes) for trial in trials)
    abstain = sum(isinstance(trial.decision, Abstain) for trial in trials)
    return Metrics(
        exact_id_acc=exact / n,
        cite_ok=ok / n,
        illegal_span_rate=(n - ok) / n,
        abstain_rate=abstain / n,
        cost_usd=cost_usd / n,
        latency_ms=latency_ms / n,
    )


def _label(trial: Trial, nodes: Mapping[NodeId, Node]) -> str:
    if isinstance(trial.decision, Act):
        name = "act:" + "+".join(cite.node_id for cite in trial.cites)
    elif isinstance(trial.decision, Review):
        name = "review"
    else:
        name = "abstain"
    if not cites_ok(trial, nodes):
        return name + " illegal"
    return name


def corpus_note(n_questions: int) -> str:
    return (
        f"The gold file has {n_questions} questions from HotpotQA dev distractor v1 "
        "(Yang et al., EMNLP 2018, https://hotpotqa.github.io/), CC BY-SA 4.0. "
        "Passages are the Wikipedia sentences frozen in that dump. This repo assigns the node ids. "
        "Each question contributes its two supporting articles, not the eight distractor paragraphs. "
        "See fixtures/LICENSE.txt and fixtures/provenance.jsonl."
    )


def verdict(metrics: Mapping[str, Metrics]) -> str:
    b = metrics["B"].exact_id_acc
    c = metrics["C"].exact_id_acc
    if b > c:
        head = f"Stub B exact_id_acc is {b:.3f} and stub C exact_id_acc is {c:.3f}. B is ahead."
    elif c > b:
        head = f"Stub B exact_id_acc is {b:.3f} and stub C exact_id_acc is {c:.3f}. C is ahead."
    else:
        head = f"Stub B and stub C tie at exact_id_acc {b:.3f}."
    return " ".join(
        [
            head,
            "On bridge rows the answer sentence is in one supporting article, and another sentence matches at least as many question tokens, so flat top-1 misses.",
            "Arm B ply 1 takes the answer article, because that article's title and sentences cover more of the question, then ply 2 takes the answer sentence.",
            "Easy rows are won by both arms.",
            "Multi rows cite two supporting sentences. Stub decide returns one winner, so both arms miss.",
            "cost_usd is 0 for both. The gap is accuracy.",
            "Risk-coverage is not in the table.",
            "Stub abstain is zero token overlap. There is no score threshold.",
            "Bridge rows were selected because this stub split holds. This is not a random HotpotQA sample.",
        ]
    )


def render(
    golds: Sequence[Gold],
    runs: Mapping[str, Sequence[Trial]],
    metrics: Mapping[str, Metrics],
    nodes: Mapping[NodeId, Node],
    *,
    mode: str,
    cost_note: str,
    lead: str,
) -> str:
    lines = [
        "# Scoreboard",
        "",
        lead,
        "",
        "`latency_ms` is the mean per question on this run. A later run can change it.",
        cost_note,
        "",
        "| arm | exact_id_acc | cite_ok | illegal_span_rate | abstain_rate | cost_usd | latency_ms |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name in ARM_NAMES:
        row = metrics[name]
        lines.append(
            "| {arm} | {exact:.3f} | {ok:.3f} | {illegal:.3f} | {abstain:.3f} | {cost:.6f} | {latency:.1f} |".format(
                arm=name,
                exact=row.exact_id_acc,
                ok=row.cite_ok,
                illegal=row.illegal_span_rate,
                abstain=row.abstain_rate,
                cost=row.cost_usd,
                latency=row.latency_ms,
            )
        )
    lines.extend(["", lead_claim(mode, metrics), ""])
    if mode == "stub":
        notes = [
            corpus_note(len(golds)),
            "Stub arm A fans out over section text and returns a 40-character quote. That quote is not `Span.text`.",
            "Arm B walks node ids at depth 1 and depth 2. `decide` returns `Act`, `Review`, or `Abstain`. Code copies `Span.text`.",
            "Arm C retrieves one depth-2 node. A score tie uses the lowest id.",
            "On a score tie, arm B returns `Review`. Review is not abstain and not an exact act.",
        ]
    else:
        notes = [
            corpus_note(len(golds)),
            "Arm A sends free-form text per depth-1 section. A quote that is not `Span.text` is an illegal span.",
            "Arm B returns `Act`, `Review`, or `Abstain`. Code copies `Span.text`.",
            "Arm C asks for ids from the top 3 depth-2 nodes. Code copies `Span.text`.",
        ]
    lines.extend(
        [
            *notes,
            "",
            "## Per question",
            "",
            "| id | gold | A | B | C |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for i, gold in enumerate(golds):
        if gold.decision == "act":
            shown = "act:" + "+".join(gold.node_ids)
        else:
            shown = gold.decision
        cells = " | ".join(_label(runs[name][i], nodes) for name in ARM_NAMES)
        lines.append(f"| {gold.id} | {shown} | {cells} |")
    lines.append("")
    return "\n".join(lines)


def lead_claim(mode: str, metrics: Mapping[str, Metrics]) -> str:
    if mode == "stub":
        return verdict(metrics)
    b = metrics["B"]
    c = metrics["C"]
    if b.exact_id_acc > c.exact_id_acc:
        head = (
            f"Live B exact_id_acc is {b.exact_id_acc:.3f} and live C exact_id_acc is {c.exact_id_acc:.3f}. "
            "B is ahead on accuracy."
        )
    elif c.exact_id_acc > b.exact_id_acc:
        head = (
            f"Live B exact_id_acc is {b.exact_id_acc:.3f} and live C exact_id_acc is {c.exact_id_acc:.3f}. "
            "C is ahead on accuracy."
        )
    else:
        head = f"Live B and live C tie at exact_id_acc {b.exact_id_acc:.3f}."
    cheaper = "B" if b.cost_usd < c.cost_usd else "C" if c.cost_usd < b.cost_usd else "neither"
    return (
        f"{head} Mean cost_usd is {b.cost_usd:.6f} for B and {c.cost_usd:.6f} for C, so {cheaper} is cheaper. "
        "Risk-coverage is not in the table. Live abstain uses the decision itself, and this run does not sweep a threshold."
    )


def _score_arm(
    golds: Sequence[Gold],
    trials: Sequence[Trial],
    nodes: Mapping[NodeId, Node],
    started: float,
    meter: Meter | None,
) -> Metrics:
    elapsed_ms = (time.perf_counter() - started) * 1000
    if meter is None:
        return score_trials(golds, trials, nodes, elapsed_ms)
    latency = meter.latency_ms if meter.latency_ms > 0 else elapsed_ms
    return score_trials(golds, trials, nodes, latency, meter.cost_usd)


def run() -> str:
    golds = load_gold()
    nodes = load_nodes()
    runs: dict[str, list[Trial]] = {}
    metrics: dict[str, Metrics] = {}
    for name in ARM_NAMES:
        started = time.perf_counter()
        trials = []
        for gold in golds:
            if name == "A":
                trials.append(arm_a(gold, nodes))
            elif name == "B":
                trials.append(arm_b(gold, nodes))
            else:
                # Hotpot rows were selected so token overlap misses bridge gold.
                trials.append(arm_c(gold, nodes, ranker="overlap"))
        runs[name] = trials
        metrics[name] = _score_arm(golds, trials, nodes, started, None)
    return render(
        golds,
        runs,
        metrics,
        nodes,
        mode="stub",
        cost_note="`cost_usd` is 0 because no provider returned a price.",
        lead="Mode `stub`. Arm A is a depth-1 text fan-out. Arm B and arm C did not call a provider.",
    )


def run_live() -> str:
    decode_clause = jev_decode_clause()
    golds = load_gold()
    nodes = load_nodes()
    runs: dict[str, list[Trial]] = {}
    metrics: dict[str, Metrics] = {}
    meters: dict[str, Meter] = {}
    for name in ARM_NAMES:
        meter = Meter()
        meters[name] = meter
        started = time.perf_counter()
        trials = []
        if name == "A":
            fanout = make_text_fanout(meter)
            trials = [arm_a(gold, nodes, fanout=fanout) for gold in golds]
        else:
            for gold in golds:
                trace: dict[str, str] = {}
                choose = make_id_choose(gold.text, nodes, meter, trace)
                if name == "B":
                    trials.append(arm_b(gold, nodes, decide=choose, trace=trace))
                else:
                    trials.append(arm_c(gold, nodes, choose=choose, k=TOP_K, trace=trace, ranker="overlap"))
        runs[name] = trials
        metrics[name] = _score_arm(golds, trials, nodes, started, meter)
    unknown = [name for name, meter in meters.items() if not meter.cost_known]
    return render(
        golds,
        runs,
        metrics,
        nodes,
        mode="live",
        cost_note=meter_cost_note(unknown),
        lead=(
            "Mode `live`. Arm A fans out one chat completion per depth-1 section. "
            "Arm B calls typed id decide. Arm C retrieves the top 3 depth-2 nodes and asks for id cites."
            + decode_clause
        ),
    )


def browsecomp_skip_note() -> str:
    return "\n".join(
        [
            "# Scoreboard live",
            "",
            "Live BrowseComp-Plus run skipped. This process has no `TYPESAFE_API_KEY`, "
            "no `OPENAI_API_KEY`, and no `ANTHROPIC_API_KEY`.",
            "",
            "Set `TYPESAFE_API_KEY` to run arm C through Jev. `MUST_CITE_JEV_DECODE` defaults to `both`.",
            "If `TYPESAFE_API_KEY` is unset, `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` runs arm C through the chat decide.",
            "Arms A and B are not run on this suite.",
            "",
            "The stub table is `results/phase0_pack/SCOREBOARD.browsecomp-plus.md`. "
            "`./scripts/run_scoreboard.sh --suite browsecomp-plus` does not call a provider.",
            "",
        ]
    )


def _browsecomp_notes(n_questions: int, mode: str) -> list[str]:
    pack = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    used = ", ".join(item["name"] for item in pack["shards"])
    pool = pack.get("eligible_pool")
    pool_clause = f" Eligible pool {pool}." if isinstance(pool, int) else ""
    notes = [
        (
            f"The pack has {n_questions} BrowseComp-Plus queries from {SOURCE} revision {REVISION}. "
            f"Pinned shard `{SHARD}` sha256 {SHARD_SHA256}. "
            f"Shards in the draw: {used}.{pool_clause} "
            "See fixtures/browsecomp_plus/LICENSE.txt and fixtures/browsecomp_plus/PACK.json."
        ),
        (
            "exact_id is set equality on the gold docids. "
            "Evidence docids are the documents labeled as needed to answer. "
            f"The flat pool adds the first {NEGATIVE_CAP} usable negative docids in release order."
        ),
        (
            "Arm C ranks that pool with Okapi BM25 "
            f"(k1={BM25_K1}, b={BM25_B}) on the full document text and calls decide on the top "
            f"{TOP_K} ids. IDF and average length are taken inside that pool. "
            "Code copies the indexed span. "
            "The span is a verbatim slice of the document with no double quote."
        ),
        "Answer accuracy is not in this table.",
        "Arms A and B are not run. Arm B remains the tree walk for a later recurse cut. This pack does not build that walk.",
    ]
    if mode == "live":
        notes.append(
            f"Live prompts send at most {PROMPT_CHARS} characters from the start of each top-k document."
        )
    else:
        notes.append(
            "Stub decide returns Act on a unique best overlap among those ids, Review on a tie, and Abstain when every overlap is 0."
        )
    return notes


def render_browsecomp(
    golds: Sequence[Gold],
    trials: Sequence[Trial],
    metrics: Mapping[str, Metrics],
    nodes: Mapping[NodeId, Node],
    *,
    mode: str,
    cost_note: str,
    lead: str,
) -> str:
    row = metrics["C"]
    if mode == "stub":
        claim = (
            f"Stub C exact_id_acc is {row.exact_id_acc:.3f} and cite_ok is {row.cite_ok:.3f}. "
            "exact_id is set equality with the gold docids. cost_usd is 0."
        )
    else:
        claim = (
            f"Live C exact_id_acc is {row.exact_id_acc:.3f} and cite_ok is {row.cite_ok:.3f}. "
            f"Mean cost_usd is {row.cost_usd:.6f}. exact_id is set equality with the gold docids."
        )
    lines = [
        "# Scoreboard",
        "",
        lead,
        "",
        "`latency_ms` is the mean per question on this run. A later run can change it.",
        cost_note,
        "",
        "| arm | exact_id_acc | cite_ok | illegal_span_rate | abstain_rate | cost_usd | latency_ms |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        "| C | {exact:.3f} | {ok:.3f} | {illegal:.3f} | {abstain:.3f} | {cost:.6f} | {latency:.1f} |".format(
            exact=row.exact_id_acc,
            ok=row.cite_ok,
            illegal=row.illegal_span_rate,
            abstain=row.abstain_rate,
            cost=row.cost_usd,
            latency=row.latency_ms,
        ),
        "",
        claim,
        "",
        *_browsecomp_notes(len(golds), mode),
        "",
        "## Per question",
        "",
        "| id | gold | C |",
        "| --- | --- | --- |",
    ]
    for gold, trial in zip(golds, trials, strict=True):
        if gold.decision == "act":
            shown = "act:" + "+".join(gold.node_ids)
        else:
            shown = gold.decision
        lines.append(f"| {gold.id} | {shown} | {_label(trial, nodes)} |")
    lines.append("")
    return "\n".join(lines)


def run_browsecomp() -> str:
    pools, nodes = load_pack()
    golds = tuple(pool.gold for pool in pools)
    started = time.perf_counter()
    trials = stub_trials(pools, TOP_K)
    metrics = {"C": _score_arm(golds, trials, nodes, started, None)}
    return render_browsecomp(
        golds,
        trials,
        metrics,
        nodes,
        mode="stub",
        cost_note="`cost_usd` is 0 because no provider returned a price.",
        lead=(
            "Mode `stub`. Suite `browsecomp-plus`. "
            "Arm C flat-retrieves over the per-question pool and calls stub decide. "
            "No provider was called."
        ),
    )


def _trace_row(
    gold: Gold, candidates: tuple[NodeId, ...], trial: Trial, raw: str, nodes: Mapping[NodeId, Node]
) -> dict:
    try:
        payload: object = json.loads(raw)
    except json.JSONDecodeError:
        payload = raw
    return {
        "id": gold.id,
        "gold": list(gold.node_ids),
        "candidates": list(candidates),
        "decision": _label(trial, nodes),
        "raw": payload,
    }


def run_browsecomp_live(
    trace_out: Path | None = None, holdout: bool = False, decider: str | None = None, k: int = TOP_K
) -> str:
    if decider is None:
        decider = "jev" if os.environ.get("TYPESAFE_API_KEY") else "chat"
    pools, nodes = load_pack()
    if holdout:
        pools = tuple(holdout_gold(pool) for pool in pools)
    golds = tuple(pool.gold for pool in pools)
    meter = Meter()
    started = time.perf_counter()
    trials = []
    rows = []
    for pool in pools:
        trace: dict[str, str] = {}
        seen: list[tuple[NodeId, ...]] = []
        decide = make_id_choose(
            pool.gold.text,
            pool.nodes,
            meter,
            trace,
            prompt_text=prompt_text(pool.body),
            decider=decider,
        )

        def choose(candidates, decide=decide, seen=seen):
            seen.append(tuple(candidates.node_ids))
            return decide(candidates)

        trial = arm_c(
            pool.gold,
            pool.nodes,
            choose=choose,
            k=k or len(pool.nodes),
            trace=trace,
            text_of=text_of_body(pool.body),
        )
        trials.append(trial)
        rows.append(_trace_row(pool.gold, seen[0] if seen else (), trial, trace.get("raw", ""), nodes))
    if trace_out is not None:
        trace_out.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    metrics = {"C": _score_arm(golds, trials, nodes, started, meter)}
    if decider == "jev":
        decode_line = jev_decode_clause().strip()
        cost_note = (
            "`cost_usd` is the mean per question. "
            "Jev uses 0.042 dollars per million input tokens."
        )
    else:
        decode_line = (
            "Arm C uses the scored chat decide: a route with p(act) and one support probability per id, "
            "decoded like Jev `both`."
        )
        cost_note = meter_cost_note([] if meter.cost_known else ["C"])
    return render_browsecomp(
        golds,
        trials,
        metrics,
        nodes,
        mode="live",
        cost_note=cost_note,
        lead=(
            "Mode `live`. Suite `browsecomp-plus`. "
            + (
                f"Arm C calls typed decide on the top {k} documents. "
                if k
                else "Arm C calls typed decide on every pool document with a nonzero BM25 score. "
            )
            + decode_line
            + (
                " Gold held out: each pool drops its gold docids, so gold is abstain and exact_id counts Abstain only."
                if holdout
                else ""
            )
        ),
    )


def run_corpus_live(
    arm: str, trace_out: Path | None = None, holdout: bool = False, from_trace: Path | None = None
) -> str:
    from concurrent.futures import ThreadPoolExecutor

    from must_cite_rlm.recurse import (
        BATCH,
        DECIDE_CHUNKS,
        DECIDE_DOCS,
        KEEP,
        MAX_CHUNKS,
        PER_QUERY,
        QUERIES,
        ROUNDS,
        flat,
        hybrid,
        load_corpus_pools,
        narrow,
        pools_from_trace,
        recurse,
    )

    if arm == "narrow":
        pools = pools_from_trace(from_trace, holdout=holdout)

        def step(pool, meter, trace):
            return (*narrow(pool.gold, pool.ranked, pool.body, pool.nodes, meter, trace), pool.nodes)

    else:
        pools = load_corpus_pools(holdout=holdout)
        step = {"recurse": recurse, "flat": flat, "hybrid": hybrid}[arm]

    def one(pool):
        meter = Meter()
        trace: dict[str, str] = {}
        trial, final, detail, nodes = step(pool, meter, trace)
        row = _trace_row(pool.gold, final, trial, trace.get("raw", ""), nodes)
        row["detail"] = detail
        return trial, row, meter, nodes

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=8) as workers:
        results = list(workers.map(one, pools))
    trials = [trial for trial, _, _, _ in results]
    meter = Meter()
    for _, _, part, _ in results:
        meter.add(part.cost_usd, part.latency_ms)
    if trace_out is not None:
        trace_out.write_text("".join(json.dumps(row) + "\n" for _, row, _, _ in results), encoding="utf-8")
    nodes = {node_id: node for _, _, _, step_nodes in results for node_id, node in step_nodes.items()}
    golds = tuple(pool.gold for pool in pools)
    metrics = {"C": _score_arm(golds, trials, nodes, started, meter)}
    if arm == "narrow":
        shape = (
            f"Arm N replays the final candidates of `{from_trace.name}`: the top {DECIDE_DOCS} by that run's decide Noul "
            f"are re-expanded and one more `both` decide sees each as its best {DECIDE_CHUNKS} chunks."
        )
    elif arm == "hybrid":
        shape = (
            f"Arm H is arm R plus search: {ROUNDS} rounds in which Claude reads snippets of the best screened docs "
            f"and writes up to {QUERIES} keyword queries, each adding its top {PER_QUERY} unseen docs to the Jev screen. "
            "Claude writes queries only; every select and decide call is Jev."
        )
    elif arm == "recurse":
        shape = (
            f"Arm R recurses over the corpus BM25 top 100: Jev Noul screens each doc's first {PROMPT_CHARS} chars "
            f"({BATCH} ids per call), the best {KEEP} docs are cut into {PROMPT_CHARS}-char chunks (at most {MAX_CHUNKS}), "
            f"and one `both` decide runs over those {KEEP} docs shown as their best chunk."
        )
    else:
        shape = f"Flat baseline: one `both` decide over the corpus BM25 top {KEEP}, first {PROMPT_CHARS} chars each."
    return render_browsecomp(
        golds,
        trials,
        metrics,
        nodes,
        mode="live",
        cost_note="`cost_usd` is the mean per question. Jev uses 0.042 dollars per million input tokens.",
        lead=(
            "Mode `live`. Suite `browsecomp-plus-corpus`. The table's C row is this arm. "
            + shape
            + jev_decode_clause()
            + (" Gold held out: gold docids are dropped from the top 100, so gold is abstain." if holdout else "")
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the A/B/C must-cite scoreboard.")
    parser.add_argument(
        "--suite",
        choices=("hotpot", "browsecomp-plus", "browsecomp-plus-corpus"),
        default="hotpot",
        help="hotpot is the cite yardstick. browsecomp-plus runs arm C on the smoke pack.",
    )
    parser.add_argument("--out", type=str, default=None)
    parser.add_argument("--live", action="store_true", help="Call providers and write the live scoreboard.")
    parser.add_argument("--live-out", type=str, default=None)
    parser.add_argument(
        "--holdout-gold",
        action="store_true",
        help="browsecomp-plus live only. Drop each pool's gold docids so the right call is not to act.",
    )
    parser.add_argument(
        "--decider",
        choices=("jev", "chat"),
        default=None,
        help="browsecomp-plus live only. Default is jev when TYPESAFE_API_KEY is set, otherwise chat.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=TOP_K,
        help="browsecomp-plus live only. Candidates per decide call. 0 is the whole pool.",
    )
    parser.add_argument(
        "--arm",
        choices=("recurse", "flat", "hybrid", "narrow"),
        default="recurse",
        help="browsecomp-plus-corpus live only. recurse is arm R, hybrid is arm H, flat is one decide over the BM25 top 8, "
        "narrow replays --from-trace.",
    )
    parser.add_argument("--from-trace", type=Path, default=None, help="Trace whose final candidates --arm narrow replays.")
    args = parser.parse_args(argv)
    if args.top_k < 0:
        parser.error("--top-k must be 0 or more")
    bcplus = args.suite == "browsecomp-plus"
    if args.suite == "browsecomp-plus-corpus":
        if not args.live or not os.environ.get("TYPESAFE_API_KEY"):
            parser.error("browsecomp-plus-corpus is live only and needs TYPESAFE_API_KEY")
        if args.arm == "narrow" and args.from_trace is None:
            parser.error("--arm narrow needs --from-trace")
        if args.arm == "hybrid" and not os.environ.get("ANTHROPIC_API_KEY"):
            parser.error("--arm hybrid needs ANTHROPIC_API_KEY for query rewrites")
        out = Path(args.live_out) if args.live_out else CORPUS_LIVE_OUT
        out.write_text(
            run_corpus_live(
                args.arm, trace_out=out.with_suffix(".trace.jsonl"), holdout=args.holdout_gold, from_trace=args.from_trace
            ),
            encoding="utf-8",
        )
        print(out)
        return 0
    if args.live:
        status = live_status()
        out = Path(args.live_out) if args.live_out else (BCPLUS_LIVE_OUT if bcplus else DEFAULT_LIVE_OUT)
        out.parent.mkdir(parents=True, exist_ok=True)
        if bcplus:
            if status == "missing":
                out.write_text(browsecomp_skip_note(), encoding="utf-8")
                print(out)
                return 0
            text = run_browsecomp_live(trace_out=out.with_suffix(".trace.jsonl"), holdout=args.holdout_gold, decider=args.decider, k=args.top_k)
        else:
            if status not in ("openai", "anthropic"):
                out.write_text(skip_note(status), encoding="utf-8")
                print(out)
                return 0
            text = run_live()
        out.write_text(text, encoding="utf-8")
        print(out)
        return 0
    text = run_browsecomp() if bcplus else run()
    out = Path(args.out) if args.out else (BCPLUS_OUT if bcplus else DEFAULT_OUT)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
