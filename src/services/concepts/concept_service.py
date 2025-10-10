"""High-level concept service orchestrating extraction and storage."""

from __future__ import annotations

import time
from typing import List, Optional

from src.domain.concept import ExtractedConcepts, Concept
from src.domain.group import SegmentGroup
from src.services.concepts.concept_extractor import ConceptExtractor
from src.services.concepts.concept_repository import ConceptRepository
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ConceptService:
    """Orchestrates two-pass concept extraction and storage operations."""

    def __init__(
        self,
        extractor: ConceptExtractor,
        repository: ConceptRepository,
        consolidator: Optional["ConceptConsolidator"] = None,
        delay_seconds: float = 0.5,
    ):
        """Initialize concept service.

        Args:
            extractor: Concept extractor instance (Pass 1)
            repository: Concept repository instance
            consolidator: Optional concept consolidator (Pass 2). If None, creates one automatically.
            delay_seconds: Delay between extractions (rate limiting)
        """
        self.extractor = extractor
        self.repository = repository
        self.delay_seconds = delay_seconds

        # Initialize consolidator (Pass 2)
        if consolidator is None:
            from src.services.concepts.concept_consolidator import ConceptConsolidator

            self.consolidator = ConceptConsolidator()
            logger.info("Initialized ConceptConsolidator for Pass 2")
        else:
            self.consolidator = consolidator

    def process_groups(
        self, groups: List[SegmentGroup], skip_existing: bool = False
    ) -> List[ExtractedConcepts]:
        """Extract and store concepts from groups using two-pass system.

        Pass 1: Extract candidate concepts from each group
        Pass 2: Consolidate all candidates into final refined set

        Args:
            groups: List of segment groups
            skip_existing: Whether to skip if concepts already exist

        Returns:
            List of ExtractedConcepts (one per group, with consolidated concepts)
        """
        if not groups:
            logger.warning("No groups provided for concept extraction")
            return []

        video_id = groups[0].video_id
        logger.info(f"🧠 TWO-PASS CONCEPT EXTRACTION for video {video_id}")
        logger.info(f"   Groups: {len(groups)}")

        # Check if concepts already exist
        if skip_existing:
            existing = self.repository.get_by_video(video_id)
            if existing:
                logger.info(f"Concepts already exist for {video_id}, skipping")
                return self._reconstruct_from_existing(existing, groups)

        # ═══════════════════════════════════════════════════════
        # PASS 1: Extract candidate concepts from each group
        # ═══════════════════════════════════════════════════════
        logger.info("\n" + "=" * 60)
        logger.info("🔍 PASS 1: Extracting candidate concepts from each group")
        logger.info("=" * 60)

        candidate_concepts = []
        total_candidates = 0

        for group in groups:
            try:
                logger.info(
                    f"  Group {group.group_id}: extracting candidates ({len(group.segments)} segments)..."
                )

                # Extract candidate concepts (Pass 1)
                extracted = self.extractor.extract_from_group(
                    video_id=group.video_id,
                    group_id=group.group_id,
                    group_text=group.text,
                    start_time=group.start_time,
                    end_time=group.end_time,
                )

                candidate_concepts.append(extracted)
                total_candidates += len(extracted.concepts)
                logger.info(
                    f"    ✓ Extracted {len(extracted.concepts)} candidate concepts"
                )

                # Rate limiting between groups
                if self.delay_seconds > 0:
                    time.sleep(self.delay_seconds)

            except Exception as e:
                logger.error(f"  ✗ Failed to process group {group.group_id}: {e}")
                continue

        logger.info(
            f"\n✅ Pass 1 complete: {total_candidates} candidate concepts from {len(candidate_concepts)} groups"
        )

        # ═══════════════════════════════════════════════════════
        # PASS 2: Consolidate candidates into final concepts
        # ═══════════════════════════════════════════════════════
        logger.info("\n" + "=" * 60)
        logger.info("🔄 PASS 2: Consolidating candidates into final concepts")
        logger.info("=" * 60)

        try:
            # Consolidate all candidates
            final_concepts = self.consolidator.consolidate(candidate_concepts, video_id)

            logger.info(f"\n✅ Pass 2 complete: {len(final_concepts)} final concepts")
            logger.info(
                f"   Consolidation ratio: {total_candidates} → {len(final_concepts)} ({len(final_concepts)/total_candidates*100:.1f}%)"
            )

        except Exception as e:
            logger.error(f"❌ Consolidation failed: {e}")
            logger.warning("Falling back to using all candidates without consolidation")
            # Fallback: use all candidates
            final_concepts = []
            for ec in candidate_concepts:
                final_concepts.extend(ec.concepts)

        # ═══════════════════════════════════════════════════════
        # STORAGE: Save final concepts to Neo4j
        # ═══════════════════════════════════════════════════════
        logger.info("\n" + "=" * 60)
        logger.info("💾 STORAGE: Saving final concepts to Neo4j")
        logger.info("=" * 60)

        success_count, failed_count = self.repository.upsert_concepts(final_concepts)

        logger.info(f"\n✅ Storage complete:")
        logger.info(f"   Stored: {success_count} concepts")
        logger.info(f"   Failed: {failed_count} concepts")

        # ═══════════════════════════════════════════════════════
        # RETURN: Reconstruct ExtractedConcepts for compatibility
        # ═══════════════════════════════════════════════════════
        # Group final concepts back by their original group_ids
        from collections import defaultdict

        grouped_final = defaultdict(list)
        for concept in final_concepts:
            grouped_final[concept.group_id].append(concept)

        # Create ExtractedConcepts objects
        result = []
        group_map = {g.group_id: g.text for g in groups}

        for group_id, concepts in grouped_final.items():
            result.append(
                ExtractedConcepts(
                    video_id=video_id,
                    group_id=group_id,
                    group_text=group_map.get(group_id, ""),
                    concepts=concepts,
                )
            )

        logger.info(f"\n🎉 TWO-PASS EXTRACTION COMPLETE")
        logger.info(
            f"   Final: {len(final_concepts)} concepts across {len(result)} groups"
        )

        return result

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
