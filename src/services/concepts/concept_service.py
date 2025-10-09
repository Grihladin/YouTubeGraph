"""High-level concept service orchestrating extraction and storage."""

from __future__ import annotations

import time
from typing import List

from src.domain.concept import ExtractedConcepts, Concept
from src.domain.group import SegmentGroup
from src.services.concepts.concept_extractor import ConceptExtractor
from src.services.concepts.concept_repository import ConceptRepository
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ConceptService:
    """Orchestrates concept extraction and storage operations."""

    def __init__(
        self,
        extractor: ConceptExtractor,
        repository: ConceptRepository,
        delay_seconds: float = 0.5,
    ):
        """Initialize concept service.

        Args:
            extractor: Concept extractor instance
            repository: Concept repository instance
            delay_seconds: Delay between extractions (rate limiting)
        """
        self.extractor = extractor
        self.repository = repository
        self.delay_seconds = delay_seconds

    def process_groups(
        self, groups: List[SegmentGroup], skip_existing: bool = False
    ) -> List[ExtractedConcepts]:
        """Extract and store concepts from groups.

        Args:
            groups: List of segment groups
            skip_existing: Whether to skip groups that already have concepts

        Returns:
            List of ExtractedConcepts
        """
        if not groups:
            logger.warning("No groups provided for concept extraction")
            return []

        video_id = groups[0].video_id
        logger.info(f"Processing {len(groups)} groups for concept extraction")

        # Check if concepts already exist
        if skip_existing:
            existing = self.repository.get_by_video(video_id)
            if existing:
                logger.info(f"Concepts already exist for {video_id}, skipping")
                return self._reconstruct_from_existing(existing, groups)

        extracted_list = []
        success_count = 0
        failed_count = 0

        for group in groups:
            try:
                logger.info(
                    f"Extracting concepts from group {group.group_id} ({len(group.segments)} segments)"
                )

                # Extract concepts
                extracted = self.extractor.extract_from_group(
                    video_id=group.video_id,
                    group_id=group.group_id,
                    group_text=group.text,
                    start_time=group.start_time,
                    end_time=group.end_time,
                )

                # Store in database
                success, failed = self.repository.upsert_concepts(extracted.concepts)
                success_count += success
                failed_count += failed

                extracted_list.append(extracted)
                logger.info(
                    f"Extracted {len(extracted.concepts)} concepts from group {group.group_id}"
                )

                # Rate limiting
                if self.delay_seconds > 0:
                    time.sleep(self.delay_seconds)

            except Exception as e:
                logger.error(f"Failed to process group {group.group_id}: {e}")
                failed_count += 1
                continue

        logger.info(
            f"Concept extraction complete: {success_count} concepts stored, {failed_count} failed"
        )
        return extracted_list

    def _reconstruct_from_existing(
        self, existing: List[dict], groups: List[SegmentGroup]
    ) -> List[ExtractedConcepts]:
        """Reconstruct ExtractedConcepts from existing database records.

        Args:
            existing: List of concept dictionaries from database
            groups: Original groups for context

        Returns:
            List of ExtractedConcepts
        """
        from collections import defaultdict

        grouped: dict[int, List[Concept]] = defaultdict(list)
        group_map = {g.group_id: g.text for g in groups}

        # Group concepts by group_id
        for record in existing:
            concept = Concept(
                name=record["name"],
                definition=record.get("definition", ""),
                type=record.get("type", "Concept"),
                importance=float(record.get("importance", 0.5)),
                confidence=float(record.get("confidence", 0.5)),
                video_id=record.get("videoId", ""),
                group_id=int(record.get("groupId", 0)),
                first_mention_time=float(record.get("firstMentionTime", 0.0)),
                last_mention_time=float(record.get("lastMentionTime", 0.0)),
                mention_count=int(record.get("mentionCount", 1)),
                aliases=record.get("aliases", []) or [],
                extracted_at=record.get("extractedAt"),
                id=record.get("id"),
            )
            grouped[concept.group_id].append(concept)

        # Create ExtractedConcepts objects
        extracted_list = []
        for group_id, concepts in grouped.items():
            group_text = group_map.get(group_id, "")
            video_id = concepts[0].video_id if concepts else ""

            extracted_list.append(
                ExtractedConcepts(
                    video_id=video_id,
                    group_id=group_id,
                    group_text=group_text,
                    concepts=concepts,
                )
            )

        return extracted_list
