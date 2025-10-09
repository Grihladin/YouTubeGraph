#!/usr/bin/env python3
"""Run grouping with stricter parameters for better cohesion."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.segment_grouper import SegmentGrouper


def main():
    """Run grouping with tuned parameters."""

    video_ids = ["HbDqLPm_2vY", "wLb9g_8r-mE", "zc9ajtpaS6k"]

    print("🔧 Running with TUNED parameters for better cohesion...\n")
    print("Changes from defaults:")
    print("  • neighbor_threshold: 0.75 → 0.80 (stricter neighbor selection)")
    print("  • adjacent_threshold: 0.60 → 0.70 (stricter joining)")
    print("  • max_group_words: 800 → 700 (smaller groups)")
    print("  • merge_centroid_threshold: 0.80 → 0.85 (less aggressive merging)")
    print()

    grouper = SegmentGrouper(
        k_neighbors=8,
        neighbor_threshold=0.80,  # ⬆️ Stricter neighbor selection
        adjacent_threshold=0.70,  # ⬆️ Stricter joining threshold
        temporal_tau=150.0,  # Keep same for now
        max_group_words=700,  # ⬇️ Smaller groups
        min_group_segments=2,
        merge_centroid_threshold=0.85,  # ⬆️ Less aggressive merging
    )

    try:
        for video_id in video_ids:
            print(f"\n{'='*70}")
            print(f"🎬 Processing: {video_id}")
            print(f"{'='*70}\n")

            try:
                groups = grouper.group_video(video_id)

                if groups:
                    # Export with "tuned" prefix
                    output_path = Path(f"output/groups/tuned_{video_id}.json")
                    grouper.export_groups_to_json(groups, output_path)

                    print(f"\n✅ Saved to: {output_path}")

            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback

                traceback.print_exc()

    finally:
        grouper.close()

    print("\n" + "=" * 70)
    print("✅ Tuned grouping complete!")
    print("=" * 70)
    print(
        "\nNext: Run `python scripts/visualize_groups.py 'tuned_*.json'` to compare results"
    )
    print("Look for files starting with 'tuned_' in the output/groups/ directory")


if __name__ == "__main__":
    main()
