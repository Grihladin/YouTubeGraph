# Phase 1 Complete: Scripts Ready

## ✅ All Scripts Implemented

### 1. Schema Initialization
```bash
python scripts/init_concept_schema.py
```
Creates Weaviate collections for concepts and concept mentions.

### 2. Concept Extraction
```bash
# Single video
python scripts/extract_concepts.py CUS6ABgI1As

# Multiple videos
python scripts/extract_concepts.py VIDEO1 VIDEO2

# All videos
python scripts/extract_concepts.py --all

# Force re-extraction
python scripts/extract_concepts.py --re-extract VIDEO_ID
```

### 3. Query Concepts
```bash
# View all concepts for video
python scripts/query_concepts.py CUS6ABgI1As

# Semantic search
python scripts/query_concepts.py --search "journalism"

# Quality analysis
python scripts/query_concepts.py --quality CUS6ABgI1As

# Database statistics
python scripts/query_concepts.py --stats
```

### 4. Visualize Concept Graph ✨ NEW
```bash
# Visualize single video
python scripts/visualize_concept_graph.py CUS6ABgI1As

# Overview of all videos
python scripts/visualize_concept_graph.py --all

# Compare two videos
python scripts/visualize_concept_graph.py --compare VIDEO1 VIDEO2
```

**Features:**
- ASCII bar charts for distributions
- Type and importance breakdowns
- Temporal timeline visualization
- Top concept rankings
- Alias coverage analysis

### 5. Extract Relationships ✨ NEW
```bash
# Analyze one video
python scripts/extract_relationships.py CUS6ABgI1As

# Analyze multiple videos
python scripts/extract_relationships.py VIDEO1 VIDEO2
```

**Features:**
- Co-occurrence analysis (concepts in same group)
- Temporal proximity (concepts in adjacent groups)
- Type-based relationship patterns
- Semantic similarity analysis
- Relationship strength scoring

---

## 🎯 Complete Workflow

```bash
# 1. Initialize schema (one-time setup)
python scripts/init_concept_schema.py

# 2. Extract concepts from your video
python scripts/extract_concepts.py CUS6ABgI1As

# 3. Query and validate
python scripts/query_concepts.py --quality CUS6ABgI1As

# 4. Visualize the concept graph
python scripts/visualize_concept_graph.py CUS6ABgI1As

# 5. Analyze relationships
python scripts/extract_relationships.py CUS6ABgI1As
```

---

## 📊 Example Output

### Visualization
```
======================================================================
📊 Concept Visualization: CUS6ABgI1As
======================================================================

📈 Overview:
   Total concepts: 25
   Avg importance: 0.68
   Avg confidence: 0.82

📊 Concept Types
======================================================================
Concept              ████████████████████████████ 8
Problem              ████████████████████ 5
Solution             ████████████████ 4
Method               ████████████ 3
Person               ██████ 2

📊 Importance Distribution
======================================================================
Critical (0.9-1.0)   ████ 2
High (0.7-0.9)       ████████████████ 8
Medium (0.5-0.7)     ████████████████████████ 12
Low (0.3-0.5)        ████ 2
Minimal (<0.3)       ██ 1

🏆 Top 10 Most Important Concepts:
----------------------------------------------------------------------

 1. Negative News Consumption (Problem)
    Importance: 0.90 | Confidence: 0.85
    Time: 4.8s - 397.6s (Group 0)
    The harmful practice of regularly consuming negative news...

 2. Hometown Heroes (Solution)
    Importance: 0.85 | Confidence: 0.90
    Time: 394.4s - 746.3s (Group 1)
    A journalism segment focused on highlighting positive...
```

### Relationship Analysis
```
======================================================================
🔗 Relationship Analysis: CUS6ABgI1As
======================================================================

🔗 Co-occurrence Analysis (Same Group)
----------------------------------------------------------------------

Found 18 co-occurrence relationships

Top 10 Co-occurrences:

 1. Negative News Consumption ↔ Shock and Awe Journalism
    Group: 1 | Strength: 0.85

 2. Hometown Heroes ↔ Good News Amplification
    Group: 1 | Strength: 0.82

⏱️  Temporal Proximity Analysis
----------------------------------------------------------------------

Found 24 temporal proximity relationships

Top 10 Temporal Relationships:

 1. Negative News Consumption → Good News Amplification
    Groups: 0 → 1 | Strength: 0.84

📊 Relationship Summary
======================================================================

Total relationships found:
  • Co-occurrence (same group): 18
  • Temporal proximity (adjacent): 24
  • Semantic similarity: 12
  • Total: 54
```

---

## 🎓 Understanding the Output

### Visualization Metrics

**Type Distribution**: Shows what kinds of concepts are in the video
- Concept, Problem, Solution, Method, etc.

**Importance Distribution**: How central concepts are to the video
- Critical: Main topic/thesis
- High: Major supporting concepts
- Medium: Relevant details
- Low: Minor references

**Temporal Timeline**: When concepts appear in the video
- Helps understand narrative flow
- Identifies dense concept regions

### Relationship Types

**Co-occurrence**: Concepts discussed together in same group
- Strength = min(importance of both concepts)
- Strong co-occurrence suggests related ideas

**Temporal Proximity**: Concepts in adjacent groups
- Strength = average importance
- Indicates topic transitions or continuations

**Semantic Similarity**: Concepts with similar embeddings
- Similarity score from vector search
- May indicate synonyms or related concepts

**Type-based Patterns**: Common type pairings
- Problem-Solution pairs
- Method-Technology associations
- Helps identify domain-specific patterns

---

## 🚀 Next Steps

### Phase 2: Full Relationship Extraction
The current relationship analysis is **foundational**. Phase 2 will add:

1. **LLM-based Extraction**
   - Explicit relationship types (Causes, Requires, Defines, etc.)
   - Confidence scores for relationships
   - Directional relationships

2. **Cross-Video Linking**
   - Match similar concepts across videos
   - Build global concept network
   - Track concept evolution

3. **Graph Storage**
   - Store relationships in Weaviate or Neo4j
   - Enable graph queries and traversal
   - Multi-hop reasoning

4. **Hierarchical Structure**
   - Concepts → Topics → Themes
   - Parent-child relationships
   - Abstraction levels

---

## 📁 Files Created

```
scripts/
├── visualize_concept_graph.py  ✨ NEW (230 lines)
└── extract_relationships.py    ✨ NEW (280 lines)
```

---

## ✅ Phase 1 Status: COMPLETE

All core functionality implemented:
- [x] Schema design and initialization
- [x] LLM-powered concept extraction
- [x] Weaviate storage and querying
- [x] Quality analysis and validation
- [x] Visualization and statistics
- [x] Relationship analysis (foundational)

**Ready for**: Phase 2 - Advanced Relationship Extraction

---

**Date**: October 9, 2025

**Try it now**:
```bash
python scripts/visualize_concept_graph.py CUS6ABgI1As
python scripts/extract_relationships.py CUS6ABgI1As
```
