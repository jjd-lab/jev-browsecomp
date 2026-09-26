#!/usr/bin/env python3
"""Rewrite fixtures from HotpotQA dev distractor v1.

The JSON is not committed. Pass its path. The script checks the sha256,
writes the markdown slice, gold, and provenance, then checks the stub gap.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from must_cite_rlm.arms import arm_b, arm_c, ranked_leaves
from must_cite_rlm.check import cites_ok
from must_cite_rlm.scoreboard import is_exact
from must_cite_rlm.tree import ROOT, _slug, parse_artifact
from must_cite_rlm.types import Gold, NodeId

SHA256 = "e3da074df24e8369009918aa5cdbdd254dadcde4c63f7569d36afd6f2268caa8"
CORPUS = ROOT / "fixtures" / "corpus"
GOLD_PATH = ROOT / "fixtures" / "gold.jsonl"
PROVENANCE_PATH = ROOT / "fixtures" / "provenance.jsonl"

# role, local id, HotpotQA _id
SLICE = (
    ("bridge", "b01", "5ae792f55542994a481bbdae"),
    ("bridge", "b02", "5abd82dc5542993062266cb6"),
    ("bridge", "b03", "5a8bd43c5542997f31a41dd6"),
    ("bridge", "b04", "5ab926bc554299131ca42285"),
    ("bridge", "b05", "5abab36455429955dce3eed1"),
    ("bridge", "b06", "5ae748d1554299572ea547b0"),
    ("bridge", "b07", "5ab953a45542996be202047f"),
    ("bridge", "b08", "5a8a2d2155429930ff3c0cdc"),
    ("bridge", "b09", "5a745e1455429929fddd83fd"),
    ("bridge", "b10", "5ab7f7465542993667794071"),
    ("bridge", "b11", "5abd94525542992ac4f382d2"),
    ("easy", "e01", "5a7c465a5542990527d5547f"),
    ("easy", "e02", "5adf39d55542992d7e9f92e6"),
    ("easy", "e03", "5abd0077554299700f9d7954"),
    ("easy", "e04", "5ab2d61155429916697740ff"),
    ("multi", "m01", "5a8e3ea95542995a26add48d"),
    ("multi", "m02", "5a87ab905542996e4f3088c1"),
)

ABSTAIN = (
    ("z01", "What is the atomic number of selenium?"),
    ("z02", "How many strings does a koto have?"),
    ("z03", "What is the boiling point of xenon?"),
    ("z04", "Which enzyme synthesizes telomeres?"),
    ("z05", "What is the half-life of molybdenum-99?"),
    ("z06", "How many legs does a horseshoe crab have?"),
)


def _bad(sentence: str) -> bool:
    text = sentence.strip()
    if not text or "\n" in text or "\r" in text or '"' in text:
        return True
    if text.startswith("##") or "{'" in text:
        return True
    # HotpotQA sometimes splits "bef. 1100" birth dates into a stub sentence.
    if "(bef." in text and len(text) < 40:
        return True
    return False


def _keep(sentences: list[str]) -> list[str]:
    return [sentence.strip() for sentence in sentences if not _bad(sentence)]


def _support_titles(example: dict) -> list[str]:
    titles: list[str] = []
    for title, _ in example["supporting_facts"]:
        if title not in titles:
            titles.append(title)
    return titles


def _raw_context(example: dict) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for title, sentences in example["context"]:
        if title in found:
            raise ValueError(f"{example['_id']} repeats {title}")
        found[title] = [sentence.strip() for sentence in sentences]
    return found


def _node_id(title: str, index: int) -> str:
    stem = _slug(title)
    return f"{stem}/{stem}/{index}"


def _write_article(title: str, sentences: list[str]) -> None:
    stem = _slug(title)
    lines = [
        f"# {title}",
        "",
        "Wikipedia passage frozen in HotpotQA dev distractor v1. CC BY-SA 4.0.",
        "See fixtures/LICENSE.txt.",
        "",
        f"## {title}",
        "",
    ]
    for sentence in sentences:
        lines.append(sentence)
        lines.append("")
    (CORPUS / f"{stem}.md").write_text("\n".join(lines), encoding="utf-8")


def _load_nodes() -> dict:
    nodes = {}
    for path in sorted(CORPUS.glob("*.md")):
        for node_id, node in parse_artifact(path).items():
            if node_id in nodes:
                raise ValueError(f"duplicate node {node_id}")
            nodes[node_id] = node
    return nodes


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python3 scripts/build_hotpot_slice.py hotpot_dev_distractor_v1.json", file=sys.stderr)
        return 2
    source = Path(argv[1])
    blob = source.read_bytes()
    digest = hashlib.sha256(blob).hexdigest()
    if digest != SHA256:
        raise SystemExit(f"sha256 {digest} != {SHA256}")
    rows = json.loads(blob)
    by_id = {row["_id"]: row for row in rows}

    articles: dict[str, list[str]] = {}
    plans: list[tuple[str, str, dict, list[tuple[str, int]]]] = []
    for role, qid, hotpot_id in SLICE:
        example = by_id[hotpot_id]
        titles = _support_titles(example)
        if len(titles) != 2:
            raise SystemExit(f"{qid} has titles {titles}")
        raw = _raw_context(example)
        cleaned = {title: _keep(raw[title]) for title in titles}
        supports: list[tuple[str, int]] = []
        for title, index in example["supporting_facts"]:
            sentence = raw[title][index]
            if _bad(sentence) or sentence not in cleaned[title]:
                raise SystemExit(f"{qid} dropped support {title}[{index}]")
            supports.append((title, cleaned[title].index(sentence)))
        for title in titles:
            if title in articles and articles[title] != cleaned[title]:
                raise SystemExit(f"{qid} sentence list for {title!r} disagrees")
            articles.setdefault(title, cleaned[title])
        plans.append((role, qid, example, supports))

    stems: dict[str, str] = {}
    for title in articles:
        stem = _slug(title)
        if not stem or stem in stems:
            raise SystemExit(f"slug clash {stem!r} for {title!r} and {stems.get(stem)!r}")
        stems[stem] = title

    CORPUS.mkdir(parents=True, exist_ok=True)
    for path in CORPUS.glob("*.md"):
        path.unlink()
    for title, sentences in articles.items():
        _write_article(title, sentences)

    nodes = _load_nodes()
    gold_lines: list[str] = []
    provenance: list[dict] = []
    strict_flat_misses = 0
    for role, qid, example, supports in plans:
        answer = example["answer"].strip()
        if role == "multi":
            node_ids = [_node_id(title, index) for title, index in supports]
            # HotpotQA lists a fact twice when two sentences in one article support it.
            # Keep each id once, in first-seen order.
            deduped: list[str] = []
            for node_id in node_ids:
                if node_id not in deduped:
                    deduped.append(node_id)
            node_ids = deduped
            if len(node_ids) != 2:
                raise SystemExit(f"{qid} support ids {node_ids}")
        else:
            hits = []
            for title, index in supports:
                sentence = nodes[NodeId(_node_id(title, index))].span.text
                if answer.casefold() in sentence.casefold():
                    hits.append(_node_id(title, index))
            if len(hits) != 1:
                raise SystemExit(f"{qid} answer hits {hits}")
            node_ids = hits
        gold = {
            "id": qid,
            "question": example["question"],
            "gold_decision": "act",
            "gold_node_ids": node_ids,
        }
        gold_lines.append(json.dumps(gold, ensure_ascii=False))
        titles = _support_titles(example)
        provenance.append(
            {
                "id": qid,
                "role": role,
                "hotpot_id": example["_id"],
                "answer": answer,
                "titles": titles,
                "policy": "both supporting sentences" if role == "multi" else "answer-bearing supporting sentence",
            }
        )
        trial_gold = Gold(qid, example["question"], "act", tuple(NodeId(node_id) for node_id in node_ids))
        got_b = is_exact(arm_b(trial_gold, nodes), trial_gold)
        got_c = is_exact(arm_c(trial_gold, nodes, ranker="overlap"), trial_gold)
        if role == "bridge" and not (got_b and not got_c):
            raise SystemExit(f"{qid} stub gap failed B={got_b} C={got_c}")
        if role == "easy" and not (got_b and got_c):
            raise SystemExit(f"{qid} easy row failed B={got_b} C={got_c}")
        if role == "multi" and (got_b or got_c):
            raise SystemExit(f"{qid} multi row was exact B={got_b} C={got_c}")
        if not cites_ok(arm_b(trial_gold, nodes), nodes) or not cites_ok(arm_c(trial_gold, nodes, ranker="overlap"), nodes):
            raise SystemExit(f"{qid} cite check failed")
        if role == "bridge":
            ranked = ranked_leaves(example["question"], nodes, ranker="overlap")
            top_score, top_id = ranked[0]
            by_id = {node_id: score for score, node_id in ranked}
            gold_score = by_id[NodeId(node_ids[0])]
            if top_id == NodeId(node_ids[0]):
                raise SystemExit(f"{qid} flat top-1 is the gold sentence")
            if top_score > gold_score:
                strict_flat_misses += 1
    if strict_flat_misses < 5:
        raise SystemExit(f"only {strict_flat_misses} bridge rows strictly outscore the answer sentence")

    for qid, question in ABSTAIN:
        gold = {"id": qid, "question": question, "gold_decision": "abstain", "gold_node_ids": []}
        gold_lines.append(json.dumps(gold, ensure_ascii=False))
        provenance.append({"id": qid, "role": "abstain", "hotpot_id": None, "answer": None, "titles": [], "policy": "off corpus"})
        trial_gold = Gold(qid, question, "abstain", ())
        if not (is_exact(arm_b(trial_gold, nodes), trial_gold) and is_exact(arm_c(trial_gold, nodes, ranker="overlap"), trial_gold)):
            raise SystemExit(f"{qid} did not abstain")

    for node in nodes.values():
        if node.depth == 2 and '"' in node.span.text:
            raise SystemExit(f"{node.id} contains a double quote")

    GOLD_PATH.write_text("\n".join(gold_lines) + "\n", encoding="utf-8")
    PROVENANCE_PATH.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in provenance) + "\n",
        encoding="utf-8",
    )
    n_files = len(list(CORPUS.glob("*.md")))
    n_sections = sum(node.depth == 1 for node in nodes.values())
    print(f"wrote {len(gold_lines)} questions, {n_files} files, {n_sections} sections")
    print(f"strict flat misses {strict_flat_misses}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
