"""Risk-coverage from a live BrowseComp-Plus Jev trace.

Each question cites its argmax Noul when its score clears a threshold. The
threshold is swept by coverage on the main trace. The held-out trace (gold
dropped from every pool) gets the same threshold, so its act rate is the
false-act rate at that operating point.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

COVERAGES = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0)


@dataclass(frozen=True)
class Row:
    pick: str | None
    correct: bool
    p_act: float
    max_noul: float
    decided_act: bool


def load_trace(path: Path) -> list[Row]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        answers = item["raw"].get("answers", {}) if isinstance(item["raw"], dict) else {}
        nouls = [(answers[c]["noul"], c) for c in item["candidates"] if c in answers]
        # A tie keeps the earliest candidate, as live decode does.
        best = max(nouls, key=lambda pair: pair[0], default=None)
        route = answers.get("route", {}).get("probabilities", {})
        rows.append(
            Row(
                pick=None if best is None else best[1],
                correct=best is not None and best[1] in item["gold"],
                p_act=float(route.get("act", 0.0)),
                max_noul=best[0] if best is not None else 0.0,
                decided_act=item["decision"].startswith("act"),
            )
        )
    return rows


def sweep(
    rows: Sequence[Row], held: Sequence[Row], score: Callable[[Row], float]
) -> list[tuple[float, float, float, float | None]]:
    """(coverage, threshold, precision, held-out false-act) per target coverage.

    Scores tie often, so a threshold acts on every row at or above it and the
    reported coverage is that actual share, not the target.
    """
    ranked = sorted((row for row in rows if row.pick is not None), key=score, reverse=True)
    out = []
    for target in COVERAGES:
        k = min(len(ranked), max(1, round(target * len(rows))))
        if k == 0:
            break
        threshold = score(ranked[k - 1])
        acted = [row for row in ranked if score(row) >= threshold]
        entry = (len(acted) / len(rows), threshold, sum(row.correct for row in acted) / len(acted))
        if held:
            entry += (sum(row.pick is not None and score(row) >= threshold for row in held) / len(held),)
        else:
            entry += (None,)
        if not out or entry[0] > out[-1][0]:
            out.append(entry)
    return out


def render(rows: Sequence[Row], held: Sequence[Row], source: str, held_source: str | None) -> str:
    n = len(rows)
    acted = [row for row in rows if row.decided_act]
    decided_precision = sum(row.correct for row in acted) / len(acted) if acted else 0.0
    lines = [
        "# Risk-coverage",
        "",
        f"Trace `{source}`, n={n}." + (f" Held-out trace `{held_source}`, n={len(held)}." if held else ""),
        "",
        "Each question cites its argmax Noul when its score is at or above the threshold. Coverage is the share of questions that act at that threshold.",
        "Held-out false-act is the share of held-out questions (gold dropped from the pool) whose score clears the same threshold.",
        "",
        f"As decided (route `act` and argmax Noul ≥ 0.5): coverage {len(acted) / n:.3f}, precision {decided_precision:.3f}.",
        f"Ceiling if every question acts on its argmax Noul: {sum(row.correct for row in rows) / n:.3f}.",
    ]
    if held:
        lines.append(f"Held-out as decided: false-act {sum(row.decided_act for row in held) / len(held):.3f}.")
    for name, score in (("route p(act)", lambda row: row.p_act), ("max Noul", lambda row: row.max_noul)):
        lines += [
            "",
            f"## Ranked by {name}",
            "",
            "| coverage | threshold | precision | held-out false-act |",
            "| ---: | ---: | ---: | ---: |",
        ]
        for coverage, threshold, precision, false_act in sweep(rows, held, score):
            shown = "—" if false_act is None else f"{false_act:.3f}"
            lines.append(f"| {coverage:.3f} | {threshold:.2f} | {precision:.3f} | {shown} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score risk-coverage from a live BrowseComp-Plus trace.")
    parser.add_argument("trace", type=Path)
    parser.add_argument("--holdout", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    rows = load_trace(args.trace)
    held = load_trace(args.holdout) if args.holdout else []
    text = render(rows, held, args.trace.name, args.holdout.name if args.holdout else None)
    if args.out is None:
        print(text)
    else:
        args.out.write_text(text, encoding="utf-8")
        print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
