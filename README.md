# YouTubeGraph

> Transform YouTube videos into structured knowledge graphs through semantic transcript analysis and grouping.

## 🎯 Overview

YouTubeGraph is a Python-based pipeline that processes YouTube video transcripts, applies semantic grouping, and prepares them for knowledge graph construction. It combines NLP, vector similarity search, and temporal analysis to create coherent topic clusters from video content.

### Key Features

- 🎥 **YouTube Transcript Extraction** - Automatic transcript fetching and punctuation restoration
- 📝 **Intelligent Segmentation** - Groups transcript segments by semantic similarity
- ⏱️ **Temporal Awareness** - Maintains narrative flow with time-decay penalties
- 🔍 **Vector Search** - Weaviate integration for k-NN similarity queries
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
│       └── segment_grouper.py    # Semantic grouping algorithm
│
├── scripts/                      # Executable scripts
│   ├── pipeline.py              # End-to-end pipeline
│   ├── run_grouping.py          # Batch grouping
│   ├── test_grouping.py         # Single video test
│   ├── visualize_groups.py      # Analytics & visualization
│   └── diagnose_embeddings.py   # Embedding quality diagnostics
│
├── docs/                         # Documentation
│   ├── GROUP_SEGMENTS.md         # Grouping strategy details
│   ├── README_GROUPING.md        # Grouping module guide
│   └── IMPLEMENTATION_SUMMARY.md # Implementation overview
│
├── output/                       # Generated files
│   ├── transcripts/             # Processed transcripts
│   └── groups/                  # Grouped segments (JSON)
│
├── requirements.txt              # Python dependencies
└── .env                         # Environment variables (not in repo)
```

## 🚀 Quick Start

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

#### Process a Single Video

```python
import sys
sys.path.insert(0, 'src')

from core import PunctuationWorker, TranscriptJob, WeaviateUploader

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
uploader.close()
```

#### Group Segments

```python
from core import SegmentGrouper

grouper = SegmentGrouper()
groups = grouper.group_video("VIDEO_ID")

# Export results
from pathlib import Path
grouper.export_groups_to_json(groups, Path("output/groups/my_video.json"))
grouper.close()
```

### 4. Using Scripts

```bash
# Process video end-to-end (fetch → punctuate → upload)
python scripts/pipeline.py

# Group all uploaded videos
python scripts/run_grouping.py

# Test single video with diagnostics
python scripts/test_grouping.py VIDEO_ID --verbose

# Analyze grouping quality
python scripts/visualize_groups.py

# Diagnose embedding similarities
python scripts/diagnose_embeddings.py VIDEO_ID
```

## 🧠 How It Works

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

1. **Start Small** - Test with 1-2 videos first
2. **Diagnose** - Run `diagnose_embeddings.py` to understand similarity distribution
3. **Tune** - Adjust hyperparameters based on diagnostics
4. **Validate** - Use `visualize_groups.py` to check quality
5. **Scale** - Batch process with `run_grouping.py`

## 📚 Documentation

- **[GROUP_SEGMENTS.md](docs/GROUP_SEGMENTS.md)** - Detailed grouping strategy and algorithm
- **[README_GROUPING.md](docs/README_GROUPING.md)** - User guide for segment grouping
- **[IMPLEMENTATION_SUMMARY.md](docs/IMPLEMENTATION_SUMMARY.md)** - Implementation details and next steps

## 🔮 Future Enhancements

- [ ] LLM-based concept extraction from groups
- [ ] Cross-video concept linking
- [ ] Neo4j knowledge graph integration
- [ ] Hierarchical grouping (groups → topics → themes)
- [ ] Web UI for interactive exploration
- [ ] Multi-language support

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
