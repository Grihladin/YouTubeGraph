"""Extract relationships between concepts (Phase 2 Foundation).

This script analyzes concepts and identifies relationships between them.
Currently provides co-occurrence analysis and similarity-based relationships.

Future phases will add:
- LLM-based relationship extraction
- Cross-video concept linking
- Hierarchical relationship discovery

Usage:
    python scripts/extract_relationships.py VIDEO_ID        # Analyze one video
    python scripts/extract_relationships.py VIDEO_ID1 VIDEO_ID2  # Multiple videos
    python scripts/extract_relationships.py --all           # All videos
"""

import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.concept_uploader import ConceptUploader


def analyze_concept_relationships(uploader: ConceptUploader, video_id: str):
    """Analyze relationships between concepts in a video.

    Args:
        uploader: ConceptUploader instance
        video_id: Video identifier
    """
    print(f"\n{'='*70}")
    print(f"🔗 Relationship Analysis: {video_id}")
    print(f"{'='*70}")

    concepts = uploader.get_concepts_for_video(video_id)

    if not concepts:
        print("\n❌ No concepts found for this video")
        return

    print(f"\n📊 Analyzing {len(concepts)} concepts...")

    # 1. Co-occurrence Analysis (concepts in same group)
    print("\n🔗 Co-occurrence Analysis (Same Group)")
    print("-" * 70)

    # Group concepts by group_id
    groups = defaultdict(list)
    for concept in concepts:
        groups[concept["groupId"]].append(concept)

    cooccurrences = []
    for group_id, group_concepts in groups.items():
        if len(group_concepts) >= 2:
            # All pairs in the group
            for i, c1 in enumerate(group_concepts):
                for c2 in group_concepts[i + 1 :]:
                    cooccurrences.append(
                        {
                            "concept1": c1["name"],
                            "concept2": c2["name"],
                            "group_id": group_id,
                            "relationship": "co-occurs-in-group",
                            "strength": min(c1["importance"], c2["importance"]),
                        }
                    )

    if cooccurrences:
        print(f"\nFound {len(cooccurrences)} co-occurrence relationships")

        # Show top 10 strongest co-occurrences
        cooccurrences.sort(key=lambda x: x["strength"], reverse=True)
        print("\nTop 10 Co-occurrences:")
        for i, rel in enumerate(cooccurrences[:10], 1):
            print(f"\n{i:2d}. {rel['concept1']} ↔ {rel['concept2']}")
            print(f"    Group: {rel['group_id']} | Strength: {rel['strength']:.2f}")
    else:
        print(
            "\nNo co-occurrence relationships found (all groups have single concepts)"
        )

    # 2. Temporal Proximity (concepts in adjacent groups)
    print("\n⏱️  Temporal Proximity Analysis")
    print("-" * 70)

    temporal_rels = []
    sorted_groups = sorted(groups.keys())

    for i in range(len(sorted_groups) - 1):
        curr_group = sorted_groups[i]
        next_group = sorted_groups[i + 1]

        curr_concepts = groups[curr_group]
        next_concepts = groups[next_group]

        # Concepts in adjacent groups likely relate
        for c1 in curr_concepts:
            for c2 in next_concepts:
                temporal_rels.append(
                    {
                        "concept1": c1["name"],
                        "concept2": c2["name"],
                        "groups": f"{curr_group} → {next_group}",
                        "relationship": "temporally-adjacent",
                        "strength": (c1["importance"] + c2["importance"]) / 2,
                    }
                )

    if temporal_rels:
        print(f"\nFound {len(temporal_rels)} temporal proximity relationships")

        temporal_rels.sort(key=lambda x: x["strength"], reverse=True)
        print("\nTop 10 Temporal Relationships:")
        for i, rel in enumerate(temporal_rels[:10], 1):
            print(f"\n{i:2d}. {rel['concept1']} → {rel['concept2']}")
            print(f"    Groups: {rel['groups']} | Strength: {rel['strength']:.2f}")
    else:
        print("\nNo temporal relationships found")

    # 3. Type-based Relationships
    print("\n🏷️  Type-based Relationship Patterns")
    print("-" * 70)

    # Common patterns: Problem → Solution, Method → Technology, etc.
    type_pairs = defaultdict(int)

    for concept in concepts:
        ctype = concept["type"]
        # Count how concepts of different types co-occur
        same_group = groups[concept["groupId"]]
        for other in same_group:
            if other["name"] != concept["name"]:
                pair = tuple(sorted([ctype, other["type"]]))
                type_pairs[pair] += 1

    if type_pairs:
        print("\nMost Common Type Pairings:")
        for i, (pair, count) in enumerate(
            sorted(type_pairs.items(), key=lambda x: x[1], reverse=True)[:10], 1
        ):
            print(f"{i:2d}. {pair[0]} ↔ {pair[1]}: {count} occurrences")
    else:
        print("\nNo type pairings found")

    # 4. Similarity-based (using semantic search)
    print("\n🔍 Semantic Similarity Analysis")
    print("-" * 70)

    print("\nFinding semantically similar concepts...")

    similarity_rels = []

    # For each concept, find similar ones
    for concept in concepts[:10]:  # Limit to first 10 to avoid too many API calls
        similar = uploader.search_concepts(concept["name"], limit=5, min_confidence=0.7)

        for sim_concept in similar:
            # Skip self-matches
            if sim_concept["name"] == concept["name"]:
                continue

            # Only include if from same video
            if sim_concept.get("videoId") == video_id:
                similarity_rels.append(
                    {
                        "concept1": concept["name"],
                        "concept2": sim_concept["name"],
                        "similarity": sim_concept.get("similarity", 0.0),
                        "relationship": "semantically-similar",
                    }
                )

    if similarity_rels:
        # Remove duplicates (A→B and B→A)
        seen = set()
        unique_rels = []
        for rel in similarity_rels:
            pair = tuple(sorted([rel["concept1"], rel["concept2"]]))
            if pair not in seen:
                seen.add(pair)
                unique_rels.append(rel)

        unique_rels.sort(key=lambda x: x["similarity"], reverse=True)

        print(f"\nFound {len(unique_rels)} similarity relationships")
        print("\nTop 10 Semantically Similar Pairs:")
        for i, rel in enumerate(unique_rels[:10], 1):
            print(f"\n{i:2d}. {rel['concept1']} ≈ {rel['concept2']}")
            print(f"    Similarity: {rel['similarity']:.3f}")
    else:
        print("\nNo semantic similarity relationships found")

    # Summary
    print("\n" + "=" * 70)
    print("📊 Relationship Summary")
    print("=" * 70)
    print(f"\nTotal relationships found:")
    print(f"  • Co-occurrence (same group): {len(cooccurrences)}")
    print(f"  • Temporal proximity (adjacent): {len(temporal_rels)}")
    print(f"  • Semantic similarity: {len(similarity_rels)}")
    print(
        f"  • Total: {len(cooccurrences) + len(temporal_rels) + len(similarity_rels)}"
    )

    print("\n💡 Next Steps:")
    print("  • Phase 2: Implement LLM-based relationship extraction")
    print("  • Phase 3: Store relationships in graph database")
    print("  • Phase 4: Enable multi-hop queries and reasoning")


def main():
    """Main entry point for relationship extraction."""
    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        return

    # Parse arguments
    process_all = "--all" in args
    if process_all:
        args = [a for a in args if a != "--all"]

    # Determine video IDs
    if process_all:
        # This would require querying Weaviate for all video IDs
        print("⚠️  --all flag not yet implemented")
        print("   Please specify video IDs explicitly")
        sys.exit(1)

    if not args:
        print("❌ No video IDs specified")
        print(
            "   Usage: python scripts/extract_relationships.py VIDEO_ID [VIDEO_ID2 ...]"
        )
        sys.exit(1)

    video_ids = args

    # Initialize uploader
    try:
        uploader = ConceptUploader()
    except Exception as e:
        print(f"❌ Failed to connect to Weaviate: {e}")
        sys.exit(1)

    try:
        for video_id in video_ids:
            analyze_concept_relationships(uploader, video_id)

            if len(video_ids) > 1:
                print("\n" + "=" * 70 + "\n")

    finally:
        uploader.close()


if __name__ == "__main__":
    main()
