"""
Update Elo and Glicko-2 ratings from all event data.
Combines all event CSVs and calculates current ratings for both systems.
"""
from pathlib import Path
import csv
import subprocess
import sys


def combine_events():
    """Combine all event CSV files into one master file."""
    events_dir = Path("data/events")
    output_file = Path("data/all_events.csv")
    
    if not events_dir.exists():
        print("ERROR: No events directory found. Run scraper first.")
        return False
    
    event_files = sorted(events_dir.glob("event_*.csv"))
    
    if not event_files:
        print("ERROR: No event files found in data/events/")
        return False
    
    print(f"Combining {len(event_files)} event files...")
    
    # Read all events and combine
    all_rows = []
    header_written = False
    
    for event_file in event_files:
        with open(event_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                all_rows.append(row)
        print(f"   ✓ {event_file.name}")
    
    # Write combined file
    if all_rows:
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=all_rows[0].keys())
            writer.writeheader()
            writer.writerows(all_rows)
        
        print(f"Combined {len(all_rows)} matches -> {output_file}")
        return True
    
    return False


def calculate_elo():
    """Run the Elo calculator on combined events."""
    combined_file = Path("data/all_events.csv")
    
    if not combined_file.exists():
        print("ERROR: Combined events file not found")
        return False
    
    print(f"\nCalculating Elo ratings...")
    
    # Delete old ratings to start fresh (prevents ghost players from filtered events)
    ratings_file = Path("ratings.json")
    if ratings_file.exists():
        ratings_file.unlink()
    
    # Run elo_updater.py
    result = subprocess.run(
        [sys.executable, "elo_updater.py", str(combined_file)],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(result.stdout)
        return True
    else:
        print(f"ERROR calculating Elo:")
        print(result.stderr)
        return False


def calculate_glicko():
    """Run the Glicko-2 calculator on combined events."""
    combined_file = Path("data/all_events.csv")
    
    if not combined_file.exists():
        print("ERROR: Combined events file not found")
        return False
    
    print(f"\nCalculating Glicko-2 ratings...")
    
    # Delete old ratings to start fresh
    ratings_file = Path("glicko_ratings.json")
    if ratings_file.exists():
        ratings_file.unlink()
    
    # Run glicko_updater.py
    result = subprocess.run(
        [sys.executable, "glicko_updater.py", str(combined_file)],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(result.stdout)
        return True
    else:
        print(f"ERROR calculating Glicko-2:")
        print(result.stderr)
        return False


def show_top_ratings():
    """Display top 10 for quick reference."""
    import json
    
    print("\n" + "=" * 60)
    print("TOP 10 RANKINGS")
    print("=" * 60)
    
    # Elo rankings
    if Path("ratings.json").exists():
        with open("ratings.json", 'r') as f:
            elo_ratings = json.load(f)
        sorted_elo = sorted(elo_ratings.items(), key=lambda x: x[1], reverse=True)
        
        print("\nElo Ratings:")
        for i, (player, rating) in enumerate(sorted_elo[:10], 1):
            print(f"  {i:2d}. {player:30s} {rating:7.2f}")
    
    # Glicko-2 rankings
    if Path("glicko_ratings.json").exists():
        with open("glicko_ratings.json", 'r') as f:
            glicko_ratings = json.load(f)
        sorted_glicko = sorted(glicko_ratings.items(), 
                              key=lambda x: x[1]['rating'], 
                              reverse=True)
        
        print("\nGlicko-2 Ratings:")
        for i, (player, data) in enumerate(sorted_glicko[:10], 1):
            rating = data['rating']
            rd = data['rd']
            print(f"  {i:2d}. {player:30s} {rating:7.2f} (±{rd:5.1f})")


def main():
    print("Updating Ratings\n")
    
    # Combine all events
    if not combine_events():
        return
    
    # Calculate both rating systems
    elo_success = calculate_elo()
    glicko_success = calculate_glicko()
    
    if elo_success or glicko_success:
        show_top_ratings()
        print("\nDone! Use 'python show_rankings.py' for full rankings.")


if __name__ == "__main__":
    main()
