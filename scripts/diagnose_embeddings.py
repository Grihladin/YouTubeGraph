#!/usr/bin/env python3
"""Diagnose why cohesion is low - inspect embeddings and similarities."""

import os
import sys
from pathlib import Path

# Add src/ to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
from dotenv import load_dotenv
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.query import MetadataQuery

load_dotenv()


def diagnose_video(video_id: str, sample_size: int = 20):
    """Diagnose embedding quality and similarity distribution.
    
    Args:
        video_id: YouTube video ID to diagnose
        sample_size: Number of adjacent pairs to sample
    """
    
    print(f"\n{'='*80}")
    print(f"🔬 DIAGNOSTIC REPORT: {video_id}")
    print(f"{'='*80}\n")
    
    # Connect to Weaviate
    weaviate_url = os.getenv("WEAVIATE_URL")
    weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=weaviate_url,
        auth_credentials=Auth.api_key(weaviate_api_key),
        headers={"X-OpenAI-Api-Key": openai_api_key} if openai_api_key else None
    )
    
    try:
        collection = client.collections.get("Segment")
        
        # Fetch segments
        print("📥 Fetching segments...")
        response = collection.query.fetch_objects(
            filters=weaviate.classes.query.Filter.by_property("videoId").equal(video_id),
            include_vector=True,
            limit=10000
        )
        
        segments = []
        for obj in response.objects:
            props = obj.properties
            segments.append({
                'id': str(obj.uuid),
                'text': props.get("text", ""),
                'start': props.get("start_s", 0.0),
                'end': props.get("end_s", 0.0),
                'words': props.get("tokens", len(props.get("text", "").split())),
                'embedding': obj.vector.get("default") if obj.vector else None,
            })
        
        # Sort by time
        segments.sort(key=lambda s: s['start'])
        
        print(f"✓ Found {len(segments)} segments\n")
        
        # Check embedding availability
        with_embeddings = sum(1 for s in segments if s['embedding'] is not None)
        print(f"📊 Embedding Coverage:")
        print(f"   • Segments with embeddings: {with_embeddings}/{len(segments)} "
              f"({with_embeddings/len(segments)*100:.1f}%)")
        
        if with_embeddings == 0:
            print("\n❌ CRITICAL: No embeddings found!")
            print("This explains the low cohesion - segments can't be compared.")
            print("\nPossible causes:")
            print("  • Vectorizer not configured in Weaviate")
            print("  • OpenAI API key missing or invalid")
            print("  • Segments uploaded without vectorization")
            return
        
        # Sample adjacent segment similarities
        print(f"\n🔍 Adjacent Segment Similarity Analysis:")
        print(f"   Sampling {min(sample_size, len(segments)-1)} consecutive pairs...\n")
        
        similarities = []
        
        for i in range(min(sample_size, len(segments) - 1)):
            if segments[i]['embedding'] and segments[i+1]['embedding']:
                v1 = np.array(segments[i]['embedding'])
                v2 = np.array(segments[i+1]['embedding'])
                
                sim = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                similarities.append(sim)
                
                # Print first 5 in detail
                if i < 5:
                    print(f"   Segment {i} → {i+1}:")
                    print(f"      Similarity: {sim:.3f}")
                    print(f"      Time gap: {segments[i+1]['start'] - segments[i]['end']:.1f}s")
                    print(f"      Text {i}: {segments[i]['text'][:60]}...")
                    print(f"      Text {i+1}: {segments[i+1]['text'][:60]}...")
                    print()
        
        if similarities:
            print(f"\n📈 Similarity Distribution (adjacent pairs):")
            print(f"   • Mean:   {np.mean(similarities):.3f}")
            print(f"   • Median: {np.median(similarities):.3f}")
            print(f"   • Std:    {np.std(similarities):.3f}")
            print(f"   • Min:    {np.min(similarities):.3f}")
            print(f"   • Max:    {np.max(similarities):.3f}")
            
            # Histogram
            print(f"\n   Distribution:")
            bins = [
                (0.0, 0.3, "Very Low"),
                (0.3, 0.5, "Low"),
                (0.5, 0.7, "Medium"),
                (0.7, 0.85, "High"),
                (0.85, 1.0, "Very High"),
            ]
            
            for min_val, max_val, label in bins:
                count = sum(1 for s in similarities if min_val <= s < max_val)
                pct = count / len(similarities) * 100
                bar = "█" * int(pct / 2)
                print(f"   {min_val:.2f}-{max_val:.2f} ({label:9}): {bar} {pct:5.1f}% ({count})")
            
            # Diagnosis
            print(f"\n💡 Diagnosis:")
            mean_sim = np.mean(similarities)
            
            if mean_sim < 0.4:
                print(f"   🔴 Very low similarity (mean={mean_sim:.3f})")
                print(f"      → Segments are semantically very different")
                print(f"      → This is EXPECTED for diverse content")
                print(f"      → Use LOWER thresholds (e.g., adjacent_threshold=0.40-0.50)")
                
            elif mean_sim < 0.6:
                print(f"   🟡 Low-medium similarity (mean={mean_sim:.3f})")
                print(f"      → Moderate topic variation")
                print(f"      → Current adjacent_threshold=0.60 may be too high")
                print(f"      → Try adjacent_threshold=0.50-0.55")
                
            elif mean_sim < 0.75:
                print(f"   🟢 Medium similarity (mean={mean_sim:.3f})")
                print(f"      → Good balance of coherence and variety")
                print(f"      → Current thresholds (0.60-0.70) should work")
                
            else:
                print(f"   🔵 High similarity (mean={mean_sim:.3f})")
                print(f"      → Very coherent content (or embeddings are too similar)")
                print(f"      → May need HIGHER thresholds or different segmentation")
            
            # Specific recommendations
            print(f"\n🔧 Recommended Hyperparameters:")
            if mean_sim < 0.5:
                print(f"   neighbor_threshold=0.65")
                print(f"   adjacent_threshold=0.45")
                print(f"   max_group_words=800")
            elif mean_sim < 0.65:
                print(f"   neighbor_threshold=0.70")
                print(f"   adjacent_threshold=0.55")
                print(f"   max_group_words=750")
            else:
                print(f"   neighbor_threshold=0.75")
                print(f"   adjacent_threshold=0.65")
                print(f"   max_group_words=700")
        
        # Sample k-NN for a few segments
        print(f"\n🔍 k-NN Similarity Analysis:")
        print(f"   Checking top-8 neighbors for 3 sample segments...\n")
        
        for idx in [0, len(segments)//2, len(segments)-1]:
            if not segments[idx]['embedding']:
                continue
            
            seg = segments[idx]
            print(f"   Segment {idx} ({seg['start']:.1f}s):")
            print(f"      Text: {seg['text'][:60]}...")
            
            # Query neighbors
            response = collection.query.near_vector(
                near_vector=seg['embedding'],
                limit=9,  # +1 for self
                return_metadata=MetadataQuery(distance=True),
                filters=weaviate.classes.query.Filter.by_property("videoId").equal(video_id)
            )
            
            neighbor_sims = []
            for obj in response.objects:
                if str(obj.uuid) == seg['id']:
                    continue  # Skip self
                
                distance = obj.metadata.distance if obj.metadata.distance else 0.0
                similarity = 1.0 - distance
                neighbor_sims.append(similarity)
            
            if neighbor_sims:
                print(f"      Top-8 neighbor similarities: {[f'{s:.3f}' for s in neighbor_sims[:8]]}")
                print(f"      Mean: {np.mean(neighbor_sims):.3f}, Min: {min(neighbor_sims):.3f}")
            print()
        
    finally:
        client.close()
    
    print(f"{'='*80}\n")


def main():
    """Run diagnostics on all videos."""
    import sys
    
    if len(sys.argv) > 1:
        video_ids = [sys.argv[1]]
    else:
        video_ids = [
            "HbDqLPm_2vY",
            "wLb9g_8r-mE",
            "zc9ajtpaS6k"
        ]
    
    for video_id in video_ids:
        diagnose_video(video_id, sample_size=20)


if __name__ == "__main__":
    main()
