#!/usr/bin/env python3
"""Ensure Neo4j constraints and optionally clean existing video data."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.infrastructure.neo4j.neo4j_graph import Neo4jGraph  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Provision Neo4j constraints for the YouTubeGraph knowledge graph",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--uri",
        default=os.getenv("NEO4J_URI"),
        help="Neo4j bolt URI (fallback to NEO4J_URI)",
    )
    parser.add_argument(
        "--user",
        default=os.getenv("NEO4J_USER"),
        help="Neo4j username (fallback to NEO4J_USER)",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("NEO4J_PASSWORD"),
        help="Neo4j password (fallback to NEO4J_PASSWORD)",
    )
    parser.add_argument(
        "--database",
        default=os.getenv("NEO4J_DATABASE"),
        help="Neo4j database name (defaults to server default if omitted)",
    )
    parser.add_argument(
        "--reset-video",
        metavar="VIDEO_ID",
        help="Delete all concepts and relationships for the specified video before exiting",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print concept and relationship counts after ensuring constraints",
    )
    return parser.parse_args()


def exit_with_error(message: str) -> None:
    print(f"❌ {message}")
    sys.exit(1)


def ensure_constraints(
    uri: str,
    user: str,
    password: str,
    database: Optional[str] = None,
    reset_video: Optional[str] = None,
    show_stats: bool = False,
) -> None:
    graph = Neo4jGraph(uri=uri, user=user, password=password, database=database)
    print(
        "✅ Ensured Neo4j constraints for Concept, ConceptMention, and GRAPH_RELATION"
    )

    try:
        if reset_video:
            concepts_removed = graph.delete_concepts_for_video(reset_video)
            relationships_removed = graph.delete_relationships_for_video(reset_video)
            print(
                f"🧹 Reset video {reset_video}: removed {concepts_removed} concepts and {relationships_removed} relationships"
            )

        if show_stats:
            concept_stats = graph.get_statistics()
            relationship_count = graph.count_relationships()
            total_concepts = concept_stats.get("total_concepts", 0)
            print("\n📊 Neo4j Summary:")
            print(f"  Concepts stored: {total_concepts}")
            print(f"  Relationships stored: {relationship_count}")
            print(
                "  Collections available: "
                + ", ".join(concept_stats.get("collections_available", []))
            )
    finally:
        graph.close()
        print("✓ Neo4j connection closed")


def main() -> None:
    load_dotenv()
    args = parse_args()

    if not args.uri or not args.user or not args.password:
        exit_with_error(
            "Missing credentials. Provide --uri/--user/--password or set NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD in .env"
        )

    ensure_constraints(
        uri=args.uri,
        user=args.user,
        password=args.password,
        database=args.database,
        reset_video=args.reset_video,
        show_stats=args.stats,
    )


if __name__ == "__main__":
    main()
