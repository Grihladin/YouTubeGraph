#!/usr/bin/env python3
"""
Comprehensive grouping quality test - combines grouping, visualization, and quality checks.

This is the main test script to validate grouping quality across all videos.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import numpy as np
from src.core.segment_grouper import SegmentGrouper
from src.core.grouping_config import TUNED_PARAMS, print_params


def print_quality_report(groups, video_id: str) -> dict:
    """Print comprehensive quality report and return metrics."""
    if not groups:
        print("❌ No groups to analyze!")
        return {}

    print(f"\n{'='*80}")
    print(f"📊 QUALITY REPORT: {video_id}")
    print(f"{'='*80}\n")

    # Collect metrics
    word_counts = [g.total_words for g in groups]
    cohesions = [g.avg_internal_similarity() for g in groups]
    durations = [g.end_time - g.start_time for g in groups]
    num_segments = [len(g.segments) for g in groups]

    # Basic stats
    print(f"📈 Basic Statistics:")
    print(f"   • Total groups: {len(groups)}")
    print(f"   • Total segments: {sum(num_segments)}")
    print(f"   • Total words: {sum(word_counts):,}")
    print(f"   • Video duration: {groups[-1].end_time / 60:.1f} minutes")

    # Word count analysis
    print(f"\n📊 Word Count Distribution:")
    print(f"   • Min:    {min(word_counts):>6}")
    print(f"   • Max:    {max(word_counts):>6}")
    print(f"   • Mean:   {np.mean(word_counts):>6.0f}")
    print(f"   • Median: {np.median(word_counts):>6.0f}")

    in_range = sum(1 for w in word_counts if 400 <= w <= 800)
    pct_in_range = in_range / len(groups) * 100
    print(f"   • In target range (400-800): {in_range}/{len(groups)} ({pct_in_range:.0f}%)")

    if pct_in_range >= 70:
        print(f"   ✅ PASS: ≥70% groups in target range")
    else:
        print(f"   ⚠️  WARN: <70% groups in target range")

    # Cohesion analysis
    print(f"\n🔗 Cohesion Distribution:")
    avg_cohesion = np.mean(cohesions)
    print(f"   • Min:    {min(cohesions):.3f}")
    print(f"   • Max:    {max(cohesions):.3f}")
    print(f"   • Mean:   {avg_cohesion:.3f}")
    print(f"   • Median: {np.median(cohesions):.3f}")

    high_cohesion = sum(1 for c in cohesions if c >= 0.70)
    pct_high_cohesion = high_cohesion / len(groups) * 100
    print(
        f"   • High cohesion (≥0.70): {high_cohesion}/{len(groups)} ({pct_high_cohesion:.0f}%)"
    )

    if avg_cohesion >= 0.70:
        print(f"   ✅ PASS: Average cohesion ≥ 0.70")
    elif avg_cohesion >= 0.60:
        print(f"   ⚠️  WARN: Cohesion acceptable but could be better")
    else:
        print(f"   ❌ FAIL: Cohesion too low")

    # Duration analysis
    print(f"\n⏱️  Duration Distribution:")
    print(f"   • Min:    {min(durations) / 60:>6.1f} min")
    print(f"   • Max:    {max(durations) / 60:>6.1f} min")
    print(f"   • Mean:   {np.mean(durations) / 60:>6.1f} min")
    print(f"   • Median: {np.median(durations) / 60:>6.1f} min")

    # Segment distribution
    print(f"\n📝 Segments per Group:")
    print(f"   • Min:    {min(num_segments)}")
    print(f"   • Max:    {max(num_segments)}")
    print(f"   • Mean:   {np.mean(num_segments):.1f}")
    print(f"   • Median: {np.median(num_segments):.0f}")

    # Overall quality score
    print(f"\n🎯 Overall Quality Score:")

    score = 0
    max_score = 4

    # Criterion 1: Word count distribution
    if pct_in_range >= 70:
        score += 1
        print(f"   ✅ Word count: GOOD ({pct_in_range:.0f}% in range)")
    else:
        print(f"   ❌ Word count: POOR ({pct_in_range:.0f}% in range)")

    # Criterion 2: Average cohesion
    if avg_cohesion >= 0.70:
        score += 1
        print(f"   ✅ Cohesion: GOOD ({avg_cohesion:.3f})")
    elif avg_cohesion >= 0.60:
        print(f"   ⚠️  Cohesion: ACCEPTABLE ({avg_cohesion:.3f})")
    else:
        print(f"   ❌ Cohesion: POOR ({avg_cohesion:.3f})")

    # Criterion 3: High cohesion percentage
    if pct_high_cohesion >= 60:
        score += 1
        print(f"   ✅ Cohesion distribution: GOOD ({pct_high_cohesion:.0f}% high)")
    else:
        print(f"   ❌ Cohesion distribution: POOR ({pct_high_cohesion:.0f}% high)")

    # Criterion 4: No extreme outliers
    has_extreme = any(w > 1200 or w < 100 for w in word_counts)
    if not has_extreme:
        score += 1
        print(f"   ✅ No extreme outliers")
    else:
        print(f"   ⚠️  Has extreme outliers")

    print(f"\n   📊 Final Score: {score}/{max_score}")

    if score == max_score:
        print(f"   🎉 EXCELLENT! Ready for concept extraction")
    elif score >= 3:
        print(f"   ✅ GOOD! Acceptable for production use")
    elif score >= 2:
        print(f"   ⚠️  ACCEPTABLE but could be improved")
    else:
        print(f"   ❌ POOR - Consider tuning parameters")

    return {
        "video_id": video_id,
        "num_groups": len(groups),
        "avg_cohesion": avg_cohesion,
        "pct_in_word_range": pct_in_range,
        "pct_high_cohesion": pct_high_cohesion,
        "quality_score": score,
        "max_quality_score": max_score,
    }


def print_timeline(groups, width: int = 70):
    """Print ASCII timeline visualization."""
    if not groups:
        return

    print(f"\n{'='*80}")
    print(f"📅 TIMELINE VIEW")
    print(f"{'='*80}\n")

    total_duration = groups[-1].end_time

    print(f"0m {' ' * (width - 6)} {total_duration/60:.1f}m")
    print("│" + "─" * width + "│")

    for group in groups:
        # Calculate position and width
        start_pos = int((group.start_time / total_duration) * width)
        end_pos = int((group.end_time / total_duration) * width)
        group_width = max(1, end_pos - start_pos)

        # Build the bar
        bar = " " * start_pos
        bar += "█" * group_width
        bar += " " * (width - start_pos - group_width)

        # Cohesion indicator
        cohesion = group.avg_internal_similarity()
        if cohesion >= 0.75:
            indicator = "🟢"
        elif cohesion >= 0.60:
            indicator = "🟡"
        else:
            indicator = "🔴"

        print(
            f"│{bar}│ {indicator} G{group.group_id:>2} ({group.total_words:>3}w, {cohesion:.2f})"
        )

    print("│" + "─" * width + "│")
    print(f"\n🟢 High cohesion (≥0.75)  🟡 Medium (≥0.60)  🔴 Low (<0.60)")


def print_sample_groups(groups, num_samples: int = 3):
    """Print sample groups with full text."""
    print(f"\n{'='*80}")
    print(f"📋 SAMPLE GROUPS (First {num_samples})")
    print(f"{'='*80}\n")

    for group in groups[:num_samples]:
        cohesion = group.avg_internal_similarity()

        print(
            f"┏━━ GROUP {group.group_id} ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        print(f"┃")
        print(f"┃ ⏱️  Timeline:")
        print(
            f"┃    {group.start_time:.1f}s → {group.end_time:.1f}s  "
            f"(duration: {(group.end_time - group.start_time):.1f}s)"
        )
        print(f"┃")
        print(f"┃ 📊 Statistics:")
        print(f"┃    Segments:  {len(group.segments)}")
        print(f"┃    Words:     {group.total_words}")
        print(f"┃    Cohesion:  {cohesion:.3f}")
        print(f"┃")
        print(f"┃ 📄 Text:")
        print(f"┃    ┌─────────────────────────────────────────────────────────┐")

        # Wrap text properly - max line width is 57 chars to fit in box
        MAX_WIDTH = 57
        words = group.text.split()
        current_line = ""
        
        for word in words:
            # Check if adding this word would exceed width
            test_line = current_line + (" " if current_line else "") + word
            
            if len(test_line) <= MAX_WIDTH:
                current_line = test_line
            else:
                # Print current line and start new one
                if current_line:
                    print(f"┃    │ {current_line:<57} │")
                current_line = word
        
        # Print last line
        if current_line:
            print(f"┃    │ {current_line:<57} │")

        print(f"┃    └─────────────────────────────────────────────────────────┘")
        print(
            f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )


def test_single_video(video_id: str, grouper: SegmentGrouper) -> dict:
    """Test grouping on a single video."""
    print(f"\n{'#'*80}")
    print(f"# TESTING VIDEO: {video_id}")
    print(f"{'#'*80}")

    try:
        # Run grouping
        groups = grouper.group_video(video_id)

        if not groups:
            print(f"\n❌ No groups created for {video_id}")
            return {"video_id": video_id, "success": False}

        # Save results
        output_path = Path(f"output/groups/quality_test_{video_id}.json")
        grouper.export_groups_to_json(groups, output_path)
        print(f"\n✅ Saved to: {output_path}")

        # Run analyses
        print_timeline(groups)
        metrics = print_quality_report(groups, video_id)
        print_sample_groups(groups, num_samples=3)

        metrics["success"] = True
        return metrics

    except Exception as e:
        print(f"\n❌ ERROR processing {video_id}: {e}")
        import traceback

        traceback.print_exc()
        return {"video_id": video_id, "success": False, "error": str(e)}


def main():
    """Run comprehensive quality tests."""
    print("\n" + "=" * 80)
    print("🧪 COMPREHENSIVE GROUPING QUALITY TEST")
    print("=" * 80)
    print_params(TUNED_PARAMS)

    # Get video IDs from command line or use defaults
    if len(sys.argv) > 1:
        video_ids = sys.argv[1:]
    else:
        # Default test videos (educational content only, no interviews)
        video_ids = ["HbDqLPm_2vY", "zc9ajtpaS6k", "51EQf_Bz5ew"]
        print(f"Testing default videos: {', '.join(video_ids)}")
        print("(Use: python test_groups_quality.py VIDEO_ID1 VIDEO_ID2 ...)\n")

    # Initialize grouper with tuned parameters
    grouper = SegmentGrouper(**TUNED_PARAMS)

    results = []

    try:
        for video_id in video_ids:
            result = test_single_video(video_id, grouper)
            results.append(result)

        # Print summary
        print(f"\n{'='*80}")
        print(f"📊 SUMMARY - ALL VIDEOS")
        print(f"{'='*80}\n")

        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]

        print(f"✅ Successful: {len(successful)}/{len(results)}")
        if failed:
            print(f"❌ Failed: {len(failed)}/{len(results)}")
            for r in failed:
                print(f"   • {r['video_id']}: {r.get('error', 'Unknown error')}")

        if successful:
            print(f"\n📈 Quality Scores:")
            for r in successful:
                score = r.get("quality_score", 0)
                max_score = r.get("max_quality_score", 4)
                pct = score / max_score * 100

                if score == max_score:
                    emoji = "🎉"
                elif score >= 3:
                    emoji = "✅"
                elif score >= 2:
                    emoji = "⚠️"
                else:
                    emoji = "❌"

                print(
                    f"   {emoji} {r['video_id']}: {score}/{max_score} ({pct:.0f}%) - "
                    f"cohesion={r.get('avg_cohesion', 0):.3f}, "
                    f"groups={r.get('num_groups', 0)}"
                )

            avg_cohesion = np.mean([r["avg_cohesion"] for r in successful])
            avg_score = np.mean([r["quality_score"] for r in successful])
            avg_pct = avg_score / 4 * 100

            print(f"\n🎯 Overall Performance:")
            print(f"   • Average cohesion: {avg_cohesion:.3f}")
            print(f"   • Average quality score: {avg_score:.1f}/4 ({avg_pct:.0f}%)")

            if avg_pct >= 75:
                print(f"   🎉 EXCELLENT! System performing great!")
            elif avg_pct >= 60:
                print(f"   ✅ GOOD! Ready for production use")
            else:
                print(f"   ⚠️  ACCEPTABLE but room for improvement")

        print(f"\n{'='*80}")
        print(f"✅ Testing complete!")
        print(f"{'='*80}")
        print(f"\nOutput files saved to: output/groups/quality_test_*.json")
        print(f"\nNext steps:")
        print(f"  1. Review the quality reports above")
        print(f"  2. If scores are good, proceed with concept extraction")
        print(f"  3. If scores are low, consider:")
        print(f"     - Checking video content type (interviews don't work well)")
        print(f"     - Running: python scripts/diagnose_embeddings.py VIDEO_ID")
        print(f"     - Adjusting TUNED_PARAMS in this script")

    finally:
        grouper.close()


if __name__ == "__main__":
    main()
