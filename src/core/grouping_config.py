"""
Tuned hyperparameters for optimal grouping quality.

These parameters have been tested and optimized for:
- Educational video content (lectures, tutorials, talks)
- Single-speaker presentations
- Well-structured, topical content

⚠️  NOT recommended for:
- Multi-speaker interviews
- Debates or panel discussions
- Highly fragmented content
"""

# PRODUCTION TUNED PARAMETERS
# These values provide the best balance of cohesion and group size
TUNED_PARAMS = {
    # k-NN search parameters
    "k_neighbors": 8,  # Number of nearest neighbors to consider
    # Similarity thresholds (0-1 scale, after temporal decay)
    "neighbor_threshold": 0.80,  # Min similarity to be considered a neighbor (stricter)
    "adjacent_threshold": 0.70,  # Min similarity to join adjacent segments (stricter)
    # Temporal parameters
    "temporal_tau": 150.0,  # Time decay constant in seconds (half-life ~2.5 min)
    # Group size constraints
    "max_group_words": 700,  # Max words per group (smaller for focused groups)
    "min_group_segments": 2,  # Min segments per group
    # Post-processing parameters
    "merge_centroid_threshold": 0.85,  # Min similarity to merge adjacent groups (less aggressive)
}

# DEFAULT (BASELINE) PARAMETERS
# Original parameters before tuning - kept for reference
DEFAULT_PARAMS = {
    "k_neighbors": 8,
    "neighbor_threshold": 0.75,
    "adjacent_threshold": 0.60,
    "temporal_tau": 150.0,
    "max_group_words": 800,
    "min_group_segments": 2,
    "merge_centroid_threshold": 0.80,
}

# STRICT PARAMETERS
# For maximum cohesion (may create more, smaller groups)
STRICT_PARAMS = {
    "k_neighbors": 8,
    "neighbor_threshold": 0.85,  # Very strict
    "adjacent_threshold": 0.75,  # Very strict
    "temporal_tau": 150.0,
    "max_group_words": 600,  # Smaller groups
    "min_group_segments": 2,
    "merge_centroid_threshold": 0.90,  # Almost no merging
}

# RELAXED PARAMETERS
# For longer, more inclusive groups (may have lower cohesion)
RELAXED_PARAMS = {
    "k_neighbors": 10,  # More neighbors
    "neighbor_threshold": 0.70,  # More permissive
    "adjacent_threshold": 0.55,  # More permissive
    "temporal_tau": 200.0,  # Longer temporal window
    "max_group_words": 900,  # Larger groups
    "min_group_segments": 2,
    "merge_centroid_threshold": 0.75,  # More aggressive merging
}


def get_params(preset: str = "tuned") -> dict:
    """Get parameter preset by name.

    Args:
        preset: One of "tuned", "default", "strict", "relaxed"

    Returns:
        Dictionary of hyperparameters

    Raises:
        ValueError: If preset name is invalid
    """
    presets = {
        "tuned": TUNED_PARAMS,
        "default": DEFAULT_PARAMS,
        "strict": STRICT_PARAMS,
        "relaxed": RELAXED_PARAMS,
    }

    if preset not in presets:
        raise ValueError(
            f"Invalid preset '{preset}'. Choose from: {list(presets.keys())}"
        )

    return presets[preset].copy()


def print_params(params: dict) -> None:
    """Print parameters in a formatted way."""
    print("\n📋 Grouping Parameters:")
    print("-" * 50)
    for key, value in params.items():
        print(f"  • {key:.<30} {value}")
    print("-" * 50)
