"""Data models for concepts and concept mentions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import NAMESPACE_URL, UUID, uuid5


class ConceptType(Enum):
    """Types of concepts that can be extracted."""

    PERSON = "Person"
    ORGANIZATION = "Organization"
    TECHNOLOGY = "Technology"
    METHOD = "Method"
    PROBLEM = "Problem"
    SOLUTION = "Solution"
    CONCEPT = "Concept"  # Abstract ideas, principles
    METRIC = "Metric"
    DATASET = "Dataset"
    EVENT = "Event"
    PLACE = "Place"

    @classmethod
    def from_string(cls, value: str) -> ConceptType:
        """Convert string to ConceptType, default to CONCEPT if invalid."""
        try:
            return cls(value)
        except ValueError:
            return cls.CONCEPT


@dataclass(slots=True)
class Concept:
    """Represents a distinct idea, entity, or topic extracted from a group.

    This is the canonical representation of a concept - deduplicated and normalized.
    """

    # Core properties
    name: str
    definition: str
    type: ConceptType
    importance: float
    confidence: float

    # Source tracking
    video_id: str
    group_id: int

    # Temporal information
    first_mention_time: float
    last_mention_time: float
    mention_count: int

    # Optional metadata
    aliases: list[str] = field(default_factory=list)
    extracted_at: datetime = field(default_factory=datetime.utcnow)

    # Weaviate ID (computed)
    id: Optional[UUID] = None

    def __post_init__(self):
        """Validate and normalize after initialization."""
        # Normalize name
        self.name = self.name.strip()
        if len(self.name) < 2:
            raise ValueError(f"Concept name too short: {self.name}")
        if len(self.name) > 100:
            self.name = self.name[:100]

        # Normalize definition
        self.definition = self.definition.strip()
        if len(self.definition) < 10:
            raise ValueError(
                f"Definition too short for '{self.name}': {self.definition}"
            )
        if len(self.definition) > 500:
            self.definition = self.definition[:500]

        # Ensure type is ConceptType enum
        if isinstance(self.type, str):
            self.type = ConceptType.from_string(self.type)

        # Clamp scores to valid range
        self.importance = max(0.0, min(1.0, self.importance))
        self.confidence = max(0.0, min(1.0, self.confidence))

        # Ensure mention count is positive
        if self.mention_count < 1:
            self.mention_count = 1

        # Generate deterministic UUID if not set
        if self.id is None:
            self.id = self._generate_uuid()

    def _generate_uuid(self) -> UUID:
        """Generate deterministic UUID based on video_id, group_id, and name."""
        key = f"{self.video_id}:{self.group_id}:{self.name.lower()}"
        return uuid5(NAMESPACE_URL, key)

    def as_weaviate_properties(self) -> dict:
        """Convert to Weaviate property dictionary.

        Returns:
            Dictionary ready for Weaviate upload
        """
        # Format datetime as RFC3339 with 'Z' suffix for UTC
        extracted_at_rfc3339 = self.extracted_at.isoformat() + "Z"
        
        return {
            "name": self.name,
            "definition": self.definition,
            "type": self.type.value,
            "importance": float(self.importance),
            "confidence": float(self.confidence),
            "aliases": self.aliases,
            "videoId": self.video_id,
            "groupId": int(self.group_id),
            "firstMentionTime": float(self.first_mention_time),
            "lastMentionTime": float(self.last_mention_time),
            "mentionCount": int(self.mention_count),
            "extractedAt": extracted_at_rfc3339,
        }

    @property
    def duration(self) -> float:
        """Duration in seconds from first to last mention."""
        return self.last_mention_time - self.first_mention_time

    @property
    def embedding_text(self) -> str:
        """Text to be embedded for vector search."""
        return f"{self.name}. {self.definition}"

    def __repr__(self) -> str:
        return f"Concept(name={self.name!r}, type={self.type.value}, importance={self.importance:.2f})"


@dataclass(slots=True)
class ConceptMention:
    """Represents a specific occurrence of a concept in transcript text.

    This enables fine-grained traceability and salience analysis.
    """

    # Core properties
    surface: str  # Exact text span
    timestamp: float  # When this occurs in video
    salience: float  # Local importance (0.0-1.0)

    # Source tracking
    video_id: str
    group_id: int

    # Reference to canonical concept
    concept_id: UUID

    # Optional text offsets
    offset_start: Optional[int] = None
    offset_end: Optional[int] = None

    # Weaviate ID (computed)
    id: Optional[UUID] = None

    def __post_init__(self):
        """Validate and normalize after initialization."""
        # Normalize surface text
        self.surface = self.surface.strip()
        if len(self.surface) < 2:
            raise ValueError(f"Surface text too short: {self.surface}")
        if len(self.surface) > 500:
            self.surface = self.surface[:500]

        # Clamp salience to valid range
        self.salience = max(0.0, min(1.0, self.salience))

        # Validate offsets
        if self.offset_start is not None and self.offset_end is not None:
            if self.offset_end <= self.offset_start:
                raise ValueError(
                    f"Invalid offsets: end ({self.offset_end}) <= start ({self.offset_start})"
                )

        # Generate deterministic UUID if not set
        if self.id is None:
            self.id = self._generate_uuid()

    def _generate_uuid(self) -> UUID:
        """Generate deterministic UUID based on concept, video, group, and timestamp."""
        key = f"{self.concept_id}:{self.video_id}:{self.group_id}:{self.timestamp:.6f}"
        return uuid5(NAMESPACE_URL, key)

    def as_weaviate_properties(self) -> dict:
        """Convert to Weaviate property dictionary.

        Returns:
            Dictionary ready for Weaviate upload
        """
        props = {
            "surface": self.surface,
            "timestamp": float(self.timestamp),
            "salience": float(self.salience),
            "videoId": self.video_id,
            "groupId": int(self.group_id),
        }

        # Add optional offsets if present
        if self.offset_start is not None:
            props["offsetStart"] = int(self.offset_start)
        if self.offset_end is not None:
            props["offsetEnd"] = int(self.offset_end)

        return props

    def __repr__(self) -> str:
        return f"ConceptMention(surface={self.surface[:30]!r}..., salience={self.salience:.2f})"


@dataclass
class ExtractedConcepts:
    """Container for all concepts extracted from a group.

    This is what the LLM extraction pipeline produces.
    """

    video_id: str
    group_id: int
    group_text: str
    concepts: list[Concept]
    mentions: list[ConceptMention] = field(default_factory=list)

    # Metadata
    extraction_time: datetime = field(default_factory=datetime.utcnow)
    model_used: Optional[str] = None

    def __len__(self) -> int:
        """Number of concepts extracted."""
        return len(self.concepts)

    @property
    def avg_importance(self) -> float:
        """Average importance score across all concepts."""
        if not self.concepts:
            return 0.0
        return sum(c.importance for c in self.concepts) / len(self.concepts)

    @property
    def avg_confidence(self) -> float:
        """Average confidence score across all concepts."""
        if not self.concepts:
            return 0.0
        return sum(c.confidence for c in self.concepts) / len(self.concepts)

    @property
    def type_distribution(self) -> dict[str, int]:
        """Count of concepts by type."""
        distribution: dict[str, int] = {}
        for concept in self.concepts:
            type_name = concept.type.value
            distribution[type_name] = distribution.get(type_name, 0) + 1
        return distribution

    def validate(self) -> tuple[bool, list[str]]:
        """Validate extracted concepts for quality.

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check count
        if len(self.concepts) < 3:
            issues.append(f"Too few concepts: {len(self.concepts)} (expected 5-7)")
        elif len(self.concepts) > 10:
            issues.append(f"Too many concepts: {len(self.concepts)} (expected 5-7)")

        # Check confidence
        if self.avg_confidence < 0.6:
            issues.append(f"Low average confidence: {self.avg_confidence:.2f}")

        # Check for duplicates
        names = [c.name.lower() for c in self.concepts]
        if len(names) != len(set(names)):
            issues.append("Duplicate concept names detected")

        # Check type diversity
        type_dist = self.type_distribution
        if len(type_dist) < 2:
            issues.append("Low type diversity - all concepts of same type")

        return (len(issues) == 0, issues)

    def __repr__(self) -> str:
        return f"ExtractedConcepts(video={self.video_id}, group={self.group_id}, concepts={len(self.concepts)})"
