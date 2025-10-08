"""Upload transcript segments to Weaviate collection."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable, List, Optional
from uuid import NAMESPACE_URL, uuid5

from dotenv import load_dotenv
import weaviate
from weaviate.classes.init import Auth

from transcript_models import TranscriptSegment

# Load environment variables from .env file
load_dotenv()


def parse_timestamp(timestamp_str: str) -> float:
    """Parse timestamp string like [00:00:07.12] to seconds.

    Args:
        timestamp_str: Timestamp in format [HH:MM:SS.MS]

    Returns:
        Time in seconds as float
    """
    # Remove brackets and split by colon
    time_str = timestamp_str.strip("[]")
    parts = time_str.split(":")

    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])

    total_seconds = hours * 3600 + minutes * 60 + seconds
    return total_seconds


def parse_transcript_file(file_path: Path) -> List[TranscriptSegment]:
    """Parse a transcript file into segments.

    Args:
        file_path: Path to the transcript file

    Returns:
        List of segment dicts with timestamp, text, and metadata
    """
    content = file_path.read_text(encoding="utf-8")

    # Extract video ID from filename (e.g., transcript_HbDqLPm_2vY.txt -> HbDqLPm_2vY)
    video_id = file_path.stem.replace("transcript_", "")

    # Split by double newlines to separate segments
    raw_segments = [chunk.strip() for chunk in content.strip().split("\n\n") if chunk.strip()]

    segments = []
    for raw_segment in raw_segments:
        # Match timestamp pattern at the start
        timestamp_match = re.match(
            r"\[(\d{2}:\d{2}:\d{2}\.\d{2})\]\s*(.*)", raw_segment, re.DOTALL
        )

        if timestamp_match:
            timestamp_str = f"[{timestamp_match.group(1)}]"
            text = timestamp_match.group(2).strip()

            start_seconds = parse_timestamp(timestamp_str)

            segments.append(
                {
                    "video_id": video_id,
                    "text": text,
                    "start_s": start_seconds,
                    "end_s": None,  # Will be calculated
                    "word_count": len(text.split()),
                }
            )

    # Calculate end times
    for i in range(len(segments)):
        if i < len(segments) - 1:
            # End time is the start of the next segment
            segments[i]["end_s"] = segments[i + 1]["start_s"]
        else:
            # For the last segment, estimate end time (add ~duration based on text length)
            # Assume ~150 words per minute speaking rate
            words = len(segments[i]["text"].split())
            estimated_duration = (words / 150) * 60  # Convert to seconds
            segments[i]["end_s"] = segments[i]["start_s"] + estimated_duration

    return [
        TranscriptSegment(
            video_id=item["video_id"],
            text=item["text"],
            start_s=item["start_s"],
            end_s=item["end_s"],
            tokens=item.get("word_count"),
        )
        for item in segments
    ]


class WeaviateUploader:
    """Upload transcript segments to Weaviate."""

    def __init__(
        self,
        cluster_url: str,
        api_key: str,
        openai_api_key: Optional[str] = None,
        collection_name: str = "Segment",
    ):
        """Initialize Weaviate client.

        Args:
            cluster_url: Weaviate cluster URL (e.g., https://xxxxx.weaviate.network)
            api_key: Weaviate API key
            openai_api_key: OpenAI API key for vectorization (defaults to OPENAI_API_KEY env var)
            collection_name: Name of the collection to upload to
        """
        self.collection_name = collection_name
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

        if not self.openai_api_key:
            raise ValueError(
                "OpenAI API key must be provided or set in OPENAI_API_KEY env var"
            )

        # Connect to Weaviate Cloud
        self.client = weaviate.connect_to_weaviate_cloud(
            cluster_url=cluster_url,
            auth_credentials=Auth.api_key(api_key),
            headers={"X-OpenAI-Api-Key": self.openai_api_key}
        )

        print(f"✓ Connected to Weaviate cluster: {cluster_url}")
        print(f"✓ Cluster is ready: {self.client.is_ready()}")

    def upload_segments(
        self, segments: Iterable[TranscriptSegment], batch_size: int = 100
    ) -> int:
        """Upload segments to Weaviate collection.

        Args:
            segments: Iterable of transcript segments
            batch_size: (Currently unused) retained for API compatibility

        Returns:
            Number of segments successfully uploaded
        """
        collection = self.client.collections.get(self.collection_name)

        uploaded_count = 0

        # Upload in batches (dynamic batching handles sizing automatically)
        with collection.batch.dynamic() as batch:
            for segment in segments:
                properties = segment.as_weaviate_properties()
                segment_uuid = self._segment_uuid(segment)
                batch.add_object(uuid=segment_uuid, properties=properties)
                uploaded_count += 1

        print(f"✓ Uploaded {uploaded_count} segments to Weaviate")
        return uploaded_count

    def upload_transcript_file(self, file_path: Path) -> int:
        """Parse and upload a transcript file.

        Args:
            file_path: Path to the transcript file

        Returns:
            Number of segments uploaded
        """
        print(f"📄 Parsing transcript file: {file_path.name}")
        segments = parse_transcript_file(file_path)
        print(f"✓ Parsed {len(segments)} segments")

        print(f"⬆️  Uploading to Weaviate...")
        count = self.upload_segments(segments)
        return count

    def close(self):
        """Close Weaviate client connection."""
        self.client.close()
        print("✓ Closed Weaviate connection")

    @staticmethod
    def _segment_uuid(segment: TranscriptSegment) -> str:
        """Generate deterministic UUID for a segment."""
        key = f"{segment.video_id}:{segment.start_s:.6f}"
        return str(uuid5(NAMESPACE_URL, key))


def main():
    """Example usage: upload a transcript file to Weaviate."""

    # Get credentials from environment variables
    WEAVIATE_URL = os.getenv("WEAVIATE_URL")
    WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    if not WEAVIATE_URL or not WEAVIATE_API_KEY:
        print(
            "❌ Error: WEAVIATE_URL and WEAVIATE_API_KEY environment variables must be set"
        )
        print("\nExample:")
        print('  export WEAVIATE_URL="https://xxxxx.weaviate.network"')
        print('  export WEAVIATE_API_KEY="your-api-key"')
        print('  export OPENAI_API_KEY="your-openai-key"')
        return

    # Initialize uploader
    uploader = WeaviateUploader(
        cluster_url=WEAVIATE_URL,
        api_key=WEAVIATE_API_KEY,
        openai_api_key=OPENAI_API_KEY,
    )

    try:
        # Upload the sample transcript
        transcript_path = Path("Transcripts/transcript_HbDqLPm_2vY.txt")

        if not transcript_path.exists():
            print(f"❌ Error: Transcript file not found at {transcript_path}")
            return

        uploader.upload_transcript_file(transcript_path)
        print("✅ Upload complete!")

    finally:
        uploader.close()


if __name__ == "__main__":
    main()
