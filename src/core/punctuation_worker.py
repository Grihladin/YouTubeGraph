"""YouTube transcript worker that restores punctuation using deepmultilingualpunctuation."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence
from urllib.parse import parse_qs, urlparse

# Limit CPU threads to reduce memory usage (prevents my Mac from freezing with low RAM)
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
os.environ["NUMEXPR_NUM_THREADS"] = "2"

from deepmultilingualpunctuation import PunctuationModel
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from .transcript_models import TranscriptResult, TranscriptSegment


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
        self.punctuator = (
            PunctuationModel(model=model_name) if model_name else PunctuationModel()
        )

    def __call__(self, job: TranscriptJob) -> TranscriptResult:
        """Execute a punctuation job end-to-end.

        Steps performed:
        1. Extract the canonical YouTube video id from the provided URL.
        2. Fetch the raw transcript segments with timestamps.
        3. Run the punctuator model to restore punctuation and casing.
        4. Resolve and create the output file path and persist the result.

        Args:
            job: A `TranscriptJob` object describing the input URL and where to
                write the result.

        Raises:
            RuntimeError: If transcript fetching fails or returns empty text.
            ValueError: If the video ID cannot be extracted from the URL.
        """

        # 1) Extract video id from the provided YouTube URL
        video_id = self._extract_video_id(job.youtube_url)

        # 2) Fetch raw transcript segments with timestamps
        segments_with_timestamps = self._fetch_transcript_segments(
            video_id, job.languages
        )

        # 3) Extract just the text for punctuation restoration
        raw_text = " ".join(seg["text"] for seg in segments_with_timestamps)
        punctuated_text = self.punctuator.restore_punctuation(raw_text)

        # 4) Blend punctuation back with timestamps and chunk into segments
        word_timeline = self._build_word_timeline(segments_with_timestamps)
        punctuated_words = punctuated_text.split()
        timed_words = self._merge_words_with_timestamps(word_timeline, punctuated_words)
        sentences = self._words_to_sentences(timed_words)
        segments = self._sentences_to_segments(sentences, video_id)

        if not segments:
            raise RuntimeError(
                f"Punctuation pipeline returned no segments for video {video_id}"
            )

        transcript_text = self._format_transcript_text(segments)

        # 5) Resolve output path, ensure directory exists, and write file
        output_path = self._resolve_output_path(job, video_id)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(transcript_text, encoding="utf-8")

        return TranscriptResult(
            video_id=video_id,
            segments=segments,
            output_path=output_path,
        )

    def _fetch_transcript_segments(
        self, video_id: str, languages: Optional[Iterable[str]]
    ) -> List[dict]:
        """Fetch transcript segments with timestamps for a video.

        Returns:
            List of dicts with 'text', 'start', and 'duration' keys.
        """
        langs = list(languages) if languages else ["en"]
        try:
            ytt_api = YouTubeTranscriptApi()
            fetched = ytt_api.fetch(video_id, languages=langs)
        except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable) as e:
            raise RuntimeError(
                f"Unable to fetch transcript for video {video_id}: {e}"
            ) from e

        if not fetched:
            raise RuntimeError(f"Fetched transcript for video {video_id} is empty")

        # Extract segments with normalized text and timing info
        segments = []
        for snippet in fetched:
            text = self._normalise_snippet_text(snippet)
            if text:
                segments.append(
                    {"text": text, "start": snippet.start, "duration": snippet.duration}
                )

        if not segments:
            raise RuntimeError(
                f"Fetched transcript for video {video_id} is empty after normalization"
            )
        return segments

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
        # FetchedTranscriptSnippet has a 'text' attribute
        text = snippet.text
        return text.replace("\n", " ").strip()

    @staticmethod
    def _build_word_timeline(segments: Sequence[dict]) -> List[dict]:
        """Return a word-level timeline using segment timing metadata."""
        timeline: List[dict] = []
        for seg in segments:
            words = seg["text"].split()
            if not words:
                continue
            word_duration = seg["duration"] / max(len(words), 1)
            for idx in range(len(words)):
                start = seg["start"] + idx * word_duration
                end = seg["start"] + (idx + 1) * word_duration
                timeline.append({"start": start, "end": end})
        return timeline

    @staticmethod
    def _merge_words_with_timestamps(
        word_timeline: Sequence[dict], punctuated_words: Sequence[str]
    ) -> List[dict]:
        """Merge punctuated words with their corresponding timestamps."""
        limit = min(len(word_timeline), len(punctuated_words))
        if not limit:
            return []

        if len(word_timeline) != len(punctuated_words):
            print(
                f"⚠️  Word alignment mismatch: "
                f"{len(word_timeline)} original words vs {len(punctuated_words)} punctuated words. "
                "Truncating to smallest length."
            )

        merged = []
        for idx in range(limit):
            merged.append(
                {
                    "text": punctuated_words[idx],
                    "start": word_timeline[idx]["start"],
                    "end": word_timeline[idx]["end"],
                }
            )
        return merged

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Convert seconds to [HH:MM:SS.MS] format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"[{hours:02d}:{minutes:02d}:{secs:05.2f}]"

    def _words_to_sentences(self, words: Sequence[dict]) -> List[dict]:
        """Group timed words into sentences."""
        sentences: List[dict] = []
        current: List[dict] = []

        for entry in words:
            current.append(entry)
            if self._word_ends_sentence(entry["text"]):
                sentences.append(self._build_sentence(current))
                current = []

        if current:
            sentences.append(self._build_sentence(current))

        return sentences

    @staticmethod
    def _word_ends_sentence(word: str) -> bool:
        """Determine if a word ends a sentence."""
        trimmed = word.rstrip("\"')]}»”’»›")
        return bool(trimmed) and trimmed[-1] in {".", "!", "?"}

    @staticmethod
    def _build_sentence(words: Sequence[dict]) -> dict:
        """Build a sentence payload from words."""
        return {
            "text": " ".join(word["text"] for word in words),
            "start": words[0]["start"],
            "end": words[-1]["end"],
            "token_count": len(words),
        }

    @staticmethod
    def _sentences_to_segments(
        sentences: Sequence[dict],
        video_id: str,
        min_tokens: int = 120,
        max_tokens: int = 320,
    ) -> List[TranscriptSegment]:
        """Group sentences into chunked transcript segments."""
        if not sentences:
            return []

        segments: List[TranscriptSegment] = []
        current: List[dict] = []
        token_count = 0

        for sentence in sentences:
            sentence_tokens = sentence["token_count"]

            should_flush = (
                current
                and token_count >= min_tokens
                and token_count + sentence_tokens > max_tokens
            )

            if should_flush:
                segments.append(
                    TranscriptSegment(
                        video_id=video_id,
                        text=" ".join(item["text"] for item in current),
                        start_s=current[0]["start"],
                        end_s=current[-1]["end"],
                        tokens=token_count,
                    )
                )
                current = []
                token_count = 0

            current.append(sentence)
            token_count += sentence_tokens

        if current:
            segments.append(
                TranscriptSegment(
                    video_id=video_id,
                    text=" ".join(item["text"] for item in current),
                    start_s=current[0]["start"],
                    end_s=current[-1]["end"],
                    tokens=token_count,
                )
            )

        return segments

    def _format_transcript_text(self, segments: Sequence[TranscriptSegment]) -> str:
        """Render structured segments back to transcript text with timestamps."""
        lines: List[str] = []
        for segment in segments:
            timestamp = self._format_timestamp(segment.start_s)
            lines.append(f"{timestamp} {segment.text}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

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

    print("🔄 Loading AI model (faster, less memory)...")
    worker = PunctuationWorker(
        model_name="oliverguhr/fullstop-punctuation-multilingual-base"
    )
    print("✓ Model loaded!")

    print("🔄 Fetching transcript from YouTube...")
    job = TranscriptJob(youtube_url=sample_link)

    print("🔄 Restoring punctuation (this may take 30-60s)...")
    result = worker(job)
    print("✓ Done!")
    if not result.output_path:
        raise RuntimeError("Transcript result did not provide an output path.")
    return result.output_path


if __name__ == "__main__":
    path = run_sample_job()
    print(f"Punctuation restored transcript written to {path}")
