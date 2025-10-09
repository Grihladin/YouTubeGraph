"""Weaviate client for vector storage operations."""

from __future__ import annotations

from typing import Optional

import weaviate
from weaviate.classes.init import Auth

from src.config import WeaviateConfig
from src.utils.logging import get_logger

logger = get_logger(__name__)


class WeaviateClient:
    """Manages Weaviate connection."""

    def __init__(self, config: WeaviateConfig):
        """Initialize Weaviate client.

        Args:
            config: Weaviate configuration
        """
        self.config = config
        self.client: Optional[weaviate.WeaviateClient] = None

    def connect(self, openai_api_key: Optional[str] = None) -> weaviate.WeaviateClient:
        """Establish connection to Weaviate.

        Args:
            openai_api_key: Optional OpenAI API key for embeddings

        Returns:
            Connected Weaviate client
        """
        if self.client and self.client.is_ready():
            return self.client

        logger.info(f"Connecting to Weaviate at {self.config.url}")

        headers = {"X-OpenAI-Api-Key": openai_api_key} if openai_api_key else None

        self.client = weaviate.connect_to_weaviate_cloud(
            cluster_url=self.config.url,
            auth_credentials=Auth.api_key(self.config.api_key),
            headers=headers,
        )

        if self.client.is_ready():
            logger.info("Successfully connected to Weaviate")
        else:
            logger.error("Failed to connect to Weaviate")

        return self.client

    def is_ready(self) -> bool:
        """Check if client is connected and ready."""
        return self.client is not None and self.client.is_ready()

    def close(self):
        """Close the Weaviate connection."""
        if self.client:
            self.client.close()
            logger.info("Closed Weaviate connection")
            self.client = None
