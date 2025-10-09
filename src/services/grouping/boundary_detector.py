"""Detect topic boundaries in segment sequences."""

from __future__ import annotations

from typing import List

from src.config import GroupingConfig
from src.domain.group import SegmentNode
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BoundaryDetector:
    """Detects topic boundaries based on cohesion dips and word limits."""

    def __init__(self, config: GroupingConfig):
        """Initialize boundary detector.

        Args:
            config: Grouping configuration
        """
        self.config = config

    def detect_boundaries(self, segments: List[SegmentNode]) -> List[int]:
        """Detect topic boundaries in segment sequence.

        Args:
            segments: List of segments in temporal order

        Returns:
            List of indices where boundaries should be placed
        """
        logger.info("Detecting topic boundaries...")

        boundaries = [0]  # Always start with first segment
        current_word_count = 0

        for i in range(len(segments) - 1):
            current_word_count += segments[i].word_count

            # Compute cohesion between current and next segment
            cohesion = self._compute_cohesion(segments[i], segments[i + 1])

            # Boundary conditions
            should_split = (
                cohesion < self.config.adjacent_threshold
                or current_word_count >= self.config.max_group_words
            )

            if should_split:
                boundaries.append(i + 1)
                current_word_count = 0

        logger.info(f"Detected {len(boundaries)} boundaries")
        return boundaries

    def _compute_cohesion(self, current: SegmentNode, next_seg: SegmentNode) -> float:
        """Compute cohesion between adjacent segments.

        Args:
            current: Current segment
            next_seg: Next segment

        Returns:
            Cohesion score (0-1)
        """
        # Find next segment in neighbors
        for neighbor in current.neighbors:
            if neighbor.segment_id == next_seg.id:
                return neighbor.effective_similarity(
                    current.start_time, self.config.temporal_tau
                )

        return 0.0  # No connection found
