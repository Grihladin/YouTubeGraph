"""YouTube transcript worker that restores punctuation using deepmultilingualpunctuation."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional
from urllib.parse import parse_qs, urlparse

from deepmultilingualpunctuation import PunctuationModel
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)


@dataclass
class TranscriptJob:
    """Input payload for the punctuation worker."""

    youtube_url: str
    output_path: Optional[Path] = None
    output_dir: Path = field(default_factory=lambda: Path("Transcripts"))
    languages: Optional[List[str]] = None


class PunctuationWorker:
    """Fetches YouTube transcripts, restores punctuation, and persists the result."""

    def __init__(self, model_name: Optional[str] = None) -> None:
        """Initialize the punctuator model.

        Args:
            model_name: Optional name or path of the model to load. If omitted,
                the library's default multilingual model is used.

        Notes:
            Loading the model may download weights the first time it is used so
            calling this in a long-running process at startup is preferred.
        """
        # When no model is provided, use library default (currently multilingual).
        self.punctuator = PunctuationModel(model=model_name) if model_name else PunctuationModel()

    def __call__(self, job: TranscriptJob) -> Path:
        """Execute a punctuation job end-to-end.

        Steps performed:
        1. Extract the canonical YouTube video id from the provided URL.
        2. Fetch the raw transcript text for the video (language preferences supported).
        3. Run the punctuator model to restore punctuation and casing.
        4. Resolve and create the output file path and persist the result.

        Args:
            job: A `TranscriptJob` object describing the input URL and where to
                write the result.

        Returns:
            Path to the written punctuated transcript file.

        Raises:
            RuntimeError: If transcript fetching fails or returns empty text.
            ValueError: If the video ID cannot be extracted from the URL.
        """

        # 1) Extract video id from the provided YouTube URL
        video_id = self._extract_video_id(job.youtube_url)

        # 2) Fetch raw transcript text (may raise RuntimeError on failure)
        raw_transcript = self._fetch_transcript(video_id, job.languages)

        # 3) Restore punctuation using the loaded model. The model expects
        #    concatenated raw text and performs any internal preprocessing.
        punctuated = self.punctuator.restore_punctuation(raw_transcript)

        # 4) Resolve output path, ensure directory exists, and write file
        output_path = self._resolve_output_path(job, video_id)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(punctuated, encoding="utf-8")
        return output_path

    def _fetch_transcript(self, video_id: str, languages: Optional[Iterable[str]]) -> str:
        """Fetch transcript text for a video, trying preferred languages in order."""
        langs = list(languages) if languages else ["en"]
        try:
            ytt_api = YouTubeTranscriptApi()
            fetched = ytt_api.fetch(video_id, languages=langs)
        except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable) as e:
            raise RuntimeError(f"Unable to fetch transcript for video {video_id}: {e}") from e

        if not fetched:
            raise RuntimeError(f"Fetched transcript for video {video_id} is empty")

        segments: List[str] = [
            self._normalise_snippet_text(snippet)
            for snippet in fetched
            if self._normalise_snippet_text(snippet)
        ]
        transcript_text = " ".join(segments)
        if not transcript_text:
            raise RuntimeError(f"Fetched transcript for video {video_id} is empty after normalization")
        return transcript_text

    def _extract_video_id(self, url: str) -> str:
        """Extract the canonical YouTube video identifier from a watch/share URL."""
        parsed = urlparse(url)
        if parsed.netloc.endswith("youtu.be"):
            video_id = parsed.path.lstrip("/")
            if video_id:
                return video_id.split("?", 1)[0]
        query = parse_qs(parsed.query)
        video_id = query.get("v", [""])[0]
        if video_id:
            return video_id
        raise ValueError("Unable to extract YouTube video ID from URL")

    @staticmethod
    def _normalise_snippet_text(snippet) -> str:
        """Return a single-line snippet string from a transcript snippet."""
        # Handle both dict and FetchedTranscriptSnippet objects
        if hasattr(snippet, 'text'):
            text = snippet.text
        elif isinstance(snippet, dict):
            text = snippet.get("text", "")
        else:
            text = str(snippet)
        return text.replace("\n", " ").strip()

    def _resolve_output_path(self, job: TranscriptJob, video_id: str) -> Path:
        """Determine where the punctuated transcript should be written."""
        filename = f"transcript_{video_id}.txt"
        if job.output_path:
            if job.output_path.suffix:
                return job.output_path
            return job.output_path / filename
        return job.output_dir / filename


def run_sample_job() -> Path:
    """Run a sample worker job for local testing."""
    sample_link = "https://www.youtube.com/watch?v=HbDqLPm_2vY"

    worker = PunctuationWorker()
    job = TranscriptJob(youtube_url=sample_link)
    result_path = worker(job)
    return result_path


if __name__ == "__main__":
    path = run_sample_job()
    print(f"Punctuation restored transcript written to {path}")
