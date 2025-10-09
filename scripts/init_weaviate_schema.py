#!/usr/bin/env python3
"""Initialize or verify Weaviate collection schema for YouTube transcript segments.

This script:
1. Connects to Weaviate
2. Checks if the 'Segment' collection exists
3. Creates it if missing (with OpenAI text2vec vectorizer)
4. Verifies the schema is properly configured
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.init import Auth

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
load_dotenv()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Initialize Weaviate collection schema for transcript segments",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--url",
        default=os.getenv("WEAVIATE_URL"),
        help="Weaviate cluster URL (or set WEAVIATE_URL env var)",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("WEAVIATE_API_KEY"),
        help="Weaviate API key (or set WEAVIATE_API_KEY env var)",
    )
    parser.add_argument(
        "--openai-key",
        default=os.getenv("OPENAI_API_KEY"),
        help="OpenAI API key for vectorization (or set OPENAI_API_KEY env var)",
    )
    parser.add_argument(
        "--collection",
        default="Segment",
        help="Collection name to create/verify",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete and recreate collection if it exists",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show collection statistics after initialization",
    )
    return parser.parse_args()


def exit_with_error(message: str) -> None:
    """Print error and exit."""
    print(f"❌ {message}")
    sys.exit(1)


def create_segment_collection(
    client: weaviate.WeaviateClient, collection_name: str, force: bool = False
) -> bool:
    """Create the Segment collection with proper schema.

    Args:
        client: Connected Weaviate client
        collection_name: Name of collection to create
        force: If True, delete existing collection first

    Returns:
        True if collection was created, False if it already existed
    """
    # Check if collection exists
    exists = client.collections.exists(collection_name)

    if exists:
        if force:
            print(
                f"⚠️  Collection '{collection_name}' exists. Deleting due to --force flag..."
            )
            client.collections.delete(collection_name)
            print(f"✓ Deleted existing collection")
        else:
            print(f"✓ Collection '{collection_name}' already exists")
            return False

    # Create collection with schema
    print(f"🔨 Creating collection '{collection_name}'...")

    client.collections.create(
        name=collection_name,
        description="YouTube transcript segments with timestamps and embeddings",
        vectorizer_config=Configure.Vectorizer.text2vec_openai(
            model="text-embedding-3-small",
            vectorize_collection_name=False,
        ),
        properties=[
            Property(
                name="videoId",
                data_type=DataType.TEXT,
                description="YouTube video ID",
                skip_vectorization=True,
                index_filterable=True,
                index_searchable=False,
            ),
            Property(
                name="text",
                data_type=DataType.TEXT,
                description="Transcript segment text (vectorized)",
                skip_vectorization=False,
                index_filterable=False,
                index_searchable=True,
            ),
            Property(
                name="start_s",
                data_type=DataType.NUMBER,
                description="Start timestamp in seconds",
                skip_vectorization=True,
                index_filterable=True,
                index_searchable=False,
            ),
            Property(
                name="end_s",
                data_type=DataType.NUMBER,
                description="End timestamp in seconds",
                skip_vectorization=True,
                index_filterable=True,
                index_searchable=False,
            ),
            Property(
                name="tokens",
                data_type=DataType.INT,
                description="Word count in segment",
                skip_vectorization=True,
                index_filterable=True,
                index_searchable=False,
            ),
        ],
    )

    print(f"✅ Created collection '{collection_name}' with OpenAI text2vec vectorizer")
    return True


def verify_schema(client: weaviate.WeaviateClient, collection_name: str) -> None:
    """Verify collection schema is correct.

    Args:
        client: Connected Weaviate client
        collection_name: Name of collection to verify
    """
    print(f"\n🔍 Verifying collection schema...")

    try:
        collection = client.collections.get(collection_name)
        config = collection.config.get()

        print(f"✓ Collection name: {config.name}")
        print(f"✓ Description: {config.description or '(none)'}")

        # Check vectorizer
        if config.vectorizer_config:
            vectorizer = config.vectorizer_config
            print(f"✓ Vectorizer: {vectorizer}")
        else:
            print("⚠️  No vectorizer configured!")

        # Check properties
        print(f"✓ Properties ({len(config.properties)}):")
        for prop in config.properties:
            print(f"   - {prop.name}: {prop.data_type}")

        print(f"\n✅ Schema verification complete")

    except Exception as e:
        print(f"⚠️  Error verifying schema: {e}")


def show_stats(client: weaviate.WeaviateClient, collection_name: str) -> None:
    """Show collection statistics.

    Args:
        client: Connected Weaviate client
        collection_name: Name of collection to check
    """
    print(f"\n📊 Collection Statistics:")

    try:
        collection = client.collections.get(collection_name)

        # Get count
        response = collection.aggregate.over_all(total_count=True)
        count = response.total_count if response.total_count else 0

        print(f"   Total segments: {count}")

        if count > 0:
            # Get sample to check videos
            sample = collection.query.fetch_objects(limit=1000)
            video_ids = set()
            for obj in sample.objects:
                video_ids.add(obj.properties.get("videoId", "unknown"))

            print(f"   Unique videos: {len(video_ids)}")
            if len(video_ids) <= 10:
                print(f"   Video IDs: {', '.join(sorted(video_ids))}")

    except Exception as e:
        print(f"⚠️  Error fetching statistics: {e}")


def main() -> None:
    """Main execution."""
    args = parse_args()

    # Validate credentials
    if not args.url or not args.api_key:
        exit_with_error(
            "Missing Weaviate credentials. Provide --url and --api-key or set "
            "WEAVIATE_URL and WEAVIATE_API_KEY environment variables"
        )

    if not args.openai_key:
        exit_with_error(
            "Missing OpenAI API key. Provide --openai-key or set OPENAI_API_KEY "
            "environment variable (required for text vectorization)"
        )

    print(f"\n{'='*60}")
    print(f"Weaviate Collection Initialization")
    print(f"{'='*60}\n")

    # Connect to Weaviate
    print(f"🔌 Connecting to Weaviate at {args.url}...")

    try:
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=args.url,
            auth_credentials=Auth.api_key(args.api_key),
            headers={"X-OpenAI-Api-Key": args.openai_key},
        )

        if not client.is_ready():
            exit_with_error("Failed to connect to Weaviate")

        print(f"✓ Connected successfully\n")

        # Create or verify collection
        created = create_segment_collection(client, args.collection, force=args.force)

        # Verify schema
        verify_schema(client, args.collection)

        # Show stats if requested
        if args.stats:
            show_stats(client, args.collection)

        print(f"\n{'='*60}")
        if created:
            print(f"✅ Collection '{args.collection}' created successfully!")
        else:
            print(f"✅ Collection '{args.collection}' verified successfully!")
        print(f"{'='*60}\n")

    except Exception as e:
        exit_with_error(f"Error: {e}")

    finally:
        if client:
            client.close()


if __name__ == "__main__":
    main()
