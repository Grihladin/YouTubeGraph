"""Extract concepts from video groups and upload to Weaviate.

This script processes JSON files containing grouped segments and extracts
key concepts using an LLM, then uploads them to Weaviate for graph construction.

Usage:
    python scripts/extract_concepts.py VIDEO_ID [VIDEO_ID2 ...]
    python scripts/extract_concepts.py --all          # Process all group files
    python scripts/extract_concepts.py --re-extract VIDEO_ID  # Force re-extraction
"""

import json
import sys
import time
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.concept_extractor import ConceptExtractor, ExtractionError
from core.concept_uploader import ConceptUploader
from core.concept_models import ExtractedConcepts


def load_groups_file(video_id: str, groups_dir: Path) -> Optional[dict]:
    """Load groups JSON file for a video.

    Args:
        video_id: Video identifier
        groups_dir: Directory containing group files

    Returns:
        Parsed JSON data or None if file not found
    """
    group_file = groups_dir / f"groups_{video_id}.json"

    if not group_file.exists():
        print(f"❌ Groups file not found: {group_file}")
        return None

    try:
        with open(group_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Failed to load {group_file}: {e}")
        return None


def extract_concepts_from_video(
    video_id: str,
    groups_data: dict,
    extractor: ConceptExtractor,
    uploader: ConceptUploader,
    force_reextract: bool = False,
) -> dict[str, any]:
    """Extract concepts from all groups in a video.

    Args:
        video_id: Video identifier
        groups_data: Parsed groups JSON
        extractor: ConceptExtractor instance
        uploader: ConceptUploader instance
        force_reextract: If True, delete existing concepts before extracting

    Returns:
        Dictionary with extraction statistics
    """
    stats = {
        "video_id": video_id,
        "groups_processed": 0,
        "groups_failed": 0,
        "concepts_extracted": 0,
        "concepts_uploaded": 0,
        "concepts_failed": 0,
        "avg_importance": 0.0,
        "avg_confidence": 0.0,
        "extraction_time": 0.0,
    }

    # Check if we should re-extract
    if force_reextract:
        print(f"🗑️  Deleting existing concepts for {video_id}...")
        uploader.delete_concepts_for_video(video_id)
    else:
        # Check if concepts already exist
        existing = uploader.get_concepts_for_video(video_id)
        if existing:
            print(f"⚠️  {len(existing)} concepts already exist for {video_id}")
            print(f"   Use --re-extract to force re-extraction")
            return stats

    groups = groups_data.get("groups", [])
    if not groups:
        print(f"❌ No groups found in data for {video_id}")
        return stats

    print(f"\n📹 Processing video: {video_id}")
    print(f"   Groups to process: {len(groups)}")

    all_extracted_concepts = []
    importance_scores = []
    confidence_scores = []

    start_time = time.time()

    # Process each group
    for i, group in enumerate(groups):
        group_id = group.get("group_id", i)
        group_text = group.get("text", "")
        start_time_s = group.get("start_time", 0.0)
        end_time_s = group.get("end_time", 0.0)

        if not group_text:
            print(f"  ⚠️  Group {group_id}: No text, skipping")
            stats["groups_failed"] += 1
            continue

        try:
            # Extract concepts
            print(
                f"  📝 Group {group_id} ({start_time_s:.1f}s - {end_time_s:.1f}s)...",
                end=" ",
            )

            extracted = extractor.extract_from_group(
                video_id=video_id,
                group_id=group_id,
                group_text=group_text,
                start_time=start_time_s,
                end_time=end_time_s,
            )

            # Validate
            is_valid, issues = extracted.validate()
            if not is_valid:
                print(f"\n    ⚠️  Validation warnings:")
                for issue in issues:
                    print(f"       - {issue}")

            # Collect stats
            all_extracted_concepts.append(extracted)
            importance_scores.extend([c.importance for c in extracted.concepts])
            confidence_scores.extend([c.confidence for c in extracted.concepts])

            print(f"✓ {len(extracted.concepts)} concepts")
            stats["groups_processed"] += 1
            stats["concepts_extracted"] += len(extracted.concepts)

            # Upload to Weaviate
            upload_stats = uploader.upload_extracted_concepts(extracted)
            stats["concepts_uploaded"] += upload_stats["concepts_success"]
            stats["concepts_failed"] += upload_stats["concepts_failed"]

            # Brief pause to avoid rate limiting
            time.sleep(0.5)

        except ExtractionError as e:
            print(f"❌ Failed: {e}")
            stats["groups_failed"] += 1
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            stats["groups_failed"] += 1

    # Calculate summary statistics
    stats["extraction_time"] = time.time() - start_time

    if importance_scores:
        stats["avg_importance"] = sum(importance_scores) / len(importance_scores)
    if confidence_scores:
        stats["avg_confidence"] = sum(confidence_scores) / len(confidence_scores)

    return stats


def print_summary(all_stats: list[dict]):
    """Print summary statistics for all processed videos.

    Args:
        all_stats: List of statistics dictionaries
    """
    print("\n" + "=" * 60)
    print("📊 EXTRACTION SUMMARY")
    print("=" * 60)

    total_videos = len(all_stats)
    total_groups = sum(s["groups_processed"] for s in all_stats)
    total_concepts = sum(s["concepts_extracted"] for s in all_stats)
    total_uploaded = sum(s["concepts_uploaded"] for s in all_stats)
    total_failed = sum(s["concepts_failed"] for s in all_stats)
    total_time = sum(s["extraction_time"] for s in all_stats)

    print(f"\nVideos processed: {total_videos}")
    print(f"Groups processed: {total_groups}")
    print(f"Concepts extracted: {total_concepts}")
    print(f"Concepts uploaded: {total_uploaded}")
    print(f"Concepts failed: {total_failed}")
    print(f"Total time: {total_time:.1f}s")

    if total_groups > 0:
        print(f"\nAverage concepts per group: {total_concepts / total_groups:.1f}")

    if all_stats:
        avg_importance = sum(s["avg_importance"] for s in all_stats) / len(all_stats)
        avg_confidence = sum(s["avg_confidence"] for s in all_stats) / len(all_stats)
        print(f"Average importance: {avg_importance:.2f}")
        print(f"Average confidence: {avg_confidence:.2f}")

    print("\n✅ Extraction complete!")
    print("\nNext steps:")
    print("  1. Query concepts: python scripts/query_concepts.py")
    print("  2. Visualize graph: python scripts/visualize_concept_graph.py")
    print("  3. Extract relationships: python scripts/extract_relationships.py")


def main():
    """Main entry point for concept extraction."""
    print("🚀 Concept Extraction Pipeline\n")

    # Parse command line arguments
    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        return

    force_reextract = "--re-extract" in args or "-f" in args
    if force_reextract:
        args = [a for a in args if a not in ["--re-extract", "-f"]]

    process_all = "--all" in args
    if process_all:
        args = [a for a in args if a != "--all"]

    # Determine which videos to process
    groups_dir = Path("output/groups")

    if not groups_dir.exists():
        print(f"❌ Groups directory not found: {groups_dir}")
        print("   Run segment grouping first: python scripts/run_grouping.py")
        sys.exit(1)

    if process_all:
        # Find all group files
        group_files = list(groups_dir.glob("groups_*.json"))
        video_ids = [f.stem.replace("groups_", "") for f in group_files]
        print(f"📂 Found {len(video_ids)} videos with groups")
    elif args:
        video_ids = args
    else:
        print("❌ No video IDs specified")
        print("   Usage: python scripts/extract_concepts.py VIDEO_ID [VIDEO_ID2 ...]")
        print("   Or: python scripts/extract_concepts.py --all")
        sys.exit(1)

    if not video_ids:
        print("❌ No videos to process")
        sys.exit(1)

    print(f"Videos to process: {len(video_ids)}")
    if force_reextract:
        print("⚠️  Force re-extract mode enabled")
    print()

    # Initialize extractor and uploader
    try:
        extractor = ConceptExtractor()
        uploader = ConceptUploader()
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        print("\nCheck that your .env file contains:")
        print("  - OPENAI_API_KEY")
        print("  - WEAVIATE_URL")
        print("  - WEAVIATE_API_KEY")
        sys.exit(1)

    # Process each video
    all_stats = []

    try:
        for video_id in video_ids:
            # Load groups data
            groups_data = load_groups_file(video_id, groups_dir)
            if not groups_data:
                continue

            # Extract and upload concepts
            stats = extract_concepts_from_video(
                video_id=video_id,
                groups_data=groups_data,
                extractor=extractor,
                uploader=uploader,
                force_reextract=force_reextract,
            )

            all_stats.append(stats)

        # Print summary
        if all_stats:
            print_summary(all_stats)

    finally:
        uploader.close()


if __name__ == "__main__":
    main()
