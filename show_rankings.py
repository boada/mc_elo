"""
Display current Elo rankings in a formatted table.
"""
import json
from pathlib import Path


def show_rankings():
    """Display current Elo rankings."""
    ratings_file = Path("ratings.json")
    
    if not ratings_file.exists():
        print("No ratings found. Run 'python update_elo.py' first.")
        return
    
    with open(ratings_file, 'r') as f:
        ratings = json.load(f)
    
    if not ratings:
        print("No ratings available yet.")
        return
    
    # Sort by rating (descending)
    sorted_ratings = sorted(ratings.items(), key=lambda x: x[1], reverse=True)
    
    # Print header in markdown format
    print("\n```")
    print("# MORALE CHECK ELO RANKINGS")
    print()
    print("| Rank | Player                  | Rating  |")
    print("|------|-------------------------|---------|")
    
    # Print rankings
    for i, (player, rating) in enumerate(sorted_ratings, 1):
        print(f"| {i:^4} | {player:<23} | {rating:>6.2f} |")
    
    print()
    print(f"**Total Players:** {len(sorted_ratings)}  ")
    print(f"**Average Rating:** {sum(ratings.values()) / len(ratings):.2f}")
    print("```\n")


if __name__ == "__main__":
    show_rankings()
