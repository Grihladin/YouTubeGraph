#!/usr/bin/env python3
"""Test segment grouping on a single video with detailed output."""

import sys
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.segment_grouper import SegmentGrouper


def test_single_video(video_id: str, verbose: bool = True):
    """Test grouping on a single video with detailed diagnostics.

    Args:
        video_id: YouTube video ID to process
        verbose: Whether to print detailed segment information
    """

    print(f"\n{'='*80}")
    print(f"🧪 TESTING SEGMENT GROUPING")
    print(f"{'='*80}\n")
    print(f"Video ID: {video_id}")
    print(f"Verbose mode: {verbose}\n")

    # Initialize with TUNED parameters for best quality
    print("🔧 Using TUNED parameters:")
    print("  • neighbor_threshold: 0.80")
    print("  • adjacent_threshold: 0.70")
    print("  • max_group_words: 700")
    print("  • merge_centroid_threshold: 0.85\n")

    grouper = SegmentGrouper(
        k_neighbors=8,
        neighbor_threshold=0.80,
        adjacent_threshold=0.70,
        temporal_tau=150.0,
        max_group_words=700,
        min_group_segments=2,
        merge_centroid_threshold=0.85,
    )

    try:
        # Run the grouping pipeline
        groups = grouper.group_video(video_id)

        if not groups:
            print("\n❌ No groups were created!")
            print("Possible issues:")
            print("  • Video not found in Weaviate")
            print("  • No segments with embeddings")
            print("  • Incorrect video_id format")
            return False

        # Export results
        output_path = Path(f"output/groups/test_{video_id}.json")
        grouper.export_groups_to_json(groups, output_path)

        # Print sample groups with full details
        print(f"\n{'='*80}")
        print(f"📋 DETAILED GROUP SAMPLES (First 3 groups)")
        print(f"{'='*80}\n")

        for i, group in enumerate(groups[:3]):
            print(
                f"┏━━ GROUP {group.group_id} ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            print(f"┃")
            print(f"┃ ⏱️  Timeline:")
            print(
                f"┃    Start:    {group.start_time:>7.1f}s  ({group.start_time/60:>6.2f} min)"
            )
            print(
                f"┃    End:      {group.end_time:>7.1f}s  ({group.end_time/60:>6.2f} min)"
            )
            print(
                f"┃    Duration: {group.end_time - group.start_time:>7.1f}s  ({(group.end_time - group.start_time)/60:>6.2f} min)"
            )
            print(f"┃")
            print(f"┃ 📊 Statistics:")
            print(f"┃    Segments:  {len(group.segments)}")
            print(f"┃    Words:     {group.total_words}")
            print(f"┃    Cohesion:  {group.avg_internal_similarity():.3f}")
            print(f"┃")

            if verbose:
                print(f"┃ 📝 Segments in this group:")
                for seg in group.segments:
                    print(
                        f"┃    • Segment {seg.index}: {seg.start_time:.1f}s → {seg.end_time:.1f}s "
                        f"({seg.word_count} words)"
                    )
                print(f"┃")

            print(f"┃ 📄 Full Text:")
            print(
                f"┃    ┌─────────────────────────────────────────────────────────────────────┐"
            )

            # Wrap text at ~70 chars
            words = group.text.split()
            line = "    "
            for word in words:
                if len(line) + len(word) + 1 > 74:
                    print(f"┃    │ {line:<70} │")
                    line = "    " + word
                else:
                    line += (" " if line != "    " else "") + word

            if line.strip():
                print(f"┃    │ {line:<70} │")

            print(
                f"┃    └─────────────────────────────────────────────────────────────────────┘"
            )
            print(
                f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )

        if len(groups) > 3:
            print(
                f"... and {len(groups) - 3} more groups (see {output_path} for full details)\n"
            )

        # Quality checks
        print(f"\n{'='*80}")
        print(f"✅ QUALITY CHECKS")
        print(f"{'='*80}\n")

        word_counts = [g.total_words for g in groups]
        cohesions = [g.avg_internal_similarity() for g in groups]

        # Check word counts
        in_range = sum(1 for w in word_counts if 400 <= w <= 800)
        print(f"📊 Word Count:")
        print(
            f"   • In target range (400-800): {in_range}/{len(groups)} ({in_range/len(groups)*100:.0f}%)"
        )
        print(f"   • Mean: {sum(word_counts)/len(word_counts):.0f}")
        print(f"   • Min/Max: {min(word_counts)}/{max(word_counts)}")

        if in_range / len(groups) >= 0.7:
            print(f"   ✅ PASS: ≥70% groups in target range")
        else:
            print(f"   ⚠️  WARN: <70% groups in target range (consider tuning)")

        # Check cohesion
        print(f"\n🔗 Cohesion:")
        avg_cohesion = sum(cohesions) / len(cohesions)
        print(f"   • Average: {avg_cohesion:.3f}")
        print(f"   • Min/Max: {min(cohesions):.3f}/{max(cohesions):.3f}")

        if avg_cohesion >= 0.70:
            print(f"   ✅ PASS: Average cohesion ≥ 0.70")
        elif avg_cohesion >= 0.60:
            print(f"   ⚠️  WARN: Cohesion acceptable but could be better")
        else:
            print(f"   ❌ FAIL: Cohesion too low (consider stricter thresholds)")

        # Coverage
        total_segments = sum(len(g.segments) for g in groups)
        print(f"\n📈 Coverage:")
        print(f"   • Total segments grouped: {total_segments}")
        print(f"   ✅ All segments assigned to groups")

        print(f"\n{'='*80}")
        print(f"✅ SUCCESS! Grouping completed.")
        print(f"{'='*80}\n")
        print(f"Output saved to: {output_path}")
        print(f"\nNext steps:")
        print(f"  1. Review the output visually")
        print(f"  2. Run: python visualize_groups.py")
        print(f"  3. If quality is good, proceed with idea extraction")
        print(f"  4. If not, tune hyperparameters (see README_GROUPING.md)")

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        grouper.close()


def main():
    """CLI entry point."""

    if len(sys.argv) < 2:
        print("Usage: python test_grouping.py <video_id> [--verbose]")
        print("\nExample:")
        print("  python test_grouping.py HbDqLPm_2vY")
        print("  python test_grouping.py HbDqLPm_2vY --verbose")
        print("\nAvailable videos:")
        print("  • HbDqLPm_2vY")
        print("  • wLb9g_8r-mE")
        print("  • zc9ajtpaS6k")
        sys.exit(1)

    video_id = sys.argv[1]
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    success = test_single_video(video_id, verbose=verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
