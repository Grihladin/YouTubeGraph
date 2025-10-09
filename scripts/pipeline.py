"""YouTube to Weaviate Pipeline - End-to-end transcript processing and upload."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from src.core.punctuation_worker import PunctuationWorker, TranscriptJob
from src.core.weaviate_uploader import WeaviateUploader
from src.core.segment_grouper import SegmentGrouper

# Load environment variables
load_dotenv()


class YouTubeToWeaviatePipeline:
    """Complete pipeline: YouTube URL → Transcript → Punctuation → Chunking → Weaviate → Grouping."""

    def __init__(
        self,
        weaviate_url: Optional[str] = None,
        weaviate_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        punctuation_model: Optional[str] = None,
        collection_name: str = "Segment",
        enable_grouping: bool = True,
        grouping_params: Optional[dict] = None,
    ):
        """Initialize the pipeline.

        Args:
            weaviate_url: Weaviate cluster URL (defaults to WEAVIATE_URL env var)
            weaviate_api_key: Weaviate API key (defaults to WEAVIATE_API_KEY env var)
            openai_api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            punctuation_model: Punctuation model name (defaults to fast multilingual model)
            collection_name: Weaviate collection name
            enable_grouping: Whether to automatically group segments after upload
            grouping_params: Optional dict of hyperparameters for SegmentGrouper
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
        self.enable_grouping = enable_grouping

        self.uploader = WeaviateUploader(
            cluster_url=self.weaviate_url,
            api_key=self.weaviate_api_key,
            openai_api_key=self.openai_api_key,
            collection_name=self.collection_name,
        )

        # Initialize grouper if enabled
        self.grouper = None
        if self.enable_grouping:
            # Use tuned parameters by default for better quality
            tuned_defaults = {
                "k_neighbors": 8,
                "neighbor_threshold": 0.80,  # Stricter neighbor selection
                "adjacent_threshold": 0.70,  # Stricter joining threshold
                "temporal_tau": 150.0,
                "max_group_words": 700,  # Smaller, more focused groups
                "min_group_segments": 2,
                "merge_centroid_threshold": 0.85,  # Less aggressive merging
            }
            # Override defaults with user-provided params
            final_params = {**tuned_defaults, **(grouping_params or {})}
            
            self.grouper = SegmentGrouper(
                weaviate_url=self.weaviate_url,
                weaviate_api_key=self.weaviate_api_key,
                openai_api_key=self.openai_api_key,
                collection_name=self.collection_name,
                **final_params,
            )

    def process_video(
        self,
        youtube_url: str,
        languages: Optional[list[str]] = None,
        output_groups: bool = True,
    ) -> dict:
        """Process a YouTube video end-to-end and upload to Weaviate.

        Args:
            youtube_url: YouTube video URL
            languages: List of language codes to try (defaults to ['en'])
            output_groups: Whether to save groups to output/groups/ directory

        Returns:
            Dictionary with:
                - segment_count: Number of segments uploaded
                - video_id: Video ID
                - groups: List of SegmentGroup objects (if grouping enabled)
                - group_count: Number of groups created (if grouping enabled)

        Steps:
            1. Fetch transcript from YouTube
            2. Restore punctuation and proper casing
            3. Chunk into semantic segments (3-6 sentences, 600-1600 chars)
            4. Upload to Weaviate with timestamps
            5. Group segments semantically (if enabled)
        """
        print(f"\n{'='*60}")
        print(f"Processing: {youtube_url}")
        print(f"{'='*60}\n")

        # Step 1 & 2 & 3: Fetch, punctuate, and chunk transcript
        print("📥 Step 1-3: Fetching transcript and processing...")
        job = TranscriptJob(
            youtube_url=youtube_url,
            languages=languages,
            output_dir=Path("output/transcripts")  # Save to output/transcripts/
        )

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
        print(f"✓ Uploaded {segment_count} segments to Weaviate")

        result = {
            "segment_count": segment_count,
            "video_id": transcript_result.video_id,
        }

        # Step 5: Group segments (if enabled)
        if self.enable_grouping and self.grouper:
            print("\n🔗 Step 5: Grouping segments semantically...")
            try:
                groups = self.grouper.group_video(transcript_result.video_id)
                result["groups"] = groups
                result["group_count"] = len(groups)

                # Save groups to file if requested
                if output_groups and groups:
                    output_path = Path(
                        f"output/groups/groups_{transcript_result.video_id}.json"
                    )
                    self.grouper.export_groups_to_json(groups, output_path)
                    print(f"✓ Saved {len(groups)} groups to {output_path}")

            except Exception as e:
                print(f"⚠️  Grouping failed: {e}")
                result["groups"] = []
                result["group_count"] = 0

        print(f"\n{'='*60}")
        print(f"✅ SUCCESS! Pipeline complete")
        print(f"{'='*60}")
        print(f"Segments uploaded: {segment_count}")
        if "group_count" in result:
            print(f"Groups created: {result['group_count']}")
        print(f"{'='*60}\n")

        return result

    def process_multiple_videos(self, youtube_urls: list[str]) -> dict[str, dict]:
        """Process multiple YouTube videos.

        Args:
            youtube_urls: List of YouTube video URLs

        Returns:
            Dictionary mapping URLs to result dicts (with segment_count, groups, etc.)
        """
        results = {}

        for i, url in enumerate(youtube_urls, 1):
            print(f"\n🎬 Processing video {i}/{len(youtube_urls)}")
            try:
                result = self.process_video(url)
                results[url] = result
            except Exception as e:
                print(f"❌ Failed to process {url}: {e}")
                results[url] = {"segment_count": 0, "group_count": 0, "error": str(e)}

        # Summary
        print(f"\n{'='*60}")
        print("📊 BATCH PROCESSING SUMMARY")
        print(f"{'='*60}")
        total_segments = 0
        total_groups = 0
        success_count = 0

        for url, result in results.items():
            segment_count = result.get("segment_count", 0)
            group_count = result.get("group_count", 0)

            status = "✓" if segment_count > 0 else "✗"
            print(f"{status} {url}:")
            print(f"   Segments: {segment_count}")
            if "group_count" in result:
                print(f"   Groups: {group_count}")

            total_segments += segment_count
            total_groups += group_count
            if segment_count > 0:
                success_count += 1

        print(f"\nTotal: {success_count}/{len(youtube_urls)} videos processed")
        print(f"Total segments: {total_segments}")
        if self.enable_grouping:
            print(f"Total groups: {total_groups}")
        print(f"{'='*60}\n")

        return results

    def close(self):
        """Clean up resources."""
        self.uploader.close()
        if self.grouper:
            self.grouper.close()


def main():
    """Example usage of the pipeline."""

    # Example 1: Full pipeline with grouping (recommended)
    print("🚀 Initializing full pipeline with grouping...\n")
    pipeline = YouTubeToWeaviatePipeline(
        enable_grouping=True,
        grouping_params={
            "k_neighbors": 8,
            "neighbor_threshold": 0.80,
            "adjacent_threshold": 0.70,
            "temporal_tau": 150.0,
            "max_group_words": 700,
        },
    )

    try:
        # Single video - full processing
        youtube_url = "https://www.youtube.com/watch?v=CUS6ABgI1As"
        result = pipeline.process_video(youtube_url)

        print(f"\n📊 Results:")
        print(f"   Video ID: {result['video_id']}")
        print(f"   Segments: {result['segment_count']}")
        if "group_count" in result:
            print(f"   Groups: {result['group_count']}")

        # Or process multiple videos:
        # video_urls = [
        #     "https://www.youtube.com/watch?v=VIDEO_ID_1",
        #     "https://www.youtube.com/watch?v=VIDEO_ID_2",
        #     "https://www.youtube.com/watch?v=VIDEO_ID_3",
        # ]
        # results = pipeline.process_multiple_videos(video_urls)

    finally:
        pipeline.close()

    # Example 2: Without grouping (faster, if you only need segments)
    # pipeline = YouTubeToWeaviatePipeline(enable_grouping=False)
    # result = pipeline.process_video(youtube_url)
    # pipeline.close()


if __name__ == "__main__":
    main()
