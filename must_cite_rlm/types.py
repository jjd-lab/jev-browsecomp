from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, NewType, Union

ArtifactId = NewType("ArtifactId", str)
NodeId = NewType("NodeId", str)


@dataclass(frozen=True)
class Span:
    node_id: NodeId
    start_char: int
    end_char: int
    text: str


@dataclass(frozen=True)
class CandidateSet:
    node_ids: tuple[NodeId, ...]


@dataclass(frozen=True)
class Act:
    node_ids: tuple[NodeId, ...]

    def __post_init__(self) -> None:
        if len(self.node_ids) < 1:
            raise ValueError("Act.node_ids is empty")


@dataclass(frozen=True)
class Review:
    pass


@dataclass(frozen=True)
class Abstain:
    pass


Decision = Union[Act, Review, Abstain]


@dataclass(frozen=True)
class Cite:
    node_id: NodeId


@dataclass(frozen=True)
class Trial:
    question_id: str
    arm: str
    decision: Decision
    cites: tuple[Cite, ...]
    text: str | None
    raw_model: str


@dataclass(frozen=True)
class Metrics:
    exact_id_acc: float
    cite_ok: float
    illegal_span_rate: float
    abstain_rate: float
    cost_usd: float
    latency_ms: float


@dataclass(frozen=True)
class Gold:
    id: str
    text: str
    decision: Literal["act", "review", "abstain"]
    node_ids: tuple[NodeId, ...]
