"""
Update Elo ratings from all event data.
Combines all event CSVs and calculates current ratings.
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
        
        # Show top 10 ratings
        import json
        with open("ratings.json", 'r') as f:
            ratings = json.load(f)
        
        sorted_ratings = sorted(ratings.items(), key=lambda x: x[1], reverse=True)
        
        print("\nCurrent Elo Ratings (Top 10):")
        print("=" * 50)
        for i, (player, rating) in enumerate(sorted_ratings[:10], 1):
            print(f"  {i:2d}. {player:30s} {rating:7.2f}")
        
        return True
    else:
        print(f"ERROR calculating Elo:")
        print(result.stderr)
        return False


def main():
    print("Updating Elo Ratings\n")
    
    # Combine all events
    if not combine_events():
        return
    
    # Calculate Elo
    if calculate_elo():
        print("\nDone! Ratings saved to ratings.json")


if __name__ == "__main__":
    main()
