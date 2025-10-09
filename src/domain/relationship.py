"""Data models for relationships between concepts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import NAMESPACE_URL, UUID, uuid5


class RelationshipType(Enum):
    """Types of relationships between concepts."""

    # Intra-group relationships (within same group)
    DEFINES = "defines"  # A defines B
    CAUSES = "causes"  # A causes B
    REQUIRES = "requires"  # A requires B
    CONTRADICTS = "contradicts"  # A contradicts B
    EXEMPLIFIES = "exemplifies"  # A exemplifies B (A is an example of B)
    IMPLEMENTS = "implements"  # A implements B (A is an implementation of B)
    USES = "uses"  # A uses B

    # Inter-group relationships (across groups in same video)
    BUILDS_ON = "builds_on"  # A builds on B (referenced from earlier)
    ELABORATES = "elaborates"  # A elaborates on B (provides more detail)
    REFERENCES = "references"  # A references B (mentioned earlier)
    REFINES = "refines"  # A refines B (improves or clarifies B)

    # Cross-video relationships (across different videos)
    COMPLEMENTS = "complements"  # A complements B (adds different perspective)
    CONTRADICTS_ACROSS = "contradicts_across"  # A contradicts B (different videos)
    EXTENDS = "extends"  # A extends B (builds on concept from another video)
    SIMILAR_TO = "similar_to"  # A is similar to B (related concepts)

    @classmethod
    def from_string(cls, value: str) -> RelationshipType:
        """Convert string to RelationshipType."""
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(f"Invalid relationship type: {value}")

    @property
    def is_intra_group(self) -> bool:
        """Check if this is an intra-group relationship."""
        return self in {
            RelationshipType.DEFINES,
            RelationshipType.CAUSES,
            RelationshipType.REQUIRES,
            RelationshipType.CONTRADICTS,
            RelationshipType.EXEMPLIFIES,
            RelationshipType.IMPLEMENTS,
            RelationshipType.USES,
        }

    @property
    def is_inter_group(self) -> bool:
        """Check if this is an inter-group relationship."""
        return self in {
            RelationshipType.BUILDS_ON,
            RelationshipType.ELABORATES,
            RelationshipType.REFERENCES,
            RelationshipType.REFINES,
        }

    @property
    def is_cross_video(self) -> bool:
        """Check if this is a cross-video relationship."""
        return self in {
            RelationshipType.COMPLEMENTS,
            RelationshipType.CONTRADICTS_ACROSS,
            RelationshipType.EXTENDS,
            RelationshipType.SIMILAR_TO,
        }


class DetectionMethod(Enum):
    """Method used to detect a relationship."""

    PATTERN_MATCHING = "pattern_matching"  # Explicit linguistic patterns
    CUE_PHRASE = "cue_phrase"  # Cue phrases like "as mentioned"
    VECTOR_SIMILARITY = "vector_similarity"  # Embedding similarity
    TEMPORAL_PROXIMITY = "temporal_proximity"  # Time-based proximity
    LLM_EXTRACTION = "llm_extraction"  # Extracted by LLM
    CROSS_REFERENCE = "cross_reference"  # Cross-video co-occurrence


@dataclass(slots=True)
class Relationship:
    """Represents a typed relationship between two concepts.

    This is a directed edge in the knowledge graph: source -> target.
    """

    # Core relationship
    source_concept_id: UUID  # "from" concept
    target_concept_id: UUID  # "to" concept
    type: RelationshipType  # relationship type
    confidence: float  # confidence score (0.0-1.0)

    # Evidence and context
    evidence: str  # Text supporting this relationship
    detection_method: DetectionMethod  # How was this detected

    # Source tracking
    source_video_id: str  # Video of source concept
    source_group_id: int  # Group of source concept
    target_video_id: str  # Video of target concept
    target_group_id: int  # Group of target concept

    # Optional temporal information
    temporal_distance: Optional[float] = None  # Time between mentions (seconds)

    # Metadata
    extracted_at: datetime = field(default_factory=datetime.utcnow)

    # Weaviate ID (computed)
    id: Optional[UUID] = None

    def __post_init__(self):
        """Validate and normalize after initialization."""
        # Ensure type is RelationshipType enum
        if isinstance(self.type, str):
            self.type = RelationshipType.from_string(self.type)

        # Ensure detection_method is DetectionMethod enum
        if isinstance(self.detection_method, str):
            self.detection_method = DetectionMethod(self.detection_method.lower())

        # Clamp confidence to valid range
        self.confidence = max(0.0, min(1.0, self.confidence))

        # Validate evidence
        self.evidence = self.evidence.strip()
        if len(self.evidence) < 10:
            raise ValueError(f"Evidence too short: {self.evidence}")
        if len(self.evidence) > 1000:
            self.evidence = self.evidence[:1000]

        # Validate temporal distance if present
        if self.temporal_distance is not None and self.temporal_distance < 0:
            raise ValueError(
                f"Invalid temporal_distance: {self.temporal_distance} (must be >= 0)"
            )

        # Generate deterministic UUID if not set
        if self.id is None:
            self.id = self._generate_uuid()

    def _generate_uuid(self) -> UUID:
        """Generate deterministic UUID based on source, target, and type."""
        key = f"{self.source_concept_id}:{self.target_concept_id}:{self.type.value}"
        return uuid5(NAMESPACE_URL, key)

    @property
    def is_same_video(self) -> bool:
        """Check if source and target are from the same video."""
        return self.source_video_id == self.target_video_id

    @property
    def is_same_group(self) -> bool:
        """Check if source and target are from the same group."""
        return self.is_same_video and self.source_group_id == self.target_group_id

    @property
    def is_cross_video(self) -> bool:
        """Check if this is a cross-video relationship."""
        return not self.is_same_video

    def as_weaviate_properties(self) -> dict:
        """Convert to Weaviate property dictionary.

        Returns:
            Dictionary ready for Weaviate upload
        """
        # Format datetime as RFC3339 with 'Z' suffix for UTC
        extracted_at_rfc3339 = self.extracted_at.isoformat() + "Z"

        props = {
            "type": self.type.value,
            "confidence": float(self.confidence),
            "evidence": self.evidence,
            "detectionMethod": self.detection_method.value,
            "sourceVideoId": self.source_video_id,
            "sourceGroupId": int(self.source_group_id),
            "targetVideoId": self.target_video_id,
            "targetGroupId": int(self.target_group_id),
            "extractedAt": extracted_at_rfc3339,
        }

        # Add optional temporal distance if present
        if self.temporal_distance is not None:
            props["temporalDistance"] = float(self.temporal_distance)

        return props

    def __repr__(self) -> str:
        return f"Relationship({self.type.value}: {self.source_concept_id} -> {self.target_concept_id}, confidence={self.confidence:.2f})"


@dataclass
class ExtractedRelationships:
    """Container for all relationships extracted from a video or set of videos.

    This is what the relationship extraction pipeline produces.
    """

    relationships: list[Relationship]

    # Metadata
    extraction_time: datetime = field(default_factory=datetime.utcnow)
    video_ids: list[str] = field(default_factory=list)
    model_used: Optional[str] = None

    def __len__(self) -> int:
        """Number of relationships extracted."""
        return len(self.relationships)

    @property
    def avg_confidence(self) -> float:
        """Average confidence score across all relationships."""
        if not self.relationships:
            return 0.0
        return sum(r.confidence for r in self.relationships) / len(self.relationships)

    @property
    def type_distribution(self) -> dict[str, int]:
        """Count of relationships by type."""
        distribution: dict[str, int] = {}
        for rel in self.relationships:
            type_name = rel.type.value
            distribution[type_name] = distribution.get(type_name, 0) + 1
        return distribution

    @property
    def detection_method_distribution(self) -> dict[str, int]:
        """Count of relationships by detection method."""
        distribution: dict[str, int] = {}
        for rel in self.relationships:
            method_name = rel.detection_method.value
            distribution[method_name] = distribution.get(method_name, 0) + 1
        return distribution

    def get_relationships_for_concept(self, concept_id: UUID) -> list[Relationship]:
        """Get all relationships where this concept is source or target."""
        return [
            r
            for r in self.relationships
            if r.source_concept_id == concept_id or r.target_concept_id == concept_id
        ]

    def get_intra_group_relationships(self) -> list[Relationship]:
        """Get all relationships within the same group."""
        return [r for r in self.relationships if r.is_same_group]

    def get_inter_group_relationships(self) -> list[Relationship]:
        """Get all relationships across groups in same video."""
        return [
            r for r in self.relationships if r.is_same_video and not r.is_same_group
        ]

    def get_cross_video_relationships(self) -> list[Relationship]:
        """Get all relationships across different videos."""
        return [r for r in self.relationships if r.is_cross_video]

    def validate(self) -> tuple[bool, list[str]]:
        """Validate extracted relationships for quality.

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check count
        if len(self.relationships) == 0:
            issues.append("No relationships extracted")

        # Check confidence
        if self.avg_confidence < 0.5:
            issues.append(
                f"Low average confidence: {self.avg_confidence:.2f} (expected >= 0.5)"
            )

        # Check for duplicates (same source, target, type)
        seen = set()
        for rel in self.relationships:
            key = (rel.source_concept_id, rel.target_concept_id, rel.type.value)
            if key in seen:
                issues.append(f"Duplicate relationship: {key}")
            seen.add(key)

        # Check type diversity
        type_dist = self.type_distribution
        if len(type_dist) < 2:
            issues.append("Low type diversity - all relationships of same type")

        return (len(issues) == 0, issues)

    def __repr__(self) -> str:
        return f"ExtractedRelationships(count={len(self.relationships)}, videos={len(self.video_ids)})"
