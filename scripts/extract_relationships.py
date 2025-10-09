#!/usr/bin/env python3
"""Extract relationships between concepts within a single video.

Phase 2 of the pipeline identifies typed edges between concepts that were
extracted in Phase 1. The detector can ingest concepts either from the saved
JSON artifacts or directly from Neo4j, then produces intra-group and
inter-group relationships using pattern matching, cue phrases, semantic
similarity, and temporal proximity.

Usage:
    python scripts/extract_relationships.py VIDEO_ID [VIDEO_ID2 ...] [options]

Options:
    --from-json            Load concepts from ``output/concepts`` instead of querying Neo4j
    --concepts-dir PATH    Override directory for concept JSON files (default: output/concepts)
    --save                 Persist relationships to ``output/relationships``
    --output-dir PATH      Override relationships output directory
    --upload               Upload relationships to Neo4j (default when no action flags provided)
    --overwrite            Delete existing relationships for the video before uploading
    --min-confidence VAL   Minimum confidence threshold to keep relationships (default: 0.6)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from dotenv import load_dotenv
from openai import OpenAI

# Add project root so we can import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.concept_models import Concept, ExtractedConcepts  # type: ignore  # noqa: E402
from src.core.neo4j_graph import Neo4jGraph  # type: ignore  # noqa: E402
from src.core.relationship_extractor import RelationshipExtractor  # type: ignore  # noqa: E402
from src.core.relationship_models import ExtractedRelationships  # type: ignore  # noqa: E402
from src.core.relationship_uploader import RelationshipUploader  # type: ignore  # noqa: E402


@dataclass(slots=True)
class ExtractionOutcome:
    """Convenience container for reporting results per video."""

    video_id: str
    relationships: ExtractedRelationships
    saved_path: Optional[Path] = None
    upload_stats: Optional[dict[str, int]] = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 2 relationship extraction for one or more videos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("video_ids", nargs="+", help="One or more video identifiers")
    parser.add_argument(
        "--from-json",
        action="store_true",
        help="Load concepts from JSON files instead of querying Neo4j",
    )
    parser.add_argument(
        "--concepts-dir",
        type=Path,
        default=Path("output/concepts"),
        help="Directory containing concepts_<VIDEO_ID>.json (default: output/concepts)",
    )
    parser.add_argument(
        "--groups-dir",
        type=Path,
        default=Path("output/groups"),
        help="Directory containing groups_<VIDEO_ID>.json for group text fallback (default: output/groups)",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save extracted relationships to output/relationships/relationships_<VIDEO_ID>.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/relationships"),
        help="Directory where relationship JSON files will be written",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload relationships to Neo4j",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Delete existing relationships for the video before uploading",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.6,
        help="Minimum confidence threshold for detected relationships (default: 0.6)",
    )
    return parser.parse_args()


def ensure_actions(args: argparse.Namespace) -> None:
    """Ensure at least one action (save/upload) is requested.

    If no explicit action flag is provided, default to uploading to Neo4j,
    matching the workflow described in the Phase 2 README."""

    if not args.save and not args.upload:
        args.upload = True


def connect_neo4j() -> Neo4jGraph:
    """Create a Neo4j client using environment variables."""

    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE")

    if not all([uri, user, password]):
        raise RuntimeError(
            "Missing environment variables. Set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD."
        )

    graph = Neo4jGraph(uri=uri, user=user, password=password, database=database)
    print("📡 Connected to Neo4j")
    return graph


def load_concepts_from_json(
    video_id: str, concepts_dir: Path
) -> list[ExtractedConcepts]:
    """Load `ExtractedConcepts` objects from the saved JSON artifact for a video."""

    json_path = concepts_dir / f"concepts_{video_id}.json"
    if not json_path.exists():
        raise FileNotFoundError(f"Concepts file not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as fp:
        data = json.load(fp)

    groups_data = data.get("groups", [])
    extracted: list[ExtractedConcepts] = []

    for idx, group in enumerate(groups_data):
        group_id = group.get("group_id") or group.get("groupId") or idx
        group_text = group.get("group_text") or group.get("text", "")
        concepts_payload = group.get("concepts", [])

        concepts: list[Concept] = []
        for concept_data in concepts_payload:
            try:
                concept = Concept(
                    name=concept_data["name"],
                    definition=concept_data.get("definition", ""),
                    type=concept_data.get("type", "Concept"),
                    importance=float(concept_data.get("importance", 0.5)),
                    confidence=float(concept_data.get("confidence", 0.5)),
                    video_id=video_id,
                    group_id=int(group_id),
                    first_mention_time=float(
                        concept_data.get("first_mention_time")
                        or concept_data.get("firstMentionTime")
                        or 0.0
                    ),
                    last_mention_time=float(
                        concept_data.get("last_mention_time")
                        or concept_data.get("lastMentionTime")
                        or 0.0
                    ),
                    mention_count=int(
                        concept_data.get("mention_count")
                        or concept_data.get("mentionCount")
                        or 1
                    ),
                    aliases=concept_data.get("aliases", []),
                )
                concepts.append(concept)
            except Exception as exc:  # ValueError from dataclass validation
                print(
                    f"⚠️  Skipping concept in group {group_id} for video {video_id}: {exc}"
                )

        extracted.append(
            ExtractedConcepts(
                video_id=video_id,
                group_id=int(group_id),
                group_text=group_text,
                concepts=concepts,
            )
        )

    print(
        f"📂 Loaded {len(extracted)} groups from {json_path} (total concepts: {sum(len(g.concepts) for g in extracted)})"
    )
    return extracted


def load_group_texts(video_id: str, groups_dir: Path) -> dict[int, str]:
    """Load group text snippets from the grouping artifact if it exists."""

    json_path = groups_dir / f"groups_{video_id}.json"
    if not json_path.exists():
        return {}

    try:
        with open(json_path, "r", encoding="utf-8") as fp:
            payload = json.load(fp)
    except json.JSONDecodeError as exc:
        print(f"⚠️  Failed to parse groups file {json_path}: {exc}")
        return {}

    groups = payload.get("groups", [])
    group_texts: dict[int, str] = {}
    for idx, group in enumerate(groups):
        group_id = group.get("group_id") or group.get("groupId") or idx
        text = group.get("group_text") or group.get("text") or ""
        try:
            group_texts[int(group_id)] = text
        except (TypeError, ValueError):
            continue

    return group_texts


def load_concepts_from_graph(
    graph: Neo4jGraph, video_id: str, group_texts: Optional[dict[int, str]] = None
) -> list[ExtractedConcepts]:
    """Reconstruct ExtractedConcepts from Neo4j-stored concepts."""

    concepts = graph.get_extracted_concepts(video_id)
    grouped: defaultdict[int, list[Concept]] = defaultdict(list)
    for concept in concepts:
        grouped[int(concept.group_id)].append(concept)

    extracted: list[ExtractedConcepts] = []
    for group_id, group_concepts in sorted(grouped.items()):
        group_text = ""
        if group_texts:
            group_text = group_texts.get(group_id, "")

        extracted.append(
            ExtractedConcepts(
                video_id=video_id,
                group_id=group_id,
                group_text=group_text,
                concepts=group_concepts,
            )
        )

    if not extracted:
        raise ValueError(f"No concepts found in Neo4j for video {video_id}")

    if group_texts and not all(group_texts.get(item.group_id) for item in extracted):
        print(
            "⚠️  Some groups were missing text in the groups JSON; pattern detectors may miss relationships."
        )

    return extracted


def extract_relationships_for_video(
    extractor: RelationshipExtractor,
    video_id: str,
    *,
    concepts: Optional[list[ExtractedConcepts]] = None,
) -> ExtractedRelationships:
    """Run the relationship extractor for a single video."""

    if concepts is not None:
        return extractor.extract_from_video(concepts, video_id)
    return extractor.extract_from_graph(video_id)


def save_relationships(
    extractor: RelationshipExtractor,
    relationships: ExtractedRelationships,
    output_dir: Path,
    video_id: str,
) -> Path:
    """Persist extracted relationships to disk and return the path."""

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"relationships_{video_id}.json"
    extractor.save_to_file(relationships, output_path)
    return output_path


def maybe_upload_relationships(
    uploader: RelationshipUploader,
    relationships: ExtractedRelationships,
    video_id: str,
    overwrite: bool,
) -> dict[str, int]:
    """Upload relationships to Neo4j, optionally overwriting existing data."""

    if overwrite:
        existing = uploader.get_relationship_count(video_id)
        if existing:
            print(f"🗑️  Removing {existing} existing relationships for {video_id}...")
            uploader.delete_relationships_for_video(video_id)

    return uploader.upload_relationships(relationships)


def print_video_header(
    video_id: str, *, source: str, actions: Iterable[str], min_conf: float
) -> None:
    """Pretty informational banner for each video processed."""

    print("\n" + "=" * 70)
    print(f"🔗 Relationship Extraction: {video_id}")
    print("=" * 70)
    print(f"Source: {source}")
    print(f"Min confidence: {min_conf:.2f}")
    if actions:
        print(f"Actions: {', '.join(actions)}")
    print("=" * 70)


def print_summary(outcomes: list[ExtractionOutcome]) -> None:
    """Summarize work across all processed videos."""

    if not outcomes:
        return

    print("\n" + "=" * 70)
    print("📊 RELATIONSHIP EXTRACTION SUMMARY")
    print("=" * 70)

    total_relationships = 0
    for outcome in outcomes:
        rel_count = len(outcome.relationships)
        total_relationships += rel_count

        print(f"\n🎬 Video: {outcome.video_id}")
        print(f"   Relationships extracted: {rel_count}")
        print(f"   Avg confidence: {outcome.relationships.avg_confidence:.2f}")
        if outcome.saved_path:
            print(f"   Saved JSON: {outcome.saved_path}")
        if outcome.upload_stats:
            uploaded = outcome.upload_stats.get("uploaded", 0)
            skipped = outcome.upload_stats.get("skipped", 0)
            failed = outcome.upload_stats.get("failed", 0)
            print(
                f"   Upload → uploaded: {uploaded}, skipped: {skipped}, failed: {failed}"
            )

        type_distribution = outcome.relationships.type_distribution
        if type_distribution:
            print("   Type distribution:")
            for rel_type, count in sorted(
                type_distribution.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"      {rel_type:20s}: {count}")

    print(f"\n✅ Total relationships extracted: {total_relationships}")
    print("=" * 70 + "\n")


def main() -> None:
    load_dotenv()
    args = parse_args()
    ensure_actions(args)

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        sys.exit(1)

    openai_client = OpenAI(api_key=openai_api_key)

    graph: Optional[Neo4jGraph] = None
    relationship_uploader: Optional[RelationshipUploader] = None

    try:
        if not args.from_json or args.upload:
            graph = connect_neo4j()
            if args.upload:
                relationship_uploader = RelationshipUploader(graph)

        extractor = RelationshipExtractor(
            openai_client=openai_client,
            graph=graph,
            min_confidence=args.min_confidence,
        )

        outcomes: list[ExtractionOutcome] = []

        for video_id in args.video_ids:
            actions = []
            if args.save:
                actions.append("save to JSON")
            if args.upload:
                actions.append("upload to Neo4j")

            source = "concept JSON" if args.from_json else "Neo4j + group JSON"
            print_video_header(
                video_id,
                source=source,
                actions=actions,
                min_conf=args.min_confidence,
            )

            try:
                concept_payload = None
                if args.from_json:
                    concept_payload = load_concepts_from_json(
                        video_id, args.concepts_dir
                    )
                else:
                    if not graph:
                        raise RuntimeError("Neo4j graph client not initialized")
                    group_texts = load_group_texts(video_id, args.groups_dir)
                    if group_texts:
                        print(
                            f"📝 Loaded group context for {len(group_texts)} groups from {args.groups_dir}/groups_{video_id}.json"
                        )
                    else:
                        print(
                            "⚠️  No group text found on disk; falling back to Neo4j-only data. Relationships may be sparse."
                        )
                    concept_payload = load_concepts_from_graph(
                        graph, video_id, group_texts
                    )

                relationships = extract_relationships_for_video(
                    extractor,
                    video_id,
                    concepts=concept_payload,
                )

                is_valid, issues = relationships.validate()
                if not is_valid:
                    print("\n⚠️  Validation issues detected:")
                    for issue in issues:
                        print(f"   - {issue}")

                saved_path = None
                upload_stats = None

                if args.save:
                    saved_path = save_relationships(
                        extractor, relationships, args.output_dir, video_id
                    )

                if args.upload:
                    if not relationship_uploader:
                        raise RuntimeError(
                            "Uploader not initialized; check Neo4j connection."
                        )
                    upload_stats = maybe_upload_relationships(
                        relationship_uploader,
                        relationships,
                        video_id,
                        args.overwrite,
                    )

                outcomes.append(
                    ExtractionOutcome(
                        video_id=video_id,
                        relationships=relationships,
                        saved_path=saved_path,
                        upload_stats=upload_stats,
                    )
                )

            except FileNotFoundError as exc:
                print(f"❌ {exc}")
            except Exception as exc:
                print(f"❌ Failed to process {video_id}: {exc}")
                import traceback

                traceback.print_exc()

        print_summary(outcomes)

    finally:
        if graph:
            graph.close()
            print("\n✓ Neo4j connection closed")


if __name__ == "__main__":
    main()
