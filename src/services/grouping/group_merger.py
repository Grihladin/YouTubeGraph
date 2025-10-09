"""Merge adjacent groups with high similarity."""

from __future__ import annotations

from typing import List

from src.config import GroupingConfig
from src.domain.group import SegmentGroup, cosine_similarity
from src.utils.logging import get_logger

logger = get_logger(__name__)


class GroupMerger:
    """Post-processes groups by merging highly similar adjacent groups."""

    def __init__(self, config: GroupingConfig):
        """Initialize group merger.

        Args:
            config: Grouping configuration
        """
        self.config = config

    def merge_groups(self, groups: List[SegmentGroup]) -> List[SegmentGroup]:
        """Merge adjacent groups with high centroid similarity.

        Args:
            groups: List of groups to potentially merge

        Returns:
            Updated list of groups after merging
        """
        logger.info(f"Post-merging {len(groups)} groups...")

        merged = []
        i = 0

        while i < len(groups):
            current = groups[i]

            # Try to merge with next group
            if i + 1 < len(groups):
                next_group = groups[i + 1]

                if self._should_merge(current, next_group):
                    # Merge the groups
                    current.segments.extend(next_group.segments)
                    for seg in next_group.segments:
                        seg.group_id = current.group_id

                    logger.debug(
                        f"Merged group {current.group_id} with {next_group.group_id}"
                    )
                    i += 1  # Skip the next group since we merged it

            merged.append(current)
            i += 1

        # Renumber groups
        for idx, group in enumerate(merged):
            group.group_id = idx
            for seg in group.segments:
                seg.group_id = idx

        logger.info(f"After merging: {len(merged)} groups")
        return merged

    def _should_merge(self, group1: SegmentGroup, group2: SegmentGroup) -> bool:
        """Check if two adjacent groups should be merged.

        Args:
            group1: First group
            group2: Second group

        Returns:
            True if groups should be merged
        """
        # Check word count constraint
        combined_words = group1.total_words + group2.total_words
        if combined_words > self.config.max_group_words * 1.25:
            return False

        # Compute centroid similarity
        centroid1 = group1.centroid_embedding()
        centroid2 = group2.centroid_embedding()

        if len(centroid1) == 0 or len(centroid2) == 0:
            return False

        similarity = cosine_similarity(centroid1.tolist(), centroid2.tolist())

        return similarity >= self.config.merge_centroid_threshold
