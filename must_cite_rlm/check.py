from __future__ import annotations

import re
from collections.abc import Mapping

from must_cite_rlm.tree import Node
from must_cite_rlm.types import NodeId, Trial

_OFFSET = re.compile(r"start_char|end_char|\[\d+\s*:\s*\d+\]")
_QUOTE = re.compile(r'"([^"]*)"')


class IllegalSpan(Exception):
    pass


def assert_cites(trial: Trial, nodes: Mapping[NodeId, Node]) -> None:
    if _OFFSET.search(trial.raw_model):
        raise IllegalSpan(trial.question_id)
    spans = []
    for cite in trial.cites:
        node = nodes.get(cite.node_id)
        if node is None:
            raise IllegalSpan(cite.node_id)
        spans.append(node.span)
    if trial.text is None:
        return
    for quote in _QUOTE.findall(trial.text):
        if not any(span.text == quote for span in spans):
            raise IllegalSpan(trial.question_id)


def cites_ok(trial: Trial, nodes: Mapping[NodeId, Node]) -> bool:
    try:
        assert_cites(trial, nodes)
    except IllegalSpan:
        return False
    return True
