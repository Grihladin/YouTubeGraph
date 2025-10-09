"""Repository for segment CRUD operations in Weaviate."""

from __future__ import annotations

from typing import List
from uuid import NAMESPACE_URL, uuid5

import weaviate
from weaviate.classes.query import MetadataQuery

from src.domain.transcript import TranscriptSegment
from src.domain.group import SegmentNode, Neighbor
from src.infrastructure.weaviate_client import WeaviateClient
from src.utils.logging import get_logger

logger = get_logger(__name__)


class SegmentRepository:
    """Manages segment storage and retrieval in Weaviate."""

    def __init__(self, client: WeaviateClient, collection_name: str = "Segment"):
        """Initialize segment repository.

        Args:
            client: Connected Weaviate client
            collection_name: Name of the collection
        """
        self.client = client
        self.collection_name = collection_name

    def upload_segments(self, segments: List[TranscriptSegment]) -> int:
        """Upload segments to Weaviate.

        Args:
            segments: List of transcript segments

        Returns:
            Number of segments uploaded
        """
        if not self.client.is_ready():
            raise RuntimeError("Vector store client not connected")

        collection = self.client.client.collections.get(self.collection_name)
        uploaded_count = 0

        logger.info(f"Uploading {len(segments)} segments to Weaviate")

        with collection.batch.dynamic() as batch:
            for segment in segments:
                properties = segment.as_weaviate_properties()
                segment_uuid = self._segment_uuid(segment)
                batch.add_object(uuid=segment_uuid, properties=properties)
                uploaded_count += 1

        logger.info(f"Successfully uploaded {uploaded_count} segments")
        return uploaded_count

    def fetch_by_video(
        self, video_id: str, include_embeddings: bool = True
    ) -> List[SegmentNode]:
        """Fetch all segments for a video.

        Args:
            video_id: Video identifier
            include_embeddings: Whether to include embedding vectors

        Returns:
            List of SegmentNode objects sorted by start time
        """
        if not self.client.is_ready():
            raise RuntimeError("Vector store client not connected")

        collection = self.client.client.collections.get(self.collection_name)

        logger.info(f"Fetching segments for video {video_id}")

        response = collection.query.fetch_objects(
            filters=weaviate.classes.query.Filter.by_property("videoId").equal(
                video_id
            ),
            include_vector=include_embeddings,
            limit=10000,
        )

        segments = []
        for i, obj in enumerate(response.objects):
            props = obj.properties
            segments.append(
                SegmentNode(
                    id=str(obj.uuid),
                    video_id=props.get("videoId", ""),
                    index=i,
                    text=props.get("text", ""),
                    start_time=props.get("start_s", 0.0),
                    end_time=props.get("end_s", 0.0),
                    word_count=props.get("tokens", len(props.get("text", "").split())),
                    embedding=obj.vector.get("default") if obj.vector else None,
                )
            )

        # Sort by start time
        segments.sort(key=lambda s: s.start_time)
        for i, seg in enumerate(segments):
            seg.index = i

        logger.info(f"Fetched {len(segments)} segments")
        return segments

    def search_neighbors(
        self, embedding: List[float], video_id: str, k: int = 10
    ) -> List[Neighbor]:
        """Search for k nearest neighbors by embedding.

        Args:
            embedding: Query embedding vector
            video_id: Filter to specific video
            k: Number of neighbors to return

        Returns:
            List of Neighbor objects
        """
        if not self.client.is_ready():
            raise RuntimeError("Vector store client not connected")

        collection = self.client.client.collections.get(self.collection_name)

        response = collection.query.near_vector(
            near_vector=embedding,
            limit=k,
            include_vector=True,
            return_metadata=MetadataQuery(distance=True),
            filters=weaviate.classes.query.Filter.by_property("videoId").equal(
                video_id
            ),
        )

        neighbors = []
        for obj in response.objects:
            props = obj.properties
            distance = obj.metadata.distance if obj.metadata.distance else 0.0
            similarity = 1.0 - distance

            neighbors.append(
                Neighbor(
                    segment_id=str(obj.uuid),
                    index=-1,  # Will be set by caller
                    similarity=similarity,
                    start_time=props.get("start_s", 0.0),
                    end_time=props.get("end_s", 0.0),
                    text=props.get("text", ""),
                    embedding=obj.vector.get("default") if obj.vector else None,
                )
            )

        return neighbors

    def delete_by_video(self, video_id: str) -> int:
        """Delete all segments for a video.

        Args:
            video_id: Video identifier

        Returns:
            Number of segments deleted
        """
        if not self.client.is_ready():
            raise RuntimeError("Vector store client not connected")

        collection = self.client.client.collections.get(self.collection_name)

        logger.info(f"Deleting segments for video {video_id}")

        result = collection.data.delete_many(
            where=weaviate.classes.query.Filter.by_property("videoId").equal(video_id)
        )

        deleted = result.matches if hasattr(result, "matches") else 0
        logger.info(f"Deleted {deleted} segments")
        return deleted

    @staticmethod
    def _segment_uuid(segment: TranscriptSegment) -> str:
        """Generate deterministic UUID for segment."""
        key = f"{segment.video_id}:{segment.start_s:.6f}"
        return str(uuid5(NAMESPACE_URL, key))
