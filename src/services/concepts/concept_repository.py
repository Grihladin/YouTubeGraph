"""Repository for concept storage and retrieval in Neo4j."""

from __future__ import annotations

from typing import Any, List, Optional

from src.domain.concept import Concept, ExtractedConcepts
from src.infrastructure.neo4j_client import Neo4jClient
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ConceptRepository:
    """Manages concept storage and retrieval in Neo4j."""

    def __init__(self, client: Neo4jClient):
        """Initialize concept repository.

        Args:
            client: Connected Neo4j client
        """
        self.client = client
        self.graph = client.graph

    def upsert_concepts(self, concepts: List[Concept]) -> tuple[int, int]:
        """Insert or update concepts in Neo4j.

        Args:
            concepts: List of concept objects

        Returns:
            Tuple of (successful_uploads, failed_uploads)
        """
        logger.info(f"Upserting {len(concepts)} concepts to Neo4j")
        success, failed = self.graph.upsert_concepts(concepts)

        if failed:
            logger.warning(f"Failed to upsert {failed} concepts")

        logger.info(f"Successfully upserted {success} concepts")
        return success, failed

    def get_by_video(self, video_id: str) -> List[dict]:
        """Retrieve all concepts for a video.

        Args:
            video_id: Video identifier

        Returns:
            List of concept data dictionaries
        """
        logger.info(f"Fetching concepts for video {video_id}")
        concepts = self.graph.get_concepts_for_video(video_id)
        logger.info(f"Retrieved {len(concepts)} concepts")
        return concepts

    def get_by_group(self, video_id: str, group_id: int) -> List[dict]:
        """Retrieve concepts for a specific group.

        Args:
            video_id: Video identifier
            group_id: Group identifier

        Returns:
            List of concept data dictionaries
        """
        logger.info(f"Fetching concepts for group {group_id} in video {video_id}")
        concepts = self.graph.get_concepts_for_group(video_id, group_id)
        logger.info(f"Retrieved {len(concepts)} concepts")
        return concepts

    def search(
        self, query: str, limit: int = 10, min_confidence: float = 0.0
    ) -> List[dict]:
        """Search for concepts by name or definition.

        Args:
            query: Search query
            limit: Maximum number of results
            min_confidence: Minimum confidence threshold

        Returns:
            List of concept dictionaries
        """
        logger.info(f"Searching concepts: '{query}'")
        results = self.graph.search_concepts(
            query, limit=limit, min_confidence=min_confidence
        )
        logger.info(f"Found {len(results)} matching concepts")
        return results

    def delete_by_video(self, video_id: str) -> int:
        """Delete all concepts for a video.

        Args:
            video_id: Video identifier

        Returns:
            Number of concepts deleted
        """
        logger.info(f"Deleting concepts for video {video_id}")
        deleted = self.graph.delete_concepts_for_video(video_id)
        logger.info(f"Deleted {deleted} concepts")
        return deleted

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about stored concepts.

        Returns:
            Dictionary with statistics
        """
        logger.info("Fetching concept statistics")
        stats = self.graph.get_statistics()
        return stats
