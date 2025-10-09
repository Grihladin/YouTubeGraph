"""Main relationship extractor that orchestrates all detection methods for a single video."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Optional

from openai import OpenAI

from src.core.concept_models import Concept, ExtractedConcepts
from src.core.inter_group_detector import InterGroupDetector
from src.core.intra_group_detector import IntraGroupDetector
from src.core.relationship_models import ExtractedRelationships, Relationship
from src.core.neo4j_graph import Neo4jGraph


class RelationshipExtractor:
    """Main orchestrator for relationship extraction within a single video."""

    def __init__(
        self,
        openai_client: OpenAI,
        graph: Optional[Neo4jGraph] = None,
        min_confidence: float = 0.6,
    ):
        """Initialize relationship extractor.

        Args:
            openai_client: OpenAI client for embeddings
            graph: Optional Neo4jGraph client to fetch concepts
            min_confidence: Minimum confidence threshold for relationships
        """
        self.openai_client = openai_client
        self.graph = graph
        self.min_confidence = min_confidence

        # Initialize detectors (single video only)
        self.intra_group_detector = IntraGroupDetector(
            min_confidence=min_confidence,
            openai_client=openai_client,
        )
        self.inter_group_detector = InterGroupDetector(
            openai_client=openai_client, min_confidence=min_confidence
        )

    def extract_from_video(
        self, all_extracted_concepts: list[ExtractedConcepts], video_id: str
    ) -> ExtractedRelationships:
        """Extract relationships from a single video's ExtractedConcepts.

        Args:
            all_extracted_concepts: List of ExtractedConcepts from multiple groups in one video
            video_id: Video ID to process

        Returns:
            ExtractedRelationships containing all detected relationships
        """
        # Filter to this video only
        video_concepts = [
            ec for ec in all_extracted_concepts if ec.video_id == video_id
        ]

        if not video_concepts:
            raise ValueError(f"No concepts found for video {video_id}")

        all_relationships = []

        print(
            f"🔍 Extracting relationships from {len(video_concepts)} groups in video {video_id}"
        )

        # Phase 1: Intra-group relationships
        print("\n🔁 Phase 1: Intra-group relationships")
        intra_count = 0
        for extracted_concepts in video_concepts:
            relationships = self.intra_group_detector.detect_relationships(
                extracted_concepts
            )
            all_relationships.extend(relationships)
            intra_count += len(relationships)

        print(f"  ✓ Found {intra_count} intra-group relationships")

        # Phase 2: Inter-group relationships (across groups in same video)
        print("\n🔗 Phase 2: Inter-group relationships")
        inter_count = 0

        relationships = self.inter_group_detector.detect_relationships(
            video_concepts, video_id
        )
        all_relationships.extend(relationships)
        inter_count += len(relationships)

        print(f"  ✓ Found {inter_count} inter-group relationships")

        # Create result
        result = ExtractedRelationships(
            relationships=all_relationships,
            video_ids=[video_id],
        )

        print(f"\n✅ Total relationships extracted: {len(result)}")
        print(f"   Average confidence: {result.avg_confidence:.2f}")
        print(f"\n📊 Type distribution:")
        for rel_type, count in sorted(result.type_distribution.items()):
            print(f"   {rel_type:20s}: {count}")

        print(f"\n🔧 Detection method distribution:")
        for method, count in sorted(result.detection_method_distribution.items()):
            print(f"   {method:20s}: {count}")

        return result

    def extract_from_graph(self, video_id: str) -> ExtractedRelationships:
        """Extract relationships from concepts stored in Neo4j for a single video.

        Args:
            video_id: Video ID to process

        Returns:
            ExtractedRelationships containing all detected relationships
        """
        if not self.graph:
            raise ValueError("Neo4j graph client required for this method")

        print(f"📡 Fetching concepts from Neo4j for video {video_id}...")

        concepts_list = self.graph.get_extracted_concepts(video_id)
        print(f"  ✓ Fetched {len(concepts_list)} concepts")

        if not concepts_list:
            raise ValueError(f"No concepts found for video {video_id}")

        grouped: dict[int, list[Concept]] = defaultdict(list)
        for concept in concepts_list:
            grouped[concept.group_id].append(concept)

        all_extracted_concepts: list[ExtractedConcepts] = []
        for group_id, concepts in sorted(grouped.items()):
            extracted = ExtractedConcepts(
                video_id=video_id,
                group_id=group_id,
                group_text="",
                concepts=concepts,
            )
            all_extracted_concepts.append(extracted)

        # Now extract relationships
        return self.extract_from_video(all_extracted_concepts, video_id)

    def save_to_file(self, relationships: ExtractedRelationships, output_path: Path):
        """Save relationships to JSON file.

        Args:
            relationships: Extracted relationships
            output_path: Path to save JSON file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "relationships": [
                {
                    "id": str(rel.id),
                    "source_concept_id": str(rel.source_concept_id),
                    "target_concept_id": str(rel.target_concept_id),
                    "type": rel.type.value,
                    "confidence": rel.confidence,
                    "evidence": rel.evidence,
                    "detection_method": rel.detection_method.value,
                    "source_video_id": rel.source_video_id,
                    "source_group_id": rel.source_group_id,
                    "target_video_id": rel.target_video_id,
                    "target_group_id": rel.target_group_id,
                    "temporal_distance": rel.temporal_distance,
                    "extracted_at": rel.extracted_at.isoformat(),
                }
                for rel in relationships.relationships
            ],
            "metadata": {
                "total_relationships": len(relationships),
                "video_ids": relationships.video_ids,
                "avg_confidence": relationships.avg_confidence,
                "type_distribution": relationships.type_distribution,
                "detection_method_distribution": relationships.detection_method_distribution,
                "extraction_time": relationships.extraction_time.isoformat(),
            },
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Saved relationships to: {output_path}")

    def load_from_file(self, input_path: Path) -> ExtractedRelationships:
        """Load relationships from JSON file.

        Args:
            input_path: Path to JSON file

        Returns:
            ExtractedRelationships loaded from file
        """
        with open(input_path, encoding="utf-8") as f:
            data = json.load(f)

        relationships = []
        for rel_data in data["relationships"]:
            rel = Relationship(
                source_concept_id=rel_data["source_concept_id"],
                target_concept_id=rel_data["target_concept_id"],
                type=rel_data["type"],
                confidence=rel_data["confidence"],
                evidence=rel_data["evidence"],
                detection_method=rel_data["detection_method"],
                source_video_id=rel_data["source_video_id"],
                source_group_id=rel_data["source_group_id"],
                target_video_id=rel_data["target_video_id"],
                target_group_id=rel_data["target_group_id"],
                temporal_distance=rel_data.get("temporal_distance"),
            )
            relationships.append(rel)

        return ExtractedRelationships(
            relationships=relationships,
            video_ids=data["metadata"]["video_ids"],
        )

    def __repr__(self) -> str:
        return f"RelationshipExtractor(min_confidence={self.min_confidence})"
