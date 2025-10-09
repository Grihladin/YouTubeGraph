# Phase 2: Relationship Detection - Implementation Summary

## Overview

Phase 2 implements **relationship detection** between concepts within a single video. This phase builds on Phase 1 (concept extraction) by identifying typed connections between concepts, creating a rich knowledge graph structure.

## Architecture

### Components

1. **Data Models** (`src/core/relationship_models.py`)
   - `RelationshipType`: Enum defining relationship types (defines, causes, requires, etc.)
   - `DetectionMethod`: How relationships are detected (pattern_matching, cue_phrase, vector_similarity, etc.)
   - `Relationship`: Core relationship data structure with source/target concepts
   - `ExtractedRelationships`: Container for batch relationship operations

2. **Intra-Group Detector** (`src/core/intra_group_detector.py`)
   - Detects relationships **within the same group**
   - Uses linguistic pattern matching (regex)
   - Identifies explicit relationships: defines, causes, requires, contradicts, exemplifies, implements, uses
   - Falls back to proximity-based detection for co-occurring concepts

3. **Inter-Group Detector** (`src/core/inter_group_detector.py`)
   - Detects relationships **across groups in the same video**
   - **Cue phrase detection**: "as mentioned earlier", "building on this", etc.
   - **Vector similarity**: Uses OpenAI embeddings to find semantically related concepts
   - **Temporal proximity**: Concepts close in time are likely related
   - Relationship types: builds_on, elaborates, references, refines

4. **Relationship Extractor** (`src/core/relationship_extractor.py`)
   - Orchestrates all detection methods
   - Processes single video at a time
   - Can load from Weaviate or JSON files
   - Saves results to JSON or uploads to Weaviate

5. **Relationship Uploader** (`src/core/relationship_uploader.py`)
   - Handles Weaviate upload with cross-references
   - Links relationships to source/target concepts
   - Supports batch operations
   - Provides delete/query utilities

## Relationship Types

### Intra-Group (Same Group)
- **defines**: A defines B
- **causes**: A causes B
- **requires**: A requires/depends on B
- **contradicts**: A contradicts B
- **exemplifies**: A is an example of B
- **implements**: A implements B
- **uses**: A uses B

### Inter-Group (Across Groups)
- **builds_on**: A builds on B (referenced from earlier)
- **elaborates**: A elaborates on B
- **references**: A references B
- **refines**: A refines/improves B

## Detection Methods

1. **Pattern Matching**
   - Uses regex patterns to match linguistic structures
   - Example: "X is Y", "X causes Y", "X requires Y"
   - Confidence: 0.7-0.95

2. **Cue Phrase Detection**
   - Identifies discourse markers
   - "as mentioned", "building on", "earlier", "going back to"
   - Confidence: 0.75-0.9

3. **Vector Similarity**
   - Computes semantic similarity using OpenAI embeddings
   - Threshold: 0.75 for inter-group, 0.80 for cross-video
   - Confidence: based on similarity score

4. **Temporal Proximity**
   - Concepts appearing within 5 minutes
   - Combined with vector similarity for higher confidence

## Neo4j Schema

### Node Labels & Constraints

- `(:Concept {id PRIMARY KEY})`
   - Properties: `name`, `definition`, `type`, `importance`, `confidence`, `aliases`, `videoId`, `groupId`, `firstMentionTime`, `lastMentionTime`, `mentionCount`, `extractedAt`
   - Constraint: `CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE`

- `(:ConceptMention {id PRIMARY KEY})`
   - Properties: `surface`, `timestamp`, `salience`, `videoId`, `groupId`, `offsetStart`, `offsetEnd`
   - Relationship: `(:ConceptMention)-[:MENTIONS]->(:Concept)`
   - Constraint: `CONSTRAINT mention_id IF NOT EXISTS FOR (m:ConceptMention) REQUIRE m.id IS UNIQUE`

- `[:GRAPH_RELATION {id PRIMARY KEY}]`
   - Properties: `type`, `confidence`, `evidence`, `detectionMethod`, `sourceVideoId`, `sourceGroupId`, `targetVideoId`, `targetGroupId`, `temporalDistance`, `extractedAt`
   - Constraint: `CONSTRAINT relationship_id IF NOT EXISTS FOR ()-[r:GRAPH_RELATION]-() REQUIRE r.id IS UNIQUE`

Constraints are provisioned automatically when `Neo4jGraph` is instantiated.

## Usage

### 1. Initialize Schema

Instantiate the Neo4j helper to ensure constraints are in place:

```bash
python scripts/init_concept_schema.py
```

### 2. Extract Relationships

Extract relationships for a video (requires concepts to already be extracted):

```bash
# From Neo4j (default)
python scripts/extract_relationships.py CUS6ABgI1As

# From JSON file
python scripts/extract_relationships.py CUS6ABgI1As --from-json

# Save to JSON
python scripts/extract_relationships.py CUS6ABgI1As --save

# Upload to Neo4j
python scripts/extract_relationships.py CUS6ABgI1As --upload
```

### 3. Visualize Relationships

Create an interactive graph visualization:

```bash
python scripts/visualize_relationships.py CUS6ABgI1As
```

This creates an HTML file at `output/graphs/relationships_CUS6ABgI1As.html` with:
- Interactive network graph
- Color-coded by concept type
- Sized by importance
- Labeled with relationship types
- Hover for details

## Example Output

```
🔍 Extracting relationships from 8 groups in video CUS6ABgI1As

📍 Phase 1: Intra-group relationships
  ✓ Found 12 intra-group relationships

🔗 Phase 2: Inter-group relationships
  ✓ Found 8 inter-group relationships

✅ Total relationships extracted: 20
   Average confidence: 0.78

📊 Type distribution:
   defines             : 5
   uses                : 4
   requires            : 3
   builds_on           : 4
   elaborates          : 2
   references          : 2

🔧 Detection method distribution:
   pattern_matching    : 12
   cue_phrase          : 4
   vector_similarity   : 4
```

## File Structure

```
src/core/
  ├── relationship_models.py      # Data models
  ├── intra_group_detector.py     # Within-group detection
  ├── inter_group_detector.py     # Across-group detection
  ├── relationship_extractor.py   # Main orchestrator
  └── relationship_uploader.py    # Weaviate upload

scripts/
  ├── init_concept_schema.py      # Schema initialization
  ├── extract_relationships.py    # Extraction script
  └── visualize_relationships.py  # Visualization script

output/
  ├── relationships/              # JSON output
  │   └── relationships_VIDEO_ID.json
  └── graphs/                     # Visualizations
      └── relationships_VIDEO_ID.html
```

## Integration with Phase 1

Phase 2 builds on Phase 1 concepts:
1. Load extracted concepts (from Weaviate or JSON)
2. Group concepts by video and group_id
3. Run intra-group detection
4. Run inter-group detection
5. Upload relationships with cross-references

## Performance Considerations

- **Intra-group**: Fast pattern matching, O(n²) per group
- **Inter-group**: Requires embeddings, API calls to OpenAI
- **Batch processing**: 100 relationships per batch for Weaviate
- **Caching**: Consider caching embeddings for frequently accessed concepts

## Future Enhancements (Phase 3+)

- LLM-based relationship extraction for implicit relationships
- Cross-video relationship detection
- Hierarchical relationship discovery (parent-child concepts)
- Relationship strength/weight learning
- Temporal evolution tracking
- Contradiction detection and resolution

## Limitations

- Currently single-video only (no cross-video relationships)
- Pattern matching requires explicit linguistic markers
- Vector similarity depends on embedding quality
- No confidence learning/adjustment over time
- Limited support for negation and complex conditionals

## Dependencies

- `weaviate-client`: Weaviate Python client
- `openai`: OpenAI API for embeddings
- `numpy`: Vector operations
- `python-dotenv`: Environment configuration
- `pyvis`: Network visualization (optional)

## Configuration

Environment variables (`.env`):
```bash
WEAVIATE_URL=https://your-cluster.weaviate.network
WEAVIATE_API_KEY=your-weaviate-api-key
OPENAI_API_KEY=your-openai-api-key
```

Tunable parameters:
- `min_confidence`: Minimum confidence threshold (default: 0.6)
- `similarity_threshold`: Vector similarity threshold (default: 0.75)
- `temporal_window`: Max time between related concepts (default: 300s)

## Testing

Run relationship extraction on test video:
```bash
# Extract concepts first (Phase 1)
python scripts/extract_concepts.py CUS6ABgI1As

# Extract relationships (Phase 2)
python scripts/extract_relationships.py CUS6ABgI1As --save

# Visualize
python scripts/visualize_relationships.py CUS6ABgI1As
```

Check output files:
- `output/relationships/relationships_CUS6ABgI1As.json`
- `output/graphs/relationships_CUS6ABgI1As.html`

## Troubleshooting

**No relationships found:**
- Check if concepts exist in Weaviate
- Lower `min_confidence` threshold
- Verify group text quality

**Low confidence scores:**
- Review pattern matching rules
- Adjust similarity thresholds
- Check embedding quality

**Missing cross-references:**
- Verify Concept collection exists
- Check concept IDs are valid UUIDs
- Ensure concepts uploaded before relationships

---

**Status**: ✅ Phase 2 Complete - Single Video Relationship Detection Implemented
**Next**: Phase 3 - Query Interface & Multi-Hop Reasoning
