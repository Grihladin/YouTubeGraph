"""Centralized configuration management for YouTubeGraph.

All environment variables and configuration settings are managed here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class WeaviateConfig:
    """Weaviate vector store configuration."""

    url: str
    api_key: str
    collection_name: str = "Segment"

    @classmethod
    def from_env(cls) -> WeaviateConfig:
        """Load configuration from environment variables."""
        url = os.getenv("WEAVIATE_URL")
        api_key = os.getenv("WEAVIATE_API_KEY")

        if not url or not api_key:
            raise ValueError(
                "Missing Weaviate credentials. Set WEAVIATE_URL and WEAVIATE_API_KEY"
            )

        return cls(url=url, api_key=api_key)


@dataclass
class Neo4jConfig:
    """Neo4j graph database configuration."""

    uri: str
    user: str
    password: str
    database: Optional[str] = None

    @classmethod
    def from_env(cls) -> Neo4jConfig:
        """Load configuration from environment variables."""
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER")
        password = os.getenv("NEO4J_PASSWORD")
        database = os.getenv("NEO4J_DATABASE")

        if not all([uri, user, password]):
            raise ValueError(
                "Missing Neo4j credentials. Set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD"
            )

        return cls(uri=uri, user=user, password=password, database=database)


@dataclass
class OpenAIConfig:
    """OpenAI/LLM API configuration."""

    api_key: str
    model: str = "gpt-4o-mini"
    base_url: Optional[str] = None
    embedding_model: str = "text-embedding-ada-002"

    @classmethod
    def from_env(cls) -> OpenAIConfig:
        """Load configuration from environment variables."""
        # Support both custom LLM binding and standard OpenAI
        api_key = os.getenv("LLM_BINDING_API_KEY") or os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError(
                "Missing OpenAI/LLM credentials. Set OPENAI_API_KEY or LLM_BINDING_API_KEY"
            )

        model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        base_url = os.getenv("LLM_BINDING_HOST")

        return cls(api_key=api_key, model=model, base_url=base_url)


@dataclass
class GroupingConfig:
    """Configuration for segment grouping algorithm."""

    k_neighbors: int = 8
    neighbor_threshold: float = 0.80
    adjacent_threshold: float = 0.70
    temporal_tau: float = 150.0
    max_group_words: int = 700
    min_group_segments: int = 2
    merge_centroid_threshold: float = 0.85


@dataclass
class PipelineConfig:
    """Configuration for the entire pipeline."""

    # Feature flags
    enable_grouping: bool = True
    enable_concepts: bool = True
    enable_relationships: bool = True

    # Processing parameters
    min_relationship_confidence: float = 0.6
    concept_delay_seconds: float = 0.5
    punctuation_model: str = "oliverguhr/fullstop-punctuation-multilingual-base"

    # Output paths
    output_dir: Path = field(default_factory=lambda: Path("output"))
    transcripts_dir: Path = field(default_factory=lambda: Path("output/transcripts"))
    groups_dir: Path = field(default_factory=lambda: Path("output/groups"))
    relationships_dir: Path = field(
        default_factory=lambda: Path("output/relationships")
    )

    def __post_init__(self):
        """Ensure all directories are Path objects."""
        self.output_dir = Path(self.output_dir)
        self.transcripts_dir = Path(self.transcripts_dir)
        self.groups_dir = Path(self.groups_dir)
        self.relationships_dir = Path(self.relationships_dir)


@dataclass
class AppConfig:
    """Main application configuration combining all sub-configs."""

    weaviate: WeaviateConfig
    neo4j: Neo4jConfig
    openai: OpenAIConfig
    grouping: GroupingConfig
    pipeline: PipelineConfig

    @classmethod
    def from_env(cls) -> AppConfig:
        """Load complete configuration from environment variables."""
        return cls(
            weaviate=WeaviateConfig.from_env(),
            neo4j=Neo4jConfig.from_env(),
            openai=OpenAIConfig.from_env(),
            grouping=GroupingConfig(),
            pipeline=PipelineConfig(),
        )

    def with_overrides(
        self,
        grouping_params: Optional[dict] = None,
        pipeline_params: Optional[dict] = None,
    ) -> AppConfig:
        """Create a new config with parameter overrides."""
        new_grouping = GroupingConfig(
            **{**self.grouping.__dict__, **(grouping_params or {})}
        )
        new_pipeline = PipelineConfig(
            **{**self.pipeline.__dict__, **(pipeline_params or {})}
        )

        return AppConfig(
            weaviate=self.weaviate,
            neo4j=self.neo4j,
            openai=self.openai,
            grouping=new_grouping,
            pipeline=new_pipeline,
        )
