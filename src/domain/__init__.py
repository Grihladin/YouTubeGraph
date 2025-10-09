"""Domain models - pure data structures with no external dependencies.

These models represent the core business entities and are shared across services.
"""

from .transcript import (
    TranscriptSegment,
    TranscriptResult,
    TranscriptJob,
)
from .group import SegmentGroup, SegmentNode, Neighbor
from .concept import Concept, ConceptType, ExtractedConcepts, ConceptMention
from .relationship import (
    Relationship,
    RelationshipType,
    ExtractedRelationships,
    DetectionMethod,
)

__all__ = [
    # Transcript models
    "TranscriptSegment",
    "TranscriptResult",
    "TranscriptJob",
    # Grouping models
    "SegmentGroup",
    "SegmentNode",
    "Neighbor",
    # Concept models
    "Concept",
    "ConceptType",
    "ExtractedConcepts",
    "ConceptMention",
    # Relationship models
    "Relationship",
    "RelationshipType",
    "ExtractedRelationships",
    "DetectionMethod",
]
