# 🚀 Quick Start Guide

Get your first video processed and grouped in 5 minutes!

## Prerequisites

- Python 3.10+
- Weaviate Cloud account (free tier works)
- OpenAI API key

## Step 1: Setup (2 minutes)

```bash
# Clone and install
git clone https://github.com/Grihladin/YouTubeGraph.git
cd YouTubeGraph
pip install -r requirements.txt

# Configure environment
cat > .env << EOF
WEAVIATE_URL=https://your-instance.weaviate.network
WEAVIATE_API_KEY=your-weaviate-api-key
OPENAI_API_KEY=your-openai-api-key
EOF
```

## Step 2: Run Pipeline (3 minutes)

### Option A: Use Default Example

```bash
# Process the example video (already in pipeline.py)
python scripts/pipeline.py
```

This will:
1. ✅ Fetch transcript from YouTube
2. ✅ Restore punctuation
3. ✅ Upload segments to Weaviate
4. ✅ Group segments semantically
5. ✅ Save groups to `output/groups/`

### Option B: Process Your Own Video

Edit `scripts/pipeline.py` and change the URL:

```python
# Change this line in main():
youtube_url = "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"
```

Then run:
```bash
python scripts/pipeline.py
```

## Step 3: View Results

### Check the groups
```bash
python scripts/visualize_groups.py
```

You'll see:
- 📊 Statistics (word counts, cohesion scores)
- 📈 Timeline visualization
- 📝 Detailed group breakdowns

### Check output files
```
output/
├── transcripts/
│   └── transcript_VIDEO_ID.txt    # Processed transcript
└── groups/
    └── groups_VIDEO_ID.json        # Semantic groups
```

## Example Output

```
✅ REFACTORING COMPLETE!

📁 Root Directory:
MIGRATION.md
README.md
REFACTORING_COMPLETE.md
docs
output
requirements.txt
scripts
src

📦 src/core/:
__init__.py
punctuation_worker.py
segment_grouper.py
transcript_models.py
weaviate_uploader.py

🔧 scripts/:
diagnose_embeddings.py
pipeline.py
run_grouping.py
run_tuned_grouping.py
test_grouping.py
visualize_groups.py

📚 docs/:
GROUP_SEGMENTS.md
IMPLEMENTATION_SUMMARY.md
README_GROUPING.md

📤 output/:
groups
transcripts

Pipeline Output:
================================================================================
Processing: https://www.youtube.com/watch?v=zc9ajtpaS6k
================================================================================

📥 Step 1-3: Fetching transcript and processing...
✓ Processed transcript saved to: output/transcripts/transcript_zc9ajtpaS6k.txt
✓ Generated 5 structured segments

📤 Step 4: Uploading to Weaviate...
✓ Uploaded 5 segments to Weaviate

🔗 Step 5: Grouping segments semantically...
✓ Detected 2 boundaries
✓ Formed 3 initial groups
✓ After merging: 3 groups
✓ Saved 3 groups to output/groups/groups_zc9ajtpaS6k.json

================================================================================
✅ SUCCESS! Pipeline complete
================================================================================
Segments uploaded: 5
Groups created: 3
================================================================================
```

## Next Steps

### 1. Analyze Quality

```bash
# See detailed statistics
python scripts/visualize_groups.py

# Diagnose embedding similarities
python scripts/diagnose_embeddings.py VIDEO_ID
```

### 2. Tune Parameters (if needed)

If groups don't look good, adjust parameters in `scripts/pipeline.py`:

```python
pipeline = YouTubeToWeaviatePipeline(
    enable_grouping=True,
    grouping_params={
        "neighbor_threshold": 0.80,    # Higher = stricter similarity
        "adjacent_threshold": 0.70,    # Higher = fewer groups
        "max_group_words": 700,        # Lower = smaller groups
    }
)
```

### 3. Process Multiple Videos

Edit `scripts/pipeline.py` main() function:

```python
video_urls = [
    "https://www.youtube.com/watch?v=VIDEO_1",
    "https://www.youtube.com/watch?v=VIDEO_2",
    "https://www.youtube.com/watch?v=VIDEO_3",
]
results = pipeline.process_multiple_videos(video_urls)
```

### 4. Use in Your Code

```python
import sys
sys.path.insert(0, 'src')
sys.path.insert(0, 'scripts')

from pipeline import YouTubeToWeaviatePipeline

pipeline = YouTubeToWeaviatePipeline(enable_grouping=True)
result = pipeline.process_video("https://www.youtube.com/watch?v=VIDEO_ID")

print(f"Created {result['group_count']} groups from {result['segment_count']} segments")

# Access the groups
for group in result['groups']:
    print(f"Group {group.group_id}: {group.total_words} words")
    print(f"  Cohesion: {group.avg_internal_similarity():.3f}")
    print(f"  Text: {group.text[:100]}...")

pipeline.close()
```

## Troubleshooting

### "No module named 'core'"
```bash
# Make sure you're running from project root
cd /path/to/YouTubeGraph
python scripts/pipeline.py
```

### "No transcript found"
- Video has no captions/subtitles
- Try a different video with auto-generated captions

### Low cohesion scores
```bash
# Run diagnostics to see actual similarities
python scripts/diagnose_embeddings.py VIDEO_ID

# Adjust thresholds based on recommendations
```

### Import errors
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

## What's Next?

Now that you have grouped segments, you can:

1. **Extract Concepts** - Feed groups to LLM for concept extraction
2. **Build Knowledge Graph** - Link concepts across videos
3. **Semantic Search** - Query concepts instead of raw text
4. **Generate Summaries** - Summarize each group/topic

See [docs/README_GROUPING.md](docs/README_GROUPING.md) for the next phase!

---

**Questions?** Check the [main README](README.md) or [documentation](docs/)
