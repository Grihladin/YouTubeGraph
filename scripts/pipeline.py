"""Simplified YouTubeGraph Pipeline using service-oriented architecture.

This is the new, clean pipeline that orchestrates all services.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from openai import OpenAI

from src.config import AppConfig
from src.domain.transcript import TranscriptJob
from src.infrastructure.weaviate_client import WeaviateClient
from src.infrastructure.neo4j_client import Neo4jClient
from src.services.transcripts import TranscriptService
from src.services.vectorstore import SegmentRepository, VectorStoreService
from src.services.grouping import GroupingService
from src.services.concepts import ConceptService, ConceptExtractor, ConceptRepository
from src.services.relationships import RelationshipService, RelationshipRepository
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PipelineResult:
    """Result from pipeline execution."""

    video_id: str
    segment_count: int
    group_count: int = 0
    concept_count: int = 0
    relationship_count: int = 0
    success: bool = True
    error: Optional[str] = None


class YouTubeGraphPipeline:
    """Simplified pipeline orchestrating all services."""

    def __init__(self, config: Optional[AppConfig] = None):
        """Initialize the pipeline with all services.

        Args:
            config: Application configuration (loads from env if not provided)
        """
        self.config = config or AppConfig.from_env()

        logger.info("Initializing YouTubeGraph Pipeline...")

        # Initialize infrastructure clients
        self.weaviate_client = WeaviateClient(self.config.weaviate)
        self.neo4j_client = Neo4jClient(self.config.neo4j)

        # Initialize services
        self._init_services()

        logger.info("Pipeline initialized successfully")

    def _init_services(self):
        """Initialize all service components."""
        # Transcript service
        self.transcript_service = TranscriptService(
            punctuation_model=self.config.pipeline.punctuation_model
        )

        # Vector store service
        # IMPORTANT: Weaviate needs the actual OpenAI key, not LLM_BINDING key
        import os
        weaviate_openai_key = os.getenv("OPENAI_API_KEY")  # Get OpenAI key directly, not LLM_BINDING
        self.weaviate_client.connect(openai_api_key=weaviate_openai_key)
        segment_repository = SegmentRepository(
            self.weaviate_client, self.config.weaviate.collection_name
        )
        self.vector_store_service = VectorStoreService(segment_repository)

        # Grouping service (only if enabled)
        if self.config.pipeline.enable_grouping:
            self.grouping_service = GroupingService(
                segment_repository, self.config.grouping
            )
        else:
            self.grouping_service = None

        # Concept service (only if enabled)
        if self.config.pipeline.enable_concepts:
            self.neo4j_client.connect()
            openai_client = OpenAI(
                api_key=self.config.openai.api_key,
                base_url=self.config.openai.base_url,
            )
            concept_extractor = ConceptExtractor(
                api_key=self.config.openai.api_key,
                model=self.config.openai.model,
                base_url=self.config.openai.base_url,
            )
            concept_repository = ConceptRepository(self.neo4j_client)
            self.concept_service = ConceptService(
                concept_extractor,
                concept_repository,
                delay_seconds=self.config.pipeline.concept_delay_seconds,
            )
        else:
            self.concept_service = None

        # Relationship service (only if enabled)
        if self.config.pipeline.enable_relationships:
            if not self.neo4j_client.graph:
                self.neo4j_client.connect()

            openai_client = OpenAI(
                api_key=self.config.openai.api_key,
                base_url=self.config.openai.base_url,
            )
            relationship_repository = RelationshipRepository(self.neo4j_client)
            self.relationship_service = RelationshipService(
                openai_client,
                self.neo4j_client,
                relationship_repository,
                min_confidence=self.config.pipeline.min_relationship_confidence,
            )
        else:
            self.relationship_service = None

    def process_video(
        self,
        youtube_url: str,
        languages: Optional[List[str]] = None,
        save_outputs: bool = True,
        skip_existing_concepts: bool = False,
        overwrite_relationships: bool = False,
    ) -> PipelineResult:
        """Process a YouTube video end-to-end.

        Args:
            youtube_url: YouTube video URL
            languages: List of language codes to try (defaults to ['en'])
            save_outputs: Whether to save groups and relationships to files
            skip_existing_concepts: Skip concept extraction if already exists
            overwrite_relationships: Overwrite existing relationships

        Returns:
            PipelineResult with statistics
        """
        logger.info("=" * 60)
        logger.info(f"Processing video: {youtube_url}")
        logger.info("=" * 60)

        try:
            # Step 1: Fetch and process transcript
            logger.info("\n📥 Step 1: Fetching and processing transcript")
            job = TranscriptJob(
                youtube_url=youtube_url,
                languages=languages,
                output_dir=self.config.pipeline.transcripts_dir,
            )
            transcript_result = self.transcript_service.process_video(job)
            video_id = transcript_result.video_id
            logger.info(
                f"✓ Processed {len(transcript_result.segments)} segments for {video_id}"
            )

            # Step 2: Upload to vector store
            logger.info("\n📤 Step 2: Uploading to vector store")
            segment_count = self.vector_store_service.store_transcript(
                transcript_result
            )
            logger.info(f"✓ Stored {segment_count} segments in Weaviate")

            result = PipelineResult(video_id=video_id, segment_count=segment_count)

            # Step 3: Group segments (if enabled)
            if self.grouping_service:
                logger.info("\n🔗 Step 3: Grouping segments semantically")
                groups = self.grouping_service.group_video(video_id)
                result.group_count = len(groups)
                logger.info(f"✓ Created {len(groups)} groups")

                # Save groups to file
                if save_outputs and groups:
                    output_path = (
                        self.config.pipeline.groups_dir / f"groups_{video_id}.json"
                    )
                    self.grouping_service.export_to_json(groups, output_path)

                # Step 4: Extract concepts (if enabled)
                if self.concept_service:
                    logger.info("\n🧠 Step 4: Extracting concepts from groups")
                    extracted_concepts = self.concept_service.process_groups(
                        groups, skip_existing=skip_existing_concepts
                    )
                    result.concept_count = sum(
                        len(ec.concepts) for ec in extracted_concepts
                    )
                    logger.info(f"✓ Extracted {result.concept_count} concepts")

                    # Step 5: Extract relationships (if enabled)
                    if self.relationship_service and extracted_concepts:
                        logger.info("\n🔗 Step 5: Extracting relationships")
                        relationships = self.relationship_service.extract_from_video(
                            extracted_concepts,
                            video_id,
                            overwrite=overwrite_relationships,
                        )
                        result.relationship_count = len(relationships)
                        logger.info(
                            f"✓ Extracted {result.relationship_count} relationships"
                        )

                        # Save relationships to file
                        if save_outputs:
                            output_path = (
                                self.config.pipeline.relationships_dir
                                / f"relationships_{video_id}.json"
                            )
                            self.relationship_service.save_to_file(
                                relationships, output_path
                            )

            # Success summary
            logger.info("\n" + "=" * 60)
            logger.info("✅ Pipeline completed successfully!")
            logger.info("=" * 60)
            logger.info(f"Video ID: {result.video_id}")
            logger.info(f"Segments: {result.segment_count}")
            if result.group_count:
                logger.info(f"Groups: {result.group_count}")
            if result.concept_count:
                logger.info(f"Concepts: {result.concept_count}")
            if result.relationship_count:
                logger.info(f"Relationships: {result.relationship_count}")
            logger.info("=" * 60)

            return result

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            return PipelineResult(
                video_id="unknown",
                segment_count=0,
                success=False,
                error=str(e),
            )

    def process_multiple_videos(
        self, youtube_urls: List[str], **kwargs
    ) -> dict[str, PipelineResult]:
        """Process multiple YouTube videos.

        Args:
            youtube_urls: List of YouTube video URLs
            **kwargs: Additional arguments passed to process_video

        Returns:
            Dictionary mapping URLs to PipelineResult objects
        """
        logger.info(f"\n🎬 Processing {len(youtube_urls)} videos")

        results = {}
        for i, url in enumerate(youtube_urls, 1):
            logger.info(f"\nVideo {i}/{len(youtube_urls)}: {url}")
            result = self.process_video(url, **kwargs)
            results[url] = result

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 BATCH PROCESSING SUMMARY")
        logger.info("=" * 60)

        success_count = sum(1 for r in results.values() if r.success)
        total_segments = sum(r.segment_count for r in results.values())
        total_groups = sum(r.group_count for r in results.values())
        total_concepts = sum(r.concept_count for r in results.values())
        total_relationships = sum(r.relationship_count for r in results.values())

        logger.info(f"Success: {success_count}/{len(youtube_urls)} videos")
        logger.info(f"Total segments: {total_segments}")
        if total_groups:
            logger.info(f"Total groups: {total_groups}")
        if total_concepts:
            logger.info(f"Total concepts: {total_concepts}")
        if total_relationships:
            logger.info(f"Total relationships: {total_relationships}")
        logger.info("=" * 60)

        return results

    def close(self):
        """Clean up all resources."""
        logger.info("Closing pipeline connections...")

        if self.weaviate_client:
            self.weaviate_client.close()

        if self.neo4j_client:
            self.neo4j_client.close()

        logger.info("Pipeline closed successfully")


def main():
    """Example usage of the new pipeline."""
    # Initialize pipeline with default config
    pipeline = YouTubeGraphPipeline()

    try:
        # Process a single video
        result = pipeline.process_video("https://www.youtube.com/watch?v=1Hp5Z2QDsKw")

        if result.success:
            print(f"\n✅ Successfully processed video {result.video_id}")
        else:
            print(f"\n❌ Failed: {result.error}")

    finally:
        pipeline.close()


if __name__ == "__main__":
    main()
