"""Upload extracted concepts to Neo4j."""

from __future__ import annotations

import os
from typing import Any, Iterable, Optional
from uuid import UUID

from dotenv import load_dotenv

from .concept_models import Concept, ConceptMention, ExtractedConcepts
from .neo4j_graph import Neo4jGraph

# Load environment variables
load_dotenv()


class ConceptUploader:
    """Upload concepts and concept mentions to Neo4j."""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ) -> None:
        """Initialize Neo4j client for concept upload.

        Args:
            uri: Neo4j bolt URI (defaults to NEO4J_URI env var)
            user: Neo4j username (defaults to NEO4J_USER env var)
            password: Neo4j password (defaults to NEO4J_PASSWORD env var)
            database: Optional Neo4j database name (defaults to NEO4J_DATABASE env var)
        """

        self.uri = uri or os.getenv("NEO4J_URI")
        self.user = user or os.getenv("NEO4J_USER")
        self.password = password or os.getenv("NEO4J_PASSWORD")
        self.database = database or os.getenv("NEO4J_DATABASE")

        if not all([self.uri, self.user, self.password]):
            raise ValueError(
                "Missing required credentials. Set NEO4J_URI, NEO4J_USER, "
                "and NEO4J_PASSWORD environment variables"
            )

        self.graph = Neo4jGraph(
            uri=self.uri,
            user=self.user,
            password=self.password,
            database=self.database,
        )

        print(f"✓ Connected to Neo4j: {self.uri}")

    def upload_concepts(
        self,
        concepts: Iterable[Concept],
        batch_size: int = 100,
    ) -> tuple[int, int]:
        """Upload concepts to Neo4j.

        Args:
            concepts: Iterable of Concept objects
            batch_size: Unused (kept for API compatibility)

        Returns:
            Tuple of (successful_uploads, failed_uploads)
        """
        success, failed = self.graph.upsert_concepts(concepts)
        if failed:
            print(f"⚠️  Failed to upload {failed} concepts")
        return success, failed

    def upload_mentions(
        self,
        mentions: Iterable[ConceptMention],
        batch_size: int = 100,
    ) -> tuple[int, int]:
        """Upload concept mentions to Neo4j.

        Args:
            mentions: Iterable of ConceptMention objects
            batch_size: Unused (kept for API compatibility)

        Returns:
            Tuple of (successful_uploads, failed_uploads)
        """
        success, failed = self.graph.upsert_mentions(mentions)
        if failed:
            print(f"⚠️  Failed to upload {failed} mentions")
        return success, failed

    def upload_extracted_concepts(
        self,
        extracted: ExtractedConcepts,
    ) -> dict[str, int]:
        """Upload all concepts and mentions from an extraction result.

        Args:
            extracted: ExtractedConcepts object from ConceptExtractor

        Returns:
            Dictionary with upload statistics
        """
        stats = {
            "concepts_success": 0,
            "concepts_failed": 0,
            "mentions_success": 0,
            "mentions_failed": 0,
        }

        # Upload concepts
        if extracted.concepts:
            c_success, c_failed = self.upload_concepts(extracted.concepts)
            stats["concepts_success"] = c_success
            stats["concepts_failed"] = c_failed

        # Upload mentions (if any)
        if extracted.mentions:
            m_success, m_failed = self.upload_mentions(extracted.mentions)
            stats["mentions_success"] = m_success
            stats["mentions_failed"] = m_failed

        return stats

    def concept_exists(self, concept_id: UUID) -> bool:
        """Check if a concept already exists in Neo4j.

        Args:
            concept_id: UUID of the concept

        Returns:
            True if concept exists, False otherwise
        """
        return self.graph.concept_exists(str(concept_id))

    def get_concepts_for_video(self, video_id: str) -> list[dict]:
        """Retrieve all concepts for a specific video.

        Args:
            video_id: Video identifier

        Returns:
            List of concept data dictionaries
        """
        return self.graph.get_concepts_for_video(video_id)

    def get_concepts_for_group(self, video_id: str, group_id: int) -> list[dict]:
        """Retrieve all concepts for a specific group.

        Args:
            video_id: Video identifier
            group_id: Group identifier

        Returns:
            List of concept data dictionaries
        """
        return self.graph.get_concepts_for_group(video_id, group_id)

    def search_concepts(
        self,
        query: str,
        limit: int = 10,
        min_confidence: float = 0.0,
    ) -> list[dict]:
        """Search for concepts by name or definition substring.

        Args:
            query: Search query
            limit: Maximum number of results
            min_confidence: Minimum confidence threshold

        Returns:
            List of concept data dictionaries with similarity scores
        """
        return self.graph.search_concepts(
            query, limit=limit, min_confidence=min_confidence
        )

    def delete_concepts_for_video(self, video_id: str) -> int:
        """Delete all concepts for a video (useful for re-extraction).

        Args:
            video_id: Video identifier

        Returns:
            Number of concepts deleted
        """
        deleted = self.graph.delete_concepts_for_video(video_id)
        print(f"✓ Deleted {deleted} concepts for video {video_id}")
        return deleted

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about stored concepts.

        Returns:
            Dictionary with various statistics
        """
        return self.graph.get_statistics()

    def close(self):
        """Close Neo4j connection."""
        self.graph.close()
        print("✓ Closed Neo4j connection")


def main():
    """Example usage of ConceptUploader."""

    # Initialize uploader
    uploader = ConceptUploader()

    try:
        # Get statistics
        print("\n📊 Neo4j Statistics:")
        stats = uploader.get_statistics()
        for key, value in stats.items():
            print(f"  {key}: {value}")

        # Search example
        print("\n🔍 Searching for concepts related to 'machine learning'...")
        results = uploader.search_concepts("machine learning", limit=5)

        if results:
            print(f"\nFound {len(results)} concepts:")
            for concept in results:
                print(f"\n  • {concept['name']} ({concept['type']})")
                confidence = concept.get("confidence")
                if confidence is not None:
                    print(f"    Confidence: {confidence:.2f}")
                print(f"    Importance: {concept['importance']:.2f}")
                print(f"    Definition: {concept['definition'][:80]}...")
        else:
            print("  No concepts found (database may be empty)")

    finally:
        uploader.close()


if __name__ == "__main__":
    main()
