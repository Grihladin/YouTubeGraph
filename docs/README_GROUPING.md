# YouTube Knowledge Graph - Segment Grouping

This module implements semantic grouping of transcript segments with temporal continuity, preparing them for LLM-based idea extraction.

## 🎯 Overview

The segment grouper takes individual transcript segments (150-300 words each) and creates coherent topic-based groups (400-800 words) that:
- ✅ Maintain narrative flow and temporal coherence
- ✅ Respect semantic similarity and topic boundaries
- ✅ Provide optimal chunk sizes for LLM processing
- ✅ Preserve timestamp information for knowledge graph linking

## 📁 Project Structure

```
YouTubeGraph/
├── pipeline.py                 # Main pipeline: YouTube → Weaviate
├── punctuation_worker.py       # Transcript cleaning & segmentation
├── weaviate_uploader.py        # Upload segments to Weaviate
├── segment_grouper.py          # 🆕 Group segments by topic (this module)
├── run_grouping.py             # 🆕 Batch script to group all videos
├── visualize_groups.py         # 🆕 Analyze and visualize groups
├── transcript_models.py        # Shared data models
├── requirements.txt            # Python dependencies
├── GROUP_SEGMENTS.md           # 📖 Detailed strategy document
├── Transcripts/                # Raw transcript files
│   ├── transcript_HbDqLPm_2vY.txt
│   ├── transcript_wLb9g_8r-mE.txt
│   └── transcript_zc9ajtpaS6k.txt
└── Groups/                     # 🆕 Output directory for grouped segments
    └── groups_{video_id}.json
```

## 🚀 Quick Start

### 1. Run Segment Grouping

```bash
# Group all videos that have been uploaded to Weaviate
python run_grouping.py
```

This will:
- Connect to your Weaviate instance
- Fetch segments for each video
- Build k-NN neighborhoods
- Detect topic boundaries
- Form coherent groups
- Export results to `Groups/groups_{video_id}.json`

### 2. Visualize Results

```bash
# Analyze and visualize the groups
python visualize_groups.py
```

This provides:
- 📊 Statistical summaries (word counts, cohesion, duration)
- 📈 Timeline visualization
- 🔍 Boundary strength analysis
- ⚠️ Outlier detection
- 📝 Detailed group breakdowns

### 3. Use Programmatically

```python
from segment_grouper import SegmentGrouper

# Initialize with custom hyperparameters
grouper = SegmentGrouper(
    k_neighbors=8,                    # Top-k similar neighbors
    neighbor_threshold=0.75,          # Min similarity to keep neighbor
    adjacent_threshold=0.60,          # Min similarity to join adjacent
    temporal_tau=150.0,               # Temporal decay (seconds)
    max_group_words=800,              # Max words per group
    min_group_segments=2,             # Min segments per group
    merge_centroid_threshold=0.80,    # Post-merge threshold
)

# Group a specific video
groups = grouper.group_video("HbDqLPm_2vY")

# Access group data
for group in groups:
    print(f"Group {group.group_id}:")
    print(f"  Time: {group.start_time:.1f}s - {group.end_time:.1f}s")
    print(f"  Words: {group.total_words}")
    print(f"  Cohesion: {group.avg_internal_similarity():.3f}")
    print(f"  Text: {group.text[:100]}...\n")

# Export to JSON
from pathlib import Path
grouper.export_groups_to_json(groups, Path("Groups/my_groups.json"))

grouper.close()
```

## 🧠 Algorithm Details

See [GROUP_SEGMENTS.md](GROUP_SEGMENTS.md) for the complete strategy document.

### Key Features

1. **k-NN Neighborhoods** - Query Weaviate for semantically similar segments
2. **Temporal Decay** - Penalize similarity across distant timestamps: `sim_eff = sim * exp(-Δt / τ)`
3. **Boundary Detection** - Identify topic shifts via cohesion dips
4. **Greedy Growth** - Build groups incrementally with word count guardrails
5. **Post-Merge** - Combine highly similar adjacent groups

### Hyperparameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `k_neighbors` | 8 | Number of nearest neighbors per segment |
| `neighbor_threshold` | 0.75 | Minimum cosine similarity to keep neighbor |
| `adjacent_threshold` | 0.60 | Minimum similarity to join adjacent segments |
| `temporal_tau` | 150s | Temporal decay constant (higher = slower decay) |
| `max_group_words` | 800 | Maximum words per group |
| `min_group_segments` | 2 | Minimum segments per group |
| `merge_centroid_threshold` | 0.80 | Centroid similarity for post-merge |

## 📊 Output Format

Groups are exported as JSON with the following schema:

```json
{
  "video_id": "HbDqLPm_2vY",
  "num_groups": 15,
  "groups": [
    {
      "group_id": 0,
      "start_time": 120.5,
      "end_time": 245.8,
      "duration": 125.3,
      "num_segments": 3,
      "total_words": 650,
      "avg_cohesion": 0.82,
      "text": "Combined text of all segments in this group...",
      "segments": [
        {
          "id": "uuid-123",
          "index": 5,
          "start_time": 120.5,
          "end_time": 145.2,
          "text": "Individual segment text...",
          "word_count": 200
        }
      ]
    }
  ]
}
```

## 🎯 Next Steps: Idea Extraction

Now that segments are grouped, you can proceed with:

### 1. Concept Extraction (per group)
```python
# Feed each group to LLM
for group in groups:
    prompt = f"""
    Extract the top 5-7 key concepts from this transcript segment:
    
    {group.text}
    
    For each concept, provide:
    - Name (2-4 words)
    - Definition (1-2 sentences)
    - Timestamp reference: {group.start_time}s - {group.end_time}s
    """
    concepts = llm_extract_concepts(prompt)
```

### 2. Cross-Reference Detection
```python
# Analyze cue phrases within and across groups
# "As we discussed...", "This relates to...", etc.
```

### 3. Knowledge Graph Construction
```python
# Build graph: Groups → Concepts → Relations
# Store in Weaviate or Neo4j with proper linking
```

## 🔧 Tuning Guide

### Groups Too Small/Fragmented?
- ⬇️ Lower `adjacent_threshold` (e.g., 0.50)
- ⬆️ Increase `temporal_tau` (e.g., 200)
- ⬆️ Increase `max_group_words` (e.g., 1000)

### Groups Too Large?
- ⬆️ Raise `adjacent_threshold` (e.g., 0.70)
- ⬇️ Decrease `temporal_tau` (e.g., 100)
- ⬇️ Decrease `max_group_words` (e.g., 600)

### Poor Cohesion?
- ⬆️ Raise `neighbor_threshold` (e.g., 0.80)
- ⬆️ Raise `adjacent_threshold` (e.g., 0.65)
- Check embedding quality in Weaviate

### Too Much Merging?
- ⬆️ Raise `merge_centroid_threshold` (e.g., 0.85)
- Or disable post-merge by setting threshold to 1.0

## 🐛 Troubleshooting

### No groups created?
- Check if segments exist in Weaviate: `collection.query.fetch_objects(filters=...)`
- Verify embeddings are present: `include_vector=True`
- Check video_id matches exactly

### Empty neighborhoods?
- Lower `neighbor_threshold` temporarily to debug
- Check if segments have valid embeddings
- Verify Weaviate vectorizer is configured (OpenAI)

### Connection errors?
- Verify `.env` file has correct credentials:
  ```
  WEAVIATE_URL=https://xxxxx.weaviate.network
  WEAVIATE_API_KEY=your-api-key
  OPENAI_API_KEY=your-openai-key
  ```

## 📚 Dependencies

All dependencies are in `requirements.txt`:
- `weaviate-client>=4.17.0` - Weaviate SDK
- `numpy>=2.3.0` - Vector operations
- `python-dotenv>=1.0.0` - Environment variables

## 🤝 Contributing

This is a research/experimental codebase. Feel free to:
- Tune hyperparameters for your use case
- Experiment with different boundary detection methods
- Add new visualization tools
- Integrate with different LLM providers

## 📖 References

- **Weaviate Documentation**: https://weaviate.io/developers/weaviate
- **TextTiling Algorithm**: Hearst, 1997 (classic topic segmentation)
- **Temporal Coherence**: Barzilay & Lapata, 2008
- **LLM Context Windows**: Anthropic's context window research

---

**Status**: ✅ Ready for idea extraction phase

**Next milestone**: Implement LLM-based concept extraction and cross-reference detection
