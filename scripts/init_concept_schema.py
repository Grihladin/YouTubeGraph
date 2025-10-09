"""Initialize Weaviate collections for Concept and ConceptMention."""

from __future__ import annotations

import os
import sys
from typing import Optional

import weaviate
from weaviate.classes.config import Configure, DataType, Property, ReferenceProperty
from weaviate.classes.init import Auth
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def create_concept_collection(
    client: weaviate.WeaviateClient, openai_api_key: str, overwrite: bool = False
) -> None:
    """Create the Concept collection in Weaviate.

    Args:
        client: Connected Weaviate client
        openai_api_key: OpenAI API key for vectorization
        overwrite: If True, delete existing collection before creating
    """
    collection_name = "Concept"

    # Check if collection exists
    if client.collections.exists(collection_name):
        if overwrite:
            print(f"⚠️  Deleting existing '{collection_name}' collection...")
            client.collections.delete(collection_name)
        else:
            print(f"✓ Collection '{collection_name}' already exists")
            return

    print(f"📝 Creating '{collection_name}' collection...")

    client.collections.create(
        name=collection_name,
        description="Knowledge concepts extracted from video transcript groups",
        # Vector configuration - embed name + definition
        vectorizer_config=Configure.Vectorizer.text2vec_openai(
            model="text-embedding-3-small",
            model_version="3",
            dimensions=1536,
        ),
        # Properties
        properties=[
            Property(
                name="name",
                data_type=DataType.TEXT,
                description="Canonical concept name (2-6 words, title case)",
                skip_vectorization=False,  # Include in embedding
            ),
            Property(
                name="definition",
                data_type=DataType.TEXT,
                description="Clear 1-3 sentence explanation of the concept",
                skip_vectorization=False,  # Include in embedding
            ),
            Property(
                name="type",
                data_type=DataType.TEXT,
                description="Category: Person, Technology, Method, Problem, Solution, Concept, Metric, Dataset, Event, Organization, Place",
            ),
            Property(
                name="importance",
                data_type=DataType.NUMBER,
                description="Global significance score (0.0-1.0)",
            ),
            Property(
                name="confidence",
                data_type=DataType.NUMBER,
                description="Extraction confidence score (0.0-1.0)",
            ),
            Property(
                name="aliases",
                data_type=DataType.TEXT_ARRAY,
                description="Alternative names or spellings",
            ),
            Property(
                name="videoId",
                data_type=DataType.TEXT,
                description="Source video ID",
                index_filterable=True,
                index_searchable=False,
            ),
            Property(
                name="groupId",
                data_type=DataType.INT,
                description="Source group ID within the video",
                index_filterable=True,
            ),
            Property(
                name="firstMentionTime",
                data_type=DataType.NUMBER,
                description="Timestamp of first appearance in video (seconds)",
            ),
            Property(
                name="lastMentionTime",
                data_type=DataType.NUMBER,
                description="Timestamp of last appearance in video (seconds)",
            ),
            Property(
                name="mentionCount",
                data_type=DataType.INT,
                description="Number of times mentioned in the group",
            ),
            Property(
                name="extractedAt",
                data_type=DataType.DATE,
                description="ISO 8601 timestamp when concept was extracted",
            ),
        ],
    )

    print(f"✅ Created collection '{collection_name}'")


def create_concept_mention_collection(
    client: weaviate.WeaviateClient, openai_api_key: str, overwrite: bool = False
) -> None:
    """Create the ConceptMention collection in Weaviate.

    Args:
        client: Connected Weaviate client
        openai_api_key: OpenAI API key for vectorization
        overwrite: If True, delete existing collection before creating
    """
    collection_name = "ConceptMention"

    # Check if collection exists
    if client.collections.exists(collection_name):
        if overwrite:
            print(f"⚠️  Deleting existing '{collection_name}' collection...")
            client.collections.delete(collection_name)
        else:
            print(f"✓ Collection '{collection_name}' already exists")
            return

    print(f"📝 Creating '{collection_name}' collection...")

    client.collections.create(
        name=collection_name,
        description="Specific occurrences of concepts in transcript text",
        # Vector configuration - embed the surface text
        vectorizer_config=Configure.Vectorizer.text2vec_openai(
            model="text-embedding-3-small",
            model_version="3",
            dimensions=1536,
        ),
        # Properties
        properties=[
            Property(
                name="surface",
                data_type=DataType.TEXT,
                description="Exact text span from transcript",
                skip_vectorization=False,  # Include in embedding
            ),
            Property(
                name="offsetStart",
                data_type=DataType.INT,
                description="Character offset in group text (optional)",
            ),
            Property(
                name="offsetEnd",
                data_type=DataType.INT,
                description="Character offset end in group text (optional)",
            ),
            Property(
                name="timestamp",
                data_type=DataType.NUMBER,
                description="When this mention occurs in video (seconds)",
            ),
            Property(
                name="salience",
                data_type=DataType.NUMBER,
                description="Local importance in this context (0.0-1.0)",
            ),
            Property(
                name="groupId",
                data_type=DataType.INT,
                description="Which group this mention is in",
                index_filterable=True,
            ),
            Property(
                name="videoId",
                data_type=DataType.TEXT,
                description="Source video ID",
                index_filterable=True,
                index_searchable=False,
            ),
        ],
        # Cross-reference to Concept
        references=[
            ReferenceProperty(
                name="concept",
                target_collection="Concept",
                description="The concept this mention refers to",
            ),
        ],
    )

    print(f"✅ Created collection '{collection_name}'")


def verify_collections(client: weaviate.WeaviateClient) -> bool:
    """Verify that collections were created successfully.

    Args:
        client: Connected Weaviate client

    Returns:
        True if all collections exist and are configured correctly
    """
    print("\n🔍 Verifying collections...")

    required_collections = ["Concept", "ConceptMention"]
    all_exist = True

    for name in required_collections:
        if client.collections.exists(name):
            collection = client.collections.get(name)
            config = collection.config.get()

            print(f"✓ {name}:")
            print(f"  - Properties: {len(config.properties)}")
            print(f"  - Vectorizer: {config.vectorizer_config}")

            if name == "ConceptMention":
                print(f"  - References: {len(config.references)}")
        else:
            print(f"❌ {name}: NOT FOUND")
            all_exist = False

    return all_exist


def main():
    """Initialize concept schema in Weaviate."""
    print("🚀 Initializing Concept Schema in Weaviate\n")

    # Get credentials from environment
    WEAVIATE_URL = os.getenv("WEAVIATE_URL")
    WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    if not all([WEAVIATE_URL, WEAVIATE_API_KEY, OPENAI_API_KEY]):
        print("❌ Error: Missing required environment variables")
        print("\nRequired:")
        print("  - WEAVIATE_URL")
        print("  - WEAVIATE_API_KEY")
        print("  - OPENAI_API_KEY")
        print("\nSet these in your .env file")
        sys.exit(1)

    # Parse command line arguments
    overwrite = "--overwrite" in sys.argv or "-f" in sys.argv

    if overwrite:
        print("⚠️  WARNING: --overwrite flag detected")
        print("This will DELETE existing Concept/ConceptMention collections!")
        response = input("Continue? (yes/no): ")
        if response.lower() != "yes":
            print("Cancelled.")
            sys.exit(0)
        print()

    # Connect to Weaviate
    print(f"📡 Connecting to Weaviate: {WEAVIATE_URL}")
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=WEAVIATE_URL,
        auth_credentials=Auth.api_key(WEAVIATE_API_KEY),
        headers={"X-OpenAI-Api-Key": OPENAI_API_KEY},
    )

    try:
        if not client.is_ready():
            print("❌ Weaviate cluster is not ready")
            sys.exit(1)

        print("✓ Connected to Weaviate\n")

        # Create collections
        create_concept_collection(client, OPENAI_API_KEY, overwrite=overwrite)
        create_concept_mention_collection(client, OPENAI_API_KEY, overwrite=overwrite)

        # Verify
        if verify_collections(client):
            print("\n✅ Schema initialization complete!")
            print("\nNext steps:")
            print("  1. Run concept extraction: python scripts/extract_concepts.py")
            print("  2. View extracted concepts: python scripts/query_concepts.py")
        else:
            print("\n❌ Schema verification failed")
            sys.exit(1)

    finally:
        client.close()
        print("\n✓ Connection closed")


if __name__ == "__main__":
    main()
