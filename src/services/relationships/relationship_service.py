"""High-level relationship service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from openai import OpenAI

from src.domain.concept import ExtractedConcepts
from src.domain.relationship import ExtractedRelationships
from src.infrastructure.neo4j_client import Neo4jClient
from src.services.relationships.relationship_repository import RelationshipRepository
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RelationshipService:
    """Orchestrates relationship detection and storage."""

    def __init__(
        self,
        openai_client: OpenAI,
        neo4j_client: Neo4jClient,
        repository: RelationshipRepository,
        min_confidence: float = 0.6,
    ):
        """Initialize relationship service.

        Args:
            openai_client: OpenAI client for embeddings
            neo4j_client: Neo4j client for graph operations
            repository: Relationship repository
            min_confidence: Minimum confidence threshold
        """
        self.openai_client = openai_client
        self.neo4j_client = neo4j_client
        self.repository = repository
        self.min_confidence = min_confidence

        # Use existing relationship extractor
        from src.services.relationships.relationship_extractor import (
            RelationshipExtractor,
        )

        self.extractor = RelationshipExtractor(
            openai_client=openai_client,
            graph=neo4j_client.graph,
            min_confidence=min_confidence,
        )

    def extract_from_video(
        self,
        extracted_concepts: List[ExtractedConcepts],
        video_id: str,
        overwrite: bool = False,
    ) -> ExtractedRelationships:
        """Extract relationships from a video's concepts.

        Args:
            extracted_concepts: List of extracted concepts from all groups
            video_id: Video identifier
            overwrite: Whether to delete existing relationships first

        Returns:
            Extracted relationships
        """
        logger.info(f"Extracting relationships for video {video_id}")

        # Delete existing if requested
        if overwrite:
            self.repository.delete_by_video(video_id)

        # Extract relationships
        relationships = self.extractor.extract_from_video(extracted_concepts, video_id)

        # Store in database
        stats = self.repository.upsert_relationships(relationships)

        logger.info(
            f"Relationship extraction complete: "
            f"{stats.get('uploaded', 0)} uploaded, "
            f"{len(relationships)} total detected"
        )

        return relationships

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

        logger.info(f"Saved relationships to {output_path}")
