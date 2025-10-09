"""Semantic segment grouping with temporal continuity.

Groups transcript segments into coherent topic clusters using:
- k-NN similarity from Weaviate vector search
- Temporal decay penalty for time-distant segments
- Boundary detection based on local cohesion dips
- Greedy growth with word count and similarity guardrails
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from dotenv import load_dotenv
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.query import MetadataQuery

load_dotenv()


@dataclass
class Neighbor:
    """A neighboring segment with similarity and temporal info."""
    
    segment_id: str
    index: int
    similarity: float
    start_time: float
    end_time: float
    text: str
    embedding: Optional[List[float]] = None
    
    def effective_similarity(self, ref_time: float, tau: float = 150.0) -> float:
        """Calculate time-penalized similarity.
        
        Args:
            ref_time: Reference timestamp in seconds
            tau: Temporal decay constant (higher = slower decay)
            
        Returns:
            Effective similarity with temporal penalty applied
        """
        time_diff = abs(self.start_time - ref_time)
        temporal_penalty = math.exp(-time_diff / tau)
        return self.similarity * temporal_penalty


@dataclass
class SegmentNode:
    """A transcript segment with neighborhood information."""
    
    id: str
    video_id: str
    index: int  # Position in video timeline
    text: str
    start_time: float
    end_time: float
    word_count: int
    embedding: Optional[List[float]] = None
    neighbors: List[Neighbor] = field(default_factory=list)
    group_id: Optional[int] = None
    
    @property
    def duration(self) -> float:
        """Duration in seconds."""
        return self.end_time - self.start_time


@dataclass
class SegmentGroup:
    """A coherent group of segments forming a topic cluster."""
    
    group_id: int
    segments: List[SegmentNode]
    video_id: str
    
    @property
    def start_time(self) -> float:
        """Earliest start time in the group."""
        return min(s.start_time for s in self.segments)
    
    @property
    def end_time(self) -> float:
        """Latest end time in the group."""
        return max(s.end_time for s in self.segments)
    
    @property
    def total_words(self) -> int:
        """Total word count across all segments."""
        return sum(s.word_count for s in self.segments)
    
    @property
    def text(self) -> str:
        """Concatenated text of all segments."""
        return " ".join(s.text for s in self.segments)
    
    def centroid_embedding(self) -> np.ndarray:
        """Average embedding vector of all segments."""
        embeddings = [s.embedding for s in self.segments if s.embedding]
        if not embeddings:
            return np.array([])
        return np.mean(embeddings, axis=0)
    
    def avg_internal_similarity(self) -> float:
        """Average pairwise cosine similarity within the group."""
        if len(self.segments) < 2:
            return 1.0
        
        embeddings = [s.embedding for s in self.segments if s.embedding]
        if len(embeddings) < 2:
            return 1.0
        
        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = cosine_similarity(embeddings[i], embeddings[j])
                similarities.append(sim)
        
        return float(np.mean(similarities))


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(np.dot(v1, v2) / (norm1 * norm2))


class SegmentGrouper:
    """Groups transcript segments using semantic similarity and temporal continuity."""
    
    def __init__(
        self,
        weaviate_url: Optional[str] = None,
        weaviate_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        collection_name: str = "Segment",
        # Hyperparameters
        k_neighbors: int = 8,
        neighbor_threshold: float = 0.75,
        adjacent_threshold: float = 0.60,
        temporal_tau: float = 150.0,
        max_group_words: int = 800,
        min_group_segments: int = 2,
        merge_centroid_threshold: float = 0.80,
    ):
        """Initialize the segment grouper.
        
        Args:
            weaviate_url: Weaviate cluster URL
            weaviate_api_key: Weaviate API key
            openai_api_key: OpenAI API key for embeddings
            collection_name: Name of the segment collection
            k_neighbors: Number of nearest neighbors to fetch per segment
            neighbor_threshold: Minimum similarity to keep a neighbor
            adjacent_threshold: Minimum similarity to join adjacent segments
            temporal_tau: Temporal decay constant in seconds
            max_group_words: Maximum words per group
            min_group_segments: Minimum segments per group
            merge_centroid_threshold: Similarity threshold for post-merge
        """
        self.collection_name = collection_name
        self.k = k_neighbors
        self.neighbor_threshold = neighbor_threshold
        self.adjacent_threshold = adjacent_threshold
        self.tau = temporal_tau
        self.max_group_words = max_group_words
        self.min_group_segments = min_group_segments
        self.merge_centroid_threshold = merge_centroid_threshold
        
        # Get credentials
        weaviate_url = weaviate_url or os.getenv("WEAVIATE_URL")
        weaviate_api_key = weaviate_api_key or os.getenv("WEAVIATE_API_KEY")
        openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        
        if not weaviate_url or not weaviate_api_key:
            raise ValueError("Weaviate credentials required")
        
        # Connect to Weaviate
        self.client = weaviate.connect_to_weaviate_cloud(
            cluster_url=weaviate_url,
            auth_credentials=Auth.api_key(weaviate_api_key),
            headers={"X-OpenAI-Api-Key": openai_api_key} if openai_api_key else None
        )
        
        print(f"✓ Connected to Weaviate: {weaviate_url}")
    
    def fetch_segments_for_video(self, video_id: str) -> List[SegmentNode]:
        """Fetch all segments for a video, ordered by start time.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            List of SegmentNode objects sorted by start time
        """
        collection = self.client.collections.get(self.collection_name)
        
        print(f"📥 Fetching segments for video: {video_id}")
        
        # Query all segments for this video
        response = collection.query.fetch_objects(
            filters=weaviate.classes.query.Filter.by_property("videoId").equal(video_id),
            include_vector=True,
            limit=10000  # Adjust if you have videos with more segments
        )
        
        segments = []
        for i, obj in enumerate(response.objects):
            props = obj.properties
            segments.append(SegmentNode(
                id=str(obj.uuid),
                video_id=props.get("videoId", ""),
                index=i,  # Will be reordered
                text=props.get("text", ""),
                start_time=props.get("start_s", 0.0),
                end_time=props.get("end_s", 0.0),
                word_count=props.get("tokens", len(props.get("text", "").split())),
                embedding=obj.vector.get("default") if obj.vector else None,
            ))
        
        # Sort by start time and reassign indices
        segments.sort(key=lambda s: s.start_time)
        for i, seg in enumerate(segments):
            seg.index = i
        
        print(f"✓ Fetched {len(segments)} segments")
        return segments
    
    def build_neighborhoods(self, segments: List[SegmentNode]) -> None:
        """Build k-NN neighborhoods for each segment using Weaviate.
        
        Mutates segments in-place to populate .neighbors field.
        
        Args:
            segments: List of segments to build neighborhoods for
        """
        collection = self.client.collections.get(self.collection_name)
        
        print(f"🔍 Building k-NN neighborhoods (k={self.k})...")
        
        for segment in segments:
            if not segment.embedding:
                continue
            
            # Query for nearest neighbors
            response = collection.query.near_vector(
                near_vector=segment.embedding,
                limit=self.k + 1,  # +1 because query will include self
                include_vector=True,
                return_metadata=MetadataQuery(distance=True),
                filters=weaviate.classes.query.Filter.by_property("videoId").equal(segment.video_id)
            )
            
            neighbors = []
            for obj in response.objects:
                neighbor_id = str(obj.uuid)
                
                # Skip self
                if neighbor_id == segment.id:
                    continue
                
                # Convert distance to similarity (Weaviate returns cosine distance)
                distance = obj.metadata.distance if obj.metadata.distance else 0.0
                similarity = 1.0 - distance
                
                # Filter by threshold
                if similarity < self.neighbor_threshold:
                    continue
                
                props = obj.properties
                
                # Find the index of this neighbor in our segments list
                neighbor_index = next(
                    (i for i, s in enumerate(segments) if s.id == neighbor_id),
                    -1
                )
                
                neighbors.append(Neighbor(
                    segment_id=neighbor_id,
                    index=neighbor_index,
                    similarity=similarity,
                    start_time=props.get("start_s", 0.0),
                    end_time=props.get("end_s", 0.0),
                    text=props.get("text", ""),
                    embedding=obj.vector.get("default") if obj.vector else None,
                ))
            
            segment.neighbors = neighbors
        
        avg_neighbors = np.mean([len(s.neighbors) for s in segments])
        print(f"✓ Built neighborhoods (avg {avg_neighbors:.1f} neighbors per segment)")
    
    def compute_local_cohesion(
        self, segments: List[SegmentNode], index: int, window: int = 3
    ) -> float:
        """Compute local cohesion around a segment.
        
        Args:
            segments: List of all segments
            index: Index of segment to compute cohesion for
            window: Number of segments to look ahead/behind
            
        Returns:
            Maximum effective similarity to neighbors within window
        """
        if index >= len(segments):
            return 0.0
        
        segment = segments[index]
        ref_time = segment.start_time
        
        max_sim = 0.0
        
        # Look at neighbors within the temporal window
        for neighbor in segment.neighbors:
            # Check if neighbor is within the window
            time_diff = abs(neighbor.start_time - ref_time)
            if time_diff <= window * 30:  # Assume ~30s per segment on average
                eff_sim = neighbor.effective_similarity(ref_time, self.tau)
                max_sim = max(max_sim, eff_sim)
        
        return max_sim
    
    def detect_boundaries(self, segments: List[SegmentNode]) -> List[int]:
        """Detect topic boundaries based on cohesion dips.
        
        Args:
            segments: List of segments in temporal order
            
        Returns:
            List of indices where boundaries should be placed
        """
        print("🔪 Detecting topic boundaries...")
        
        boundaries = [0]  # Always start with first segment
        current_word_count = 0
        
        for i in range(len(segments) - 1):
            current_word_count += segments[i].word_count
            
            # Compute cohesion between current and next segment
            cohesion = 0.0
            if segments[i].neighbors:
                # Find next segment in neighbors
                next_segment = segments[i + 1]
                for neighbor in segments[i].neighbors:
                    if neighbor.segment_id == next_segment.id:
                        cohesion = neighbor.effective_similarity(
                            segments[i].start_time, self.tau
                        )
                        break
            
            # Boundary conditions
            should_split = (
                cohesion < self.adjacent_threshold or
                current_word_count >= self.max_group_words
            )
            
            if should_split:
                boundaries.append(i + 1)
                current_word_count = 0
        
        print(f"✓ Detected {len(boundaries)} boundaries")
        return boundaries
    
    def form_groups(self, segments: List[SegmentNode]) -> List[SegmentGroup]:
        """Form segment groups using greedy growth with guardrails.
        
        Args:
            segments: List of segments with populated neighborhoods
            
        Returns:
            List of SegmentGroup objects
        """
        print("🔨 Forming segment groups...")
        
        boundaries = self.detect_boundaries(segments)
        groups = []
        
        for group_idx in range(len(boundaries)):
            start_idx = boundaries[group_idx]
            end_idx = boundaries[group_idx + 1] if group_idx + 1 < len(boundaries) else len(segments)
            
            group_segments = segments[start_idx:end_idx]
            
            # Skip if too small
            if len(group_segments) < self.min_group_segments and group_idx < len(boundaries) - 1:
                # Try to merge with previous group if possible
                if groups and groups[-1].total_words + sum(s.word_count for s in group_segments) <= self.max_group_words * 1.2:
                    groups[-1].segments.extend(group_segments)
                    for seg in group_segments:
                        seg.group_id = groups[-1].group_id
                    continue
            
            # Create the group
            group = SegmentGroup(
                group_id=len(groups),
                segments=group_segments,
                video_id=segments[0].video_id,
            )
            
            # Assign group IDs to segments
            for seg in group_segments:
                seg.group_id = group.group_id
            
            groups.append(group)
        
        print(f"✓ Formed {len(groups)} initial groups")
        return groups
    
    def post_merge_groups(self, groups: List[SegmentGroup]) -> List[SegmentGroup]:
        """Merge adjacent groups with high centroid similarity.
        
        Args:
            groups: List of groups to potentially merge
            
        Returns:
            Updated list of groups after merging
        """
        print("🔗 Post-merging adjacent groups...")
        
        merged = []
        i = 0
        
        while i < len(groups):
            current = groups[i]
            
            # Try to merge with next group
            if i + 1 < len(groups):
                next_group = groups[i + 1]
                
                # Check if they can be merged
                combined_words = current.total_words + next_group.total_words
                
                if combined_words <= self.max_group_words * 1.25:
                    # Compute centroid similarity
                    centroid_sim = cosine_similarity(
                        current.centroid_embedding().tolist(),
                        next_group.centroid_embedding().tolist()
                    )
                    
                    if centroid_sim >= self.merge_centroid_threshold:
                        # Merge the groups
                        current.segments.extend(next_group.segments)
                        for seg in next_group.segments:
                            seg.group_id = current.group_id
                        
                        i += 1  # Skip the next group since we merged it
            
            merged.append(current)
            i += 1
        
        # Renumber groups
        for idx, group in enumerate(merged):
            group.group_id = idx
            for seg in group.segments:
                seg.group_id = idx
        
        print(f"✓ After merging: {len(merged)} groups")
        return merged
    
    def group_video(self, video_id: str) -> List[SegmentGroup]:
        """Complete grouping pipeline for a video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            List of SegmentGroup objects
        """
        print(f"\n{'='*60}")
        print(f"Grouping segments for video: {video_id}")
        print(f"{'='*60}\n")
        
        # Step 1: Fetch segments
        segments = self.fetch_segments_for_video(video_id)
        
        if not segments:
            print("⚠️  No segments found for this video")
            return []
        
        # Step 2: Build neighborhoods
        self.build_neighborhoods(segments)
        
        # Step 3: Form groups
        groups = self.form_groups(segments)
        
        # Step 4: Post-merge
        groups = self.post_merge_groups(groups)
        
        # Step 5: Report statistics
        self._report_stats(groups)
        
        return groups
    
    def _report_stats(self, groups: List[SegmentGroup]) -> None:
        """Print statistics about the groups."""
        print(f"\n{'='*60}")
        print("📊 GROUPING STATISTICS")
        print(f"{'='*60}")
        
        total_segments = sum(len(g.segments) for g in groups)
        word_counts = [g.total_words for g in groups]
        cohesions = [g.avg_internal_similarity() for g in groups]
        
        print(f"Total groups: {len(groups)}")
        print(f"Total segments: {total_segments}")
        print(f"Avg segments per group: {total_segments / len(groups):.1f}")
        print(f"\nWord counts:")
        print(f"  Min: {min(word_counts)}")
        print(f"  Max: {max(word_counts)}")
        print(f"  Mean: {np.mean(word_counts):.0f}")
        print(f"  Median: {np.median(word_counts):.0f}")
        print(f"\nInternal cohesion:")
        print(f"  Min: {min(cohesions):.3f}")
        print(f"  Max: {max(cohesions):.3f}")
        print(f"  Mean: {np.mean(cohesions):.3f}")
        print(f"{'='*60}\n")
    
    def export_groups_to_json(
        self, groups: List[SegmentGroup], output_path: Path
    ) -> None:
        """Export groups to JSON file.
        
        Args:
            groups: List of groups to export
            output_path: Path to output JSON file
        """
        import json
        
        output = {
            "video_id": groups[0].video_id if groups else "",
            "num_groups": len(groups),
            "groups": [
                {
                    "group_id": g.group_id,
                    "start_time": g.start_time,
                    "end_time": g.end_time,
                    "duration": g.end_time - g.start_time,
                    "num_segments": len(g.segments),
                    "total_words": g.total_words,
                    "text": g.text,
                    "avg_cohesion": g.avg_internal_similarity(),
                    "segments": [
                        {
                            "id": s.id,
                            "index": s.index,
                            "start_time": s.start_time,
                            "end_time": s.end_time,
                            "text": s.text,
                            "word_count": s.word_count,
                        }
                        for s in g.segments
                    ],
                }
                for g in groups
            ],
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Exported groups to: {output_path}")
    
    def close(self):
        """Close Weaviate connection."""
        self.client.close()
        print("✓ Closed Weaviate connection")


def main():
    """Example usage."""
    grouper = SegmentGrouper()
    
    try:
        # Process one of your existing videos
        video_id = "HbDqLPm_2vY"  # Adjust to your video ID
        groups = grouper.group_video(video_id)
        
        # Export results
        output_path = Path(f"Groups/groups_{video_id}.json")
        grouper.export_groups_to_json(groups, output_path)
        
        # Print sample groups
        print("\n📝 Sample groups:")
        for i, group in enumerate(groups[:3]):
            print(f"\n--- Group {i} ---")
            print(f"Time: {group.start_time:.1f}s - {group.end_time:.1f}s")
            print(f"Words: {group.total_words}")
            print(f"Segments: {len(group.segments)}")
            print(f"Text preview: {group.text[:200]}...")
        
    finally:
        grouper.close()


if __name__ == "__main__":
    main()
