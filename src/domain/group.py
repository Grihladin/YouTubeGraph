"""Segment grouping domain models."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np


@dataclass
class Neighbor:
    """A neighboring segment with similarity and temporal info."""

    segment_id: str
    index: int
    similarity: float
    start_time: float
    end_time: float
    text: str
    embedding: Optional[List[float]] = None

    def effective_similarity(self, ref_time: float, tau: float = 150.0) -> float:
        """Calculate time-penalized similarity.

        Args:
            ref_time: Reference timestamp in seconds
            tau: Temporal decay constant (higher = slower decay)

        Returns:
            Effective similarity with temporal penalty applied
        """
        time_diff = abs(self.start_time - ref_time)
        temporal_penalty = math.exp(-time_diff / tau)
        return self.similarity * temporal_penalty


@dataclass
class SegmentNode:
    """A transcript segment with neighborhood information."""

    id: str
    video_id: str
    index: int  # Position in video timeline
    text: str
    start_time: float
    end_time: float
    word_count: int
    embedding: Optional[List[float]] = None
    neighbors: List[Neighbor] = field(default_factory=list)
    group_id: Optional[int] = None

    @property
    def duration(self) -> float:
        """Duration in seconds."""
        return self.end_time - self.start_time


@dataclass
class SegmentGroup:
    """A coherent group of segments forming a topic cluster."""

    group_id: int
    segments: List[SegmentNode]
    video_id: str

    @property
    def start_time(self) -> float:
        """Earliest start time in the group."""
        return min(s.start_time for s in self.segments)

    @property
    def end_time(self) -> float:
        """Latest end time in the group."""
        return max(s.end_time for s in self.segments)

    @property
    def total_words(self) -> int:
        """Total word count across all segments."""
        return sum(s.word_count for s in self.segments)

    @property
    def text(self) -> str:
        """Concatenated text of all segments."""
        return " ".join(s.text for s in self.segments)

    def centroid_embedding(self) -> np.ndarray:
        """Average embedding vector of all segments."""
        embeddings = [s.embedding for s in self.segments if s.embedding]
        if not embeddings:
            return np.array([])
        return np.mean(embeddings, axis=0)

    def avg_internal_similarity(self) -> float:
        """Average pairwise cosine similarity within the group."""
        if len(self.segments) < 2:
            return 1.0

        embeddings = [s.embedding for s in self.segments if s.embedding]
        if len(embeddings) < 2:
            return 1.0

        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = cosine_similarity(embeddings[i], embeddings[j])
                similarities.append(sim)

        return float(np.mean(similarities))

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "group_id": self.group_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.end_time - self.start_time,
            "num_segments": len(self.segments),
            "total_words": self.total_words,
            "text": self.text,
            "avg_cohesion": self.avg_internal_similarity(),
            "segments": [
                {
                    "id": s.id,
                    "index": s.index,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "text": s.text,
                    "word_count": s.word_count,
                }
                for s in self.segments
            ],
        }


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    v1 = np.array(vec1)
    v2 = np.array(vec2)

    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return float(np.dot(v1, v2) / (norm1 * norm2))
