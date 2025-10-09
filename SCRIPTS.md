# Scripts Documentation

Complete guide to all executable scripts in the YouTubeGraph project.

---

## 📋 Overview

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `pipeline.py` | Main processing pipeline | Process new videos |
| `init_weaviate_schema.py` | Setup Weaviate | **First time only** |
| `init_concept_schema.py` | Setup Neo4j | **First time only** |
| `test_pipeline.py` | Test full pipeline | Verify setup |
| `test_groups_quality.py` | Quality validation | After processing |
| `query_concepts.py` | Query knowledge graph | Explore results |
| `diagnose_embeddings.py` | Debug low quality | Troubleshooting |
| `visualize_groups.py` | Group analytics | Deep analysis |
| `visualize_concept_graph.py` | Concept visualization | Graph exploration |
| `visualize_relationships.py` | Relationship visualization | Connection analysis |

---

## 🚀 Core Scripts

### 1. `pipeline.py` - Main Pipeline

**Purpose:** End-to-end video processing (transcript → groups → concepts → relationships)

**Usage:**
```bash
# Interactive mode (prompts for URL)
python scripts/pipeline.py

# Or use programmatically
python -c "
from scripts.pipeline import YouTubeGraphPipeline
pipeline = YouTubeGraphPipeline()
result = pipeline.process_video('https://youtube.com/watch?v=VIDEO_ID')
print(f'✅ Processed: {result.segment_count} segments, {result.concept_count} concepts')
pipeline.close()
"
```

**What it does:**
1. Fetches YouTube transcript
2. Restores punctuation with AI
3. Segments into 150-300 word chunks
4. Uploads to Weaviate (with OpenAI embeddings)
5. Groups semantically into 400-800 word topics
6. Extracts concepts using GPT-4o-mini
7. Detects relationships between concepts
8. Stores everything in Neo4j

**Output:**
```
✅ Processing: https://youtube.com/watch?v=VIDEO_ID

📥 Step 1-3: Fetching transcript and processing...
✓ Fetched transcript (180 segments)
✓ Restored punctuation
✓ Segmented (180 segments, 150-300 words each)

⬆️ Step 4: Uploading to Weaviate...
✓ Uploaded 180 segments

🔗 Step 5: Semantic grouping...
✓ Created 22 groups (avg 650 words, cohesion 0.82)

🧠 Step 6: Extracting concepts...
✓ Extracted 137 concepts from 22 groups

🕸️ Step 7: Detecting relationships...
✓ Found 89 relationships

💾 Step 8: Storing in Neo4j...
✓ Stored 137 concepts and 89 relationships

✅ COMPLETE!
   Video: VIDEO_ID
   Segments: 180
   Groups: 22
   Concepts: 137
   Relationships: 89
```

**Configuration:**
```python
from scripts.pipeline import YouTubeGraphPipeline

pipeline = YouTubeGraphPipeline(
    # Override config if needed
    config=custom_config
)
```

**When to use:**
- Processing any new YouTube video
- Batch processing multiple videos
- Updating existing videos with new analysis

---

### 2. `test_pipeline.py` - Pipeline Testing

**Purpose:** Verify that the entire pipeline works correctly

**Usage:**
```bash
python scripts/test_pipeline.py
```

**What it does:**
Tests the full pipeline with a known video to ensure:
- All services initialize correctly
- Video processing completes successfully
- All components (Weaviate, Neo4j, OpenAI) are accessible
- Output is generated correctly

**When to use:**
- After initial setup
- After configuration changes
- Before processing important videos
- When troubleshooting errors

---

## ⚙️ Setup Scripts (Run Once)

### 3. `init_weaviate_schema.py` - Weaviate Setup

**Purpose:** Create and verify Weaviate collection schema

**Usage:**
```bash
# Basic setup
python scripts/init_weaviate_schema.py

# With statistics
python scripts/init_weaviate_schema.py --stats

# Force recreation (⚠️ deletes data)
python scripts/init_weaviate_schema.py --force

# Custom collection name
python scripts/init_weaviate_schema.py --collection MySegments

# Full help
python scripts/init_weaviate_schema.py --help
```

**What it creates:**

Collection: `Segment`

| Property | Type | Description | Indexed | Vectorized |
|----------|------|-------------|---------|------------|
| `videoId` | TEXT | YouTube video ID | ✅ Filterable | ❌ |
| `text` | TEXT | Segment content | 🔍 Searchable | ✅ OpenAI |
| `start_s` | NUMBER | Start timestamp (seconds) | ✅ Filterable | ❌ |
| `end_s` | NUMBER | End timestamp (seconds) | ✅ Filterable | ❌ |
| `tokens` | INT | Word count | ✅ Filterable | ❌ |

**Vectorizer:** OpenAI `text-embedding-3-small` (1536 dimensions)

**Output:**
```
🔌 Connecting to Weaviate...
✓ Connected successfully

🔨 Creating collection 'Segment'...
✅ Created collection with OpenAI text2vec vectorizer

🔍 Verifying schema...
✓ Collection name: Segment
✓ Vectorizer: text2vec_openai
✓ Properties (5): videoId, text, start_s, end_s, tokens

📊 Collection Statistics:
   Total segments: 0
   Unique videos: 0

✅ Collection 'Segment' created successfully!
```

**When to use:**
- **Before first video upload** (required)
- After Weaviate reset/migration
- To verify schema is correct
- To recreate collection (with `--force`)

**Troubleshooting:**
```bash
# If collection exists and you get errors:
python scripts/init_weaviate_schema.py --force

# Check current state:
python scripts/init_weaviate_schema.py --stats
```

---

### 4. `init_concept_schema.py` - Neo4j Setup

**Purpose:** Create Neo4j constraints and indexes

**Usage:**
```bash
# Basic setup
python scripts/init_concept_schema.py

# With statistics
python scripts/init_concept_schema.py --stats

# Reset specific video data
python scripts/init_concept_schema.py --reset-video VIDEO_ID

# Full help
python scripts/init_concept_schema.py --help
```

**What it creates:**

**Node Types:**
- `Concept` - Extracted concepts (entities, methods, ideas)
- `ConceptMention` - Specific mentions in transcript

**Constraints:**
- Unique concept IDs
- Indexed by video ID, name, type

**Relationships:**
- `REQUIRES` - Prerequisites
- `IMPLEMENTS` - Implementation
- `PART_OF` - Composition
- `CAUSES` - Causation
- `SIMILAR_TO` - Similarity
- `PRECEDES` - Temporal order

**Output:**
```
✅ Ensured Neo4j constraints for Concept and ConceptMention

📊 Neo4j Summary:
  Concepts stored: 0
  Relationships stored: 0
  Collections available: Concept, ConceptMention, Relationship

✓ Neo4j connection closed
```

**When to use:**
- **Before first concept extraction** (required)
- After Neo4j reset/migration
- To reset data for specific video

---

## 🔍 Quality & Analysis Scripts

### 5. `test_groups_quality.py` - Quality Validation ⭐

**Purpose:** Comprehensive quality analysis of semantic grouping

**Usage:**
```bash
# Test default videos (from quality_test_*.json files)
python scripts/test_groups_quality.py

# Test specific videos
python scripts/test_groups_quality.py VIDEO_ID1 VIDEO_ID2 VIDEO_ID3

# Full help
python scripts/test_groups_quality.py --help
```

**What it analyzes:**

1. **Basic Statistics**
   - Total groups, segments, words
   - Video duration

2. **Word Count Distribution**
   - Min, max, mean, median
   - Percentage in target range (400-800)
   - Pass/fail criteria

3. **Cohesion Analysis**
   - Average internal similarity
   - Distribution of cohesion scores
   - High-cohesion group percentage

4. **Temporal Analysis**
   - Group durations
   - Time gaps between groups
   - Coverage percentage

5. **Quality Score** (0-4 scale)
   - 0: Failed (major issues)
   - 1: Poor (needs tuning)
   - 2: Fair (acceptable)
   - 3: Good (recommended)
   - 4: Excellent (optimal)

6. **Visual Timeline**
   - ASCII-based group visualization
   - Shows group boundaries
   - Highlights cohesion levels

**Output:**
```
================================================================================
📊 QUALITY REPORT: VIDEO_ID
================================================================================

📈 Basic Statistics:
   • Total groups: 22
   • Total segments: 180
   • Total words: 14,520
   • Video duration: 45.3 minutes

📊 Word Count Distribution:
   • Min:    412
   • Max:    792
   • Mean:   660
   • Median: 648
   • In target range (400-800): 21/22 (95%)
   ✅ PASS: ≥70% groups in target range

🔗 Cohesion Distribution:
   • Min:    0.68
   • Max:    0.94
   • Mean:   0.82
   • Median: 0.83
   • High cohesion (≥0.70): 20/22 (91%)
   ✅ PASS: Average cohesion ≥ 0.70

⏱️ Duration Analysis:
   • Min:    25.3s
   • Max:    185.7s
   • Mean:   98.4s
   • Median: 95.2s

📈 QUALITY SCORE: 4/4 ⭐⭐⭐⭐

🎯 VERDICT: EXCELLENT
   This is high-quality grouping ready for concept extraction!
```

**When to use:**
- **After processing any video** (recommended)
- Before concept extraction
- When tuning grouping parameters
- To compare multiple videos

---

### 6. `diagnose_embeddings.py` - Debug Tool

**Purpose:** Diagnose low cohesion or embedding quality issues

**Usage:**
```bash
python scripts/diagnose_embeddings.py VIDEO_ID

# Example
python scripts/diagnose_embeddings.py CUS6ABgI1As
```

**What it checks:**

1. **Embedding Coverage**
   - How many segments have embeddings
   - Missing embeddings indicate vectorizer issues

2. **Adjacent Similarity**
   - Similarity between consecutive segments
   - Should be moderate (0.65-0.85)

3. **k-NN Neighborhoods**
   - Average similarity to neighbors
   - Distribution of neighbor similarities

4. **Problematic Patterns**
   - Very low similarities (< 0.50)
   - Very high similarities (> 0.95)
   - Unusual distributions

**Output:**
```
================================================================================
🔬 DIAGNOSTIC REPORT: VIDEO_ID
================================================================================

📥 Fetching segments...
✓ Found 180 segments

📊 Embedding Coverage:
   • Segments with embeddings: 180/180 (100%)
   ✅ All segments have embeddings

🔍 Adjacent Segment Similarity Analysis:
   Sampling 20 consecutive pairs...

   Segment 0 → 1:
      Similarity: 0.782
      Time gap: 2.3s
      Text 0: Today we'll discuss neural networks...
      Text 1: A neural network consists of layers...

   [... 19 more pairs ...]

📊 Overall Statistics:
   • Mean adjacent similarity: 0.756
   • Std deviation: 0.092
   • Min: 0.612
   • Max: 0.891

✅ GOOD: Mean similarity in healthy range (0.70-0.85)

🔍 k-NN Neighborhood Analysis:
   Testing 5 random segments...

   Segment 42 (245.8s):
      Text: Gradient descent is an optimization...
      Avg neighbor similarity: 0.812
      ✅ Strong neighborhood

📊 Recommendation:
   • Embeddings are high quality
   • Current parameters should work well
   • Suggested k_neighbors: 8
   • Suggested thresholds: 0.75-0.80
```

**When to use:**
- When quality scores are low (< 0.60 cohesion)
- Before tuning grouping parameters
- To understand video-specific characteristics
- When groups seem fragmented or oversized

---

### 7. `visualize_groups.py` - Group Analytics

**Purpose:** Visualize and analyze existing group JSON files

**Usage:**
```bash
# Visualize all groups in output/groups/
python scripts/visualize_groups.py

# Visualize specific pattern
python scripts/visualize_groups.py 'groups_*.json'
python scripts/visualize_groups.py 'quality_test_*.json'

# Specific file
python scripts/visualize_groups.py output/groups/groups_VIDEO_ID.json
```

**What it shows:**

1. **Summary Statistics**
   - Total groups, segments, words
   - Average group size and cohesion

2. **Timeline Visualization**
   - Visual representation of groups
   - Time spans and boundaries

3. **Distribution Plots** (ASCII)
   - Word count distribution
   - Cohesion distribution
   - Duration distribution

4. **Boundary Analysis**
   - Time gaps between groups
   - Potential merge candidates

5. **Outlier Detection**
   - Unusually small/large groups
   - Low cohesion groups

6. **Detailed Group Breakdown**
   - First 5 and last 5 groups
   - Full details for each

**When to use:**
- Deep dive analysis of grouping results
- Understanding video structure
- Identifying problematic groups
- Comparing different grouping runs

---

## 🕸️ Knowledge Graph Scripts

### 8. `query_concepts.py` - Concept Queries

**Purpose:** Query and analyze concepts in Neo4j knowledge graph

**Usage:**
```bash
# View concepts for specific video
python scripts/query_concepts.py VIDEO_ID

# Semantic search across all videos
python scripts/query_concepts.py --search "neural networks"

# Quality analysis
python scripts/query_concepts.py --quality VIDEO_ID

# Database statistics
python scripts/query_concepts.py --stats

# Full help
python scripts/query_concepts.py --help
```

**Query Modes:**

**1. Video Concepts** (`VIDEO_ID`)
```bash
python scripts/query_concepts.py CUS6ABgI1As
```
Shows:
- All concepts extracted from video
- Grouped by type (Entity, Method, Concept, etc.)
- Sorted by importance
- With definitions and timestamps

**2. Semantic Search** (`--search "query"`)
```bash
python scripts/query_concepts.py --search "machine learning"
```
Finds:
- Concepts semantically similar to query
- Across all videos in database
- Ranked by relevance

**3. Quality Analysis** (`--quality VIDEO_ID`)
```bash
python scripts/query_concepts.py --quality CUS6ABgI1As
```
Analyzes:
- Concept extraction coverage
- Type distribution
- Importance scores
- Potential duplicates

**4. Database Statistics** (`--stats`)
```bash
python scripts/query_concepts.py --stats
```
Shows:
- Total concepts and relationships
- Videos processed
- Concepts per video
- Type breakdown

**Output Example:**
```
📊 CONCEPTS FOR VIDEO: CUS6ABgI1As

═══════════════════════════════════════════════════════════════

📦 ENTITY (12 concepts)

  🔷 TensorFlow (importance: 0.85, confidence: 0.92)
     Definition: An open-source machine learning framework...
     First mentioned: 245.8s
     Aliases: TF

  🔷 PyTorch (importance: 0.82, confidence: 0.90)
     Definition: A popular deep learning library...
     First mentioned: 312.4s

═══════════════════════════════════════════════════════════════

🔬 METHOD (18 concepts)

  🔹 Gradient Descent (importance: 0.95, confidence: 0.98)
     Definition: An optimization algorithm that...
     First mentioned: 180.2s
     Aliases: GD, gradient optimization

  🔹 Backpropagation (importance: 0.92, confidence: 0.96)
     Definition: Algorithm for computing gradients...
     First mentioned: 195.7s

═══════════════════════════════════════════════════════════════

💡 CONCEPT (25 concepts)

  💡 Neural Network (importance: 0.98, confidence: 0.99)
     Definition: A computational model inspired by...
     First mentioned: 120.5s
     Aliases: NN, artificial neural network

[... more concepts ...]

═══════════════════════════════════════════════════════════════

📈 SUMMARY:
   Total concepts: 137
   Unique videos: 1
   Avg importance: 0.78
   Avg confidence: 0.89
```

**When to use:**
- Explore extracted concepts
- Verify extraction quality
- Find concepts across videos
- Check database statistics

---

### 9. `visualize_concept_graph.py` - Graph Visualization

**Purpose:** Visualize concept network and relationships

**Usage:**
```bash
# Visualize specific video
python scripts/visualize_concept_graph.py VIDEO_ID

# Visualize all concepts
python scripts/visualize_concept_graph.py --all

# Filter by importance
python scripts/visualize_concept_graph.py VIDEO_ID --min-importance 0.8

# Full help
python scripts/visualize_concept_graph.py --help
```

**Output:**
- Interactive graph visualization
- Nodes: Concepts (colored by type)
- Edges: Relationships (labeled by type)
- Size: Based on importance scores

**When to use:**
- Understand concept relationships
- Find clusters and patterns
- Present extracted knowledge
- Identify key concepts

---

### 10. `visualize_relationships.py` - Relationship Analysis

**Purpose:** Analyze and visualize relationships between concepts

**Usage:**
```bash
# Visualize relationships for video
python scripts/visualize_relationships.py VIDEO_ID

# Filter by type
python scripts/visualize_relationships.py VIDEO_ID --type REQUIRES

# Filter by confidence
python scripts/visualize_relationships.py VIDEO_ID --min-confidence 0.8

# Full help
python scripts/visualize_relationships.py --help
```

**Shows:**
- All relationships for video/concepts
- Relationship types and counts
- Confidence scores
- Evidence text
- Network statistics

**When to use:**
- Explore concept connections
- Verify relationship quality
- Find dependency chains
- Analyze knowledge structure

---

## 🔧 Advanced Usage

### Programmatic Usage

All scripts can be used as Python modules:

```python
# Import pipeline
from scripts.pipeline import YouTubeGraphPipeline

# Initialize
pipeline = YouTubeGraphPipeline()

# Process video
result = pipeline.process_video("https://youtube.com/watch?v=VIDEO_ID")

# Access results
print(f"Segments: {result.segment_count}")
print(f"Groups: {result.group_count}")
print(f"Concepts: {result.concept_count}")
print(f"Relationships: {result.relationship_count}")

# Clean up
pipeline.close()
```

### Batch Processing

```python
from scripts.pipeline import YouTubeGraphPipeline
from pathlib import Path

pipeline = YouTubeGraphPipeline()

# Read URLs from file
urls = Path("videos.txt").read_text().strip().split("\n")

for url in urls:
    try:
        result = pipeline.process_video(url)
        print(f"✅ {result.video_id}: Success")
    except Exception as e:
        print(f"❌ {url}: {e}")

pipeline.close()
```

---

## 📊 Typical Workflow

### Complete Pipeline

```bash
# 1. Setup (one time)
python scripts/init_weaviate_schema.py --stats
python scripts/init_concept_schema.py --stats

# 2. Test setup
python scripts/test_pipeline.py

# 3. Process video
python scripts/pipeline.py
# (enter YouTube URL when prompted)

# 4. Validate quality
python scripts/test_groups_quality.py VIDEO_ID

# 5. Query results
python scripts/query_concepts.py VIDEO_ID

# 6. Visualize
python scripts/visualize_groups.py
python scripts/visualize_concept_graph.py VIDEO_ID
```

### Troubleshooting Workflow

```bash
# 1. Check embeddings
python scripts/diagnose_embeddings.py VIDEO_ID

# 2. Check quality metrics
python scripts/test_groups_quality.py VIDEO_ID

# 3. Analyze groups
python scripts/visualize_groups.py

# 4. Verify concepts
python scripts/query_concepts.py --quality VIDEO_ID
```

---

## 🆘 Common Issues

### Script Won't Run

```bash
# Check Python path
which python
python --version  # Should be 3.10+

# Check dependencies
pip install -r requirements.txt

# Check .env file exists
cat .env
```

### "Collection not found"

```bash
# Initialize Weaviate
python scripts/init_weaviate_schema.py
```

### "No concepts found"

```bash
# Check Neo4j connection
python scripts/init_concept_schema.py --stats

# Verify video was processed
python scripts/query_concepts.py --stats
```

### Low Quality Scores

```bash
# Diagnose embeddings
python scripts/diagnose_embeddings.py VIDEO_ID

# Check specific groups
python scripts/visualize_groups.py
```

---

## 📝 Summary

**Must run once:**
1. `init_weaviate_schema.py` - Setup Weaviate
2. `init_concept_schema.py` - Setup Neo4j

**Regular use:**
1. `pipeline.py` - Process videos
2. `test_groups_quality.py` - Validate quality
3. `query_concepts.py` - Explore results

**When needed:**
- `diagnose_embeddings.py` - Debug issues
- `visualize_*.py` - Deep analysis
- `test_pipeline.py` - Verify setup

---

**For more details:** Run any script with `--help` flag
