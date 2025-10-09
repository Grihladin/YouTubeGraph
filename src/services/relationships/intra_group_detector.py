"""Detect relationships within the same group using multiple heuristics."""

from __future__ import annotations

import re
from typing import Dict, Optional
from uuid import UUID

import numpy as np
from openai import OpenAI

from src.domain.concept import Concept, ExtractedConcepts
from src.domain.relationship import (
    DetectionMethod,
    Relationship,
    RelationshipType,
)


# Pattern definitions for different relationship types
RELATIONSHIP_PATTERNS = {
    RelationshipType.DEFINES: [
        r"{source}\s+(?:is|are|refers? to|means?|defined as)\s+{target}",
        r"{source}\s*[:\-]\s*{target}",
        r"{target}\s+(?:is|are)\s+(?:called|known as|termed)\s+{source}",
    ],
    RelationshipType.CAUSES: [
        r"{source}\s+(?:causes?|leads? to|results? in|produces?)\s+{target}",
        r"{target}\s+(?:is|are)\s+(?:caused by|due to|result of)\s+{source}",
        r"(?:because|since|as)\s+{source}.+{target}",
    ],
    RelationshipType.REQUIRES: [
        r"{source}\s+(?:requires?|needs?|depends? on|relies? on)\s+{target}",
        r"{target}\s+(?:is|are)\s+(?:required|needed|necessary)\s+(?:for|by)\s+{source}",
        r"(?:to|for)\s+{source}.+(?:need|require)\s+{target}",
    ],
    RelationshipType.CONTRADICTS: [
        r"{source}\s+(?:contradicts?|conflicts? with|opposes?)\s+{target}",
        r"{source}\s+(?:but|however|yet)\s+{target}",
        r"(?:unlike|contrary to|in contrast to)\s+{source}.+{target}",
    ],
    RelationshipType.EXEMPLIFIES: [
        r"{source}\s+(?:is|are)\s+(?:an?|one)\s+(?:example|instance)\s+of\s+{target}",
        r"{target}\s+(?:such as|like|including|e\.g\.|for example)\s+{source}",
        r"(?:for example|for instance|such as).+{source}.+{target}",
    ],
    RelationshipType.IMPLEMENTS: [
        r"{source}\s+(?:implements?|realizes?)\s+{target}",
        r"{target}\s+(?:is|are)\s+implemented (?:by|in|using)\s+{source}",
    ],
    RelationshipType.USES: [
        r"{source}\s+(?:uses?|utilizes?|employs?|applies?)\s+{target}",
        r"{target}\s+(?:is|are)\s+used (?:by|in|for)\s+{source}",
    ],
}


def normalize_for_pattern(text: str) -> str:
    """Normalize text for pattern matching (lowercase, collapse whitespace)."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def create_concept_regex(concept_name: str) -> str:
    """Create regex pattern for concept name with flexible matching.

    Handles:
    - Case insensitivity
    - Optional plural/possessive forms
    - Word boundaries
    """
    # Escape special regex characters
    escaped = re.escape(concept_name.lower())
    # Allow optional 's or 's at end (plural/possessive)
    escaped = escaped + r"(?:'?s)?"
    # Wrap in word boundaries
    return r"\b" + escaped + r"\b"


def find_relationship_in_text(
    text: str,
    source_concept: Concept,
    target_concept: Concept,
    rel_type: RelationshipType,
) -> Optional[tuple[str, float]]:
    """Try to find evidence of a specific relationship type in text.

    Args:
        text: Text to search
        source_concept: Source concept
        target_concept: Target concept
        rel_type: Relationship type to look for

    Returns:
        Tuple of (evidence_text, confidence_score) if found, None otherwise
    """
    if rel_type not in RELATIONSHIP_PATTERNS:
        return None

    normalized_text = normalize_for_pattern(text)

    # Create regex patterns for concept names
    source_pattern = create_concept_regex(source_concept.name)
    target_pattern = create_concept_regex(target_concept.name)

    # Try each pattern for this relationship type
    for pattern_template in RELATIONSHIP_PATTERNS[rel_type]:
        # Substitute concept patterns into template
        pattern = pattern_template.format(source=source_pattern, target=target_pattern)

        try:
            match = re.search(pattern, normalized_text, re.IGNORECASE)
            if match:
                # Extract matching text with some context
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                evidence = text[start:end].strip()

                # Confidence based on pattern specificity and concept importance
                base_confidence = 0.7
                importance_boost = (
                    source_concept.importance + target_concept.importance
                ) / 4
                confidence = min(0.95, base_confidence + importance_boost)

                return (evidence, confidence)
        except re.error:
            # Skip malformed patterns
            continue

    return None


def detect_proximity_relationship(
    source_concept: Concept,
    target_concept: Concept,
    group_text: str,
) -> Optional[tuple[RelationshipType, str, float]]:
    """Detect relationship based on proximity and co-occurrence in text.

    This is a fallback for concepts that appear close together but don't match
    explicit patterns. Uses a generic "uses" relationship.
    """
    normalized_text = normalize_for_pattern(group_text)

    source_pattern = create_concept_regex(source_concept.name)
    target_pattern = create_concept_regex(target_concept.name)

    # Find positions of both concepts
    source_matches = list(re.finditer(source_pattern, normalized_text, re.IGNORECASE))
    target_matches = list(re.finditer(target_pattern, normalized_text, re.IGNORECASE))

    if not source_matches or not target_matches:
        return None

    # Find closest pair
    min_distance = float("inf")
    closest_source = None
    closest_target = None

    for s_match in source_matches:
        for t_match in target_matches:
            distance = abs(s_match.start() - t_match.start())
            if distance < min_distance:
                min_distance = distance
                closest_source = s_match
                closest_target = t_match

    # If concepts are within 100 characters, consider them related
    PROXIMITY_THRESHOLD = 100
    if min_distance < PROXIMITY_THRESHOLD:
        # Extract evidence text
        start = min(closest_source.start(), closest_target.start())
        end = max(closest_source.end(), closest_target.end())
        start = max(0, start - 30)
        end = min(len(group_text), end + 30)
        evidence = group_text[start:end].strip()

        # Lower confidence for proximity-based detection
        confidence = 0.5 + (1 - min_distance / PROXIMITY_THRESHOLD) * 0.2

        # Use USES as generic relationship
        return (RelationshipType.USES, evidence, confidence)

    return None


class IntraGroupDetector:
    """Detects relationships within the same group."""

    def __init__(
        self,
        min_confidence: float = 0.6,
        openai_client: Optional[OpenAI] = None,
        vector_similarity_threshold: float = 0.6,
    ):
        """Initialize detector.

        Args:
            min_confidence: Minimum confidence threshold for relationships
            openai_client: Optional OpenAI client for embedding-based heuristics
            vector_similarity_threshold: Minimum cosine similarity to infer relationships
        """

        self.min_confidence = min_confidence
        self.openai_client = openai_client
        self.vector_similarity_threshold = vector_similarity_threshold
        self._embedding_cache: Dict[str, Optional[np.ndarray]] = {}

    def _get_embedding(self, concept: Concept) -> Optional[np.ndarray]:
        """Fetch or compute an embedding for a concept's definition text."""

        if not self.openai_client:
            return None

        concept_key = (
            str(concept.id)
            if concept.id is not None
            else f"{concept.video_id}:{concept.group_id}:{concept.name.lower()}"
        )
        if concept_key in self._embedding_cache:
            return self._embedding_cache[concept_key]

        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=concept.embedding_text,
                dimensions=1536,
            )
            vector = np.array(response.data[0].embedding, dtype=np.float32)
            self._embedding_cache[concept_key] = vector
            return vector
        except Exception as exc:  # pragma: no cover - external service
            print(
                f"Warning: Failed to compute embedding for concept '{concept.name}': {exc}"
            )
            self._embedding_cache[concept_key] = None
            return None

    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""

        denom = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        if denom == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / denom)

    def detect_relationships(
        self, extracted_concepts: ExtractedConcepts
    ) -> list[Relationship]:
        """Detect all relationships within a group.

        Args:
            extracted_concepts: Concepts extracted from a single group

        Returns:
            List of detected relationships
        """
        relationships = []
        concepts = extracted_concepts.concepts
        group_text = extracted_concepts.group_text

        # Try all pairs of concepts
        for i, source in enumerate(concepts):
            for j, target in enumerate(concepts):
                if i == j:
                    continue  # Skip self-relationships

                # Try explicit pattern matching for each relationship type
                for rel_type in RelationshipType:
                    if not rel_type.is_intra_group:
                        continue  # Only intra-group types

                    result = find_relationship_in_text(
                        group_text, source, target, rel_type
                    )

                    if result:
                        evidence, confidence = result

                        if confidence >= self.min_confidence:
                            relationship = Relationship(
                                source_concept_id=source.id,
                                target_concept_id=target.id,
                                type=rel_type,
                                confidence=confidence,
                                evidence=evidence,
                                detection_method=DetectionMethod.PATTERN_MATCHING,
                                source_video_id=source.video_id,
                                source_group_id=source.group_id,
                                target_video_id=target.video_id,
                                target_group_id=target.group_id,
                                temporal_distance=abs(
                                    source.first_mention_time
                                    - target.first_mention_time
                                ),
                            )
                            relationships.append(relationship)
                            break  # Found relationship for this pair, move on

                # If no explicit pattern found, try proximity-based detection
                if not any(
                    r.source_concept_id == source.id
                    and r.target_concept_id == target.id
                    for r in relationships
                ):
                    proximity_result = detect_proximity_relationship(
                        source, target, group_text
                    )

                    if proximity_result:
                        rel_type, evidence, confidence = proximity_result

                        if confidence >= self.min_confidence:
                            relationship = Relationship(
                                source_concept_id=source.id,
                                target_concept_id=target.id,
                                type=rel_type,
                                confidence=confidence,
                                evidence=evidence,
                                detection_method=DetectionMethod.PATTERN_MATCHING,
                                source_video_id=source.video_id,
                                source_group_id=source.group_id,
                                target_video_id=target.video_id,
                                target_group_id=target.group_id,
                                temporal_distance=abs(
                                    source.first_mention_time
                                    - target.first_mention_time
                                ),
                            )
                            relationships.append(relationship)

                # Fallback 3: semantic similarity of concept definitions
                if self.openai_client and not any(
                    r.source_concept_id == source.id
                    and r.target_concept_id == target.id
                    for r in relationships
                ):
                    source_vec = self._get_embedding(source)
                    target_vec = self._get_embedding(target)

                    if source_vec is not None and target_vec is not None:
                        similarity = self._cosine_similarity(source_vec, target_vec)

                        if similarity >= self.vector_similarity_threshold:
                            temporal_distance = abs(
                                source.first_mention_time - target.first_mention_time
                            )
                            evidence = (
                                "Concept definitions are semantically aligned "
                                f"(similarity {similarity:.2f})."
                            )
                            confidence = max(
                                self.min_confidence,
                                similarity * 0.6
                                + (source.confidence + target.confidence) / 4,
                            )

                            relationship = Relationship(
                                source_concept_id=source.id,
                                target_concept_id=target.id,
                                type=RelationshipType.USES,
                                confidence=confidence,
                                evidence=evidence,
                                detection_method=DetectionMethod.VECTOR_SIMILARITY,
                                source_video_id=source.video_id,
                                source_group_id=source.group_id,
                                target_video_id=target.video_id,
                                target_group_id=target.group_id,
                                temporal_distance=temporal_distance,
                            )
                            relationships.append(relationship)

        return relationships

    def __repr__(self) -> str:
        return f"IntraGroupDetector(min_confidence={self.min_confidence})"
