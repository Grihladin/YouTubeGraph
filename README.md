# YouTubeGraph

> Transform YouTube videos into structured knowledge graphs through semantic transcript analysis and grouping.

## 🎯 Overview

YouTubeGraph is a Python-based pipeline that processes YouTube video transcripts, applies semantic grouping, and prepares them for knowledge graph construction. It combines NLP, vector similarity search, and temporal analysis to create coherent topic clusters from video content.

### Key Features

- 🎥 **YouTube Transcript Extraction** - Automatic transcript fetching and punctuation restoration
- 📝 **Intelligent Segmentation** - Groups transcript segments by semantic similarity
- ⏱️ **Temporal Awareness** - Maintains narrative flow with time-decay penalties
- 🔍 **Vector Search** - Weaviate integration for k-NN similarity queries
- 🧠 **LLM Concept Extraction** - Extract key concepts from groups using GPT ✨ NEW
- 📊 **Rich Analytics** - Visualizations and diagnostics for group quality
- 🚀 **Production Ready** - Clean architecture, type hints, comprehensive docs

## 📦 Project Structure

```
YouTubeGraph/
├── src/                          # Core library code
│   └── core/                     # Main modules
│       ├── transcript_models.py  # Data models
│       ├── punctuation_worker.py # Transcript fetching & cleaning
│       ├── weaviate_uploader.py  # Weaviate integration
│       ├── segment_grouper.py    # Semantic grouping algorithm
│       ├── concept_models.py     # ✨ Concept data models
│       ├── concept_extractor.py  # ✨ LLM-powered extraction
│       └── concept_uploader.py   # ✨ Concept storage
│
├── scripts/                      # Executable scripts  
│   ├── pipeline.py              # End-to-end processing pipeline
│   ├── test_groups_quality.py   # Main quality validation (⭐ primary test)
│   ├── visualize_groups.py      # Analytics & visualization
│   ├── diagnose_embeddings.py   # Embedding quality diagnostics
│   ├── init_concept_schema.py   # ✨ Initialize concept schema
│   ├── extract_concepts.py      # ✨ Extract concepts from groups
│   └── query_concepts.py        # ✨ Query and analyze concepts
│
├── docs/                         # Documentation
│   ├── GROUP_SEGMENTS.md         # Grouping strategy details
│   ├── README_GROUPING.md        # Grouping module guide
│   ├── IMPLEMENTATION_SUMMARY.md # Implementation overview
│   ├── CONCEPT_SCHEMA.md         # ✨ Concept schema design
│   ├── PHASE1_IMPLEMENTATION.md  # ✨ Phase 1 guide
│   └── PHASE1_SUMMARY.md         # ✨ Phase 1 summary
│
├── output/                       # Generated files
│   ├── transcripts/             # Processed transcripts
│   └── groups/                  # Grouped segments (JSON)
│
├── requirements.txt              # Python dependencies
└── .env                         # Environment variables (not in repo)
```

## 🚀 Quick Start

> 💡 **New user?** Check out [QUICKSTART.md](QUICKSTART.md) for a 5-minute getting started guide!

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/Grihladin/YouTubeGraph.git
cd YouTubeGraph

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the project root:

```bash
# Weaviate Cloud Configuration
WEAVIATE_URL=https://your-instance.weaviate.network
WEAVIATE_API_KEY=your-weaviate-api-key

# OpenAI API (for embeddings via Weaviate)
OPENAI_API_KEY=your-openai-api-key
```

### 3. Basic Usage

#### Option A: Full Pipeline (Recommended) 🚀

Process everything automatically: fetch → punctuate → upload → group

```python
import sys
sys.path.insert(0, 'src')
sys.path.insert(0, 'scripts')

from pipeline import YouTubeToWeaviatePipeline

# Initialize pipeline with grouping enabled
pipeline = YouTubeToWeaviatePipeline(
    enable_grouping=True,  # Automatically group segments
    grouping_params={
        "k_neighbors": 8,
        "neighbor_threshold": 0.80,
        "adjacent_threshold": 0.70,
        "max_group_words": 700,
    }
)

# Process a video end-to-end
result = pipeline.process_video("https://www.youtube.com/watch?v=VIDEO_ID")

print(f"✅ Segments: {result['segment_count']}")
print(f"✅ Groups: {result['group_count']}")

pipeline.close()
```

#### Option B: Step-by-Step Processing

If you need more control over each step:

```python
import sys
sys.path.insert(0, 'src')

from core import PunctuationWorker, TranscriptJob, WeaviateUploader, SegmentGrouper

# Step 1: Fetch and process transcript
worker = PunctuationWorker()
job = TranscriptJob(
    youtube_url="https://www.youtube.com/watch?v=VIDEO_ID",
    output_dir="output/transcripts"
)
result = worker(job)

# Step 2: Upload to Weaviate
uploader = WeaviateUploader()
uploader.upload_segments(result.segments)

# Step 3: Group segments
grouper = SegmentGrouper()
groups = grouper.group_video(result.video_id)

# Export results
from pathlib import Path
grouper.export_groups_to_json(groups, Path("output/groups/my_video.json"))

# Cleanup
uploader.close()
grouper.close()
```

### 4. Using Scripts

#### Full Pipeline (Fetch + Upload + Group)

```bash
# Process video end-to-end: fetch → punctuate → upload → group
python scripts/pipeline.py
```

This automatically:
- ✅ Fetches YouTube transcript
- ✅ Restores punctuation
- ✅ Uploads segments to Weaviate
- ✅ Groups segments semantically
- ✅ Saves groups to `output/groups/`

#### Test Grouping Quality ⭐

```bash
# Test grouping quality (comprehensive analysis)
python scripts/test_groups_quality.py VIDEO_ID

# Test multiple videos
python scripts/test_groups_quality.py VIDEO_ID1 VIDEO_ID2 VIDEO_ID3
```

**This is your main quality validation tool!** It provides:
- Quality score (0-4 scale)
- Cohesion metrics
- Timeline visualization
- Sample group inspection

#### Analysis & Diagnostics

```bash
# Visualize existing groups
python scripts/visualize_groups.py

# Diagnose low quality issues
python scripts/diagnose_embeddings.py VIDEO_ID
```

#### ✨ NEW: Concept Extraction (Phase 1)

```bash
# Initialize concept schema (one-time)
python scripts/init_concept_schema.py

# Extract concepts from groups
python scripts/extract_concepts.py VIDEO_ID
python scripts/extract_concepts.py --all  # Process all videos

# Query and analyze concepts
python scripts/query_concepts.py VIDEO_ID
python scripts/query_concepts.py --search "machine learning"
python scripts/query_concepts.py --quality VIDEO_ID
```

See [docs/PHASE1_IMPLEMENTATION.md](docs/PHASE1_IMPLEMENTATION.md) for complete guide.

## 🧠 How It Works

### Complete Pipeline

```
YouTube URL 
    ↓
Fetch Transcript
    ↓
Restore Punctuation
    ↓
Segment (150-300 words)
    ↓
Upload to Weaviate (with embeddings)
    ↓
Semantic Grouping (400-800 words)
    ↓
Topic Groups (JSON output)
```

### 1. Transcript Processing

```
YouTube URL → Fetch Raw Transcript → Restore Punctuation → Segment by Sentences
```

- Fetches auto-generated or manual transcripts
- Restores punctuation using AI (deepmultilingualpunctuation)
- Chunks into 150-300 word segments with timestamps

### 2. Semantic Grouping

```
Segments → Vector Embeddings → k-NN Graph → Boundary Detection → Topic Groups
```

**Core Algorithm:**
1. **Build k-NN Neighborhoods** - Find similar segments via Weaviate vector search
2. **Apply Temporal Decay** - Penalize distant segments: `sim_eff = sim * exp(-Δt / τ)`
3. **Detect Boundaries** - Identify topic shifts via cohesion dips
4. **Greedy Growth** - Form groups with word count guardrails (400-800 words)
5. **Post-Merge** - Combine highly similar adjacent groups

See [docs/GROUP_SEGMENTS.md](docs/GROUP_SEGMENTS.md) for detailed strategy.

### 3. Output Format

Groups are exported as JSON:

```json
{
  "video_id": "VIDEO_ID",
  "num_groups": 15,
  "groups": [
    {
      "group_id": 0,
      "start_time": 120.5,
      "end_time": 245.8,
      "num_segments": 3,
      "total_words": 650,
      "avg_cohesion": 0.82,
      "text": "Combined text of all segments...",
      "segments": [...]
    }
  ]
}
```

## 📊 Quality Metrics

Good grouping results show:

- ✅ **Average cohesion ≥ 0.70** - Segments within groups are semantically similar
- ✅ **Word counts 400-800** - Optimal for LLM processing
- ✅ **≥80% coverage** - Most segments assigned to groups
- ✅ **Reasonable group count** - Typically 20-30 groups per hour of video

## 🔧 Configuration

### Hyperparameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `k_neighbors` | 8 | Number of nearest neighbors to fetch |
| `neighbor_threshold` | 0.75 | Minimum similarity to keep a neighbor |
| `adjacent_threshold` | 0.70 | Minimum similarity to join adjacent segments |
| `temporal_tau` | 150s | Temporal decay constant (higher = slower decay) |
| `max_group_words` | 700 | Maximum words per group |
| `min_group_segments` | 2 | Minimum segments per group |
| `merge_centroid_threshold` | 0.85 | Similarity threshold for post-merge |

### Tuning Guide

**If groups are too fragmented:**
- ↓ Lower `adjacent_threshold` (e.g., 0.60)
- ↑ Increase `temporal_tau` (e.g., 200)

**If groups are too large:**
- ↑ Raise `adjacent_threshold` (e.g., 0.75)
- ↓ Decrease `max_group_words` (e.g., 600)

**If cohesion is too low:**
- ↑ Raise both thresholds
- Run `diagnose_embeddings.py` for data-specific recommendations

## 🎓 Best Practices

### Recommended Content Types

✅ **Works Great:**
- Educational tutorials
- Technical presentations
- Single-speaker lectures
- Gaming commentary
- Product reviews

⚠️ **Challenging:**
- Multi-speaker interviews (topic switching)
- Debates (adversarial content)
- Music videos (minimal dialogue)

### Workflow

#### Quick Start (Full Pipeline)

1. **Set up environment** - Create `.env` with API keys
2. **Run pipeline** - `python scripts/pipeline.py` (processes and groups automatically)
3. **Visualize** - `python scripts/visualize_groups.py` to check quality
4. **Iterate** - Adjust `grouping_params` in pipeline if needed

#### Advanced (Manual Control)

1. **Start Small** - Test with 1-2 videos first
2. **Diagnose** - Run `python scripts/diagnose_embeddings.py VIDEO_ID` to understand similarity
3. **Tune** - Adjust hyperparameters based on diagnostics
4. **Validate** - Use `python scripts/visualize_groups.py` to check quality
5. **Scale** - Batch process with `python scripts/run_grouping.py`

## 📚 Documentation

- **[GROUP_SEGMENTS.md](docs/GROUP_SEGMENTS.md)** - Detailed grouping strategy and algorithm
- **[README_GROUPING.md](docs/README_GROUPING.md)** - User guide for segment grouping
- **[IMPLEMENTATION_SUMMARY.md](docs/IMPLEMENTATION_SUMMARY.md)** - Implementation details and next steps

## 🎯 Current Status

### ✅ Completed
- [x] YouTube transcript fetching
- [x] Punctuation restoration
- [x] Semantic segmentation (150-300 words)
- [x] Weaviate upload with embeddings
- [x] Semantic grouping (400-800 words)
- [x] Temporal coherence preservation
- [x] Automated end-to-end pipeline
- [x] Quality analytics & visualization

### 🚧 In Progress
- [ ] LLM-based concept extraction from groups
- [ ] Cue-phrase detection and cross-references

## 🔮 Future Enhancements

- [ ] Cross-video concept linking
- [ ] Neo4j knowledge graph integration
- [ ] Hierarchical grouping (groups → topics → themes)
- [ ] Web UI for interactive exploration
- [ ] Multi-language support
- [ ] Real-time streaming support

## 🤝 Contributing

This is a research/experimental project. Contributions welcome!

## 📝 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- **Weaviate** - Vector database
- **OpenAI** - Text embeddings (text-embedding-ada-002)
- **deepmultilingualpunctuation** - Punctuation restoration
- **youtube-transcript-api** - Transcript fetching

---

**Status:** ✅ Transcript processing and grouping complete. Ready for idea extraction phase.

**Author:** [Grihladin](https://github.com/Grihladin)

**Version:** 0.1.0
