"""Transcript domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class TranscriptSegment:
    """A single transcript segment with timing information."""

    video_id: str
    text: str
    start_s: float  # Start time in seconds
    end_s: float  # End time in seconds
    tokens: Optional[int] = None  # Word count

    def as_weaviate_properties(self) -> dict:
        """Convert to Weaviate property dictionary."""
        return {
            "videoId": self.video_id,
            "text": self.text,
            "start_s": self.start_s,
            "end_s": self.end_s,
            "tokens": self.tokens or len(self.text.split()),
        }

    @property
    def duration(self) -> float:
        """Duration in seconds."""
        return self.end_s - self.start_s

    @property
    def word_count(self) -> int:
        """Number of words in the segment."""
        return self.tokens or len(self.text.split())


@dataclass
class TranscriptResult:
    """Result from transcript processing."""

    video_id: str
    segments: List[TranscriptSegment]
    output_path: Optional[Path] = None
    raw_text: Optional[str] = None

    @property
    def total_words(self) -> int:
        """Total word count across all segments."""
        return sum(seg.word_count for seg in self.segments)

    @property
    def duration(self) -> float:
        """Total duration in seconds."""
        if not self.segments:
            return 0.0
        return self.segments[-1].end_s


@dataclass
class TranscriptJob:
    """Job configuration for transcript processing."""

    youtube_url: str
    output_path: Optional[Path] = None
    output_dir: Path = field(default_factory=lambda: Path("output/transcripts"))
    languages: Optional[List[str]] = None
