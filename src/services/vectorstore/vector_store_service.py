"""High-level vector store service."""

from __future__ import annotations

from typing import List

from src.domain.transcript import TranscriptResult
from src.domain.group import SegmentNode
from src.services.vectorstore.segment_repository import SegmentRepository
from src.utils.logging import get_logger

logger = get_logger(__name__)


class VectorStoreService:
    """High-level vector store operations."""

    def __init__(self, repository: SegmentRepository):
        """Initialize vector store service.

        Args:
            repository: Segment repository instance
        """
        self.repository = repository

    def store_transcript(self, result: TranscriptResult) -> int:
        """Store transcript segments in vector store.

        Args:
            result: Transcript result with segments

        Returns:
            Number of segments stored
        """
        logger.info(f"Storing transcript for video {result.video_id}")
        count = self.repository.upload_segments(result.segments)
        logger.info(f"Stored {count} segments for video {result.video_id}")
        return count

    def retrieve_for_grouping(self, video_id: str) -> List[SegmentNode]:
        """Retrieve segments for grouping operations.

        Args:
            video_id: Video identifier

        Returns:
            List of segment nodes with embeddings
        """
        logger.info(f"Retrieving segments for grouping: {video_id}")
        segments = self.repository.fetch_by_video(video_id, include_embeddings=True)
        logger.info(f"Retrieved {len(segments)} segments for grouping")
        return segments

    def delete_video(self, video_id: str) -> int:
        """Delete all segments for a video.

        Args:
            video_id: Video identifier

        Returns:
            Number of segments deleted
        """
        logger.info(f"Deleting all segments for video {video_id}")
        count = self.repository.delete_by_video(video_id)
        logger.info(f"Deleted {count} segments")
        return count
