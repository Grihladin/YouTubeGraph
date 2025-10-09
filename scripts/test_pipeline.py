#!/usr/bin/env python3
"""
Quick test script for the pipeline.

This script tests the service-oriented architecture.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.pipeline import YouTubeGraphPipeline


def test_pipeline():
    """Test the new pipeline with a sample video."""
    print("🧪 Testing refactored pipeline...")
    print("=" * 60)

    # Initialize pipeline
    pipeline = YouTubeGraphPipeline()

    try:
        # Test with a short video
        test_url = "https://www.youtube.com/watch?v=3T9hNqr-Aic"

        print(f"\n📹 Processing test video: {test_url}")
        print("This may take a few minutes...\n")

        result = pipeline.process_video(test_url)

        # Display results
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS")
        print("=" * 60)

        if result.success:
            print("✅ Status: SUCCESS")
            print(f"📹 Video ID: {result.video_id}")
            print(f"📝 Segments: {result.segment_count}")
            print(f"🔗 Groups: {result.group_count}")
            print(f"🧠 Concepts: {result.concept_count}")
            print(f"🔗 Relationships: {result.relationship_count}")
        else:
            print("❌ Status: FAILED")
            print(f"Error: {result.error}")

        print("=" * 60)

        return result.success

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        pipeline.close()


if __name__ == "__main__":
    success = test_pipeline()
    sys.exit(0 if success else 1)
