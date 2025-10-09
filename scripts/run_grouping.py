#!/usr/bin/env python3
"""Quick script to run segment grouping on existing videos."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.segment_grouper import SegmentGrouper


def main():
    """Run grouping on all videos we have transcripts for."""

    # Your video IDs (extracted from Transcripts/ directory)
    video_ids = ["HbDqLPm_2vY", "wLb9g_8r-mE", "zc9ajtpaS6k"]

    # Initialize grouper with TUNED parameters
    print("🚀 Initializing SegmentGrouper with TUNED parameters...\n")
    print("Using optimized hyperparameters for best quality:")
    print("  • neighbor_threshold: 0.80 (stricter neighbor selection)")
    print("  • adjacent_threshold: 0.70 (stricter joining)")
    print("  • max_group_words: 700 (smaller, focused groups)")
    print("  • merge_centroid_threshold: 0.85 (less aggressive merging)\n")

    grouper = SegmentGrouper(
        k_neighbors=8,
        neighbor_threshold=0.80,  # Stricter neighbor selection
        adjacent_threshold=0.70,  # Stricter joining threshold
        temporal_tau=150.0,
        max_group_words=700,  # Smaller, more focused groups
        min_group_segments=2,
        merge_centroid_threshold=0.85,  # Less aggressive merging
    )

    try:
        all_results = []

        for video_id in video_ids:
            print(f"\n{'='*70}")
            print(f"🎬 Processing: {video_id}")
            print(f"{'='*70}\n")

            try:
                # Run grouping pipeline
                groups = grouper.group_video(video_id)

                if groups:
                    # Export to JSON
                    output_path = Path(f"output/groups/groups_{video_id}.json")
                    grouper.export_groups_to_json(groups, output_path)

                    # Store results
                    all_results.append(
                        {
                            "video_id": video_id,
                            "num_groups": len(groups),
                            "output_path": str(output_path),
                            "groups": groups,
                        }
                    )

                    # Print preview
                    print("\n📝 Group Preview:")
                    for i, group in enumerate(groups[:3]):
                        print(f"\n  Group {i}:")
                        print(
                            f"    Time: {group.start_time:.1f}s → {group.end_time:.1f}s ({group.end_time - group.start_time:.1f}s)"
                        )
                        print(f"    Segments: {len(group.segments)}")
                        print(f"    Words: {group.total_words}")
                        print(f"    Cohesion: {group.avg_internal_similarity():.3f}")
                        print(f"    Text: {group.text[:120]}...")

                    if len(groups) > 3:
                        print(f"\n  ... and {len(groups) - 3} more groups")

                else:
                    print(f"⚠️  No groups created for {video_id}")

            except Exception as e:
                print(f"❌ Error processing {video_id}: {e}")
                import traceback

                traceback.print_exc()

        # Final summary
        print(f"\n{'='*70}")
        print("📊 BATCH PROCESSING SUMMARY")
        print(f"{'='*70}")

        for result in all_results:
            print(f"\n✓ {result['video_id']}: {result['num_groups']} groups")
            print(f"  Saved to: {result['output_path']}")

        total_groups = sum(r["num_groups"] for r in all_results)
        print(
            f"\n🎉 Total: {len(all_results)} videos processed, {total_groups} groups created"
        )
        print(f"{'='*70}\n")

    finally:
        grouper.close()


if __name__ == "__main__":
    main()
