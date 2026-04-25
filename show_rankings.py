"""
Display current Elo and Glicko-2 rankings in formatted tables.
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
    """Display current Elo and Glicko-2 rankings."""
    elo_file = Path("ratings.json")
    glicko_file = Path("glicko_ratings.json")
    
    if not elo_file.exists() and not glicko_file.exists():
        print("No ratings found. Run 'python update_elo.py' first.")
        return
    
    # Calculate records
    records = calculate_records()
    has_draws = any(rec['draws'] > 0 for rec in records.values())
    
    print("\n```")
    print("# MORALE CHECK RANKINGS")
    print()
    
    # ===== ELO RANKINGS =====
    if elo_file.exists():
        with open(elo_file, 'r') as f:
            elo_ratings = json.load(f)
        
        if elo_ratings:
            sorted_elo = sorted(elo_ratings.items(), key=lambda x: x[1], reverse=True)
            max_name_len = max(len(player) for player in elo_ratings.keys())
            name_width = max_name_len + 2
            
            print("## Elo Ratings")
            print()
            
            if has_draws:
                print(f"| Rank | {'Player':<{name_width}} | Rating  | Record    |")
                print(f"|------|{'-' * (name_width + 2)}|---------|-----------|")
            else:
                print(f"| Rank | {'Player':<{name_width}} | Rating  | Record  |")
                print(f"|------|{'-' * (name_width + 2)}|---------|---------|")
            
            for i, (player, rating) in enumerate(sorted_elo, 1):
                rec = records[player]
                record_str = format_record(rec['wins'], rec['draws'], rec['losses'], has_draws)
                
                if has_draws:
                    print(f"| {i:^4} | {player:<{name_width}} | {rating:>6.2f} | {record_str:^9} |")
                else:
                    print(f"| {i:^4} | {player:<{name_width}} | {rating:>6.2f} | {record_str:^7} |")
            
            elo_avg = sum(elo_ratings.values()) / len(elo_ratings)
            print()
            print(f"**Average Elo:** {elo_avg:.2f}")
            print()
    
    # ===== GLICKO-2 RANKINGS =====
    if glicko_file.exists():
        with open(glicko_file, 'r') as f:
            glicko_ratings = json.load(f)
        
        if glicko_ratings:
            sorted_glicko = sorted(glicko_ratings.items(), 
                                  key=lambda x: x[1]['rating'], 
                                  reverse=True)
            max_name_len = max(len(player) for player in glicko_ratings.keys())
            name_width = max_name_len + 2
            
            print("## Glicko-2 Ratings")
            print("*(Lower RD = higher confidence in rating)*")
            print()
            
            if has_draws:
                print(f"| Rank | {'Player':<{name_width}} | Rating  | RD    | Games | Record    |")
                print(f"|------|{'-' * (name_width + 2)}|---------|-------|-------|-----------|")
            else:
                print(f"| Rank | {'Player':<{name_width}} | Rating  | RD    | Games | Record  |")
                print(f"|------|{'-' * (name_width + 2)}|---------|-------|-------|---------|")
            
            for i, (player, data) in enumerate(sorted_glicko, 1):
                rec = records[player]
                record_str = format_record(rec['wins'], rec['draws'], rec['losses'], has_draws)
                rating = data['rating']
                rd = data['rd']
                games = data.get('games', 0)
                
                if has_draws:
                    print(f"| {i:^4} | {player:<{name_width}} | {rating:>6.2f} | {rd:>5.1f} | {games:^5} | {record_str:^9} |")
                else:
                    print(f"| {i:^4} | {player:<{name_width}} | {rating:>6.2f} | {rd:>5.1f} | {games:^5} | {record_str:^7} |")
            
            glicko_avg = sum(d['rating'] for d in glicko_ratings.values()) / len(glicko_ratings)
            print()
            print(f"**Average Glicko-2:** {glicko_avg:.2f}")
            print()
    
    # ===== SUMMARY =====
    if elo_file.exists() or glicko_file.exists():
        total_players = len(elo_ratings) if elo_file.exists() else len(glicko_ratings)
        total_games = sum(p.get('games', sum(records[name].values())) 
                         for name, p in (glicko_ratings.items() if glicko_file.exists() 
                                       else {name: {} for name in elo_ratings.keys()}.items())) // 2
        
        print(f"**Total Players:** {total_players}  ")
        print(f"**Total Matches:** {total_games if glicko_file.exists() else sum(sum(rec.values()) for rec in records.values()) // 2}")
    
    print("```\n")


if __name__ == "__main__":
    show_rankings()
