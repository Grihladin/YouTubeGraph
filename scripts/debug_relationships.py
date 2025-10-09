#!/usr/bin/env python3
"""Debug script to check why relationships aren't being found."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import AppConfig
from src.infrastructure.neo4j_client import Neo4jClient
from src.services.grouping.grouping_service import GroupingService
from src.infrastructure.weaviate_client import WeaviateClient
from src.services.concepts.concept_repository import ConceptRepository
import json


def main():
    """Check extracted concepts and groups."""
    config = AppConfig.from_env()

    # Video ID to check
    video_id = "3T9hNqr-Aic"  # Testing with this video

    print(f"🔍 Debugging relationship extraction for video: {video_id}")
    print("=" * 60)

    # Load groups from JSON
    groups_file = config.pipeline.groups_dir / f"groups_{video_id}.json"
    if not groups_file.exists():
        print(f"❌ Groups file not found: {groups_file}")
        return

    with open(groups_file) as f:
        groups_data = json.load(f)

    print(f"\n📁 Groups loaded from JSON:")
    print(f"  Number of groups: {len(groups_data['groups'])}")
    for group in groups_data["groups"]:
        print(
            f"  Group {group['group_id']}: {group['num_segments']} segments, {group['total_words']} words"
        )
        print(f"    Text length: {len(group['text'])} chars")
        print(f"    First 100 chars: {group['text'][:100]}...")

    # Check Neo4j for concepts
    print(f"\n📊 Checking Neo4j for concepts...")
    neo4j_client = Neo4jClient(config.neo4j)
    neo4j_client.connect()

    try:
        repo = ConceptRepository(neo4j_client)
        concepts = repo.get_by_video(video_id)

        if not concepts:
            print(f"❌ No concepts found in Neo4j for video {video_id}")
            print("Run pipeline to extract concepts first!")
            return

        print(f"✓ Found {len(concepts)} concepts in Neo4j")

        # Group concepts by group_id
        from collections import defaultdict

        grouped = defaultdict(list)
        for concept in concepts:
            group_id = concept.get("groupId", 0)
            grouped[group_id].append(concept)

        print(f"\n📊 Concepts by group:")
        for group_id in sorted(grouped.keys()):
            concepts_in_group = grouped[group_id]
            print(f"  Group {group_id}: {len(concepts_in_group)} concepts")
            for concept in concepts_in_group[:3]:  # Show first 3
                print(f"    - {concept['name']}")

        # Now reconstruct ExtractedConcepts
        print(f"\n🔧 Testing reconstruction...")
        from src.domain.group import SegmentGroup, SegmentNode
        from src.domain.concept import ExtractedConcepts, Concept

        # Create minimal SegmentGroup objects
        groups = []
        for group_data in groups_data["groups"]:
            segments = []
            for seg_data in group_data["segments"]:
                seg = SegmentNode(
                    id=seg_data["id"],
                    video_id=video_id,
                    index=seg_data["index"],
                    text=seg_data["text"],
                    start_time=seg_data["start_time"],
                    end_time=seg_data["end_time"],
                    word_count=seg_data["word_count"],
                )
                segments.append(seg)

            group = SegmentGroup(
                group_id=group_data["group_id"],
                video_id=video_id,
                segments=segments,
            )
            groups.append(group)

        # Reconstruct as the concept service would
        group_map = {g.group_id: g.text for g in groups}

        extracted_list = []
        for group_id, concept_records in grouped.items():
            group_text = group_map.get(group_id, "")

            concepts_objs = []
            for rec in concept_records:
                c = Concept(
                    name=rec["name"],
                    definition=rec.get("definition", ""),
                    type=rec.get("type", "Concept"),
                    importance=float(rec.get("importance", 0.5)),
                    confidence=float(rec.get("confidence", 0.5)),
                    video_id=rec.get("videoId", video_id),
                    group_id=int(rec.get("groupId", group_id)),
                    first_mention_time=float(rec.get("firstMentionTime", 0.0)),
                    last_mention_time=float(rec.get("lastMentionTime", 0.0)),
                    mention_count=int(rec.get("mentionCount", 1)),
                    aliases=rec.get("aliases", []) or [],
                    extracted_at=rec.get("extractedAt"),
                    id=rec.get("id"),
                )
                concepts_objs.append(c)

            extracted = ExtractedConcepts(
                video_id=video_id,
                group_id=group_id,
                group_text=group_text,
                concepts=concepts_objs,
            )
            extracted_list.append(extracted)

        print(f"\n✅ Reconstructed {len(extracted_list)} ExtractedConcepts:")
        for ec in extracted_list:
            print(
                f"  Group {ec.group_id}: {len(ec.concepts)} concepts, group_text length: {len(ec.group_text)}"
            )
            if not ec.group_text:
                print(f"    ⚠️  WARNING: Empty group_text!")
            else:
                print(f"    First 100 chars: {ec.group_text[:100]}...")

        # Now test relationship extraction
        print(f"\n🔗 Testing relationship extraction...")
        from openai import OpenAI
        from src.services.relationships.relationship_extractor import (
            RelationshipExtractor,
        )

        openai_client = OpenAI(
            api_key=config.openai.api_key, base_url=config.openai.base_url
        )
        extractor = RelationshipExtractor(
            openai_client=openai_client,
            graph=neo4j_client.graph,
            min_confidence=0.6,
        )

        relationships = extractor.extract_from_video(extracted_list, video_id)

        print(f"\n✅ Extraction complete!")
        print(f"Total relationships found: {len(relationships)}")

    finally:
        neo4j_client.close()


if __name__ == "__main__":
    main()
