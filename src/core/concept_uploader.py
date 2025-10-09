"""Upload extracted concepts to Weaviate."""

from __future__ import annotations

import os
from typing import Iterable, Optional
from uuid import UUID

from dotenv import load_dotenv
import weaviate
from weaviate.classes.init import Auth

from .concept_models import Concept, ConceptMention, ExtractedConcepts

# Load environment variables
load_dotenv()


class ConceptUploader:
    """Upload concepts and concept mentions to Weaviate."""

    def __init__(
        self,
        cluster_url: Optional[str] = None,
        api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
    ):
        """Initialize Weaviate client for concept upload.

        Args:
            cluster_url: Weaviate cluster URL (defaults to WEAVIATE_URL env var)
            api_key: Weaviate API key (defaults to WEAVIATE_API_KEY env var)
            openai_api_key: OpenAI API key for vectorization (defaults to OPENAI_API_KEY env var)
        """
        self.cluster_url = cluster_url or os.getenv("WEAVIATE_URL")
        self.api_key = api_key or os.getenv("WEAVIATE_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

        if not all([self.cluster_url, self.api_key, self.openai_api_key]):
            raise ValueError(
                "Missing required credentials. Set WEAVIATE_URL, WEAVIATE_API_KEY, "
                "and OPENAI_API_KEY environment variables"
            )

        # Connect to Weaviate
        self.client = weaviate.connect_to_weaviate_cloud(
            cluster_url=self.cluster_url,
            auth_credentials=Auth.api_key(self.api_key),
            headers={"X-OpenAI-Api-Key": self.openai_api_key},
        )

        if not self.client.is_ready():
            raise RuntimeError("Weaviate cluster is not ready")

        print(f"✓ Connected to Weaviate: {self.cluster_url}")

        # Get collections
        self.concept_collection = self.client.collections.get("Concept")
        self.mention_collection = self.client.collections.get("ConceptMention")

    def upload_concepts(
        self,
        concepts: Iterable[Concept],
        batch_size: int = 100,
    ) -> tuple[int, int]:
        """Upload concepts to Weaviate.

        Args:
            concepts: Iterable of Concept objects
            batch_size: Unused (kept for API compatibility)

        Returns:
            Tuple of (successful_uploads, failed_uploads)
        """
        success_count = 0
        failed_count = 0

        with self.concept_collection.batch.dynamic() as batch:
            for concept in concepts:
                try:
                    properties = concept.as_weaviate_properties()
                    batch.add_object(
                        uuid=concept.id,
                        properties=properties,
                    )
                    success_count += 1
                except Exception as e:
                    print(f"⚠️  Failed to upload concept '{concept.name}': {e}")
                    failed_count += 1

        return success_count, failed_count

    def upload_mentions(
        self,
        mentions: Iterable[ConceptMention],
        batch_size: int = 100,
    ) -> tuple[int, int]:
        """Upload concept mentions to Weaviate.

        Args:
            mentions: Iterable of ConceptMention objects
            batch_size: Unused (kept for API compatibility)

        Returns:
            Tuple of (successful_uploads, failed_uploads)
        """
        success_count = 0
        failed_count = 0

        with self.mention_collection.batch.dynamic() as batch:
            for mention in mentions:
                try:
                    properties = mention.as_weaviate_properties()

                    # Add with cross-reference to Concept
                    batch.add_object(
                        uuid=mention.id,
                        properties=properties,
                        references={
                            "concept": mention.concept_id,  # Cross-ref to Concept
                        },
                    )
                    success_count += 1
                except Exception as e:
                    print(f"⚠️  Failed to upload mention: {e}")
                    failed_count += 1

        return success_count, failed_count

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
        """Check if a concept already exists in Weaviate.

        Args:
            concept_id: UUID of the concept

        Returns:
            True if concept exists, False otherwise
        """
        try:
            result = self.concept_collection.query.fetch_object_by_id(concept_id)
            return result is not None
        except Exception:
            return False

    def get_concepts_for_video(self, video_id: str) -> list[dict]:
        """Retrieve all concepts for a specific video.

        Args:
            video_id: Video identifier

        Returns:
            List of concept data dictionaries
        """
        try:
            result = self.concept_collection.query.fetch_objects(
                filters=weaviate.classes.query.Filter.by_property("videoId").equal(
                    video_id
                ),
                limit=1000,
            )
            return [obj.properties for obj in result.objects]
        except Exception as e:
            print(f"⚠️  Failed to fetch concepts for video {video_id}: {e}")
            return []

    def get_concepts_for_group(self, video_id: str, group_id: int) -> list[dict]:
        """Retrieve all concepts for a specific group.

        Args:
            video_id: Video identifier
            group_id: Group identifier

        Returns:
            List of concept data dictionaries
        """
        try:
            result = self.concept_collection.query.fetch_objects(
                filters=(
                    weaviate.classes.query.Filter.by_property("videoId").equal(video_id)
                    & weaviate.classes.query.Filter.by_property("groupId").equal(
                        group_id
                    )
                ),
                limit=100,
            )
            return [obj.properties for obj in result.objects]
        except Exception as e:
            print(f"⚠️  Failed to fetch concepts for group {group_id}: {e}")
            return []

    def search_concepts(
        self,
        query: str,
        limit: int = 10,
        min_confidence: float = 0.0,
    ) -> list[dict]:
        """Semantic search for concepts.

        Args:
            query: Search query
            limit: Maximum number of results
            min_confidence: Minimum confidence threshold

        Returns:
            List of concept data dictionaries with similarity scores
        """
        try:
            result = self.concept_collection.query.near_text(
                query=query,
                limit=limit,
                return_metadata=["distance"],
                filters=(
                    (
                        weaviate.classes.query.Filter.by_property(
                            "confidence"
                        ).greater_or_equal(min_confidence)
                    )
                    if min_confidence > 0
                    else None
                ),
            )

            return [
                {
                    **obj.properties,
                    "similarity": 1 - obj.metadata.distance,
                }
                for obj in result.objects
            ]
        except Exception as e:
            print(f"⚠️  Search failed: {e}")
            return []

    def delete_concepts_for_video(self, video_id: str) -> int:
        """Delete all concepts for a video (useful for re-extraction).

        Args:
            video_id: Video identifier

        Returns:
            Number of concepts deleted
        """
        try:
            result = self.concept_collection.data.delete_many(
                where=weaviate.classes.query.Filter.by_property("videoId").equal(
                    video_id
                )
            )
            count = result.successful if hasattr(result, "successful") else 0
            print(f"✓ Deleted {count} concepts for video {video_id}")
            return count
        except Exception as e:
            print(f"⚠️  Failed to delete concepts: {e}")
            return 0

    def get_statistics(self) -> dict[str, any]:
        """Get statistics about stored concepts.

        Returns:
            Dictionary with various statistics
        """
        try:
            # Get total counts
            concept_result = self.concept_collection.aggregate.over_all(
                total_count=True,
            )

            total_concepts = concept_result.total_count if concept_result else 0

            # Note: More detailed stats would require aggregation queries
            # This is a basic implementation

            return {
                "total_concepts": total_concepts,
                "collections_available": ["Concept", "ConceptMention"],
            }
        except Exception as e:
            print(f"⚠️  Failed to get statistics: {e}")
            return {}

    def close(self):
        """Close Weaviate connection."""
        self.client.close()
        print("✓ Closed Weaviate connection")


def main():
    """Example usage of ConceptUploader."""
    from datetime import datetime

    # Initialize uploader
    uploader = ConceptUploader()

    try:
        # Get statistics
        print("\n📊 Weaviate Statistics:")
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
                print(f"    Similarity: {concept['similarity']:.3f}")
                print(f"    Importance: {concept['importance']:.2f}")
                print(f"    Definition: {concept['definition'][:80]}...")
        else:
            print("  No concepts found (database may be empty)")

    finally:
        uploader.close()


if __name__ == "__main__":
    main()
