"""Visualize concept graph and statistics.

This script provides visualization and analysis of extracted concepts,
showing relationships, distributions, and network structure.

Usage:
    python scripts/visualize_concept_graph.py VIDEO_ID        # Visualize concepts for video
    python scripts/visualize_concept_graph.py --all           # All videos overview
    python scripts/visualize_concept_graph.py --compare V1 V2 # Compare two videos
"""

import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.concept_uploader import ConceptUploader


def draw_ascii_bar_chart(data: dict[str, int], title: str, max_bar_width: int = 50):
    """Draw an ASCII bar chart for the given data."""
    print(f"\n{title}")
    print("=" * 70)

    if not data:
        print("  (no data)")
        return

    max_count = max(data.values())

    for label, count in sorted(data.items(), key=lambda x: x[1], reverse=True):
        # Calculate bar width
        if max_count > 0:
            bar_width = int((count / max_count) * max_bar_width)
        else:
            bar_width = 0

        bar = "█" * bar_width
        print(f"{str(label):20s} {bar} {count}")


def visualize_video_concepts(uploader: ConceptUploader, video_id: str):
    """Visualize concepts for a single video.

    Args:
        uploader: ConceptUploader instance
        video_id: Video identifier
    """
    print(f"\n{'='*70}")
    print(f"📊 Concept Visualization: {video_id}")
    print(f"{'='*70}")

    concepts = uploader.get_concepts_for_video(video_id)

    if not concepts:
        print("\n❌ No concepts found for this video")
        return

    # Basic statistics
    print(f"\n📈 Overview:")
    print(f"   Total concepts: {len(concepts)}")
    print(
        f"   Avg importance: {sum(c['importance'] for c in concepts) / len(concepts):.2f}"
    )
    print(
        f"   Avg confidence: {sum(c['confidence'] for c in concepts) / len(concepts):.2f}"
    )

    # Type distribution
    type_counts = Counter(c["type"] for c in concepts)
    draw_ascii_bar_chart(dict(type_counts), "📊 Concept Types")

    # Importance distribution
    importance_bins = {
        "Critical (0.9-1.0)": sum(1 for c in concepts if c["importance"] >= 0.9),
        "High (0.7-0.9)": sum(1 for c in concepts if 0.7 <= c["importance"] < 0.9),
        "Medium (0.5-0.7)": sum(1 for c in concepts if 0.5 <= c["importance"] < 0.7),
        "Low (0.3-0.5)": sum(1 for c in concepts if 0.3 <= c["importance"] < 0.5),
        "Minimal (<0.3)": sum(1 for c in concepts if c["importance"] < 0.3),
    }
    draw_ascii_bar_chart(importance_bins, "📊 Importance Distribution")

    # Confidence distribution
    confidence_bins = {
        "Very High (0.9-1.0)": sum(1 for c in concepts if c["confidence"] >= 0.9),
        "High (0.8-0.9)": sum(1 for c in concepts if 0.8 <= c["confidence"] < 0.9),
        "Good (0.7-0.8)": sum(1 for c in concepts if 0.7 <= c["confidence"] < 0.8),
        "Medium (0.6-0.7)": sum(1 for c in concepts if 0.6 <= c["confidence"] < 0.7),
        "Low (<0.6)": sum(1 for c in concepts if c["confidence"] < 0.6),
    }
    draw_ascii_bar_chart(confidence_bins, "📊 Confidence Distribution")

    # Temporal distribution (by group)
    group_counts = Counter(c["groupId"] for c in concepts)
    draw_ascii_bar_chart(dict(group_counts), "📊 Concepts per Group")

    # Top concepts
    print("\n🏆 Top 10 Most Important Concepts:")
    print("-" * 70)
    top_concepts = sorted(concepts, key=lambda c: c["importance"], reverse=True)[:10]
    for i, concept in enumerate(top_concepts, 1):
        print(f"\n{i:2d}. {concept['name']} ({concept['type']})")
        print(
            f"    Importance: {concept['importance']:.2f} | Confidence: {concept['confidence']:.2f}"
        )
        print(
            f"    Time: {concept['firstMentionTime']:.1f}s - {concept['lastMentionTime']:.1f}s (Group {concept['groupId']})"
        )
        print(f"    {concept['definition'][:100]}...")

    # Timeline visualization
    print("\n⏱️  Concept Timeline:")
    print("-" * 70)

    # Group concepts by time intervals
    max_time = max(c["lastMentionTime"] for c in concepts)
    num_intervals = 10
    interval_size = max_time / num_intervals

    timeline = defaultdict(list)
    for concept in concepts:
        interval = int(concept["firstMentionTime"] / interval_size)
        timeline[interval].append(concept["name"][:20])

    for i in range(num_intervals):
        start_time = i * interval_size
        end_time = (i + 1) * interval_size
        concepts_in_interval = timeline.get(i, [])

        print(
            f"\n{start_time:6.0f}s - {end_time:6.0f}s ({len(concepts_in_interval)} concepts)"
        )
        if concepts_in_interval:
            for name in concepts_in_interval[:5]:  # Show first 5
                print(f"  • {name}")
            if len(concepts_in_interval) > 5:
                print(f"  ... and {len(concepts_in_interval) - 5} more")

    # Aliases coverage
    concepts_with_aliases = sum(1 for c in concepts if c.get("aliases"))
    print(
        f"\n🏷️  Alias Coverage: {concepts_with_aliases}/{len(concepts)} concepts have aliases ({concepts_with_aliases/len(concepts)*100:.1f}%)"
    )


def visualize_all_videos(uploader: ConceptUploader):
    """Show overview of all videos with concepts.

    Args:
        uploader: ConceptUploader instance
    """
    print("\n" + "=" * 70)
    print("📊 All Videos Overview")
    print("=" * 70)

    stats = uploader.get_statistics()
    total_concepts = stats.get("total_concepts", 0)

    if total_concepts == 0:
        print("\n❌ No concepts found in database")
        return

    print(f"\n📈 Database Statistics:")
    print(f"   Total concepts: {total_concepts}")
    print(f"   Collections: {', '.join(stats.get('collections_available', []))}")

    print("\n💡 Next Steps:")
    print(
        "   • View specific video: python scripts/visualize_concept_graph.py VIDEO_ID"
    )
    print("   • Search concepts: python scripts/query_concepts.py --search 'topic'")
    print(
        "   • Extract relationships: python scripts/extract_relationships.py VIDEO_ID"
    )


def compare_videos(uploader: ConceptUploader, video_id1: str, video_id2: str):
    """Compare concepts between two videos.

    Args:
        uploader: ConceptUploader instance
        video_id1: First video identifier
        video_id2: Second video identifier
    """
    print(f"\n{'='*70}")
    print(f"📊 Comparing Videos: {video_id1} vs {video_id2}")
    print(f"{'='*70}")

    concepts1 = uploader.get_concepts_for_video(video_id1)
    concepts2 = uploader.get_concepts_for_video(video_id2)

    if not concepts1:
        print(f"\n❌ No concepts found for {video_id1}")
        return
    if not concepts2:
        print(f"\n❌ No concepts found for {video_id2}")
        return

    # Basic comparison
    print(f"\n📊 Basic Statistics:")
    print(f"   {video_id1}: {len(concepts1)} concepts")
    print(f"   {video_id2}: {len(concepts2)} concepts")

    # Type comparison
    types1 = Counter(c["type"] for c in concepts1)
    types2 = Counter(c["type"] for c in concepts2)

    all_types = set(types1.keys()) | set(types2.keys())

    print(f"\n📊 Type Distribution Comparison:")
    print(f"{'Type':<20} {video_id1[:10]:>10} {video_id2[:10]:>10}")
    print("-" * 45)
    for ctype in sorted(all_types):
        count1 = types1.get(ctype, 0)
        count2 = types2.get(ctype, 0)
        print(f"{ctype:<20} {count1:>10} {count2:>10}")

    # Find similar concepts (by name similarity)
    names1 = set(c["name"].lower() for c in concepts1)
    names2 = set(c["name"].lower() for c in concepts2)

    common = names1 & names2
    unique1 = names1 - names2
    unique2 = names2 - names1

    print(f"\n🔗 Concept Overlap:")
    print(f"   Common concepts: {len(common)}")
    print(f"   Unique to {video_id1}: {len(unique1)}")
    print(f"   Unique to {video_id2}: {len(unique2)}")

    if common:
        print(f"\n   Common concepts:")
        for name in sorted(common)[:10]:
            print(f"   • {name.title()}")
        if len(common) > 10:
            print(f"   ... and {len(common) - 10} more")


def main():
    """Main entry point for concept graph visualization."""
    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        return

    # Initialize uploader
    try:
        uploader = ConceptUploader()
    except Exception as e:
        print(f"❌ Failed to connect to Weaviate: {e}")
        sys.exit(1)

    try:
        if "--all" in args:
            visualize_all_videos(uploader)

        elif "--compare" in args:
            idx = args.index("--compare")
            if idx + 2 >= len(args):
                print("❌ --compare requires two video IDs")
                sys.exit(1)
            video_id1 = args[idx + 1]
            video_id2 = args[idx + 2]
            compare_videos(uploader, video_id1, video_id2)

        else:
            # Single video visualization
            video_id = args[0]
            visualize_video_concepts(uploader, video_id)

    finally:
        uploader.close()


if __name__ == "__main__":
    main()
