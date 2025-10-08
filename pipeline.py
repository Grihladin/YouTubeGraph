"""YouTube to Weaviate Pipeline - End-to-end transcript processing and upload."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from punctuation_worker import PunctuationWorker, TranscriptJob
from weaviate_uploader import WeaviateUploader

# Load environment variables
load_dotenv()


class YouTubeToWeaviatePipeline:
    """Complete pipeline: YouTube URL → Transcript → Punctuation → Chunking → Weaviate."""

    def __init__(
        self,
        weaviate_url: Optional[str] = None,
        weaviate_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        punctuation_model: Optional[str] = None,
        collection_name: str = "Segment",
    ):
        """Initialize the pipeline.

        Args:
            weaviate_url: Weaviate cluster URL (defaults to WEAVIATE_URL env var)
            weaviate_api_key: Weaviate API key (defaults to WEAVIATE_API_KEY env var)
            openai_api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            punctuation_model: Punctuation model name (defaults to fast multilingual model)
            collection_name: Weaviate collection name
        """
        # Get credentials from env vars if not provided
        self.weaviate_url = weaviate_url or os.getenv("WEAVIATE_URL")
        self.weaviate_api_key = weaviate_api_key or os.getenv("WEAVIATE_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

        if not self.weaviate_url or not self.weaviate_api_key:
            raise ValueError(
                "Weaviate credentials must be provided or set in environment variables"
            )

        # Initialize the punctuation worker
        print("🔄 Loading punctuation model...")
        self.punctuation_worker = PunctuationWorker(
            model_name=punctuation_model
            or "oliverguhr/fullstop-punctuation-multilingual-base"
        )
        print("✓ Punctuation model loaded!")

        # Store collection name for uploader
        self.collection_name = collection_name
        self.uploader = WeaviateUploader(
            cluster_url=self.weaviate_url,
            api_key=self.weaviate_api_key,
            openai_api_key=self.openai_api_key,
            collection_name=self.collection_name,
        )

    def process_video(
        self, youtube_url: str, languages: Optional[list[str]] = None
    ) -> int:
        """Process a YouTube video end-to-end and upload to Weaviate.

        Args:
            youtube_url: YouTube video URL
            languages: List of language codes to try (defaults to ['en'])

        Returns:
            Number of segments uploaded to Weaviate

        Steps:
            1. Fetch transcript from YouTube
            2. Restore punctuation and proper casing
            3. Chunk into semantic segments (3-6 sentences, 600-1600 chars)
            4. Upload to Weaviate with timestamps
        """
        print(f"\n{'='*60}")
        print(f"Processing: {youtube_url}")
        print(f"{'='*60}\n")

        # Step 1 & 2 & 3: Fetch, punctuate, and chunk transcript
        print("📥 Step 1-3: Fetching transcript and processing...")
        job = TranscriptJob(youtube_url=youtube_url, languages=languages)

        try:
            transcript_result = self.punctuation_worker(job)
            transcript_path = transcript_result.output_path
            if transcript_path:
                print(f"✓ Processed transcript saved to: {transcript_path}")
            print(f"✓ Generated {len(transcript_result.segments)} structured segments")
        except Exception as e:
            print(f"❌ Error processing transcript: {e}")
            raise

        # Step 4: Upload to Weaviate
        print("\n📤 Step 4: Uploading to Weaviate...")

        segment_count = self.uploader.upload_segments(transcript_result.segments)
        print(f"\n{'='*60}")
        print(f"✅ SUCCESS! Uploaded {segment_count} segments to Weaviate")
        print(f"{'='*60}\n")
        return segment_count

    def process_multiple_videos(self, youtube_urls: list[str]) -> dict[str, int]:
        """Process multiple YouTube videos.

        Args:
            youtube_urls: List of YouTube video URLs

        Returns:
            Dictionary mapping URLs to number of segments uploaded
        """
        results = {}

        for i, url in enumerate(youtube_urls, 1):
            print(f"\n🎬 Processing video {i}/{len(youtube_urls)}")
            try:
                count = self.process_video(url)
                results[url] = count
            except Exception as e:
                print(f"❌ Failed to process {url}: {e}")
                results[url] = 0

        # Summary
        print(f"\n{'='*60}")
        print("📊 BATCH PROCESSING SUMMARY")
        print(f"{'='*60}")
        total_segments = 0
        success_count = 0

        for url, count in results.items():
            status = "✓" if count > 0 else "✗"
            print(f"{status} {url}: {count} segments")
            total_segments += count
            if count > 0:
                success_count += 1

        print(f"\nTotal: {success_count}/{len(youtube_urls)} videos processed")
        print(f"Total segments uploaded: {total_segments}")
        print(f"{'='*60}\n")

        return results

    def close(self):
        """Clean up resources."""
        self.uploader.close()


def main():
    """Example usage of the pipeline."""

    # Example: Process a single video
    pipeline = YouTubeToWeaviatePipeline()

    try:
        # Single video
        youtube_url = "https://www.youtube.com/watch?v=zc9ajtpaS6k"
        pipeline.process_video(youtube_url)

        # Or process multiple videos:
        # video_urls = [
        #     "https://www.youtube.com/watch?v=VIDEO_ID_1",
        #     "https://www.youtube.com/watch?v=VIDEO_ID_2",
        #     "https://www.youtube.com/watch?v=VIDEO_ID_3",
        # ]
        # pipeline.process_multiple_videos(video_urls)
    finally:
        pipeline.close()


if __name__ == "__main__":
    main()
