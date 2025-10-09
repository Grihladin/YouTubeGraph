"""Visualize segment groups - analyze cohesion, boundaries, and temporal flow."""

import json
from pathlib import Path
from typing import List, Dict, Any

import numpy as np


def load_groups(json_path: Path) -> Dict[str, Any]:
    """Load groups from JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def print_group_summary(groups_data: Dict[str, Any]) -> None:
    """Print a detailed summary of groups."""
    video_id = groups_data['video_id']
    groups = groups_data['groups']
    num_groups = len(groups)
    
    print(f"\n{'='*80}")
    print(f"VIDEO: {video_id}")
    print(f"{'='*80}\n")
    
    print(f"📊 Overview:")
    print(f"  • Total groups: {num_groups}")
    print(f"  • Total segments: {sum(g['num_segments'] for g in groups)}")
    print(f"  • Total words: {sum(g['total_words'] for g in groups):,}")
    
    # Statistics
    word_counts = [g['total_words'] for g in groups]
    cohesions = [g['avg_cohesion'] for g in groups]
    durations = [g['duration'] for g in groups]
    
    print(f"\n📏 Word Count Distribution:")
    print(f"  • Min:    {min(word_counts):>6}")
    print(f"  • Max:    {max(word_counts):>6}")
    print(f"  • Mean:   {np.mean(word_counts):>6.0f}")
    print(f"  • Median: {np.median(word_counts):>6.0f}")
    
    print(f"\n🔗 Cohesion Distribution:")
    print(f"  • Min:    {min(cohesions):.3f}")
    print(f"  • Max:    {max(cohesions):.3f}")
    print(f"  • Mean:   {np.mean(cohesions):.3f}")
    print(f"  • Median: {np.median(cohesions):.3f}")
    
    print(f"\n⏱️  Duration Distribution:")
    print(f"  • Min:    {min(durations)/60:>6.1f} min")
    print(f"  • Max:    {max(durations)/60:>6.1f} min")
    print(f"  • Mean:   {np.mean(durations)/60:>6.1f} min")
    print(f"  • Median: {np.median(durations)/60:>6.1f} min")


def print_detailed_groups(groups_data: Dict[str, Any], max_groups: int = 10) -> None:
    """Print detailed information for each group."""
    groups = groups_data['groups']
    
    print(f"\n{'='*80}")
    print(f"DETAILED GROUP BREAKDOWN (showing first {max_groups})")
    print(f"{'='*80}\n")
    
    for i, group in enumerate(groups[:max_groups]):
        print(f"┌─ Group {group['group_id']} " + "─" * 65)
        
        # Time info
        start_min = group['start_time'] / 60
        end_min = group['end_time'] / 60
        duration_min = group['duration'] / 60
        
        print(f"│ 🕐 Time:     {start_min:.1f}m → {end_min:.1f}m  (duration: {duration_min:.1f}m)")
        print(f"│ 📝 Segments: {group['num_segments']}")
        print(f"│ 📊 Words:    {group['total_words']}")
        print(f"│ 🔗 Cohesion: {group['avg_cohesion']:.3f}")
        
        # Text preview
        text = group['text']
        if len(text) > 200:
            text = text[:200] + "..."
        
        print(f"│")
        print(f"│ 📄 Text Preview:")
        for line in text.split('\n'):
            if line.strip():
                print(f"│    {line[:76]}")
        
        print(f"└" + "─" * 78 + "\n")
    
    if len(groups) > max_groups:
        print(f"... and {len(groups) - max_groups} more groups\n")


def print_boundary_analysis(groups_data: Dict[str, Any]) -> None:
    """Analyze gaps between groups (boundary strength)."""
    groups = groups_data['groups']
    
    print(f"\n{'='*80}")
    print(f"BOUNDARY ANALYSIS")
    print(f"{'='*80}\n")
    
    print("Gaps between consecutive groups (potential topic shifts):\n")
    
    for i in range(len(groups) - 1):
        curr = groups[i]
        next_group = groups[i + 1]
        
        gap = next_group['start_time'] - curr['end_time']
        
        # Classify gap strength
        if gap > 10:
            strength = "🔴 STRONG"
        elif gap > 2:
            strength = "🟡 MEDIUM"
        else:
            strength = "🟢 WEAK"
        
        print(f"  Group {curr['group_id']:>2} → {next_group['group_id']:>2}:  "
              f"{gap:>6.1f}s gap  {strength}")


def print_outlier_groups(groups_data: Dict[str, Any]) -> None:
    """Identify and report outlier groups."""
    groups = groups_data['groups']
    
    word_counts = [g['total_words'] for g in groups]
    cohesions = [g['avg_cohesion'] for g in groups]
    
    mean_words = np.mean(word_counts)
    std_words = np.std(word_counts)
    mean_cohesion = np.mean(cohesions)
    
    print(f"\n{'='*80}")
    print(f"OUTLIER DETECTION")
    print(f"{'='*80}\n")
    
    # Word count outliers
    print("📊 Word Count Outliers (>1.5 std from mean):\n")
    found_word_outliers = False
    for group in groups:
        z_score = (group['total_words'] - mean_words) / std_words if std_words > 0 else 0
        if abs(z_score) > 1.5:
            found_word_outliers = True
            marker = "📈" if z_score > 0 else "📉"
            print(f"  {marker} Group {group['group_id']:>2}: {group['total_words']:>4} words "
                  f"(z={z_score:+.2f})")
    
    if not found_word_outliers:
        print("  ✓ No significant word count outliers detected")
    
    # Cohesion outliers
    print("\n🔗 Cohesion Outliers (significantly below mean):\n")
    found_cohesion_outliers = False
    for group in groups:
        if group['avg_cohesion'] < mean_cohesion - 0.15:
            found_cohesion_outliers = True
            print(f"  ⚠️  Group {group['group_id']:>2}: cohesion={group['avg_cohesion']:.3f} "
                  f"(mean={mean_cohesion:.3f})")
    
    if not found_cohesion_outliers:
        print("  ✓ All groups have acceptable cohesion")


def generate_timeline_view(groups_data: Dict[str, Any], width: int = 70) -> None:
    """Generate ASCII timeline visualization."""
    groups = groups_data['groups']
    
    if not groups:
        return
    
    print(f"\n{'='*80}")
    print(f"TIMELINE VIEW")
    print(f"{'='*80}\n")
    
    total_duration = groups[-1]['end_time']
    
    print(f"0m {' ' * (width - 6)} {total_duration/60:.1f}m")
    print("│" + "─" * width + "│")
    
    for group in groups:
        # Calculate position and width
        start_pos = int((group['start_time'] / total_duration) * width)
        end_pos = int((group['end_time'] / total_duration) * width)
        group_width = max(1, end_pos - start_pos)
        
        # Build the bar
        bar = " " * start_pos
        bar += "█" * group_width
        bar += " " * (width - start_pos - group_width)
        
        # Cohesion indicator
        if group['avg_cohesion'] >= 0.75:
            indicator = "🟢"
        elif group['avg_cohesion'] >= 0.60:
            indicator = "🟡"
        else:
            indicator = "🔴"
        
        print(f"│{bar}│ {indicator} G{group['group_id']:>2} ({group['total_words']:>3}w)")
    
    print("│" + "─" * width + "│")
    print(f"\nLegend: 🟢 High cohesion (≥0.75)  🟡 Medium (≥0.60)  🔴 Low (<0.60)")


def main():
    """Visualize all group files."""
    import sys
    
    groups_dir = Path("output/groups")
    
    if not groups_dir.exists():
        print(f"❌ Groups directory not found: {groups_dir}")
        return
    
    # Accept pattern as argument (e.g., "tuned_*.json" or "groups_*.json")
    pattern = sys.argv[1] if len(sys.argv) > 1 else "*.json"
    json_files = list(groups_dir.glob(pattern))
    
    if not json_files:
        print(f"❌ No files matching '{pattern}' found in {groups_dir}")
        print(f"\nUsage: python visualize_groups.py [pattern]")
        print(f"Examples:")
        print(f"  python visualize_groups.py                # All JSON files")
        print(f"  python visualize_groups.py 'groups_*.json' # Only default grouping")
        print(f"  python visualize_groups.py 'tuned_*.json'  # Only tuned grouping")
        return
    
    print(f"Found {len(json_files)} file(s) matching '{pattern}'\n")
    
    for json_path in json_files:
        print(f"\n{'#'*80}")
        print(f"# Analyzing: {json_path.name}")
        print(f"{'#'*80}")
        
        try:
            groups_data = load_groups(json_path)
            
            # Run all analyses
            print_group_summary(groups_data)
            generate_timeline_view(groups_data)
            print_boundary_analysis(groups_data)
            print_outlier_groups(groups_data)
            print_detailed_groups(groups_data, max_groups=5)
            
        except Exception as e:
            print(f"❌ Error analyzing {json_path.name}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
