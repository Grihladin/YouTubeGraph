"""Upload relationships to Neo4j with proper cross-references."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from src.core.neo4j_graph import Neo4jGraph
from src.core.relationship_models import ExtractedRelationships


class RelationshipUploader:
    """Handles uploading relationships to Neo4j."""

    def __init__(self, graph: Neo4jGraph):
        self.graph = graph

    def upload_relationships(
        self, relationships: ExtractedRelationships, batch_size: int = 100
    ) -> dict[str, int]:
        """Upload relationships to Neo4j.

        Args:
            relationships: ExtractedRelationships to upload
            batch_size: Number of relationships to upload per batch

        Returns:
            Dictionary with upload statistics
        """
        total = len(relationships.relationships)
        if not total:
            print("⚠️  No relationships to upload")
            return {"uploaded": 0, "failed": 0, "skipped": 0}

        print(f"\n📤 Uploading {total} relationships to Neo4j...")
        stats = self.graph.upsert_relationships(relationships, batch_size=batch_size)
        print("\n✅ Upload complete:")
        print(f"   Uploaded: {stats.get('uploaded', 0)}")
        print(f"   Skipped (duplicates): {stats.get('skipped', 0)}")
        print(f"   Failed: {stats.get('failed', 0)}")
        return stats

    def delete_relationships_for_video(self, video_id: str) -> int:
        """Delete all relationships for a specific video.

        Args:
            video_id: Video ID

        Returns:
            Number of relationships deleted
        """
        print(f"\n🗑️  Deleting relationships for video {video_id}...")
        deleted = self.graph.delete_relationships_for_video(video_id)
        print(f"  ✓ Deleted {deleted} relationships")
        return deleted

    def get_relationship_count(self, video_id: Optional[str] = None) -> int:
        """Get count of relationships in Neo4j.

        Args:
            video_id: Optional video ID to filter by

        Returns:
            Number of relationships
        """
        return self.graph.count_relationships(video_id)

    def get_relationships_for_concept(
        self, concept_id: UUID, limit: int = 100
    ) -> list[dict]:
        """Get all relationships involving a specific concept.

        Args:
            concept_id: Concept UUID
            limit: Maximum number of relationships to return

        Returns:
            List of relationship dictionaries
        """
        return self.graph.fetch_relationships_for_concept(str(concept_id), limit=limit)

    def __repr__(self) -> str:
        return "RelationshipUploader(backend=Neo4j)"
