"""
Display current Elo rankings in a formatted table.
"""
import json
import csv
from pathlib import Path
from collections import defaultdict


def calculate_records():
    """Calculate win-draw-loss records from all_events.csv."""
    all_events = Path("data/all_events.csv")
    
    if not all_events.exists():
        return {}
    
    records = defaultdict(lambda: {'wins': 0, 'draws': 0, 'losses': 0})
    
    with open(all_events, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            p1 = row['player1']
            p2 = row['player2']
            result = float(row['result'])
            
            if result == 1:  # Player 1 wins
                records[p1]['wins'] += 1
                records[p2]['losses'] += 1
            elif result == 0:  # Player 2 wins
                records[p1]['losses'] += 1
                records[p2]['wins'] += 1
            else:  # Draw
                records[p1]['draws'] += 1
                records[p2]['draws'] += 1
    
    return records


def format_record(wins, draws, losses, include_draws):
    """Format record as W-L or W-D-L."""
    if include_draws:
        return f"{wins}-{draws}-{losses}"
    return f"{wins}-{losses}"


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
    
    # Calculate records
    records = calculate_records()
    
    # Check if any draws exist
    has_draws = any(rec['draws'] > 0 for rec in records.values())
    
    # Sort by rating (descending)
    sorted_ratings = sorted(ratings.items(), key=lambda x: x[1], reverse=True)
    
    # Calculate dynamic name column width (longest name + 2 spaces)
    max_name_len = max(len(player) for player in ratings.keys())
    name_width = max_name_len + 2
    
    # Print header in markdown format
    print("\n```")
    print("# MORALE CHECK ELO RANKINGS")
    print()
    if has_draws:
        print(f"| Rank | {'Player':<{name_width}} | Rating  | Record    |")
        print(f"|------|{'-' * (name_width + 2)}|---------|-----------|")
    else:
        print(f"| Rank | {'Player':<{name_width}} | Rating  | Record  |")
        print(f"|------|{'-' * (name_width + 2)}|---------|---------|")
    
    # Print rankings
    for i, (player, rating) in enumerate(sorted_ratings, 1):
        rec = records[player]
        record_str = format_record(rec['wins'], rec['draws'], rec['losses'], has_draws)
        if has_draws:
            print(f"| {i:^4} | {player:<{name_width}} | {rating:>6.2f} | {record_str:^9} |")
        else:
            print(f"| {i:^4} | {player:<{name_width}} | {rating:>6.2f} | {record_str:^7} |")
    
    print()
    print(f"**Total Players:** {len(sorted_ratings)}  ")
    print(f"**Average Rating:** {sum(ratings.values()) / len(ratings):.2f}")
    print("```\n")


if __name__ == "__main__":
    show_rankings()
