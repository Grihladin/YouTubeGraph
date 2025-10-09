# Phase 1: Concept Extraction - Implementation Guide

## 🎯 Overview

This guide covers **Phase 1** of building the YouTubeGraph knowledge graph: extracting structured concepts from transcript groups and storing them in Weaviate.

**Status**: ✅ Fully implemented and ready to use

---

## 📋 What Was Implemented

### Core Components

1. **Schema Design** (`docs/CONCEPT_SCHEMA.md`)
   - Concept entity with 13 properties
   - ConceptMention entity for traceability
   - 11 concept types (Person, Technology, Method, etc.)
   - Scoring rubrics for importance, confidence, and salience

2. **Data Models** (`src/core/concept_models.py`)
   - `Concept` dataclass with validation
   - `ConceptMention` dataclass for specific occurrences
   - `ExtractedConcepts` container with quality metrics
   - `ConceptType` enum for categorization

3. **LLM Extraction** (`src/core/concept_extractor.py`)
   - OpenAI GPT integration
   - Structured prompts for concept extraction
   - JSON response parsing and validation
   - Error handling and retry logic

4. **Weaviate Integration** (`src/core/concept_uploader.py`)
   - Batch uploading to Weaviate
   - Cross-reference management
   - Semantic search capabilities
   - CRUD operations for concepts

5. **Automation Scripts**
   - `scripts/init_concept_schema.py` - Initialize Weaviate collections
   - `scripts/extract_concepts.py` - Extract and upload concepts
   - `scripts/query_concepts.py` - Query and analyze concepts

---

## 🚀 Quick Start

### Step 1: Initialize Weaviate Schema

Create the Concept and ConceptMention collections:

```bash
python scripts/init_concept_schema.py
```

**What this does:**
- Creates `Concept` collection with OpenAI vectorizer
- Creates `ConceptMention` collection with cross-references
- Verifies collections are properly configured

**Output:**
```
✓ Connected to Weaviate
✓ Created collection 'Concept'
✓ Created collection 'ConceptMention'
✅ Schema initialization complete!
```

---

### Step 2: Extract Concepts from Groups

Process your grouped segments to extract concepts:

```bash
# Extract from a single video
python scripts/extract_concepts.py CUS6ABgI1As

# Extract from multiple videos
python scripts/extract_concepts.py CUS6ABgI1As VIDEO_ID2 VIDEO_ID3

# Extract from ALL videos with groups
python scripts/extract_concepts.py --all

# Force re-extraction (deletes existing concepts)
python scripts/extract_concepts.py --re-extract CUS6ABgI1As
```

**What this does:**
1. Loads groups from `output/groups/groups_{VIDEO_ID}.json`
2. For each group:
   - Sends text to OpenAI GPT-4o-mini
   - Extracts 5-7 key concepts with metadata
   - Validates extraction quality
   - Uploads to Weaviate with embeddings
3. Prints detailed progress and statistics

**Example Output:**
```
📹 Processing video: CUS6ABgI1As
   Groups to process: 4

  📝 Group 0 (4.8s - 397.6s)... ✓ 6 concepts
  📝 Group 1 (394.4s - 746.3s)... ✓ 7 concepts
  📝 Group 2 (746.3s - 914.2s)... ✓ 5 concepts
  📝 Group 3 (914.2s - 992.5s)... ✓ 4 concepts

📊 EXTRACTION SUMMARY
Videos processed: 1
Groups processed: 4
Concepts extracted: 22
Concepts uploaded: 22
Average importance: 0.68
Average confidence: 0.82
```

---

### Step 3: Query and Validate

Explore the extracted concepts:

```bash
# View all concepts for a video
python scripts/query_concepts.py CUS6ABgI1As

# Semantic search
python scripts/query_concepts.py --search "journalism"

# Quality analysis
python scripts/query_concepts.py --quality CUS6ABgI1As

# Database statistics
python scripts/query_concepts.py --stats
```

**Example Output (Quality Analysis):**
```
🔬 Quality Analysis for video: CUS6ABgI1As

Overall Metrics:
  Total concepts: 22
  Average importance: 0.68
  Average confidence: 0.82

Type Distribution:
  Concept: 8 (36.4%)
  Problem: 5 (22.7%)
  Solution: 4 (18.2%)
  Method: 3 (13.6%)
  Person: 2 (9.1%)

Quality Assessment:
  ✅ Quality looks good!

Top 5 Most Important Concepts:
  1. Negative News Consumption (0.90)
  2. Hometown Heroes (0.85)
  3. Shock and Awe Journalism (0.82)
  4. Good News Amplification (0.78)
  5. Civil Disobedience (0.72)
```

---

## 📊 Data Flow

```
Groups JSON
    ↓
ConceptExtractor (LLM)
    ↓
Concept Objects (validated)
    ↓
ConceptUploader
    ↓
Weaviate (with embeddings)
```

---

## 🎓 How It Works

### 1. Schema Design

Each **Concept** represents a distinct idea:

| Field | Example |
|-------|---------|
| name | "Temporal Decay Penalty" |
| definition | "A technique that reduces similarity scores..." |
| type | Method |
| importance | 0.85 |
| confidence | 0.95 |
| videoId | "HbDqLPm_2vY" |
| groupId | 3 |
| firstMentionTime | 245.8 |
| lastMentionTime | 312.4 |

### 2. LLM Prompt Engineering

The system uses a carefully crafted prompt that:
- Provides context (video ID, group ID, timestamps)
- Shows the full group text
- Requests structured JSON output
- Defines clear scoring criteria
- Examples for each field type

### 3. Validation Pipeline

Every extraction goes through quality checks:
1. **Field validation**: Names, definitions, types
2. **Score clamping**: Ensure 0.0-1.0 range
3. **Duplicate detection**: Catch same concept twice
4. **Type diversity**: Warn if all concepts same type
5. **Concept count**: Target 5-7 per group

### 4. Weaviate Storage

Concepts are stored with:
- **Vector embeddings**: From name + definition
- **Filterable properties**: videoId, groupId, type
- **Searchable text**: For full-text search
- **Cross-references**: To mentions (Phase 2)

---

## 📖 API Reference

### ConceptExtractor

```python
from core.concept_extractor import ConceptExtractor

extractor = ConceptExtractor(
    api_key="sk-...",           # Optional, reads from env
    model="gpt-4o-mini",        # Or "gpt-4", "gpt-4-turbo"
    temperature=0.3,            # Lower = more consistent
)

result = extractor.extract_from_group(
    video_id="VIDEO_ID",
    group_id=0,
    group_text="...",
    start_time=120.5,
    end_time=245.8,
)

# Result is ExtractedConcepts object
print(f"Extracted {len(result.concepts)} concepts")
print(f"Average confidence: {result.avg_confidence:.2f}")

is_valid, issues = result.validate()
```

### ConceptUploader

```python
from core.concept_uploader import ConceptUploader

uploader = ConceptUploader()

# Upload extracted concepts
stats = uploader.upload_extracted_concepts(result)

# Query concepts
concepts = uploader.get_concepts_for_video("VIDEO_ID")
concepts = uploader.get_concepts_for_group("VIDEO_ID", 0)

# Semantic search
results = uploader.search_concepts("neural networks", limit=10)

# Delete for re-extraction
uploader.delete_concepts_for_video("VIDEO_ID")

uploader.close()
```

---

## ⚙️ Configuration

### Environment Variables

Required in your `.env` file:

```bash
# OpenAI (for concept extraction)
OPENAI_API_KEY=sk-...

# Weaviate Cloud
WEAVIATE_URL=https://xxxxx.weaviate.network
WEAVIATE_API_KEY=...
```

### LLM Model Selection

Trade-offs:

| Model | Speed | Quality | Cost | Recommendation |
|-------|-------|---------|------|----------------|
| gpt-4o-mini | ⚡⚡⚡ | ⭐⭐⭐ | 💰 | **Default** (best balance) |
| gpt-4-turbo | ⚡⚡ | ⭐⭐⭐⭐ | 💰💰 | High quality needed |
| gpt-4 | ⚡ | ⭐⭐⭐⭐⭐ | 💰💰💰 | Maximum quality |

Change in `concept_extractor.py`:

```python
extractor = ConceptExtractor(model="gpt-4-turbo")
```

### Extraction Parameters

Customize in `concept_extractor.py`:

```python
EXTRACTION_PROMPT = """
...extract 5-7 key concepts...  # Change target count
"""

extractor = ConceptExtractor(
    temperature=0.3,  # 0.0 = deterministic, 1.0 = creative
)
```

---

## 🔍 Quality Metrics

Track these to ensure good extraction:

### Target Metrics

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Concepts per group | 5-7 | 3-4 or 8-10 | <3 or >10 |
| Average confidence | ≥0.75 | 0.65-0.74 | <0.65 |
| Average importance | 0.5-0.7 | 0.4-0.5 | <0.4 |
| Type diversity | ≥3 types | 2 types | 1 type |
| Duplicate names | 0 | 1-2 | >2 |

### Checking Quality

```bash
# Run quality analysis
python scripts/query_concepts.py --quality VIDEO_ID
```

This reports:
- Overall metrics (counts, averages)
- Type distribution
- Confidence/importance distributions
- Quality issues and warnings
- Top concepts by importance

---

## 🐛 Troubleshooting

### Issue: "No concepts extracted"

**Possible causes:**
1. Group text is too short or empty
2. LLM API rate limit hit
3. Invalid API key

**Solutions:**
- Check group JSON files have `text` field
- Add delays between requests: `time.sleep(1)`
- Verify `OPENAI_API_KEY` in `.env`

### Issue: "Low confidence scores"

**Possible causes:**
1. Group text is ambiguous or unclear
2. Video is conversational/unstructured
3. Temperature setting too high

**Solutions:**
- Improve segmentation/grouping quality first
- Lower `temperature` to 0.1-0.2
- Try a better model (gpt-4-turbo)

### Issue: "Concepts too generic"

**Possible causes:**
1. LLM extracting surface-level ideas
2. Importance scoring too lenient
3. Group text lacks depth

**Solutions:**
- Refine prompt to emphasize specificity
- Filter out low-importance concepts (<0.4)
- Review grouping parameters

### Issue: "Duplicate concepts across groups"

**This is normal and expected!** The same concept can appear in multiple groups.

For deduplication, see **Phase 3: Graph Construction**.

---

## 📈 Performance

### Extraction Speed

| Videos | Groups | Concepts | Time | Rate |
|--------|--------|----------|------|------|
| 1 | 4 | 22 | ~30s | 0.7 groups/s |
| 5 | 20 | 110 | ~150s | 0.7 groups/s |
| 10 | 50 | 280 | ~6min | 0.7 groups/s |

**Bottleneck**: OpenAI API calls (~1-2s per group)

**Optimization options:**
- Batch processing (not yet implemented)
- Parallel requests with rate limiting
- Local LLM (faster but lower quality)

### Cost Estimation

Using `gpt-4o-mini` (as of Oct 2025):

| Input | Output | Total per Group | Total per Video (4 groups) |
|-------|--------|-----------------|---------------------------|
| $0.00015/1K tokens | $0.0006/1K tokens | ~$0.002 | ~$0.008 |

**Example**: 10 videos ≈ **$0.08**

Much cheaper than gpt-4 (~10x cost reduction).

---

## ✅ Success Criteria

You'll know Phase 1 is working when:

- [x] Schema initialized in Weaviate
- [x] Concepts extracted with ≥0.75 average confidence
- [x] 5-7 concepts per group (most groups)
- [x] Type diversity (≥3 different types)
- [x] Concepts searchable via semantic queries
- [x] Quality analysis passes without critical issues

---

## 🎯 Next Steps: Phase 2

Once Phase 1 is complete, proceed to **Phase 2: Relationship Detection**.

This involves:
1. **Intra-Group Relationships**: Extract how concepts relate within same group
2. **Inter-Group Relationships**: Find connections across groups via cue-phrases
3. **Cross-Video Relationships**: Match similar concepts across videos

See `docs/PHASE2_RELATIONSHIPS.md` (coming soon).

---

## 📚 Files Reference

### Core Library (`src/core/`)
- `concept_models.py` - Data models for concepts
- `concept_extractor.py` - LLM extraction logic
- `concept_uploader.py` - Weaviate integration

### Scripts (`scripts/`)
- `init_concept_schema.py` - Create Weaviate collections
- `extract_concepts.py` - Main extraction pipeline
- `query_concepts.py` - Query and analysis tools

### Documentation (`docs/`)
- `CONCEPT_SCHEMA.md` - Detailed schema design
- `PHASE1_IMPLEMENTATION.md` - This file

---

## 🙋 FAQ

**Q: Can I use a local LLM instead of OpenAI?**  
A: Yes! Modify `concept_extractor.py` to use Ollama, LMStudio, or any OpenAI-compatible API.

**Q: What if I want more than 7 concepts per group?**  
A: Edit the `EXTRACTION_PROMPT` in `concept_extractor.py` and change "5-7" to "7-10" or desired range.

**Q: Can I extract concepts from segments instead of groups?**  
A: Yes, but not recommended. Segments are short (150-300 words) and may not contain enough context. Groups (400-800 words) are optimal for LLM analysis.

**Q: How do I handle multi-language videos?**  
A: OpenAI models handle multiple languages. Ensure your transcripts are in the source language, and the LLM will extract concepts appropriately.

**Q: Can I re-extract concepts with different parameters?**  
A: Yes! Use `--re-extract` flag to delete existing concepts and extract fresh.

---

**Status**: ✅ Phase 1 Complete - Ready for Phase 2

**Last Updated**: October 9, 2025
