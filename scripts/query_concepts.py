"""Query and analyze extracted concepts in Weaviate.

This script provides utilities for exploring, searching, and validating
concepts extracted from video transcripts.

Usage:
    python scripts/query_concepts.py VIDEO_ID              # Show all concepts for video
    python scripts/query_concepts.py --search "query"      # Semantic search
    python scripts/query_concepts.py --stats               # Show statistics
    python scripts/query_concepts.py --quality VIDEO_ID    # Quality analysis
"""

import sys
from collections import Counter
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.concept_uploader import ConceptUploader


def show_concepts_for_video(uploader: ConceptUploader, video_id: str):
    """Display all concepts for a specific video.

    Args:
        uploader: ConceptUploader instance
        video_id: Video identifier
    """
    print(f"\n📹 Concepts for video: {video_id}\n")

    concepts = uploader.get_concepts_for_video(video_id)

    if not concepts:
        print("   No concepts found")
        return

    # Sort by importance
    concepts.sort(key=lambda c: c["importance"], reverse=True)

    print(f"Found {len(concepts)} concepts:\n")

    for i, concept in enumerate(concepts, 1):
        print(f"{i}. {concept['name']} ({concept['type']})")
        print(
            f"   Importance: {concept['importance']:.2f} | Confidence: {concept['confidence']:.2f}"
        )
        print(
            f"   Time: {concept['firstMentionTime']:.1f}s - {concept['lastMentionTime']:.1f}s"
        )
        print(f"   Definition: {concept['definition'][:100]}...")

        if concept.get("aliases"):
            print(f"   Aliases: {', '.join(concept['aliases'])}")

        print()


def semantic_search(uploader: ConceptUploader, query: str, limit: int = 10):
    """Perform semantic search for concepts.

    Args:
        uploader: ConceptUploader instance
        query: Search query
        limit: Maximum number of results
    """
    print(f"\n🔍 Searching for: '{query}'\n")

    results = uploader.search_concepts(query, limit=limit)

    if not results:
        print("   No results found")
        return

    print(f"Found {len(results)} matching concepts:\n")

    for i, concept in enumerate(results, 1):
        print(f"{i}. {concept['name']} ({concept['type']})")
        print(
            f"   Similarity: {concept['similarity']:.3f} | Importance: {concept['importance']:.2f}"
        )
        print(f"   Video: {concept['videoId']} | Group: {concept['groupId']}")
        print(f"   Definition: {concept['definition'][:100]}...")
        print()


def show_statistics(uploader: ConceptUploader):
    """Display overall concept statistics.

    Args:
        uploader: ConceptUploader instance
    """
    print("\n📊 Concept Database Statistics\n")

    stats = uploader.get_statistics()

    print(f"Total concepts: {stats.get('total_concepts', 'N/A')}")
    print(f"Collections: {', '.join(stats.get('collections_available', []))}")

    print("\n✅ Database is accessible")


def analyze_quality(uploader: ConceptUploader, video_id: str):
    """Analyze concept extraction quality for a video.

    Args:
        uploader: ConceptUploader instance
        video_id: Video identifier
    """
    print(f"\n🔬 Quality Analysis for video: {video_id}\n")

    concepts = uploader.get_concepts_for_video(video_id)

    if not concepts:
        print("   No concepts found")
        return

    # Calculate metrics
    total = len(concepts)
    avg_importance = sum(c["importance"] for c in concepts) / total
    avg_confidence = sum(c["confidence"] for c in concepts) / total

    # Type distribution
    type_counts = Counter(c["type"] for c in concepts)

    # Confidence distribution
    high_conf = sum(1 for c in concepts if c["confidence"] >= 0.8)
    med_conf = sum(1 for c in concepts if 0.6 <= c["confidence"] < 0.8)
    low_conf = sum(1 for c in concepts if c["confidence"] < 0.6)

    # Importance distribution
    high_imp = sum(1 for c in concepts if c["importance"] >= 0.7)
    med_imp = sum(1 for c in concepts if 0.4 <= c["importance"] < 0.7)
    low_imp = sum(1 for c in concepts if c["importance"] < 0.4)

    # Check for duplicates/near-duplicates
    names = [c["name"].lower() for c in concepts]
    duplicates = [name for name in set(names) if names.count(name) > 1]

    # Print results
    print("Overall Metrics:")
    print(f"  Total concepts: {total}")
    print(f"  Average importance: {avg_importance:.2f}")
    print(f"  Average confidence: {avg_confidence:.2f}")

    print("\nType Distribution:")
    for concept_type, count in type_counts.most_common():
        pct = (count / total) * 100
        print(f"  {concept_type}: {count} ({pct:.1f}%)")

    print("\nConfidence Distribution:")
    print(f"  High (≥0.8): {high_conf} ({high_conf/total*100:.1f}%)")
    print(f"  Medium (0.6-0.8): {med_conf} ({med_conf/total*100:.1f}%)")
    print(f"  Low (<0.6): {low_conf} ({low_conf/total*100:.1f}%)")

    print("\nImportance Distribution:")
    print(f"  High (≥0.7): {high_imp} ({high_imp/total*100:.1f}%)")
    print(f"  Medium (0.4-0.7): {med_imp} ({med_imp/total*100:.1f}%)")
    print(f"  Low (<0.4): {low_imp} ({low_imp/total*100:.1f}%)")

    # Quality assessment
    print("\nQuality Assessment:")

    issues = []
    warnings = []

    if avg_confidence < 0.7:
        issues.append(f"Low average confidence ({avg_confidence:.2f})")
    elif avg_confidence < 0.75:
        warnings.append(f"Borderline average confidence ({avg_confidence:.2f})")

    if len(type_counts) < 3:
        warnings.append(f"Low type diversity ({len(type_counts)} types)")

    if duplicates:
        issues.append(f"Duplicate concept names: {', '.join(duplicates[:3])}")

    if low_conf > total * 0.2:
        warnings.append(
            f"High proportion of low-confidence concepts ({low_conf/total*100:.1f}%)"
        )

    if issues:
        print("  ❌ Issues detected:")
        for issue in issues:
            print(f"     - {issue}")

    if warnings:
        print("  ⚠️  Warnings:")
        for warning in warnings:
            print(f"     - {warning}")

    if not issues and not warnings:
        print("  ✅ Quality looks good!")

    # Top concepts
    print("\nTop 5 Most Important Concepts:")
    top_concepts = sorted(concepts, key=lambda c: c["importance"], reverse=True)[:5]
    for i, concept in enumerate(top_concepts, 1):
        print(f"  {i}. {concept['name']} ({concept['importance']:.2f})")


def main():
    """Main entry point for concept querying."""
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
        # Parse command
        if "--stats" in args:
            show_statistics(uploader)

        elif "--search" in args:
            idx = args.index("--search")
            if idx + 1 >= len(args):
                print("❌ --search requires a query argument")
                sys.exit(1)
            query = args[idx + 1]
            limit = 10
            if "--limit" in args:
                limit_idx = args.index("--limit")
                if limit_idx + 1 < len(args):
                    limit = int(args[limit_idx + 1])
            semantic_search(uploader, query, limit)

        elif "--quality" in args:
            idx = args.index("--quality")
            if idx + 1 >= len(args):
                print("❌ --quality requires a video ID argument")
                sys.exit(1)
            video_id = args[idx + 1]
            analyze_quality(uploader, video_id)

        else:
            # Assume first arg is video ID
            video_id = args[0]
            show_concepts_for_video(uploader, video_id)

    finally:
        uploader.close()


if __name__ == "__main__":
    main()
