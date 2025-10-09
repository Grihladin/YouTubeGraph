"""Repository for relationship storage in Neo4j."""

from __future__ import annotations

from typing import List

from src.domain.relationship import Relationship, ExtractedRelationships
from src.infrastructure.neo4j_client import Neo4jClient
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RelationshipRepository:
    """Manages relationship storage and retrieval in Neo4j."""

    def __init__(self, client: Neo4jClient):
        """Initialize relationship repository.

        Args:
            client: Connected Neo4j client
        """
        self.client = client
        self.graph = client.graph

    def upsert_relationships(self, relationships: ExtractedRelationships) -> dict:
        """Insert or update relationships in Neo4j.

        Args:
            relationships: Extracted relationships

        Returns:
            Dictionary with upload statistics
        """
        logger.info(f"Upserting {len(relationships)} relationships to Neo4j")

        # Use the relationship uploader
        from src.services.relationships.relationship_uploader import (
            RelationshipUploader,
        )

        uploader = RelationshipUploader(self.graph)
        stats = uploader.upload_relationships(relationships)

        logger.info(
            f"Uploaded {stats.get('uploaded', 0)} relationships, "
            f"skipped {stats.get('skipped', 0)}, "
            f"failed {stats.get('failed', 0)}"
        )

        return stats

    def get_by_video(self, video_id: str) -> List[dict]:
        """Retrieve all relationships for a video.

        Args:
            video_id: Video identifier

        Returns:
            List of relationship dictionaries
        """
        logger.info(f"Fetching relationships for video {video_id}")
        # This would need to be implemented in Neo4jGraph
        # For now, return empty list
        logger.warning("get_by_video not yet implemented in Neo4jGraph")
        return []

    def delete_by_video(self, video_id: str) -> int:
        """Delete all relationships for a video.

        Args:
            video_id: Video identifier

        Returns:
            Number of relationships deleted
        """
        logger.info(f"Deleting relationships for video {video_id}")

        # Use the relationship uploader
        from src.services.relationships.relationship_uploader import (
            RelationshipUploader,
        )

        uploader = RelationshipUploader(self.graph)
        uploader.delete_relationships_for_video(video_id)

        logger.info(f"Deleted relationships for video {video_id}")
        return 0  # Actual count not returned by current implementation
