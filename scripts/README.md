# 📁 Scripts Directory - Clean Structure

## Overview

The `scripts/` directory now contains **4 essential scripts** for your YouTube transcript processing pipeline. All redundant scripts have been removed.

---

## 🚀 Main Scripts

### 1. **`pipeline.py`** - Full Processing Pipeline

**Purpose:** End-to-end YouTube video processing with automatic grouping

**Usage:**
```bash
python scripts/pipeline.py
```

**What it does:**
1. Fetches YouTube transcript
2. Restores punctuation
3. Uploads to Weaviate
4. **Automatically groups segments** (with tuned params)
5. Saves groups to `output/groups/`

**Features:**
- ✅ Uses tuned parameters by default
- ✅ Can process single or multiple videos
- ✅ Automatic group creation
- ✅ Customizable parameters

**Configuration:**
```python
pipeline = YouTubeToWeaviatePipeline(
    enable_grouping=True,        # Enable automatic grouping
    grouping_params={...}        # Optional: override tuned params
)
```

**When to use:** Processing new videos from YouTube URLs

---

### 2. **`test_groups_quality.py`** ⭐ - Quality Testing

**Purpose:** Comprehensive quality validation for grouped segments

**Usage:**
```bash
# Test default videos
python scripts/test_groups_quality.py

# Test specific videos
python scripts/test_groups_quality.py VIDEO_ID1 VIDEO_ID2 VIDEO_ID3
```

**What it does:**
1. Groups segments using tuned parameters
2. Analyzes quality metrics (cohesion, word counts, etc.)
3. Generates visual timeline
4. Shows sample groups
5. Provides quality score (0-4)
6. Multi-video summary

**Output:**
- Comprehensive quality report
- Quality scoring (0-4 scale)
- Timeline visualization
- Sample group inspection
- Saves to `output/groups/quality_test_*.json`

**When to use:** After processing videos, to validate grouping quality before concept extraction

**This is your main quality validation tool!** ⭐

---

### 3. **`visualize_groups.py`** - Results Visualization

**Purpose:** Visualize and analyze existing group JSON files

**Usage:**
```bash
# Visualize all groups
python scripts/visualize_groups.py

# Visualize specific pattern
python scripts/visualize_groups.py 'groups_*.json'
python scripts/visualize_groups.py 'quality_test_*.json'
```

**What it does:**
1. Loads group JSON files
2. Shows statistics (word counts, cohesion, durations)
3. Timeline visualization
4. Boundary analysis (gaps between groups)
5. Outlier detection
6. Detailed group breakdown

**When to use:** Deep dive analysis of existing group files

---

### 4. **`diagnose_embeddings.py`** - Diagnostic Tool

**Purpose:** Diagnose low cohesion or embedding quality issues

**Usage:**
```bash
python scripts/diagnose_embeddings.py VIDEO_ID
```

**What it does:**
1. Fetches segments from Weaviate
2. Analyzes embedding quality
3. Shows similarity distributions
4. Identifies problematic patterns
5. Recommends parameter adjustments

**Output:**
- Similarity histograms
- Adjacent segment similarity
- Overall statistics
- Parameter recommendations

**When to use:** When you get low quality scores and need to investigate why
