"""Detect relationships across groups in the same video using cue phrases, vector similarity, and temporal proximity."""

from __future__ import annotations

import re
from typing import Optional
from uuid import UUID

import numpy as np
from openai import OpenAI

from src.domain.concept import Concept, ExtractedConcepts
from src.domain.relationship import (
    DetectionMethod,
    Relationship,
    RelationshipType,
)


# Cue phrases that indicate cross-group relationships
CUE_PHRASES = {
    RelationshipType.BUILDS_ON: [
        r"(?:building|built) (?:on|upon)",
        r"(?:extending|extends?) (?:on|from)",
        r"taking (?:this|that|it) further",
        r"going deeper into",
        r"expanding on",
    ],
    RelationshipType.ELABORATES: [
        r"(?:more|further) detail(?:s|ed)?",
        r"(?:to|let me) elaborate",
        r"specifically",
        r"in particular",
        r"(?:diving|dig) deeper",
        r"(?:closer|detailed) look",
    ],
    RelationshipType.REFERENCES: [
        r"(?:as|like) (?:I|we) (?:mentioned|said|discussed)",
        r"(?:earlier|previously|before)",
        r"(?:remember|recall) (?:that|when)",
        r"(?:back|going back) to",
        r"(?:as|like) (?:discussed|talked about)",
    ],
    RelationshipType.REFINES: [
        r"(?:more|better|improved) (?:accurate|precise|refined)",
        r"(?:to be|more) (?:clear|specific)",
        r"(?:actually|in fact|really)",
        r"(?:correcting|correction)",
        r"(?:refining|refined)",
    ],
}


def normalize_text(text: str) -> str:
    """Normalize text for cue phrase detection."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def detect_cue_phrase_relationship(
    source_concept: Concept,
    target_concept: Concept,
    source_group_text: str,
    target_group_text: str,
) -> Optional[tuple[RelationshipType, str, float]]:
    """Detect relationship using cue phrase analysis.

    Args:
        source_concept: Concept from later group
        target_concept: Concept from earlier group
        source_group_text: Text of the later group
        target_group_text: Text of the earlier group

    Returns:
        Tuple of (relationship_type, evidence, confidence) if found
    """
    normalized_source = normalize_text(source_group_text)

    # Create regex for target concept name
    target_pattern = re.escape(target_concept.name.lower())

    # Look for cue phrases + target concept mention in source group
    for rel_type, patterns in CUE_PHRASES.items():
        for pattern in patterns:
            # Check if cue phrase appears in source text
            cue_match = re.search(pattern, normalized_source, re.IGNORECASE)
            if not cue_match:
                continue

            # Check if target concept is mentioned nearby (within 200 chars)
            cue_pos = cue_match.start()
            search_start = max(0, cue_pos - 100)
            search_end = min(len(normalized_source), cue_pos + 200)
            search_region = normalized_source[search_start:search_end]

            if re.search(r"\b" + target_pattern + r"\b", search_region):
                # Found cue phrase + concept mention!
                # Extract evidence
                evidence_start = max(0, cue_pos - 50)
                evidence_end = min(len(source_group_text), cue_pos + 150)
                evidence = source_group_text[evidence_start:evidence_end].strip()

                # Confidence based on pattern specificity
                confidence = 0.75 + (source_concept.importance * 0.15)

                return (rel_type, evidence, confidence)

    return None


def get_embedding(text: str, client: OpenAI) -> np.ndarray:
    """Get OpenAI embedding for text.

    Args:
        text: Text to embed
        client: OpenAI client

    Returns:
        Numpy array of embedding vector
    """
    response = client.embeddings.create(
        model="text-embedding-3-small", input=text, dimensions=1536
    )
    return np.array(response.data[0].embedding)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


class InterGroupDetector:
    """Detects relationships across groups in the same video."""

    def __init__(
        self,
        openai_client: Optional[OpenAI] = None,
        min_confidence: float = 0.6,
        similarity_threshold: float = 0.75,
        temporal_window: float = 300.0,  # 5 minutes
    ):
        """Initialize detector.

        Args:
            openai_client: Optional OpenAI client for embeddings (if None, only cue phrase detection is used)
            min_confidence: Minimum confidence threshold
            similarity_threshold: Minimum vector similarity for relationships
            temporal_window: Maximum time difference for temporal proximity (seconds)
        """
        self.openai_client = openai_client
        self.min_confidence = min_confidence
        self.similarity_threshold = similarity_threshold
        self.temporal_window = temporal_window

    def detect_relationships(
        self,
        all_extracted_concepts: list[ExtractedConcepts],
        video_id: str,
    ) -> list[Relationship]:
        """Detect relationships across groups in a video.

        Args:
            all_extracted_concepts: List of ExtractedConcepts for each group
            video_id: Video ID to process

        Returns:
            List of detected inter-group relationships
        """
        # Filter to this video and sort by group_id
        video_concepts = [
            ec for ec in all_extracted_concepts if ec.video_id == video_id
        ]
        video_concepts.sort(key=lambda ec: ec.group_id)

        relationships = []

        # Compare each group with later groups
        for i, source_group in enumerate(video_concepts):
            for j, target_group in enumerate(video_concepts):
                if j <= i:
                    continue  # Only look forward in time

                # Compare all concept pairs between these groups
                for source_concept in source_group.concepts:
                    for target_concept in target_group.concepts:
                        # Method 1: Cue phrase detection
                        cue_result = detect_cue_phrase_relationship(
                            source_concept,
                            target_concept,
                            source_group.group_text,
                            target_group.group_text,
                        )

                        if cue_result:
                            rel_type, evidence, confidence = cue_result

                            if confidence >= self.min_confidence:
                                temporal_distance = abs(
                                    source_concept.first_mention_time
                                    - target_concept.first_mention_time
                                )

                                relationship = Relationship(
                                    source_concept_id=source_concept.id,
                                    target_concept_id=target_concept.id,
                                    type=rel_type,
                                    confidence=confidence,
                                    evidence=evidence,
                                    detection_method=DetectionMethod.CUE_PHRASE,
                                    source_video_id=source_concept.video_id,
                                    source_group_id=source_concept.group_id,
                                    target_video_id=target_concept.video_id,
                                    target_group_id=target_concept.group_id,
                                    temporal_distance=temporal_distance,
                                )
                                relationships.append(relationship)
                                continue  # Found relationship, move to next pair

                        # Method 2: Vector similarity (skip if no OpenAI client)
                        if self.openai_client is None:
                            continue  # Skip embedding-based detection

                        try:
                            source_emb = get_embedding(
                                source_concept.embedding_text, self.openai_client
                            )
                            target_emb = get_embedding(
                                target_concept.embedding_text, self.openai_client
                            )

                            similarity = cosine_similarity(source_emb, target_emb)

                            if similarity >= self.similarity_threshold:
                                # High similarity suggests related concepts
                                temporal_distance = abs(
                                    source_concept.first_mention_time
                                    - target_concept.first_mention_time
                                )

                                # Check temporal proximity
                                if temporal_distance <= self.temporal_window:
                                    # Close in time + semantically similar = likely related
                                    evidence = f"Semantically similar concepts (similarity: {similarity:.2f}) appearing within {temporal_distance:.0f}s"

                                    confidence = (
                                        similarity * 0.7
                                        + (1 - temporal_distance / self.temporal_window)
                                        * 0.2
                                    )

                                    if confidence >= self.min_confidence:
                                        relationship = Relationship(
                                            source_concept_id=source_concept.id,
                                            target_concept_id=target_concept.id,
                                            type=RelationshipType.BUILDS_ON,
                                            confidence=confidence,
                                            evidence=evidence,
                                            detection_method=DetectionMethod.VECTOR_SIMILARITY,
                                            source_video_id=source_concept.video_id,
                                            source_group_id=source_concept.group_id,
                                            target_video_id=target_concept.video_id,
                                            target_group_id=target_concept.group_id,
                                            temporal_distance=temporal_distance,
                                        )
                                        relationships.append(relationship)

                        except Exception as e:
                            # Skip if embedding fails
                            print(
                                f"Warning: Failed to get embeddings for concepts: {e}"
                            )
                            continue

        return relationships

    def __repr__(self) -> str:
        return f"InterGroupDetector(min_confidence={self.min_confidence}, similarity_threshold={self.similarity_threshold})"
