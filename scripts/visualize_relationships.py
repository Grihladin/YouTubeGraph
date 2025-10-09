"""Visualize concept graph with typed relationships.

This script creates a visual representation of concepts and their relationships
from Weaviate, showing the knowledge graph structure.

Usage:
    python scripts/visualize_relationships.py VIDEO_ID [--output FILE] [--format FORMAT]

Arguments:
    VIDEO_ID          Video identifier (e.g., CUS6ABgI1As)
    --output FILE     Output filename (default: output/graphs/relationships_VIDEO_ID.html)
    --format FORMAT   Output format: html, png, svg, pdf (default: html)
"""

import os
import sys
from pathlib import Path
from uuid import UUID

import weaviate
from dotenv import load_dotenv
from weaviate.classes.init import Auth

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load environment
load_dotenv()


def fetch_concepts_and_relationships(client: weaviate.WeaviateClient, video_id: str):
    """Fetch concepts and relationships for a video.

    Args:
        client: Weaviate client
        video_id: Video ID

    Returns:
        Tuple of (concepts_dict, relationships_list)
    """
    print(f"📡 Fetching data for video {video_id}...")

    # Fetch concepts
    concept_collection = client.collections.get("Concept")
    concept_response = concept_collection.query.fetch_objects(
        filters={"path": ["videoId"], "operator": "Equal", "valueText": video_id},
        limit=1000,
    )

    concepts = {}
    for obj in concept_response.objects:
        props = obj.properties
        concepts[str(obj.uuid)] = {
            "id": str(obj.uuid),
            "name": props["name"],
            "type": props["type"],
            "importance": props["importance"],
            "confidence": props["confidence"],
            "group_id": props["groupId"],
        }

    print(f"  ✓ Fetched {len(concepts)} concepts")

    # Fetch relationships
    relationship_collection = client.collections.get("Relationship")

    # Get relationships where source or target is from this video
    relationship_response = relationship_collection.query.fetch_objects(
        filters={
            "operator": "Or",
            "operands": [
                {"path": ["sourceVideoId"], "operator": "Equal", "valueText": video_id},
                {"path": ["targetVideoId"], "operator": "Equal", "valueText": video_id},
            ],
        },
        limit=10000,
        return_references=["sourceConcept", "targetConcept"],
    )

    relationships = []
    for obj in relationship_response.objects:
        props = obj.properties
        refs = obj.references

        # Get source and target concept IDs
        source_id = str(refs["sourceConcept"].objects[0].uuid)
        target_id = str(refs["targetConcept"].objects[0].uuid)

        relationships.append(
            {
                "id": str(obj.uuid),
                "source": source_id,
                "target": target_id,
                "type": props["type"],
                "confidence": props["confidence"],
                "evidence": props.get("evidence", ""),
                "detection_method": props["detectionMethod"],
            }
        )

    print(f"  ✓ Fetched {len(relationships)} relationships")

    return concepts, relationships


def create_visualization(
    concepts, relationships, output_file: Path, format: str = "html"
):
    """Create visualization using network graph.

    Args:
        concepts: Dictionary of concepts
        relationships: List of relationships
        output_file: Output file path
        format: Output format (html, png, svg, pdf)
    """
    try:
        from pyvis.network import Network
    except ImportError:
        print("❌ pyvis not installed. Install with: pip install pyvis")
        sys.exit(1)

    print(f"\n📊 Creating {format.upper()} visualization...")

    # Create network
    net = Network(
        height="900px",
        width="100%",
        bgcolor="#ffffff",
        font_color="#000000",
        directed=True,
    )

    # Configure physics
    net.set_options(
        """
    {
        "physics": {
            "enabled": true,
            "barnesHut": {
                "gravitationalConstant": -8000,
                "centralGravity": 0.3,
                "springLength": 200,
                "springConstant": 0.04,
                "damping": 0.09
            },
            "minVelocity": 0.75
        }
    }
    """
    )

    # Color mapping for concept types
    type_colors = {
        "Person": "#ff6b6b",
        "Organization": "#4ecdc4",
        "Technology": "#45b7d1",
        "Method": "#96ceb4",
        "Problem": "#ffeaa7",
        "Solution": "#55efc4",
        "Concept": "#a29bfe",
        "Metric": "#fd79a8",
        "Dataset": "#fdcb6e",
        "Event": "#e17055",
        "Place": "#00b894",
    }

    # Add concept nodes
    for concept_id, concept in concepts.items():
        color = type_colors.get(concept["type"], "#95a5a6")

        # Size based on importance
        size = 10 + (concept["importance"] * 30)

        # Title with metadata
        title = f"<b>{concept['name']}</b><br>"
        title += f"Type: {concept['type']}<br>"
        title += f"Importance: {concept['importance']:.2f}<br>"
        title += f"Confidence: {concept['confidence']:.2f}<br>"
        title += f"Group: {concept['group_id']}"

        net.add_node(
            concept_id,
            label=concept["name"],
            title=title,
            color=color,
            size=size,
            font={"size": 12},
        )

    # Color mapping for relationship types
    rel_type_colors = {
        "defines": "#e74c3c",
        "causes": "#e67e22",
        "requires": "#f39c12",
        "contradicts": "#c0392b",
        "exemplifies": "#16a085",
        "implements": "#27ae60",
        "uses": "#2980b9",
        "builds_on": "#8e44ad",
        "elaborates": "#9b59b6",
        "references": "#34495e",
        "refines": "#1abc9c",
    }

    # Add relationship edges
    for rel in relationships:
        # Skip if source or target not in concepts (e.g., cross-video relationships)
        if rel["source"] not in concepts or rel["target"] not in concepts:
            continue

        color = rel_type_colors.get(rel["type"], "#7f8c8d")

        # Width based on confidence
        width = 1 + (rel["confidence"] * 3)

        # Title with metadata
        title = f"<b>{rel['type']}</b><br>"
        title += f"Confidence: {rel['confidence']:.2f}<br>"
        title += f"Method: {rel['detection_method']}<br>"
        if rel["evidence"]:
            evidence_preview = (
                rel["evidence"][:100] + "..."
                if len(rel["evidence"]) > 100
                else rel["evidence"]
            )
            title += f"Evidence: {evidence_preview}"

        net.add_edge(
            rel["source"],
            rel["target"],
            title=title,
            color=color,
            width=width,
            arrows="to",
            label=rel["type"],
            font={"size": 8, "align": "middle"},
        )

    # Save visualization
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if format == "html":
        net.show(str(output_file))
        print(f"✅ Saved visualization to: {output_file}")
        print(f"   Open in browser to view the interactive graph")
    else:
        print(f"⚠️  Non-HTML formats require additional dependencies")
        print(f"   Falling back to HTML format")
        net.show(str(output_file.with_suffix(".html")))
        print(f"✅ Saved visualization to: {output_file.with_suffix('.html')}")

    # Print statistics
    print(f"\n📊 Graph Statistics:")
    print(f"   Nodes (Concepts): {len(concepts)}")
    print(
        f"   Edges (Relationships): {len([r for r in relationships if r['source'] in concepts and r['target'] in concepts])}"
    )

    # Relationship type distribution
    rel_types = {}
    for rel in relationships:
        if rel["source"] in concepts and rel["target"] in concepts:
            rel_types[rel["type"]] = rel_types.get(rel["type"], 0) + 1

    print(f"\n   Relationship Types:")
    for rel_type, count in sorted(rel_types.items(), key=lambda x: x[1], reverse=True):
        print(f"      {rel_type:20s}: {count}")


def main():
    """Main entry point."""
    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        return

    # Parse arguments
    video_id = None
    output_file = None
    format = "html"

    i = 0
    while i < len(args):
        arg = args[i]

        if arg == "--output":
            if i + 1 < len(args):
                output_file = Path(args[i + 1])
                i += 2
            else:
                print("❌ --output requires a filename")
                sys.exit(1)
        elif arg == "--format":
            if i + 1 < len(args):
                format = args[i + 1].lower()
                i += 2
            else:
                print("❌ --format requires a format type")
                sys.exit(1)
        elif not arg.startswith("--"):
            video_id = arg
            i += 1
        else:
            print(f"❌ Unknown argument: {arg}")
            sys.exit(1)

    if not video_id:
        print("❌ No video ID specified")
        print("   Usage: python scripts/visualize_relationships.py VIDEO_ID [options]")
        sys.exit(1)

    # Default output file
    if not output_file:
        output_file = Path(f"output/graphs/relationships_{video_id}.{format}")

    print("🎨 Relationship Visualization")
    print(f"{'='*70}")
    print(f"Video ID: {video_id}")
    print(f"Output: {output_file}")
    print(f"Format: {format}")
    print(f"{'='*70}\n")

    # Connect to Weaviate
    WEAVIATE_URL = os.getenv("WEAVIATE_URL")
    WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    if not all([WEAVIATE_URL, WEAVIATE_API_KEY, OPENAI_API_KEY]):
        print("❌ Missing environment variables")
        sys.exit(1)

    print("📡 Connecting to Weaviate...")
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=WEAVIATE_URL,
        auth_credentials=Auth.api_key(WEAVIATE_API_KEY),
        headers={"X-OpenAI-Api-Key": OPENAI_API_KEY},
    )

    try:
        if not client.is_ready():
            print("❌ Weaviate cluster is not ready")
            sys.exit(1)

        print("  ✓ Connected\n")

        # Fetch data
        concepts, relationships = fetch_concepts_and_relationships(client, video_id)

        if not concepts:
            print("❌ No concepts found for this video")
            sys.exit(1)

        if not relationships:
            print("⚠️  No relationships found for this video")
            print("   Run: python scripts/extract_relationships.py", video_id)
            sys.exit(1)

        # Create visualization
        create_visualization(concepts, relationships, output_file, format)

        print("\n🎉 Done!")

    finally:
        client.close()
        print("\n✓ Connection closed")


if __name__ == "__main__":
    main()
