# YouTubeGraph# YouTubeGraph



> Transform YouTube videos into a knowledge graph: transcripts → semantic groups → concepts → relationships> Transform YouTube videos into structured knowledge graphs through semantic transcript analysis and grouping.



---## 🎯 Overview



## 🎯 What Does This Do?YouTubeGraph is a Python-based pipeline that processes YouTube video transcripts, applies semantic grouping, and prepares them for knowledge graph construction. It combines NLP, vector similarity search, and temporal analysis to create coherent topic clusters from video content.



**YouTubeGraph** processes YouTube videos into structured knowledge:### Key Features



1. **📹 Fetch transcript** from YouTube (with punctuation restoration)- 🎥 **YouTube Transcript Extraction** - Automatic transcript fetching and punctuation restoration

2. **✂️ Segment** into chunks (150-300 words each)- 📝 **Intelligent Segmentation** - Groups transcript segments by semantic similarity

3. **🔍 Group semantically** using AI embeddings (400-800 words per group)- ⏱️ **Temporal Awareness** - Maintains narrative flow with time-decay penalties

4. **🧠 Extract concepts** from groups using GPT (entities, methods, ideas)- 🔍 **Vector Search** - Weaviate integration for k-NN similarity queries

5. **🕸️ Build knowledge graph** with concepts and relationships in Neo4j- 🕸️ **Knowledge Graph Storage** - Neo4j backend for concepts and relationships

- 🧠 **LLM Concept Extraction** - Extract key concepts from groups using GPT ✨ NEW

**Result:** A queryable knowledge graph of everything discussed in the video!- 📊 **Rich Analytics** - Visualizations and diagnostics for group quality

- 🚀 **Production Ready** - Clean architecture, type hints, comprehensive docs

---

## 📦 Project Structure

## 🚀 Quick Start

```

### 1. InstallYouTubeGraph/

├── src/                          # Core library code

```bash│   └── core/                     # Main modules

git clone https://github.com/Grihladin/YouTubeGraph.git│       ├── transcript_models.py  # Data models

cd YouTubeGraph│       ├── punctuation_worker.py # Transcript fetching & cleaning

pip install -r requirements.txt│       ├── weaviate_uploader.py  # Weaviate integration

```│       ├── segment_grouper.py    # Semantic grouping algorithm

│       ├── concept_models.py     # ✨ Concept data models

### 2. Configure│       ├── concept_extractor.py  # ✨ LLM-powered extraction

│       └── concept_uploader.py   # ✨ Concept storage

Create `.env` file:│

├── scripts/                      # Executable scripts  

```bash│   ├── pipeline.py              # End-to-end processing pipeline

# Weaviate (vector storage for segments)│   ├── test_groups_quality.py   # Main quality validation (⭐ primary test)

WEAVIATE_URL=https://your-cluster.weaviate.network│   ├── visualize_groups.py      # Analytics & visualization

WEAVIATE_API_KEY=your-key│   ├── diagnose_embeddings.py   # Embedding quality diagnostics

│   ├── init_concept_schema.py   # ✨ Initialize concept schema

# Neo4j (knowledge graph storage)│   ├── extract_concepts.py      # ✨ Extract concepts from groups

NEO4J_URI=bolt+s://your-instance.neo4j.io│   └── query_concepts.py        # ✨ Query and analyze concepts

NEO4J_USER=neo4j│

NEO4J_PASSWORD=your-password├── docs/                         # Documentation

│   ├── GROUP_SEGMENTS.md         # Grouping strategy details

# OpenAI (embeddings + concept extraction)│   ├── README_GROUPING.md        # Grouping module guide

OPENAI_API_KEY=sk-your-key│   ├── IMPLEMENTATION_SUMMARY.md # Implementation overview

```│   ├── CONCEPT_SCHEMA.md         # ✨ Concept schema design

│   ├── PHASE1_IMPLEMENTATION.md  # ✨ Phase 1 guide

### 3. Initialize (One Time)│   └── PHASE1_SUMMARY.md         # ✨ Phase 1 summary

│

```bash├── output/                       # Generated files

# Create Weaviate collection│   ├── transcripts/             # Processed transcripts

python scripts/init_weaviate_schema.py --stats│   └── groups/                  # Grouped segments (JSON)

│

# Create Neo4j schema├── requirements.txt              # Python dependencies

python scripts/init_concept_schema.py└── .env                         # Environment variables (not in repo)

``````



### 4. Process a Video## 🚀 Quick Start



```bash> 💡 **New user?** Check out [QUICKSTART.md](QUICKSTART.md) for a 5-minute getting started guide!

python scripts/pipeline.py

```### 1. Installation



That's it! Enter a YouTube URL and it processes everything automatically.```bash

# Clone the repository

---git clone https://github.com/Grihladin/YouTubeGraph.git

cd YouTubeGraph

## 📊 What You Get

# Install dependencies

### Inputpip install -r requirements.txt

``````

YouTube URL: https://youtube.com/watch?v=VIDEO_ID

```### 2. Configuration



### OutputCreate a `.env` file in the project root:



**1. Segments in Weaviate** (vector searchable)```bash

```json# Weaviate Cloud Configuration (segment storage)

{WEAVIATE_URL=https://your-instance.weaviate.network

  "videoId": "VIDEO_ID",WEAVIATE_API_KEY=your-weaviate-api-key

  "text": "Machine learning is...",

  "start_s": 120.5,# Neo4j Graph Database (concept + relationship storage)

  "end_s": 145.2,NEO4J_URI=bolt+s://your-neo4j-instance.databases.neo4j.io

  "tokens": 203NEO4J_USER=neo4j

}NEO4J_PASSWORD=your-neo4j-password

```

# OpenAI API (LLM + embeddings)

**2. Semantic Groups** (saved to `output/groups/`)OPENAI_API_KEY=your-openai-api-key

```json```

{

  "group_id": 3,### 3. Basic Usage

  "start_time": 245.8,

  "end_time": 312.4,#### Option A: Full Pipeline (Recommended) 🚀

  "total_words": 650,

  "avg_cohesion": 0.82,Process everything automatically: fetch → punctuate → upload → group

  "text": "Combined topic-focused text..."

}```python

```import sys

sys.path.insert(0, 'src')

**3. Concepts in Neo4j** (graph queryable)sys.path.insert(0, 'scripts')

```json

{from pipeline import YouTubeToWeaviatePipeline

  "name": "Gradient Descent",

  "type": "Method",# Initialize pipeline with grouping enabled

  "definition": "An optimization algorithm...",pipeline = YouTubeToWeaviatePipeline(

  "importance": 0.85,    enable_grouping=True,  # Automatically group segments

  "firstMentionTime": 245.8    grouping_params={

}        "k_neighbors": 8,

```        "neighbor_threshold": 0.80,

        "adjacent_threshold": 0.70,

**4. Relationships in Neo4j**        "max_group_words": 700,

```    }

(Gradient Descent)-[REQUIRES]->(Loss Function))

(Neural Network)-[IMPLEMENTS]->(Gradient Descent)

```# Process a video end-to-end

result = pipeline.process_video("https://www.youtube.com/watch?v=VIDEO_ID")

---

print(f"✅ Segments: {result['segment_count']}")

## 🏗️ Architectureprint(f"✅ Groups: {result['group_count']}")



```pipeline.close()

YouTubeGraph/```

├── scripts/          # Executable scripts (see SCRIPTS.md)

│   ├── pipeline.py                  # Main pipeline#### Option B: Step-by-Step Processing

│   ├── init_weaviate_schema.py      # Setup Weaviate

│   ├── init_concept_schema.py       # Setup Neo4jIf you need more control over each step:

│   ├── test_pipeline.py             # Test everything

│   ├── test_groups_quality.py       # Quality checks```python

│   ├── query_concepts.py            # Query knowledge graphimport sys

│   └── visualize_*.py               # Visualization toolssys.path.insert(0, 'src')

│

├── src/              # Library codefrom core import PunctuationWorker, TranscriptJob, WeaviateUploader, SegmentGrouper

│   ├── config.py                    # Configuration

│   ├── domain/                      # Data models# Step 1: Fetch and process transcript

│   ├── infrastructure/              # Weaviate & Neo4j clientsworker = PunctuationWorker()

│   ├── services/                    # Business logicjob = TranscriptJob(

│   │   ├── transcripts/             # Fetch & process    youtube_url="https://www.youtube.com/watch?v=VIDEO_ID",

│   │   ├── vectorstore/             # Weaviate ops    output_dir="output/transcripts"

│   │   ├── grouping/                # Semantic grouping)

│   │   ├── concepts/                # Concept extractionresult = worker(job)

│   │   └── relationships/           # Relationship detection

│   └── utils/                       # Logging, helpers# Step 2: Upload to Weaviate

│uploader = WeaviateUploader()

└── output/           # Generated filesuploader.upload_segments(result.segments)

    ├── transcripts/  # Processed transcripts

    └── groups/       # Semantic groups (JSON)# Step 3: Group segments

```grouper = SegmentGrouper()

groups = grouper.group_video(result.video_id)

---

# Export results

## 🔄 How It Worksfrom pathlib import Path

grouper.export_groups_to_json(groups, Path("output/groups/my_video.json"))

### Pipeline Flow

# Cleanup

```uploader.close()

YouTube URLgrouper.close()

    ↓```

[1] Fetch Transcript (youtube-transcript-api)

    ↓### 4. Using Scripts

[2] Restore Punctuation (deepmultilingualpunctuation)

    ↓#### Full Pipeline (Fetch + Upload + Group)

[3] Segment (150-300 words with timestamps)

    ↓```bash

[4] Upload to Weaviate (OpenAI embeddings: text-embedding-3-small)# Process video end-to-end: fetch → punctuate → upload → group

    ↓python scripts/pipeline.py

[5] Semantic Grouping (k-NN + temporal coherence)```

    ↓  

[6] Extract Concepts (GPT-4o-mini: entities, methods, ideas)This automatically:

    ↓- ✅ Fetches YouTube transcript

[7] Detect Relationships (between concepts)- ✅ Restores punctuation

    ↓- ✅ Uploads segments to Weaviate

[8] Store in Neo4j (knowledge graph)- ✅ Groups segments semantically

    ↓- ✅ Saves groups to `output/groups/`

✅ Done!

```#### Test Grouping Quality ⭐



### Semantic Grouping Algorithm```bash

# Test grouping quality (comprehensive analysis)

Groups segments by topic using:python scripts/test_groups_quality.py VIDEO_ID



- **k-NN Neighborhoods**: Find similar segments via vector search# Test multiple videos

- **Temporal Decay**: Penalize distant segments: `similarity_effective = similarity × e^(-Δt / 150s)`python scripts/test_groups_quality.py VIDEO_ID1 VIDEO_ID2 VIDEO_ID3

- **Boundary Detection**: Identify topic shifts when cohesion drops```

- **Greedy Growth**: Build groups respecting 400-800 word limits

- **Post-Merge**: Combine adjacent similar groups**This is your main quality validation tool!** It provides:

- Quality score (0-4 scale)

**Result:** Coherent 400-800 word topic groups (optimal for LLM processing)- Cohesion metrics

- Timeline visualization

### Concept Extraction- Sample group inspection



For each group, GPT-4o-mini extracts:#### Analysis & Diagnostics



- **Entities**: People, organizations, products (e.g., "TensorFlow")```bash

- **Methods**: Techniques, algorithms (e.g., "Gradient Descent")# Visualize existing groups

- **Concepts**: Abstract ideas (e.g., "Overfitting")python scripts/visualize_groups.py

- **Technologies**: Tools, frameworks (e.g., "React")

- **Theories**: Principles, laws (e.g., "Universal Approximation Theorem")# Diagnose low quality issues

python scripts/diagnose_embeddings.py VIDEO_ID

Each concept includes:```

- Name, definition, type

- Importance score (0-1)#### ✨ NEW: Concept Extraction (Phase 1)

- Confidence score (0-1)

- Timestamps (first/last mention)```bash

- Aliases (alternative names)# Initialize concept schema (one-time)

python scripts/init_concept_schema.py

### Relationship Detection

# Extract concepts from groups

Detects relationships between concepts:python scripts/extract_concepts.py VIDEO_ID

python scripts/extract_concepts.py --all  # Process all videos

- **REQUIRES**: Prerequisites (e.g., "Calculus REQUIRES Algebra")

- **IMPLEMENTS**: Implementation (e.g., "PyTorch IMPLEMENTS Neural Networks")# Query and analyze concepts

- **PART_OF**: Composition (e.g., "Layer PART_OF Neural Network")python scripts/query_concepts.py VIDEO_ID

- **CAUSES**: Causation (e.g., "Overfitting CAUSES Poor Generalization")python scripts/query_concepts.py --search "machine learning"

- **SIMILAR_TO**: Similarity (e.g., "RNN SIMILAR_TO LSTM")python scripts/query_concepts.py --quality VIDEO_ID

- **PRECEDES**: Temporal order (e.g., "Data Collection PRECEDES Training")```



---See [docs/PHASE1_IMPLEMENTATION.md](docs/PHASE1_IMPLEMENTATION.md) for complete guide.



## 📚 Common Workflows## 🧠 How It Works



### Workflow 1: Process New Video### Complete Pipeline



```bash```

# 1. Run pipelineYouTube URL 

python scripts/pipeline.py    ↓

# Enter YouTube URL when promptedFetch Transcript

    ↓

# 2. Check qualityRestore Punctuation

python scripts/test_groups_quality.py VIDEO_ID    ↓

Segment (150-300 words)

# 3. Query concepts    ↓

python scripts/query_concepts.py VIDEO_IDUpload to Weaviate (with embeddings)

    ↓

# 4. VisualizeSemantic Grouping (400-800 words)

python scripts/visualize_groups.py    ↓

python scripts/visualize_concept_graph.pyTopic Groups (JSON output)

``````



### Workflow 2: Batch Process Multiple Videos### 1. Transcript Processing



```python```

from scripts.pipeline import YouTubeGraphPipelineYouTube URL → Fetch Raw Transcript → Restore Punctuation → Segment by Sentences

```

pipeline = YouTubeGraphPipeline()

- Fetches auto-generated or manual transcripts

urls = [- Restores punctuation using AI (deepmultilingualpunctuation)

    "https://youtube.com/watch?v=VIDEO1",- Chunks into 150-300 word segments with timestamps

    "https://youtube.com/watch?v=VIDEO2",

    "https://youtube.com/watch?v=VIDEO3",### 2. Semantic Grouping

]

```

for url in urls:Segments → Vector Embeddings → k-NN Graph → Boundary Detection → Topic Groups

    result = pipeline.process_video(url)```

    print(f"✅ {result.video_id}: {result.concept_count} concepts")

**Core Algorithm:**

pipeline.close()1. **Build k-NN Neighborhoods** - Find similar segments via Weaviate vector search

```2. **Apply Temporal Decay** - Penalize distant segments: `sim_eff = sim * exp(-Δt / τ)`

3. **Detect Boundaries** - Identify topic shifts via cohesion dips

### Workflow 3: Query Knowledge Graph4. **Greedy Growth** - Form groups with word count guardrails (400-800 words)

5. **Post-Merge** - Combine highly similar adjacent groups

```bash

# View all concepts for a videoSee [docs/GROUP_SEGMENTS.md](docs/GROUP_SEGMENTS.md) for detailed strategy.

python scripts/query_concepts.py VIDEO_ID

### 3. Output Format

# Semantic search across all videos

python scripts/query_concepts.py --search "neural networks"Groups are exported as JSON:



# Quality analysis```json

python scripts/query_concepts.py --quality VIDEO_ID{

  "video_id": "VIDEO_ID",

# Database statistics  "num_groups": 15,

python scripts/query_concepts.py --stats  "groups": [

```    {

      "group_id": 0,

---      "start_time": 120.5,

      "end_time": 245.8,

## 🎯 Quality Metrics      "num_segments": 3,

      "total_words": 650,

Good results show:      "avg_cohesion": 0.82,

      "text": "Combined text of all segments...",

- ✅ **Cohesion ≥ 0.70** - Segments within groups are semantically related      "segments": [...]

- ✅ **Group size 400-800 words** - Optimal for LLM processing    }

- ✅ **15-30 groups per hour** - Appropriate granularity  ]

- ✅ **Concept extraction ≥ 5 per group** - Rich knowledge capture}

- ✅ **Relationship detection ≥ 2 per group** - Connected knowledge graph```



---## 📊 Quality Metrics



## 🔧 TroubleshootingGood grouping results show:



### "Collection 'Segment' not found"- ✅ **Average cohesion ≥ 0.70** - Segments within groups are semantically similar

→ Run `python scripts/init_weaviate_schema.py`- ✅ **Word counts 400-800** - Optimal for LLM processing

- ✅ **≥80% coverage** - Most segments assigned to groups

### "Low cohesion scores (< 0.60)"- ✅ **Reasonable group count** - Typically 20-30 groups per hour of video

→ Run `python scripts/diagnose_embeddings.py VIDEO_ID` for diagnostics

## 🔧 Configuration

### "Few concepts extracted"

→ Check video content (technical content works best)### Hyperparameters



### "No relationships detected"| Parameter | Default | Description |

→ Ensure concepts are from same video/group (intra-group relationships)|-----------|---------|-------------|

| `k_neighbors` | 8 | Number of nearest neighbors to fetch |

---| `neighbor_threshold` | 0.75 | Minimum similarity to keep a neighbor |

| `adjacent_threshold` | 0.70 | Minimum similarity to join adjacent segments |

## 📖 Documentation| `temporal_tau` | 150s | Temporal decay constant (higher = slower decay) |

| `max_group_words` | 700 | Maximum words per group |

- **README.md** (this file) - Overview and quick start| `min_group_segments` | 2 | Minimum segments per group |

- **SCRIPTS.md** - Detailed explanation of all scripts| `merge_centroid_threshold` | 0.85 | Similarity threshold for post-merge |

- See `scripts/` directory for individual script `--help`

### Tuning Guide

---

**If groups are too fragmented:**

## 🛠️ Tech Stack- ↓ Lower `adjacent_threshold` (e.g., 0.60)

- ↑ Increase `temporal_tau` (e.g., 200)

| Component | Technology | Purpose |

|-----------|-----------|---------|**If groups are too large:**

| **Vector DB** | Weaviate | Segment storage + similarity search |- ↑ Raise `adjacent_threshold` (e.g., 0.75)

| **Graph DB** | Neo4j | Concept + relationship storage |- ↓ Decrease `max_group_words` (e.g., 600)

| **Embeddings** | OpenAI text-embedding-3-small | Semantic vectors |

| **LLM** | OpenAI GPT-4o-mini | Concept extraction |**If cohesion is too low:**

| **Transcript** | youtube-transcript-api | Video transcript fetching |- ↑ Raise both thresholds

| **Punctuation** | deepmultilingualpunctuation | Sentence restoration |- Run `diagnose_embeddings.py` for data-specific recommendations



---## 🎓 Best Practices



## 🎓 Best For### Recommended Content Types



**✅ Works Great:**✅ **Works Great:**

- Educational videos (tutorials, lectures)- Educational tutorials

- Technical presentations (conferences, talks)- Technical presentations

- Product reviews and demos- Single-speaker lectures

- Gaming commentary with narration- Gaming commentary

- Podcast recordings- Product reviews



**⚠️ Challenging:**⚠️ **Challenging:**

- Music videos (minimal dialogue)- Multi-speaker interviews (topic switching)

- Multi-speaker debates (rapid topic switching)- Debates (adversarial content)

- Short clips (< 5 minutes)- Music videos (minimal dialogue)



---### Workflow



## 📊 Example Results#### Quick Start (Full Pipeline)



### Input Video1. **Set up environment** - Create `.env` with API keys

"Introduction to Neural Networks" (45 minutes)2. **Run pipeline** - `python scripts/pipeline.py` (processes and groups automatically)

3. **Visualize** - `python scripts/visualize_groups.py` to check quality

### Output4. **Iterate** - Adjust `grouping_params` in pipeline if needed

- **Segments**: 180 (150-300 words each)

- **Groups**: 22 (400-800 words each)#### Advanced (Manual Control)

- **Concepts**: 137 (entities, methods, ideas)

- **Relationships**: 89 (connections between concepts)1. **Start Small** - Test with 1-2 videos first

2. **Diagnose** - Run `python scripts/diagnose_embeddings.py VIDEO_ID` to understand similarity

### Sample Concepts3. **Tune** - Adjust hyperparameters based on diagnostics

```4. **Validate** - Use `python scripts/visualize_groups.py` to check quality

Neural Network (Concept, importance: 0.95)5. **Scale** - Batch process with `python scripts/run_grouping.py`

Gradient Descent (Method, importance: 0.88)

Backpropagation (Method, importance: 0.92)## 📚 Documentation

Activation Function (Concept, importance: 0.85)

TensorFlow (Technology, importance: 0.75)- **[GROUP_SEGMENTS.md](docs/GROUP_SEGMENTS.md)** - Detailed grouping strategy and algorithm

```- **[README_GROUPING.md](docs/README_GROUPING.md)** - User guide for segment grouping

- **[IMPLEMENTATION_SUMMARY.md](docs/IMPLEMENTATION_SUMMARY.md)** - Implementation details and next steps

### Sample Relationships

```## 🎯 Current Status

(Neural Network)-[IMPLEMENTS]->(Gradient Descent)

(Backpropagation)-[REQUIRES]->(Chain Rule)### ✅ Completed

(Activation Function)-[PART_OF]->(Neural Network)- [x] YouTube transcript fetching

```- [x] Punctuation restoration

- [x] Semantic segmentation (150-300 words)

---- [x] Weaviate upload with embeddings

- [x] Semantic grouping (400-800 words)

## 🚀 Next Steps- [x] Temporal coherence preservation

- [x] Automated end-to-end pipeline

1. **Try it**: `python scripts/pipeline.py`- [x] Quality analytics & visualization

2. **Read scripts**: See `SCRIPTS.md` for detailed script documentation- [x] LLM-based concept extraction from groups

3. **Explore code**: Check `src/` for library implementation- [x] Neo4j-backed concept + relationship storage

4. **Query graph**: Use Neo4j Browser or `scripts/query_concepts.py`

### 🚧 In Progress

---- [ ] Cue-phrase detection and cross-references



## 📝 License## 🔮 Future Enhancements



MIT License- [ ] Cross-video concept linking

- [ ] Neo4j knowledge graph integration

## 👤 Author- [ ] Hierarchical grouping (groups → topics → themes)

- [ ] Web UI for interactive exploration

[Grihladin](https://github.com/Grihladin)- [ ] Multi-language support

- [ ] Real-time streaming support

---

## 🤝 Contributing

**Status**: ✅ Production Ready

This is a research/experimental project. Contributions welcome!

**Version**: 2.0.0 (Refactored Architecture)

## 📝 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- **Weaviate** - Vector database
- **Neo4j** - Graph database
- **OpenAI** - Text embeddings (text-embedding-ada-002)
- **deepmultilingualpunctuation** - Punctuation restoration
- **youtube-transcript-api** - Transcript fetching

---

**Status:** ✅ Transcript processing and grouping complete. Ready for idea extraction phase.

**Author:** [Grihladin](https://github.com/Grihladin)

**Version:** 0.1.0
