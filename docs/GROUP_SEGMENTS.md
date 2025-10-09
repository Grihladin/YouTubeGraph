# Segment Grouping Strategy

This document outlines the semantic grouping strategy for transcript segments, implementing a hybrid approach that balances **semantic similarity** with **temporal continuity**.

## Core Concept

Instead of pure clustering (which ignores narrative flow) or pure time-windows (which miss thematic connections), we use:
- **k-NN neighborhoods** from Weaviate vector search
- **Temporal decay penalty** to preserve chronological flow
- **Boundary detection** based on local cohesion dips
- **Greedy growth with guardrails** for robust, readable groups

---

## Implementation Steps

### 1. Target Chunk Size
- **Goal**: 400–800 words per group
- **Rationale**: Optimal for LLM context windows
- **Expected**: Most groups = 2–3 segments (given 150–300 word segments)

### 2. Build k-NN Neighborhoods
For each segment `s_i`:
- Query **top-k similar segments** via Weaviate `nearVector` (k = 6–10)
- **Filter**: Keep neighbors with `cosine_similarity >= 0.75`
- **Store**: `(segment_id, index, similarity, start_time, text)`

### 3. Temporal Continuity Bias (Critical!)
Prevent "topic teleportation" across distant parts of video:

```
effective_similarity = similarity * exp(-|time_i - time_j| / τ)
```

- **τ (tau)**: Temporal decay constant (~120–180 seconds)
- **Effect**: Similarity fades as temporal distance grows
- **Preserves**: Narrative flow and causality

### 4. Detect Boundaries First
Instead of global clustering, do **topic boundary detection**:

#### 4.1 Local Cohesion Curve
For each adjacent pair `(s_i, s_{i+1})`:
- Compute max effective similarity between `s_i` and neighbors within ±3 segments of `i+1`
- Creates a 1D cohesion curve over the video timeline
- **Dips indicate topic shifts**

#### 4.2 Boundary Rules
Place boundary at `i | i+1` if:
- `local_cohesion < 0.55–0.60`, **OR**
- Current group word count would exceed ~800 words if merged

### 5. Greedy Growth with Guardrails
Walk from start to end:
1. **Start** new group with `s_i`
2. **Tentatively add** `s_{i+1}` if:
   - `effective_similarity(i, i+1) >= 0.60`, AND
   - Group word count stays `<= 800`
3. **If boundary triggered**: Start new group
4. **Ensure**: Min group size = 2 segments (except last leftover)

### 6. Post-Merge Micro-Clusters (Optional)
After first pass, merge adjacent groups `A` and `B` if:
- `cosine(centroid_A, centroid_B) >= 0.80`, AND
- `total_words <= 1000`

### 7. Weaviate Query Pattern
```python
# 1. Fetch all segments for video (ordered by start_time)
segments = fetch_segments(video_id, order_by="start_s")

# 2. For each segment, get k-NN neighbors
for segment in segments:
    neighbors = collection.query.near_vector(
        near_vector=segment.embedding,
        limit=k,
        include_vector=True,
        return_metadata=MetadataQuery(distance=True),
        filters=Filter.by_property("videoId").equal(video_id)
    )
    
    # 3. Filter by similarity threshold
    segment.neighbors = [n for n in neighbors if n.similarity >= 0.75]
```

### 8. Sanity Checks
Before passing to LLM:
- ✅ Word count: 400–800 per group (allow 300–1000 outliers)
- ✅ Coverage: ≥80% of segments assigned
- ✅ Cohesion: Average intra-group cosine ≥0.70

---

## Why This Hybrid Works

| Approach | Problem | Solution |
|----------|---------|----------|
| **Pure clustering** (HDBSCAN/K-Means) | Ignores narration flow, creates cross-video "teleports" | ❌ |
| **Pure time windows** | Misses thematic returns and short detours | ❌ |
| **Hybrid (this approach)** | Temporal penalty + boundary dips preserve flow **while** respecting semantics | ✅ |

---

## Hyperparameters (Defaults)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `k_neighbors` | 8 | Number of nearest neighbors to fetch |
| `neighbor_threshold` | 0.75 | Min similarity to keep neighbor |
| `adjacent_threshold` | 0.60 | Min similarity to join adjacent segments |
| `temporal_tau` | 150s | Temporal decay constant |
| `max_group_words` | 800 | Max words per group |
| `min_group_segments` | 2 | Min segments per group |
| `merge_centroid_threshold` | 0.80 | Similarity for post-merge |

**Tuning recommendations:**
- Start with defaults
- If groups too fragmented: ↓ `adjacent_threshold`, ↑ `temporal_tau`
- If groups too large: ↑ `adjacent_threshold`, ↓ `max_group_words`
- If merging too aggressive: ↑ `merge_centroid_threshold`

---

## Usage Example

```python
from segment_grouper import SegmentGrouper

# Initialize with defaults
grouper = SegmentGrouper()

# Group segments for a video
groups = grouper.group_video("HbDqLPm_2vY")

# Export to JSON
grouper.export_groups_to_json(groups, Path("Groups/groups_video.json"))

# Access group properties
for group in groups:
    print(f"Group {group.group_id}:")
    print(f"  Time: {group.start_time:.1f}s - {group.end_time:.1f}s")
    print(f"  Words: {group.total_words}")
    print(f"  Segments: {len(group.segments)}")
    print(f"  Cohesion: {group.avg_internal_similarity():.3f}")
    print(f"  Text: {group.text[:100]}...\n")

grouper.close()
```

---

## Next Steps: Idea Extraction

Once groups are formed, feed each group (not individual segments) to LLM for:

1. **Concept Refinement**
   - Extract top 5–7 concepts per group
   - Generate short definitions (1-2 sentences)
   - Link to timestamps

2. **Cue-Phrase Detection**
   - Within each group, detect transition phrases
   - "This relates to...", "As we discussed...", etc.
   - Validate top edges with LLM for cross-group connections

3. **Hierarchical Structuring**
   - Groups → Topics → Themes
   - Build knowledge graph with proper granularity

---

## Output Schema

Each group stores:

```json
{
  "group_id": 0,
  "video_id": "HbDqLPm_2vY",
  "start_time": 120.5,
  "end_time": 245.8,
  "duration": 125.3,
  "num_segments": 3,
  "total_words": 650,
  "avg_cohesion": 0.82,
  "text": "Combined text of all segments...",
  "segments": [
    {
      "id": "uuid-1",
      "index": 5,
      "start_time": 120.5,
      "end_time": 145.2,
      "text": "Segment text...",
      "word_count": 200
    }
  ]
}
```

---

## Performance Considerations

- **Memory**: All segments + embeddings loaded in memory (fine for <10k segments/video)
- **Queries**: k-NN query per segment (batching possible for optimization)
- **Speed**: ~1-2 minutes for typical 1-hour video with 200 segments
- **Scalability**: For very long videos (>500 segments), consider chunking by chapter/hour

---

## Credits

This approach combines ideas from:
- Topic segmentation literature (TextTiling, C99)
- Modern semantic search (vector databases)
- Temporal coherence from video understanding
- LLM context optimization strategies
