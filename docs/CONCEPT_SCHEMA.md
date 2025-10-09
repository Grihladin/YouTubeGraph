# Concept Schema Design

## Overview

This document defines the schema for extracting and storing **concepts** from video transcript groups. Concepts represent the key ideas, entities, and themes discussed in videos, forming the foundation of our knowledge graph.

---

## Core Entities

### 1. Concept

A **Concept** represents a distinct idea, entity, or topic extracted from a group of transcript segments.

#### Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `id` | UUID | Yes | Auto-generated deterministic UUID |
| `name` | String | Yes | Canonical name (2-6 words, title case) |
| `definition` | Text | Yes | Clear 1-3 sentence explanation |
| `type` | Enum | Yes | Category of concept (see below) |
| `importance` | Float | Yes | Global significance (0.0-1.0) |
| `confidence` | Float | Yes | Extraction confidence (0.0-1.0) |
| `aliases` | String[] | No | Alternative names/spellings |
| `videoId` | String | Yes | Source video ID |
| `groupId` | Integer | Yes | Source group ID within video |
| `firstMentionTime` | Float | Yes | Timestamp of first appearance (seconds) |
| `lastMentionTime` | Float | Yes | Timestamp of last appearance (seconds) |
| `mentionCount` | Integer | Yes | Number of times mentioned in group |
| `extractedAt` | DateTime | Yes | When concept was extracted |

#### Vector Embedding

- **Source**: `name` + `definition` (concatenated)
- **Vectorizer**: OpenAI `text-embedding-3-small` or `text-embedding-ada-002`
- **Purpose**: Enable semantic search and similarity between concepts

---

### 2. ConceptMention (Optional but Recommended)

A **ConceptMention** represents a specific occurrence of a concept in the transcript text. This enables fine-grained traceability and salience analysis.

#### Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `id` | UUID | Yes | Auto-generated |
| `surface` | String | Yes | Exact text span from transcript |
| `offsetStart` | Integer | No | Character offset in group text |
| `offsetEnd` | Integer | No | Character offset end |
| `timestamp` | Float | Yes | When this mention occurs (seconds) |
| `salience` | Float | Yes | Local importance in this context (0.0-1.0) |
| `conceptId` | Reference | Yes | Cross-ref to Concept |
| `groupId` | Integer | Yes | Which group this mention is in |
| `videoId` | String | Yes | Source video |

#### Vector Embedding

- **Source**: `surface` (the actual text mention)
- **Vectorizer**: Same as Concept
- **Purpose**: Context-aware retrieval of specific mentions

---

## Concept Types (Enum)

We define 11 concept types based on common knowledge representation patterns:

| Type | Description | Examples |
|------|-------------|----------|
| `Person` | Individual humans or characters | "Albert Einstein", "The Speaker" |
| `Organization` | Companies, institutions, groups | "OpenAI", "United Nations" |
| `Technology` | Tools, frameworks, systems | "Neural Networks", "React Framework" |
| `Method` | Processes, techniques, approaches | "Gradient Descent", "Agile Development" |
| `Problem` | Challenges, issues, questions | "Climate Change", "Overfitting" |
| `Solution` | Answers, fixes, resolutions | "Carbon Capture", "Regularization" |
| `Concept` | Abstract ideas, principles | "Emergence", "Free Will", "Sustainability" |
| `Metric` | Measurements, KPIs | "Accuracy", "Response Time", "ROI" |
| `Dataset` | Data sources, corpora | "ImageNet", "Common Crawl" |
| `Event` | Occurrences, happenings | "World War II", "2008 Financial Crisis" |
| `Place` | Locations, regions | "Silicon Valley", "The Cloud" |

**Default**: When uncertain, use `Concept` as the catch-all type.

---

## Scoring Rubrics

### Importance Score (0.0 - 1.0)

Measures the **global significance** of a concept across the entire video/corpus.

| Score | Criteria |
|-------|----------|
| 0.9-1.0 | Central thesis, main topic, primary focus |
| 0.7-0.8 | Major supporting concept, key component |
| 0.5-0.6 | Relevant detail, supporting example |
| 0.3-0.4 | Minor reference, tangential mention |
| 0.0-0.2 | Passing mention, not elaborated |

### Confidence Score (0.0 - 1.0)

Measures the **extraction quality** and clarity of the concept.

| Score | Criteria |
|-------|----------|
| 0.9-1.0 | Explicitly named and defined in text |
| 0.7-0.8 | Clearly implied, strong contextual clues |
| 0.5-0.6 | Inferred from discussion, some ambiguity |
| 0.3-0.4 | Weak inference, needs validation |
| 0.0-0.2 | Speculative, low certainty |

### Salience Score (0.0 - 1.0) - For ConceptMention

Measures how **prominent** this specific mention is in its local context.

| Score | Criteria |
|-------|----------|
| 0.9-1.0 | Main focus of the sentence/paragraph |
| 0.7-0.8 | Important supporting detail |
| 0.5-0.6 | Relevant but not central |
| 0.3-0.4 | Background information |
| 0.0-0.2 | Passing reference |

---

## Relationships to Existing Schema

### Cross-References

```
Video (existing)
  ↓ contains
Group (from segment_grouper)
  ↓ contains
Segment (existing in Weaviate)
  ↓ mentions
Concept (new)
  ↓ has
ConceptMention (new, optional)
```

### Implementation Strategy

1. **Concept → Group**: Store `videoId` + `groupId` as properties
2. **ConceptMention → Concept**: Use Weaviate cross-reference
3. **Concept → Segment**: Indirect via group membership (can add direct refs later)

---

## Example Data

### Concept Example

```json
{
  "id": "c7e3f8a9-4b21-5c32-8d4e-9f1a2b3c4d5e",
  "name": "Temporal Decay Penalty",
  "definition": "A technique that reduces similarity scores between distant segments using exponential decay, preventing topic teleportation in semantic grouping.",
  "type": "Method",
  "importance": 0.85,
  "confidence": 0.95,
  "aliases": ["temporal penalty", "time decay", "exponential temporal decay"],
  "videoId": "HbDqLPm_2vY",
  "groupId": 3,
  "firstMentionTime": 245.8,
  "lastMentionTime": 312.4,
  "mentionCount": 4,
  "extractedAt": "2025-10-09T10:30:00Z"
}
```

### ConceptMention Example

```json
{
  "id": "m1a2b3c4-d5e6-7f8g-9h0i-1j2k3l4m5n6",
  "surface": "temporal decay penalty prevents topic teleportation",
  "offsetStart": 1234,
  "offsetEnd": 1286,
  "timestamp": 267.2,
  "salience": 0.92,
  "conceptId": "c7e3f8a9-4b21-5c32-8d4e-9f1a2b3c4d5e",
  "groupId": 3,
  "videoId": "HbDqLPm_2vY"
}
```

---

## Design Rationale

### Why This Schema?

1. **Separation of Concept vs. Mention**
   - Concepts are **canonical** (deduplicated, normalized)
   - Mentions are **instances** (traceable to exact text)
   - Enables both high-level reasoning and fine-grained citation

2. **Rich Metadata**
   - Timestamps enable temporal analysis
   - Scores enable filtering and ranking
   - Types enable category-specific queries

3. **Weaviate-Native**
   - Leverages vector search for concept similarity
   - Cross-references maintain graph structure
   - Scales to thousands of videos/concepts

4. **LLM-Friendly**
   - Clear extraction targets (name, definition, type, scores)
   - Structured output format (JSON)
   - Validation-ready fields

---

## Validation Rules

Before storing a concept, validate:

| Rule | Check | Action if Failed |
|------|-------|------------------|
| Name length | 2-100 characters | Skip or truncate |
| Definition length | 10-500 characters | Regenerate or skip |
| Type validity | Must be in enum | Default to "Concept" |
| Importance range | 0.0 ≤ x ≤ 1.0 | Clamp to range |
| Confidence range | 0.0 ≤ x ≤ 1.0 | Clamp to range |
| Mention count | > 0 | Set to 1 |
| Video/Group IDs | Must exist | Skip concept |

---

## Quality Metrics

Track these metrics after extraction:

| Metric | Target | Purpose |
|--------|--------|---------|
| Concepts per group | 5-7 | Ensure adequate extraction |
| Avg importance | 0.5-0.7 | Check for over/under-scoring |
| Avg confidence | ≥ 0.75 | Validate extraction quality |
| Type distribution | Diverse | Avoid type bias |
| Unique concepts per video | 80-95% | Check for redundancy |
| Alias coverage | 20-40% have aliases | Improve recall |

---

## Usage in Knowledge Graph

Once extracted, concepts enable:

1. **Semantic Search**: "Find all concepts related to machine learning"
2. **Concept Discovery**: "What new ideas are introduced in video X?"
3. **Cross-Video Linking**: "Which videos discuss neural networks?"
4. **Timeline Analysis**: "How does the speaker's explanation evolve?"
5. **RAG Enhancement**: Retrieve concepts → Expand with definitions → Generate response

---

## Next Steps

After implementing this schema:

1. **Phase 2**: Extract relationships between concepts (Part-Of, Causes, Requires, etc.)
2. **Phase 3**: Build hierarchical clustering (Concepts → Topics → Themes)
3. **Phase 4**: Cross-video concept matching and deduplication
4. **Phase 5**: Interactive query and visualization

---

## References

- Weaviate cross-reference docs: https://weaviate.io/developers/weaviate/manage-data/cross-references
- OpenAI embeddings: https://platform.openai.com/docs/guides/embeddings
- Knowledge graph design patterns: https://patterns.dataincubator.org/

---

**Status**: ✅ Schema defined, ready for implementation

**Author**: YouTubeGraph Team

**Last Updated**: October 9, 2025
