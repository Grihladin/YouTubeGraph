"""Neo4j client for graph database operations."""

from __future__ import annotations

from typing import Optional

from src.config import Neo4jConfig
from src.infrastructure.neo4j.neo4j_graph import Neo4jGraph
from src.utils.logging import get_logger

logger = get_logger(__name__)


class Neo4jClient:
    """Manages Neo4j connection using existing Neo4jGraph."""

    def __init__(self, config: Neo4jConfig):
        """Initialize Neo4j client.

        Args:
            config: Neo4j configuration
        """
        self.config = config
        self.graph: Optional[Neo4jGraph] = None

    def connect(self) -> Neo4jGraph:
        """Establish connection to Neo4j.

        Returns:
            Connected Neo4jGraph instance
        """
        if self.graph:
            return self.graph

        logger.info(f"Connecting to Neo4j at {self.config.uri}")

        self.graph = Neo4jGraph(
            uri=self.config.uri,
            user=self.config.user,
            password=self.config.password,
            database=self.config.database,
        )

        logger.info("Successfully connected to Neo4j")
        return self.graph

    def close(self):
        """Close the Neo4j connection."""
        if self.graph:
            self.graph.close()
            logger.info("Closed Neo4j connection")
            self.graph = None
