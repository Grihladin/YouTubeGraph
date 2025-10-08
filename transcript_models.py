"""Shared transcript data models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(slots=True)
class TranscriptSegment:
    """Structured transcript segment with metadata."""

    video_id: str
    text: str
    start_s: float
    end_s: float
    tokens: int | None = None

    def as_weaviate_properties(self) -> dict:
        """Return a dict of properties expected by Weaviate."""
        properties = {
            "videoId": self.video_id,
            "text": self.text,
            "start_s": self.start_s,
            "end_s": self.end_s,
        }
        if self.tokens is not None:
            properties["tokens"] = int(self.tokens)
        return properties


@dataclass(slots=True)
class TranscriptResult:
    """Container for transcript output data."""

    video_id: str
    segments: Sequence[TranscriptSegment]
    output_path: Path | None

    def __iter__(self) -> Iterable[TranscriptSegment]:
        return iter(self.segments)

    def __len__(self) -> int:
        return len(self.segments)
