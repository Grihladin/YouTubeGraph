"""Main grouping service orchestrating the grouping pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import numpy as np

from src.config import GroupingConfig
from src.domain.group import SegmentGroup, SegmentNode
from src.services.vectorstore.segment_repository import SegmentRepository
from src.services.grouping.boundary_detector import BoundaryDetector
from src.services.grouping.group_merger import GroupMerger
from src.utils.logging import get_logger

logger = get_logger(__name__)


class GroupingService:
    """Orchestrates segment grouping operations."""

    def __init__(
        self,
        repository: SegmentRepository,
        config: GroupingConfig,
    ):
        """Initialize grouping service.

        Args:
            repository: Segment repository for data access
            config: Grouping configuration
        """
        self.repository = repository
        self.config = config
        self.boundary_detector = BoundaryDetector(config)
        self.group_merger = GroupMerger(config)

    def group_video(self, video_id: str) -> List[SegmentGroup]:
        """Complete grouping pipeline for a video.

        Args:
            video_id: YouTube video ID

        Returns:
            List of SegmentGroup objects
        """
        logger.info(f"Grouping segments for video: {video_id}")

        # Step 1: Fetch segments with embeddings
        segments = self.repository.fetch_by_video(video_id, include_embeddings=True)

        if not segments:
            logger.warning(f"No segments found for video {video_id}")
            return []

        # Step 2: Build neighborhoods
        self._build_neighborhoods(segments)

        # Step 3: Form initial groups
        groups = self._form_groups(segments)

        # Step 4: Post-merge similar groups
        groups = self.group_merger.merge_groups(groups)

        # Step 5: Report statistics
        self._report_stats(groups)

        logger.info(f"Completed grouping: {len(groups)} groups created")
        return groups

    def _build_neighborhoods(self, segments: List[SegmentNode]) -> None:
        """Build k-NN neighborhoods for each segment.

        Args:
            segments: List of segments to build neighborhoods for
        """
        logger.info(f"Building k-NN neighborhoods (k={self.config.k_neighbors})...")

        for segment in segments:
            if not segment.embedding:
                continue

            # Search for neighbors
            neighbors = self.repository.search_neighbors(
                embedding=segment.embedding,
                video_id=segment.video_id,
                k=self.config.k_neighbors + 1,  # +1 because it includes self
            )

            # Filter out self and apply threshold
            filtered_neighbors = []
            for neighbor in neighbors:
                if neighbor.segment_id == segment.id:
                    continue

                if neighbor.similarity < self.config.neighbor_threshold:
                    continue

                # Find and set the index
                neighbor_index = next(
                    (i for i, s in enumerate(segments) if s.id == neighbor.segment_id),
                    -1,
                )
                neighbor.index = neighbor_index
                filtered_neighbors.append(neighbor)

            segment.neighbors = filtered_neighbors

        avg_neighbors = np.mean([len(s.neighbors) for s in segments])
        logger.info(f"Built neighborhoods (avg {avg_neighbors:.1f} neighbors/segment)")

    def _form_groups(self, segments: List[SegmentNode]) -> List[SegmentGroup]:
        """Form segment groups using boundary detection.

        Args:
            segments: List of segments with neighborhoods

        Returns:
            List of SegmentGroup objects
        """
        logger.info("Forming segment groups...")

        boundaries = self.boundary_detector.detect_boundaries(segments)
        groups = []

        for group_idx in range(len(boundaries)):
            start_idx = boundaries[group_idx]
            end_idx = (
                boundaries[group_idx + 1]
                if group_idx + 1 < len(boundaries)
                else len(segments)
            )

            group_segments = segments[start_idx:end_idx]

            # Skip if too small (except for last group)
            if (
                len(group_segments) < self.config.min_group_segments
                and group_idx < len(boundaries) - 1
            ):
                # Try to merge with previous group
                if (
                    groups
                    and groups[-1].total_words
                    + sum(s.word_count for s in group_segments)
                    <= self.config.max_group_words * 1.2
                ):
                    groups[-1].segments.extend(group_segments)
                    for seg in group_segments:
                        seg.group_id = groups[-1].group_id
                    continue

            # Create the group
            group = SegmentGroup(
                group_id=len(groups),
                segments=group_segments,
                video_id=segments[0].video_id,
            )

            # Assign group IDs to segments
            for seg in group_segments:
                seg.group_id = group.group_id

            groups.append(group)

        logger.info(f"Formed {len(groups)} initial groups")
        return groups

    def export_to_json(self, groups: List[SegmentGroup], output_path: Path) -> None:
        """Export groups to JSON file.

        Args:
            groups: List of groups to export
            output_path: Path to output JSON file
        """
        if not groups:
            logger.warning("No groups to export")
            return

        output = {
            "video_id": groups[0].video_id,
            "num_groups": len(groups),
            "groups": [group.to_dict() for group in groups],
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported {len(groups)} groups to {output_path}")

    def _report_stats(self, groups: List[SegmentGroup]) -> None:
        """Log statistics about the groups.

        Args:
            groups: List of groups to analyze
        """
        if not groups:
            return

        total_segments = sum(len(g.segments) for g in groups)
        word_counts = [g.total_words for g in groups]
        cohesions = [g.avg_internal_similarity() for g in groups]

        logger.info("=" * 60)
        logger.info("GROUPING STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Total groups: {len(groups)}")
        logger.info(f"Total segments: {total_segments}")
        logger.info(f"Avg segments per group: {total_segments / len(groups):.1f}")
        logger.info(
            f"Word counts: min={min(word_counts)}, max={max(word_counts)}, "
            f"mean={np.mean(word_counts):.0f}"
        )
        logger.info(
            f"Internal cohesion: min={min(cohesions):.3f}, "
            f"max={max(cohesions):.3f}, mean={np.mean(cohesions):.3f}"
        )
        logger.info("=" * 60)
