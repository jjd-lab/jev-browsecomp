from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from must_cite_rlm.types import ArtifactId, Gold, NodeId, Span

ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "fixtures" / "corpus"
GOLD_PATH = ROOT / "fixtures" / "gold.jsonl"

_HEADING = re.compile(r"(?m)^## .+$")


@dataclass(frozen=True)
class Node:
    id: NodeId
    artifact_id: ArtifactId
    depth: int
    child_ids: tuple[NodeId, ...]
    span: Span


def _slug(heading: str) -> str:
    folded = unicodedata.normalize("NFKD", heading)
    ascii_text = "".join(ch for ch in folded if not unicodedata.combining(ch))
    words = re.findall(r"[a-z0-9]+", ascii_text.lower())
    if not words:
        raise ValueError(f"heading {heading!r} has no slug")
    return "-".join(words)


def _rstrip(text: str, start: int, end: int) -> int:
    while end > start and text[end - 1] in " \n":
        end -= 1
    return end


def _paragraphs(text: str, start: int, end: int) -> list[tuple[int, int]]:
    blocks: list[tuple[int, int]] = []
    i = start
    while i < end and text[i] == "\n":
        i += 1
    para_start: int | None = None
    while i < end:
        if text[i] == "\n" and i + 1 < end and text[i + 1] == "\n":
            if para_start is not None:
                blocks.append((para_start, _rstrip(text, para_start, i)))
                para_start = None
            i += 1
            continue
        if para_start is None and text[i] != "\n":
            para_start = i
        i += 1
    if para_start is not None:
        blocks.append((para_start, _rstrip(text, para_start, end)))
    return [(s, e) for s, e in blocks if e > s]


def parse_artifact(path: Path) -> dict[NodeId, Node]:
    text = path.read_text(encoding="utf-8")
    artifact = ArtifactId(path.stem)
    matches = list(_HEADING.finditer(text))
    if not matches:
        raise ValueError(f"{path} has no ## headings")
    nodes: dict[NodeId, Node] = {}
    section_ids: list[NodeId] = []
    root_id = NodeId(str(artifact))
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        end = _rstrip(text, start, end)
        heading = match.group(0)[3:].strip()
        section_id = NodeId(f"{artifact}/{_slug(heading)}")
        if section_id in nodes:
            raise ValueError(f"duplicate node {section_id}")
        line_end = text.find("\n", start)
        body_start = end if line_end == -1 or line_end >= end else line_end + 1
        child_ids: list[NodeId] = []
        for pi, (ps, pe) in enumerate(_paragraphs(text, body_start, end)):
            para_id = NodeId(f"{section_id}/{pi}")
            child_ids.append(para_id)
            nodes[para_id] = Node(
                para_id,
                artifact,
                2,
                (),
                Span(para_id, ps, pe, text[ps:pe]),
            )
        nodes[section_id] = Node(
            section_id,
            artifact,
            1,
            tuple(child_ids),
            Span(section_id, start, end, text[start:end]),
        )
        section_ids.append(section_id)
    root_end = _rstrip(text, 0, len(text))
    nodes[root_id] = Node(
        root_id,
        artifact,
        0,
        tuple(section_ids),
        Span(root_id, 0, root_end, text[:root_end]),
    )
    return nodes


def load_nodes(directory: Path = CORPUS_DIR) -> dict[NodeId, Node]:
    paths = sorted(directory.glob("*.md"))
    if not 8 <= len(paths) <= 48:
        raise ValueError(f"expected 8 to 48 markdown files, found {len(paths)}")
    nodes: dict[NodeId, Node] = {}
    for path in paths:
        for node_id, node in parse_artifact(path).items():
            if node_id in nodes:
                raise ValueError(f"duplicate node {node_id}")
            nodes[node_id] = node
    return nodes


def load_gold(path: Path = GOLD_PATH) -> tuple[Gold, ...]:
    rows: list[Gold] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise ValueError("gold row is not an object")
        qid = obj["id"]
        text = obj["question"]
        decision = obj["gold_decision"]
        raw_ids = obj["gold_node_ids"]
        if not isinstance(qid, str) or not isinstance(text, str):
            raise ValueError("gold id and question must be strings")
        if decision not in ("act", "review", "abstain"):
            raise ValueError(f"{qid} has gold_decision {decision!r}")
        if not isinstance(raw_ids, list) or not all(isinstance(x, str) for x in raw_ids):
            raise ValueError(f"{qid} gold_node_ids must be a list of strings")
        node_ids = tuple(NodeId(x) for x in raw_ids)
        if decision == "act" and len(node_ids) < 1:
            raise ValueError(f"{qid} act gold has no ids")
        if decision != "act" and len(node_ids) > 0:
            raise ValueError(f"{qid} {decision} gold must not cite ids")
        rows.append(Gold(qid, text, decision, node_ids))
    if not 20 <= len(rows) <= 40:
        raise ValueError(f"expected 20 to 40 questions, found {len(rows)}")
    abstain = sum(row.decision == "abstain" for row in rows)
    if abstain < 5:
        raise ValueError(f"expected at least 5 abstain questions, found {abstain}")
    return tuple(rows)
