"""LLM-powered concept consolidation for two-pass extraction.

This module implements Pass 2 of the two-pass concept extraction system.
It takes candidate concepts from all groups and consolidates them into
a final, refined set of concepts with proper deduplication and relationship
detection.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional
from uuid import uuid4

import openai

from src.domain.concept import Concept, ConceptType, ExtractedConcepts
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ConceptConsolidator:
    """Consolidates candidate concepts from multiple groups into a refined final set."""

    # Prompt template for consolidation
    CONSOLIDATION_PROMPT = """Merge duplicate concepts from video segments. Return 1-20 final concepts.

**Candidates ({num_candidates} from {num_groups} groups):**
{candidates_json}

Output JSON:
{{
  "consolidatedConcepts": [
    {{
      "name": "Concept Name",
      "definition": "Definition",
      "type": "Concept",
      "importance": 0.8,
      "confidence": 0.9,
      "aliases": [],
      "firstMentionTime": 0.0,
      "lastMentionTime": 300.0,
      "mentionCount": 2,
      "groupIds": [0, 1],
      "sourceConceptIds": ["id1", "id2"]
    }}
  ],
  "consolidationMetadata": {{
    "totalCandidates": {num_candidates},
    "finalConceptCount": 15,
    "mergedGroups": {num_groups},
    "conversionRatio": 0.6
  }}
}}

Rules: Merge same concepts with different names. Importance: 0.9-1.0=core, 0.7-0.8=major, 0.5-0.6=supporting.
- Only keep concepts that are genuinely significant to understanding the video
- Aim for 15-30 final concepts (fewer for short videos, more for long ones)
"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        base_url: Optional[str] = None,
    ):
        """Initialize the concept consolidator.

        Args:
            api_key: API key (defaults to environment variables)
            model: Model to use (defaults to gpt-4o-mini)
            temperature: Lower temperature for more consistent consolidation
            base_url: Base URL for API
        """
        import os

        self.api_key = (
            api_key or os.getenv("LLM_BINDING_API_KEY") or os.getenv("OPENAI_API_KEY")
        )
        if not self.api_key:
            raise ValueError(
                "API key required for consolidation. Set LLM_BINDING_API_KEY or OPENAI_API_KEY"
            )

        self.model = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"
        self.base_url = base_url or os.getenv("LLM_BINDING_HOST")
        self.temperature = temperature

        # Initialize OpenAI client
        if self.base_url:
            self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
            logger.info(f"Initialized ConceptConsolidator with model: {self.model}")
            logger.info(f"Using custom endpoint: {self.base_url}")
        else:
            self.client = openai.OpenAI(api_key=self.api_key)
            logger.info(f"Initialized ConceptConsolidator with model: {self.model}")

    def consolidate(
        self, candidate_concepts: list[ExtractedConcepts], video_id: str
    ) -> list[Concept]:
        """Consolidate candidate concepts from multiple groups into final set.

        Args:
            candidate_concepts: List of ExtractedConcepts from all groups
            video_id: Video identifier

        Returns:
            List of consolidated Concept objects

        Raises:
            ConsolidationError: If consolidation fails
        """
        if not candidate_concepts:
            logger.warning("No candidate concepts to consolidate")
            return []

        # Flatten all candidates
        all_candidates = []
        for ec in candidate_concepts:
            all_candidates.extend(ec.concepts)

        if not all_candidates:
            logger.warning("No candidate concepts found in extracted groups")
            return []

        logger.info(
            f"Consolidating {len(all_candidates)} candidate concepts from {len(candidate_concepts)} groups"
        )

        # Prepare candidate data for LLM
        candidates_data = self._prepare_candidates_data(all_candidates)

        # Format the prompt
        prompt = self.CONSOLIDATION_PROMPT.format(
            video_id=video_id,
            num_groups=len(candidate_concepts),
            num_candidates=len(all_candidates),
            candidates_json=json.dumps(candidates_data, indent=2, ensure_ascii=False),
        )

        try:
            # Call LLM for consolidation
            logger.info("Calling LLM for concept consolidation...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Output ONLY valid JSON. No thinking, no explanation.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=8000,  # High limit for reasoning models
            )

            # Extract response - handle reasoning models
            message = response.choices[0].message
            raw_response = message.content
            if (
                not raw_response
                and hasattr(message, "reasoning_content")
                and message.reasoning_content
            ):
                raw_response = message.reasoning_content
                logger.warning(
                    f"LLM returned reasoning_content instead of content. "
                    f"Finish reason: {response.choices[0].finish_reason}"
                )
            consolidated_data = self._parse_response(raw_response)

            # Build final concepts
            final_concepts = self._build_consolidated_concepts(
                consolidated_data, video_id, all_candidates
            )

            # Log results
            metadata = consolidated_data.get("consolidationMetadata", {})
            logger.info(
                f"✅ Consolidation complete: {len(all_candidates)} candidates → {len(final_concepts)} final concepts"
            )
            if metadata:
                logger.info(f"   Merged groups: {metadata.get('mergedGroups', 'N/A')}")
                logger.info(
                    f"   Conversion ratio: {metadata.get('conversionRatio', 'N/A'):.2f}"
                )

            return final_concepts

        except Exception as e:
            raise ConsolidationError(f"Failed to consolidate concepts: {e}") from e

    def _prepare_candidates_data(self, candidates: list[Concept]) -> list[dict]:
        """Prepare candidate concepts data for LLM consumption.

        Args:
            candidates: List of candidate Concept objects

        Returns:
            List of dictionaries with candidate data
        """
        candidates_data = []

        for concept in candidates:
            candidates_data.append(
                {
                    "id": str(concept.id),
                    "name": concept.name,
                    "definition": concept.definition,
                    "type": concept.type.value,
                    "importance": concept.importance,
                    "confidence": concept.confidence,
                    "groupId": concept.group_id,
                    "firstMentionTime": concept.first_mention_time,
                    "lastMentionTime": concept.last_mention_time,
                    "mentionCount": concept.mention_count,
                    "aliases": concept.aliases,
                }
            )

        return candidates_data

    def _parse_response(self, raw_response: str) -> dict:
        """Parse LLM consolidation response.

        Args:
            raw_response: Raw text from LLM

        Returns:
            Parsed JSON dictionary

        Raises:
            ConsolidationError: If parsing fails
        """
        # Check if response is None or empty
        if not raw_response:
            raise ConsolidationError("LLM returned empty or None response")

        # Try to find JSON in the response
        json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = raw_response

        try:
            data = json.loads(json_str)

            if "consolidatedConcepts" not in data:
                raise ConsolidationError("Response missing 'consolidatedConcepts' key")

            if not isinstance(data["consolidatedConcepts"], list):
                raise ConsolidationError("'consolidatedConcepts' must be a list")

            return data

        except json.JSONDecodeError as e:
            raise ConsolidationError(f"Invalid JSON response: {e}") from e

    def _build_consolidated_concepts(
        self, consolidated_data: dict, video_id: str, source_candidates: list[Concept]
    ) -> list[Concept]:
        """Build final Concept objects from consolidated data.

        Args:
            consolidated_data: Parsed consolidation response
            video_id: Video identifier
            source_candidates: Original candidate concepts for reference

        Returns:
            List of final Concept objects
        """
        final_concepts = []

        for concept_dict in consolidated_data["consolidatedConcepts"]:
            try:
                # Extract fields
                name = concept_dict.get("name", "").strip()
                definition = concept_dict.get("definition", "").strip()
                type_str = concept_dict.get("type", "Concept")
                importance = float(concept_dict.get("importance", 0.5))
                confidence = float(concept_dict.get("confidence", 0.7))
                aliases = concept_dict.get("aliases", [])
                first_mention = float(concept_dict.get("firstMentionTime", 0.0))
                last_mention = float(concept_dict.get("lastMentionTime", 0.0))
                mention_count = int(concept_dict.get("mentionCount", 1))

                # Get group_id (use first group from groupIds, or 0 as fallback)
                group_ids = concept_dict.get("groupIds", [0])
                group_id = group_ids[0] if group_ids else 0

                if not name or not definition:
                    logger.warning("Skipping concept: missing name or definition")
                    continue

                # Create consolidated Concept
                concept = Concept(
                    id=uuid4(),  # New UUID for consolidated concept
                    name=name,
                    definition=definition,
                    type=ConceptType.from_string(type_str),
                    importance=importance,
                    confidence=confidence,
                    video_id=video_id,
                    group_id=group_id,
                    first_mention_time=first_mention,
                    last_mention_time=last_mention,
                    mention_count=mention_count,
                    aliases=aliases if isinstance(aliases, list) else [],
                )

                final_concepts.append(concept)

            except Exception as e:
                logger.warning(f"Failed to build consolidated concept: {e}")
                continue

        return final_concepts


class ConsolidationError(Exception):
    """Raised when concept consolidation fails."""

    pass
