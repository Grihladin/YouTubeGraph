"""YouTubeGraph Pipeline - Full video processing into Weaviate + Neo4j."""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from openai import OpenAI

from src.core.concept_extractor import ConceptExtractor, ExtractionError
from src.core.concept_models import Concept, ExtractedConcepts
from src.core.concept_uploader import ConceptUploader
from src.core.neo4j_graph import Neo4jGraph
from src.core.punctuation_worker import PunctuationWorker, TranscriptJob
from src.core.relationship_extractor import RelationshipExtractor
from src.core.relationship_models import ExtractedRelationships
from src.core.relationship_uploader import RelationshipUploader
from src.core.segment_grouper import SegmentGrouper, SegmentGroup
from src.core.weaviate_uploader import WeaviateUploader

# Load environment variables
load_dotenv()


@dataclass
class ConceptExtractionStats:
    video_id: str
    groups_processed: int = 0
    groups_failed: int = 0
    concepts_extracted: int = 0
    concepts_uploaded: int = 0
    concepts_failed: int = 0
    avg_importance: float = 0.0
    avg_confidence: float = 0.0
    extraction_time: float = 0.0


@dataclass
class RelationshipExtractionStats:
    video_id: str
    relationships_detected: int = 0
    uploaded: int = 0
    skipped: int = 0
    failed: int = 0
    avg_confidence: float = 0.0
    type_distribution: dict[str, int] = field(default_factory=dict)


class YouTubeGraphPipeline:
    """End-to-end pipeline: YouTube URL → Transcript → Weaviate → Groups → Neo4j graph."""

    def __init__(
        self,
        weaviate_url: Optional[str] = None,
        weaviate_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        punctuation_model: Optional[str] = None,
        collection_name: str = "Segment",
        enable_grouping: bool = True,
        grouping_params: Optional[dict] = None,
        enable_concepts: bool = True,
        enable_relationships: bool = True,
        min_relationship_confidence: float = 0.6,
        concept_delay_seconds: float = 0.5,
    ):
        """Initialize the pipeline.

        Args:
            weaviate_url: Weaviate cluster URL (defaults to WEAVIATE_URL env var)
            weaviate_api_key: Weaviate API key (defaults to WEAVIATE_API_KEY env var)
            openai_api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            punctuation_model: Punctuation model name (defaults to fast multilingual model)
            collection_name: Weaviate collection name
            enable_grouping: Whether to automatically group segments after upload
            grouping_params: Optional dict of hyperparameters for SegmentGrouper
        """
        # Get credentials from env vars if not provided
        self.weaviate_url = weaviate_url or os.getenv("WEAVIATE_URL")
        self.weaviate_api_key = weaviate_api_key or os.getenv("WEAVIATE_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

        if not self.weaviate_url or not self.weaviate_api_key:
            raise ValueError(
                "Weaviate credentials must be provided or set in environment variables"
            )

        # Initialize the punctuation worker
        print("🔄 Loading punctuation model...")
        self.punctuation_worker = PunctuationWorker(
            model_name=punctuation_model
            or "oliverguhr/fullstop-punctuation-multilingual-base"
        )
        print("✓ Punctuation model loaded!")

        # Store collection name for uploader and feature flags
        self.collection_name = collection_name
        self.enable_grouping = enable_grouping
        self.enable_concepts = enable_concepts
        self.enable_relationships = enable_relationships
        self.concept_delay_seconds = concept_delay_seconds

        self.uploader = WeaviateUploader(
            cluster_url=self.weaviate_url,
            api_key=self.weaviate_api_key,
            openai_api_key=self.openai_api_key,
            collection_name=self.collection_name,
        )

        # Initialize grouper if enabled
        self.grouper = None
        if self.enable_grouping:
            # Use tuned parameters by default for better quality
            tuned_defaults = {
                "k_neighbors": 8,
                "neighbor_threshold": 0.80,  # Stricter neighbor selection
                "adjacent_threshold": 0.70,  # Stricter joining threshold
                "temporal_tau": 150.0,
                "max_group_words": 700,  # Smaller, more focused groups
                "min_group_segments": 2,
                "merge_centroid_threshold": 0.85,  # Less aggressive merging
            }
            # Override defaults with user-provided params
            final_params = {**tuned_defaults, **(grouping_params or {})}

            self.grouper = SegmentGrouper(
                weaviate_url=self.weaviate_url,
                weaviate_api_key=self.weaviate_api_key,
                openai_api_key=self.openai_api_key,
                collection_name=self.collection_name,
                **final_params,
            )

        # Neo4j + concept extraction components
        self.concept_extractor: Optional[ConceptExtractor] = None
        self.concept_uploader: Optional[ConceptUploader] = None
        self.neo4j_graph: Optional[Neo4jGraph] = None
        self.relationship_extractor: Optional[RelationshipExtractor] = None
        self.relationship_uploader: Optional[RelationshipUploader] = None
        self.relationship_client: Optional[OpenAI] = None

        if self.enable_concepts or self.enable_relationships:
            self._initialize_graph_components(
                enable_concepts=self.enable_concepts,
                enable_relationships=self.enable_relationships,
                min_relationship_confidence=min_relationship_confidence,
            )

        # Output directories
        self.groups_output_dir = Path("output/groups")
        self.relationships_output_dir = Path("output/relationships")

    # ------------------------------------------------------------------
    # Initialization helpers
    # ------------------------------------------------------------------
    def _initialize_graph_components(
        self,
        *,
        enable_concepts: bool,
        enable_relationships: bool,
        min_relationship_confidence: float,
    ) -> None:
        """Set up Neo4j clients, concept extractor, and relationship tools."""

        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_user = os.getenv("NEO4J_USER")
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        neo4j_database = os.getenv("NEO4J_DATABASE")

        if not all([neo4j_uri, neo4j_user, neo4j_password]):
            raise ValueError(
                "Neo4j credentials missing. Set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD in the environment."
            )

        if enable_concepts:
            self.concept_extractor = ConceptExtractor()
            self.concept_uploader = ConceptUploader(
                uri=neo4j_uri,
                user=neo4j_user,
                password=neo4j_password,
                database=neo4j_database,
            )
            self.neo4j_graph = self.concept_uploader.graph
        else:
            self.neo4j_graph = Neo4jGraph(
                uri=neo4j_uri,
                user=neo4j_user,
                password=neo4j_password,
                database=neo4j_database,
            )

        if enable_relationships:
            if not self.openai_api_key:
                raise ValueError(
                    "OPENAI_API_KEY (or compatible LLM binding) required for relationship extraction"
                )
            self.relationship_client = OpenAI(api_key=self.openai_api_key)
            self.relationship_extractor = RelationshipExtractor(
                openai_client=self.relationship_client,
                graph=self.neo4j_graph,
                min_confidence=min_relationship_confidence,
            )
            self.relationship_uploader = RelationshipUploader(self.neo4j_graph)

    # ------------------------------------------------------------------
    # Core processing steps
    # ------------------------------------------------------------------

    def process_video(
        self,
        youtube_url: str,
        languages: Optional[list[str]] = None,
        output_groups: bool = True,
        skip_concept_extraction_if_exists: bool = False,
        overwrite_relationships: bool = False,
        save_relationships: bool = True,
    ) -> dict:
        """Process a YouTube video end-to-end and populate Neo4j.

        Args:
            youtube_url: YouTube video URL
            languages: List of language codes to try (defaults to ['en'])
            output_groups: Whether to save groups to output/groups/ directory

        Returns:
            Dictionary with:
                - segment_count: Number of segments uploaded
                - video_id: Video ID
                - groups: List of SegmentGroup objects (if grouping enabled)
                - group_count: Number of groups created (if grouping enabled)

        Steps:
            1. Fetch transcript from YouTube
            2. Restore punctuation and proper casing
            3. Chunk into semantic segments (3-6 sentences, 600-1600 chars)
            4. Upload to Weaviate with timestamps
            5. Group segments semantically (if enabled)
        """
        print(f"\n{'='*60}")
        print(f"Processing: {youtube_url}")
        print(f"{'='*60}\n")

        # Step 1 & 2 & 3: Fetch, punctuate, and chunk transcript
        print("📥 Step 1-3: Fetching transcript and processing...")
        job = TranscriptJob(
            youtube_url=youtube_url,
            languages=languages,
            output_dir=Path("output/transcripts"),  # Save to output/transcripts/
        )

        try:
            transcript_result = self.punctuation_worker(job)
            transcript_path = transcript_result.output_path
            if transcript_path:
                print(f"✓ Processed transcript saved to: {transcript_path}")
            print(f"✓ Generated {len(transcript_result.segments)} structured segments")
        except Exception as e:
            print(f"❌ Error processing transcript: {e}")
            raise

        # Step 4: Upload to Weaviate
        print("\n📤 Step 4: Uploading to Weaviate...")
        segment_count = self.uploader.upload_segments(transcript_result.segments)
        print(f"✓ Uploaded {segment_count} segments to Weaviate")

        video_id = transcript_result.video_id

        result = {
            "segment_count": segment_count,
            "video_id": video_id,
        }

        # Step 5: Group segments (if enabled)
        if self.enable_grouping and self.grouper:
            print("\n🔗 Step 5: Grouping segments semantically...")
            try:
                groups = self.grouper.group_video(video_id)
                result["groups"] = groups
                result["group_count"] = len(groups)

                # Save groups to file if requested
                if output_groups and groups:
                    output_path = Path(f"output/groups/groups_{video_id}.json")
                    self.grouper.export_groups_to_json(groups, output_path)
                    print(f"✓ Saved {len(groups)} groups to {output_path}")

                # Step 6: Concept extraction + upload
                if self.enable_concepts:
                    concept_stats, extracted_concepts = (
                        self._extract_and_upload_concepts(
                            video_id,
                            groups,
                            skip_if_exists=skip_concept_extraction_if_exists,
                        )
                    )
                    result["concept_stats"] = concept_stats.__dict__
                else:
                    extracted_concepts = self._load_concepts_for_relationships(
                        video_id, groups
                    )

                # Step 7: Relationship extraction + upload
                if self.enable_relationships and extracted_concepts:
                    relationship_stats = self._extract_and_upload_relationships(
                        video_id,
                        extracted_concepts,
                        overwrite=overwrite_relationships,
                        save_output=save_relationships,
                    )
                    result["relationship_stats"] = relationship_stats.__dict__

            except Exception as e:
                print(f"⚠️  Grouping failed: {e}")
                result["groups"] = []
                result["group_count"] = 0

        print(f"\n{'='*60}")
        print(f"✅ SUCCESS! Pipeline complete")
        print(f"{'='*60}")
        print(f"Segments uploaded: {segment_count}")
        if "group_count" in result:
            print(f"Groups created: {result['group_count']}")
        if result.get("concept_stats"):
            stats = result["concept_stats"]
            print(
                f"Concepts uploaded: {stats['concepts_uploaded']} (groups processed: {stats['groups_processed']})"
            )
        if result.get("relationship_stats"):
            rel_stats = result["relationship_stats"]
            print(
                f"Relationships uploaded: {rel_stats['uploaded']} (detected: {rel_stats['relationships_detected']})"
            )
        print(f"{'='*60}\n")

        return result

    # ------------------------------------------------------------------
    # Concept extraction helpers
    # ------------------------------------------------------------------
    def _extract_and_upload_concepts(
        self,
        video_id: str,
        groups: Iterable[SegmentGroup],
        *,
        skip_if_exists: bool,
    ) -> tuple[ConceptExtractionStats, list[ExtractedConcepts]]:
        if not self.concept_extractor or not self.concept_uploader:
            raise RuntimeError("Concept components not initialized")

        stats = ConceptExtractionStats(video_id=video_id)
        extracted_payload: list[ExtractedConcepts] = []
        importance_scores: list[float] = []
        confidence_scores: list[float] = []

        if skip_if_exists:
            existing = self.concept_uploader.get_concepts_for_video(video_id)
            if existing:
                print(
                    f"⚠️  {len(existing)} concepts already exist for {video_id}; skipping re-extraction"
                )
                reconstructed = self._convert_existing_concepts(
                    video_id, existing, groups
                )
                stats.groups_processed = len(reconstructed)
                stats.concepts_extracted = sum(
                    len(item.concepts) for item in reconstructed
                )
                if stats.concepts_extracted:
                    importance_scores.extend(
                        concept.importance
                        for item in reconstructed
                        for concept in item.concepts
                    )
                    confidence_scores.extend(
                        concept.confidence
                        for item in reconstructed
                        for concept in item.concepts
                    )
                    stats.avg_importance = sum(importance_scores) / len(
                        importance_scores
                    )
                    stats.avg_confidence = sum(confidence_scores) / len(
                        confidence_scores
                    )
                return stats, reconstructed

        start_time = time.time()

        for group in groups or []:
            group_id = group.group_id
            group_text = group.text
            if not group_text.strip():
                print(f"  ⚠️  Group {group_id}: No text, skipping concept extraction")
                stats.groups_failed += 1
                continue

            print(
                f"🧠 Extracting concepts for group {group_id} (video {video_id})...",
                end=" ",
            )
            try:
                extracted = self.concept_extractor.extract_from_group(
                    video_id=video_id,
                    group_id=group_id,
                    group_text=group_text,
                    start_time=group.start_time,
                    end_time=group.end_time,
                )

                is_valid, issues = extracted.validate()
                if not is_valid:
                    print("\n    ⚠️  Validation warnings:")
                    for issue in issues:
                        print(f"       - {issue}")

                upload_stats = self.concept_uploader.upload_extracted_concepts(
                    extracted
                )

                extracted_payload.append(extracted)
                stats.groups_processed += 1
                stats.concepts_extracted += len(extracted.concepts)
                stats.concepts_uploaded += upload_stats["concepts_success"]
                stats.concepts_failed += upload_stats["concepts_failed"]

                importance_scores.extend(c.importance for c in extracted.concepts)
                confidence_scores.extend(c.confidence for c in extracted.concepts)

                print(f"✓ {len(extracted.concepts)} concepts")

                time.sleep(self.concept_delay_seconds)

            except ExtractionError as exc:
                print(f"❌ Failed: {exc}")
                stats.groups_failed += 1
            except Exception as exc:
                print(f"❌ Unexpected error: {exc}")
                stats.groups_failed += 1

        stats.extraction_time = time.time() - start_time
        if importance_scores:
            stats.avg_importance = sum(importance_scores) / len(importance_scores)
        if confidence_scores:
            stats.avg_confidence = sum(confidence_scores) / len(confidence_scores)
        return stats, extracted_payload

    def _convert_existing_concepts(
        self,
        video_id: str,
        records: list[dict],
        groups: Iterable[SegmentGroup],
    ) -> list[ExtractedConcepts]:
        group_map = {g.group_id: g.text for g in groups or []}
        grouped: dict[int, list[Concept]] = {}

        for record in records:
            concept = Concept(
                name=record["name"],
                definition=record.get("definition", ""),
                type=record.get("type", "Concept"),
                importance=float(record.get("importance", 0.5)),
                confidence=float(record.get("confidence", 0.5)),
                video_id=video_id,
                group_id=int(record.get("groupId", 0)),
                first_mention_time=float(record.get("firstMentionTime", 0.0)),
                last_mention_time=float(record.get("lastMentionTime", 0.0)),
                mention_count=int(record.get("mentionCount", 1)),
                aliases=record.get("aliases", []) or [],
                extracted_at=record.get("extractedAt"),
                id=record.get("id"),
            )
            grouped.setdefault(concept.group_id, []).append(concept)

        extracted_payload: list[ExtractedConcepts] = []
        for group_id, concepts in grouped.items():
            group_text = group_map.get(group_id, "")
            extracted_payload.append(
                ExtractedConcepts(
                    video_id=video_id,
                    group_id=group_id,
                    group_text=group_text,
                    concepts=concepts,
                )
            )

        return extracted_payload

    def _load_concepts_for_relationships(
        self,
        video_id: str,
        groups: Iterable[SegmentGroup],
    ) -> list[ExtractedConcepts]:
        if not self.concept_uploader:
            raise RuntimeError("Concept uploader not available")
        records = self.concept_uploader.get_concepts_for_video(video_id)
        if not records:
            print("⚠️  No concepts found in Neo4j; relationships will be skipped")
            return []
        return self._convert_existing_concepts(video_id, records, groups)

    # ------------------------------------------------------------------
    # Relationship extraction helpers
    # ------------------------------------------------------------------
    def _extract_and_upload_relationships(
        self,
        video_id: str,
        extracted_concepts: list[ExtractedConcepts],
        *,
        overwrite: bool,
        save_output: bool,
    ) -> RelationshipExtractionStats:
        if not self.relationship_extractor or not self.relationship_uploader:
            raise RuntimeError("Relationship components not initialized")

        print("\n🔗 Step 6: Extracting relationships...")
        relationships: ExtractedRelationships = (
            self.relationship_extractor.extract_from_video(extracted_concepts, video_id)
        )

        stats = RelationshipExtractionStats(
            video_id=video_id,
            relationships_detected=len(relationships),
            avg_confidence=relationships.avg_confidence,
            type_distribution=relationships.type_distribution,
        )

        if overwrite:
            self.relationship_uploader.delete_relationships_for_video(video_id)

        upload_stats = self.relationship_uploader.upload_relationships(relationships)
        stats.uploaded = upload_stats.get("uploaded", 0)
        stats.skipped = upload_stats.get("skipped", 0)
        stats.failed = upload_stats.get("failed", 0)

        if save_output:
            output_path = (
                self.relationships_output_dir / f"relationships_{video_id}.json"
            )
            self.relationships_output_dir.mkdir(parents=True, exist_ok=True)
            self.relationship_extractor.save_to_file(relationships, output_path)

        return stats

    def process_multiple_videos(self, youtube_urls: list[str]) -> dict[str, dict]:
        """Process multiple YouTube videos.

        Args:
            youtube_urls: List of YouTube video URLs

        Returns:
            Dictionary mapping URLs to result dicts (with segment_count, groups, etc.)
        """
        results = {}

        for i, url in enumerate(youtube_urls, 1):
            print(f"\n🎬 Processing video {i}/{len(youtube_urls)}")
            try:
                result = self.process_video(url)
                results[url] = result
            except Exception as e:
                print(f"❌ Failed to process {url}: {e}")
                results[url] = {"segment_count": 0, "group_count": 0, "error": str(e)}

        # Summary
        print(f"\n{'='*60}")
        print("📊 BATCH PROCESSING SUMMARY")
        print(f"{'='*60}")
        total_segments = 0
        total_groups = 0
        success_count = 0

        for url, result in results.items():
            segment_count = result.get("segment_count", 0)
            group_count = result.get("group_count", 0)

            status = "✓" if segment_count > 0 else "✗"
            print(f"{status} {url}:")
            print(f"   Segments: {segment_count}")
            if "group_count" in result:
                print(f"   Groups: {group_count}")

            total_segments += segment_count
            total_groups += group_count
            if segment_count > 0:
                success_count += 1

        print(f"\nTotal: {success_count}/{len(youtube_urls)} videos processed")
        print(f"Total segments: {total_segments}")
        if self.enable_grouping:
            print(f"Total groups: {total_groups}")
        print(f"{'='*60}\n")

        return results

    def close(self):
        """Clean up resources."""
        self.uploader.close()
        if self.grouper:
            self.grouper.close()
        if self.concept_uploader:
            self.concept_uploader.close()
        elif self.neo4j_graph:
            self.neo4j_graph.close()


# Backwards compatibility with old class name
YouTubeToWeaviatePipeline = YouTubeGraphPipeline


def main():
    """Example usage of the pipeline."""

    # Example 1: Full pipeline with grouping (recommended)
    print("🚀 Initializing full pipeline with grouping...\n")
    pipeline = YouTubeGraphPipeline(
        enable_grouping=True,
        grouping_params={
            "k_neighbors": 8,
            "neighbor_threshold": 0.80,
            "adjacent_threshold": 0.70,
            "temporal_tau": 150.0,
            "max_group_words": 700,
        },
    )

    try:
        # Single video - full processing
        youtube_url = "https://www.youtube.com/watch?v=3T9hNqr-Aic"
        result = pipeline.process_video(youtube_url)

        print(f"\n📊 Results:")
        print(f"   Video ID: {result['video_id']}")
        print(f"   Segments: {result['segment_count']}")
        if "group_count" in result:
            print(f"   Groups: {result['group_count']}")

        # Or process multiple videos:
        # video_urls = [
        #     "https://www.youtube.com/watch?v=VIDEO_ID_1",
        #     "https://www.youtube.com/watch?v=VIDEO_ID_2",
        #     "https://www.youtube.com/watch?v=VIDEO_ID_3",
        # ]
        # results = pipeline.process_multiple_videos(video_urls)

    finally:
        pipeline.close()

    # Example 2: Without grouping (faster, if you only need segments)
    # pipeline = YouTubeToWeaviatePipeline(enable_grouping=False)
    # result = pipeline.process_video(youtube_url)
    # pipeline.close()


if __name__ == "__main__":
    main()
