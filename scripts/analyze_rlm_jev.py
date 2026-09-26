#!/usr/bin/env python3
"""Phase 1 analysis: does the Jev gate beat the model's own confidence, and how do the arms compare?

Fixed before the full run (Phase 1, see results/findings/phase1_rlm.md):

- Scorers, on the same answers: `jev` = post-hoc gate p(act) (`gate_post`), and
  `self` = the answer's stated confidence (missing counts as 100%, the
  BrowseComp-Plus judge convention). A row with no exact answer is an abstention
  and scores 0 under both.
- Primary: arm A answers, since arm A never saw Jev. Co-primary: arm A answers
  plus arm A on the held-out set (gold and evidence removed), where a gate
  matters most. No document supports a held-out answer, so every held-out row
  counts as one that should not be acted on, even if the judge marks it correct
  (for example, answered from the model's own memory). Metric: AURC (area under the
  risk-coverage curve, lower is better; ties count at their expected value).
  Δ = AURC(jev) − AURC(self), 95% CI from 10,000 paired bootstrap resamples over
  questions, seed 20260925.
- Verdict: "Jev gate wins" if the whole CI is below 0, "self-confidence wins" if
  the whole CI is above 0, otherwise "no clear difference".
- Secondary: the same on arm B and on A+B pooled; AUROC; selective accuracy at
  coverage 0.8; held-out act rate at score ≥ 0.5 when a *.holdout.jsonl exists;
  arm A vs B accuracy (exact McNemar).
- Arm B vs A (does Jev in the loop help?), paired over questions both arms
  finished: B − A in accuracy, $/question (RLM + Jev), and wall seconds/question,
  each with a 95% paired bootstrap CI. Per endpoint: "B better" / "B worse" if the
  whole CI is on one side of 0, else "no clear difference". Accuracy also gets
  the exact McNemar p.
- Arm J vs A (the Jev-first reader, rules set after the 38-question probe):
  the same paired table, and the same table on only the questions not in the
  probe (`J.probe_ids.txt`).
- Held-out answers per arm: how many are answered, median stated confidence,
  median Jev p(act), and how many clear 0.5 on each score.
- Label audit: questions where both arms gave the same normalized answer but
  the judge labelled them differently are listed for manual review.
"""

from __future__ import annotations

import json
import math
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "results" / "phase1_rlm"
SEED = 20260925
RESAMPLES = 10_000


def jev(row: dict) -> float:
    return row["gate_post"]["p_act"]


def self_conf(row: dict) -> float:
    if row["exact_answer"] is None:
        return 0.0
    return 1.0 if row["confidence"] is None else row["confidence"]


def _norm(answer: str | None) -> str:
    return " ".join((answer or "").lower().split())


def aurc(scores: list[float], wrong: list[bool]) -> float:
    """Mean risk over coverages 1/n..n/n, with tied scores in expected (random) order."""
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    total, seen, errors, i = 0.0, 0, 0.0, 0
    while i < len(order):
        j = i
        while j < len(order) and scores[order[j]] == scores[order[i]]:
            j += 1
        group = order[i:j]
        rate = sum(wrong[g] for g in group) / len(group)
        for step in range(1, len(group) + 1):
            total += (errors + step * rate) / (seen + step)
        seen += len(group)
        errors += rate * len(group)
        i = j
    return total / len(order)


def auroc(scores: list[float], wrong: list[bool]) -> float | None:
    right = [s for s, w in zip(scores, wrong) if not w]
    bad = [s for s, w in zip(scores, wrong) if w]
    if not right or not bad:
        return None
    wins = sum((r > b) + 0.5 * (r == b) for r in right for b in bad)
    return wins / (len(right) * len(bad))


def selective_accuracy(scores: list[float], wrong: list[bool], coverage: float) -> float:
    k = max(1, round(coverage * len(scores)))
    return 1 - _topk_error(scores, wrong, k)


def _topk_error(scores: list[float], wrong: list[bool], k: int) -> float:
    """Expected error rate among the top k, ties in random order."""
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    taken, errors, i = 0, 0.0, 0
    while i < len(order) and taken < k:
        j = i
        while j < len(order) and scores[order[j]] == scores[order[i]]:
            j += 1
        group = order[i:j]
        use = min(len(group), k - taken)
        errors += use * sum(wrong[g] for g in group) / len(group)
        taken += use
        i = j
    return errors / k


def compare(rows: list[dict]) -> dict:
    wrong = [not r["correct"] for r in rows]
    a, b = [jev(r) for r in rows], [self_conf(r) for r in rows]
    delta = aurc(a, wrong) - aurc(b, wrong)
    rng = random.Random(SEED)
    deltas = []
    for _ in range(RESAMPLES):
        idx = [rng.randrange(len(rows)) for _ in rows]
        w = [wrong[i] for i in idx]
        deltas.append(aurc([a[i] for i in idx], w) - aurc([b[i] for i in idx], w))
    deltas.sort()
    low, high = deltas[int(0.025 * RESAMPLES)], deltas[int(0.975 * RESAMPLES) - 1]
    verdict = "Jev gate wins" if high < 0 else "self-confidence wins" if low > 0 else "no clear difference"
    return {
        "n": len(rows),
        "errors": sum(wrong),
        "aurc_jev": aurc(a, wrong),
        "aurc_self": aurc(b, wrong),
        "delta": delta,
        "ci": (low, high),
        "verdict": verdict,
        "auroc_jev": auroc(a, wrong),
        "auroc_self": auroc(b, wrong),
        "sel80_jev": selective_accuracy(a, wrong, 0.8),
        "sel80_self": selective_accuracy(b, wrong, 0.8),
    }


def paired_diff(values_b: list[float], values_a: list[float]) -> tuple[float, float, float]:
    diffs = [b - a for b, a in zip(values_b, values_a)]
    rng = random.Random(SEED)
    means = sorted(
        sum(diffs[rng.randrange(len(diffs))] for _ in diffs) / len(diffs) for _ in range(RESAMPLES)
    )
    return sum(diffs) / len(diffs), means[int(0.025 * RESAMPLES)], means[int(0.975 * RESAMPLES) - 1]


def _cost(row: dict) -> float:
    return (row["cost_rlm"] or 0) + row["cost_jev"]


def _turns(row: dict) -> int:
    return (row.get("tokens_rlm") or {}).get("claude-sonnet-5", {}).get("calls", 0)


def overview(arms: dict[str, dict[str, dict]]) -> list[str]:
    """One row per arm: accuracy, answers, limits hit, and cost split by caller."""
    lines = [
        "## Overview",
        "",
        "| arm | n | accuracy | gold cited | no answer | token stops | $/q RLM | $/q Jev | $/q total | s/q | median turns |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for arm, by_id in arms.items():
        rows = list(by_id.values())
        if not rows:
            continue
        n = len(rows)
        rlm = sum(r["cost_rlm"] or 0 for r in rows) / n
        jev_cost = sum(r["cost_jev"] for r in rows) / n
        turns = sorted(_turns(r) for r in rows)
        lines.append(
            f"| {arm} | {n} | {sum(r['correct'] for r in rows) / n:.3f} | {sum(r['gold_cited'] for r in rows) / n:.3f} "
            f"| {sum(not r['exact_answer'] for r in rows)} | {sum('TokenLimit' in (r['error'] or '') for r in rows)} "
            f"| {rlm:.4f} | {jev_cost:.4f} | {rlm + jev_cost:.4f} | {sum(r['seconds'] for r in rows) / n:.0f} "
            f"| {turns[n // 2]} |"
        )
    return lines + [""]


# An exact answer that only says the documents don't settle it. Reported separately; scoring is unchanged.
DECLINED = re.compile(r"cannot be determined|unable to (?:conclusively )?determine|not (?:found|determinable)|insufficient", re.I)


def paired_block(
    arm: str,
    base: dict[str, dict],
    other: dict[str, dict],
    ids: list[str],
    label: str | None = None,
) -> list[str]:
    """Paired arm − A table over `ids`; verdict needs the whole 95% CI on one side of 0."""
    a_rows, x_rows = [base[i] for i in ids], [other[i] for i in ids]
    lines = [
        "",
        f"## Arm {arm} vs A, paired (n={len(ids)}{', ' + label if label else ''})",
        "",
        f"| endpoint | A | {arm} | {arm} − A | 95% CI | verdict |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ]
    for name, get, better in (
        ("accuracy", lambda r: float(r["correct"]), "higher"),
        ("$/question", _cost, "lower"),
        ("seconds/question", lambda r: r["seconds"], "lower"),
    ):
        va, vx = [get(r) for r in a_rows], [get(r) for r in x_rows]
        mean, low, high = paired_diff(vx, va)
        good, bad = (low > 0, high < 0) if better == "higher" else (high < 0, low > 0)
        verdict = f"{arm} better" if good else f"{arm} worse" if bad else "no clear difference"
        lines.append(
            f"| {name} | {sum(va) / len(va):.3f} | {sum(vx) / len(vx):.3f} | {mean:+.3f} | [{low:+.3f}, {high:+.3f}] | {verdict} |"
        )
    jev_cost = sum(r["cost_jev"] for r in x_rows) / len(x_rows)
    lines += ["", f"Mean Jev $/question in {arm}: {jev_cost:.4f}; items screened/question: {sum(r['jev_screened'] for r in x_rows) / len(x_rows):.0f}.", ""]
    return lines


def mcnemar(a_rows: dict, b_rows: dict) -> tuple[int, int, float]:
    ids = set(a_rows) & set(b_rows)
    only_a = sum(a_rows[i]["correct"] and not b_rows[i]["correct"] for i in ids)
    only_b = sum(b_rows[i]["correct"] and not a_rows[i]["correct"] for i in ids)
    n = only_a + only_b
    tail = sum(math.comb(n, k) for k in range(0, min(only_a, only_b) + 1)) / 2**n if n else 1.0
    return only_a, only_b, min(1.0, 2 * tail)


def _load(name: str) -> dict[str, dict]:
    path = DIR / name
    if not path.exists():
        return {}
    return {r["id"]: r for r in map(json.loads, path.read_text(encoding="utf-8").splitlines())}


def _fmt(x: float | None) -> str:
    return "—" if x is None else f"{x:.3f}"


def main(argv: list[str]) -> int:
    """`--patch TAG` swaps in {arm}.TAG.jsonl rows (reruns) by id and writes ANALYSIS.TAG.md."""
    tag = argv[argv.index("--patch") + 1] if "--patch" in argv else None
    arms = {
        "A": _load("A.jsonl"),
        "B": _load("B.jsonl"),
        "J": _load("J.jsonl"),
        "A.holdout": _load("A.holdout.jsonl"),
        "J.holdout": _load("J.holdout.jsonl"),
    }
    if tag:
        for arm in ("A", "B"):
            arms[arm].update(_load(f"{arm}.{tag}.jsonl"))
    for arm, rows in arms.items():
        missing = [i for i, r in rows.items() if "gate_post" not in r]
        if missing:
            raise SystemExit(f"{arm}: {len(missing)} rows lack gate_post; run scripts/gate_rlm_jev.py first")
    sets = {"A (primary)": list(arms["A"].values()), "B": list(arms["B"].values())}
    sets["A + held-out (co-primary)"] = sets["A (primary)"] + [
        {**r, "id": f"h{r['id']}", "correct": False} for r in arms["A.holdout"].values()
    ]
    sets["A+B"] = sets["A (primary)"] + sets["B"]
    lines = [
        "# Phase 1 analysis",
        "",
        *overview(arms),
        "## Jev gate vs self-confidence",
        "",
        "Same answers, two scorers: `jev` = post-hoc gate p(act), `self` = stated confidence. "
        "AURC is lower-better. Δ = AURC(jev) − AURC(self), 95% paired bootstrap CI.",
        "",
        "| set | n | errors | AURC jev | AURC self | Δ | 95% CI | verdict | AUROC jev | AUROC self | acc@cov0.8 jev | acc@cov0.8 self |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for name, rows in sets.items():
        if not rows:
            continue
        c = compare(rows)
        lines.append(
            f"| {name} | {c['n']} | {c['errors']} | {c['aurc_jev']:.3f} | {c['aurc_self']:.3f} | {c['delta']:+.3f} "
            f"| [{c['ci'][0]:+.3f}, {c['ci'][1]:+.3f}] | {c['verdict']} | {_fmt(c['auroc_jev'])} | {_fmt(c['auroc_self'])} "
            f"| {c['sel80_jev']:.3f} | {c['sel80_self']:.3f} |"
        )
    if arms["A"] and arms["B"]:
        flips = sorted(
            (i for i in set(arms["A"]) & set(arms["B"])
             if arms["A"][i]["exact_answer"] and _norm(arms["A"][i]["exact_answer"]) == _norm(arms["B"][i]["exact_answer"])
             and arms["A"][i]["correct"] != arms["B"][i]["correct"]),
            key=int,
        )
        lines += ["", f"Label audit: same answer, different judge label on {len(flips)} question(s)" + (f": {', '.join(flips)}." if flips else ".")]
        only_a, only_b, p = mcnemar(arms["A"], arms["B"])
        lines += paired_block("B", arms["A"], arms["B"], sorted(set(arms["A"]) & set(arms["B"]), key=int))
        lines += [
            f"Accuracy discordant pairs: A-only correct {only_a}, B-only correct {only_b}, exact McNemar p = {p:.3f}.",
        ]
    if arms["A"] and arms.get("J"):
        ids = sorted(set(arms["A"]) & set(arms["J"]), key=int)
        probe = set((DIR / "J.probe_ids.txt").read_text(encoding="utf-8").strip().split(",")) if (DIR / "J.probe_ids.txt").exists() else set()
        only_a, only_j, p = mcnemar({i: arms["A"][i] for i in ids}, {i: arms["J"][i] for i in ids})
        lines += paired_block("J", arms["A"], arms["J"], ids)
        lines += [f"Accuracy discordant pairs: A-only correct {only_a}, J-only correct {only_j}, exact McNemar p = {p:.3f}.", ""]
        fresh = [i for i in ids if i not in probe]
        if probe and fresh:
            lines += paired_block("J", arms["A"], arms["J"], fresh, label="fresh questions only (not in the 38-question probe)")
    held = {name: list(arms.get(name, {}).values()) for name in ("A.holdout", "J.holdout")}
    if any(held.values()):
        lines += ["", "## Held-out answers (no supporting document)", "", "| arm | n | no answer | declined in words | gave an answer | median stated confidence | median Jev p(act) | answers with self ≥ 0.5 | answers with Jev ≥ 0.5 |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for name, rows in held.items():
            if not rows:
                continue
            declined = [r for r in rows if r["exact_answer"] and DECLINED.search(r["exact_answer"])]
            answered = [r for r in rows if r["exact_answer"] and r not in declined]
            conf = sorted(self_conf(r) for r in answered) or [0.0]
            gate = sorted(jev(r) for r in answered) or [0.0]
            lines.append(
                f"| {name} | {len(rows)} | {sum(not r['exact_answer'] for r in rows)} | {len(declined)} | {len(answered)} "
                f"| {conf[len(conf) // 2]:.2f} | {gate[len(gate) // 2]:.2f} "
                f"| {sum(self_conf(r) >= 0.5 for r in answered)} | {sum(jev(r) >= 0.5 for r in answered)} |"
            )
    lines.append("")
    if tag:
        lines.insert(1, f"\nRows from `A.{tag}.jsonl` / `B.{tag}.jsonl` replace the original rows for those question ids.")
    (DIR / (f"ANALYSIS.{tag}.md" if tag else "ANALYSIS.md")).write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
