"""
Glicko-2 rating calculator for MORALE CHECK.
Parallel to elo_updater.py but uses the Glicko-2 system.

Glicko-2 advantages over Elo:
- Tracks rating deviation (RD) showing confidence in the rating
- Handles rating period volatility
- Better for players with few games
- Industry standard for 1v1 competitive games (chess, Go)
"""
import json
import csv
from pathlib import Path
from typing import Dict, List, Tuple
from glicko2 import Player

RATINGS_FILE: Path = Path("glicko_ratings.json")


class PlayerData:
    """Container for a player's Glicko-2 rating and game count."""
    
    def __init__(self, name: str):
        self.name = name
        self.player = Player()  # Default: rating=1500, rd=350, vol=0.06
        self.games = 0
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "rating": round(self.player.getRating(), 2),
            "rd": round(self.player.getRd(), 2),
            "vol": round(self.player.vol, 6),
            "games": self.games
        }
    
    @classmethod
    def from_dict(cls, name: str, data: dict) -> 'PlayerData':
        """Load from saved data."""
        player_data = cls(name)
        player_data.games = data.get("games", 0)
        
        # Restore Glicko-2 state
        player_data.player.setRating(data.get("rating", 1500.0))
        player_data.player.setRd(data.get("rd", 350.0))
        player_data.player.vol = data.get("vol", 0.06)
        
        return player_data


def load_ratings() -> Dict[str, PlayerData]:
    """Load player ratings from JSON file."""
    if not RATINGS_FILE.exists():
        return {}
    
    with open(RATINGS_FILE, "r") as f:
        data = json.load(f)
    
    return {name: PlayerData.from_dict(name, ratings) 
            for name, ratings in data.items()}


def save_ratings(players: Dict[str, PlayerData]) -> None:
    """Save player ratings to JSON file."""
    data = {name: player.to_dict() for name, player in players.items()}
    
    with open(RATINGS_FILE, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def process_results(csv_path: Path, players: Dict[str, PlayerData]) -> Dict[str, PlayerData]:
    """
    Process match results and update Glicko-2 ratings.
    
    Glicko-2 processes all matches in a rating period as a batch,
    which gives more accurate results than incremental updates.
    """
    # Collect all matches
    all_matches: List[Tuple[str, str, float]] = []
    
    with open(csv_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            p1_name = row["player1"].strip()
            p2_name = row["player2"].strip()
            result = float(row["result"])
            
            # Initialize players if needed
            if p1_name not in players:
                players[p1_name] = PlayerData(p1_name)
            if p2_name not in players:
                players[p2_name] = PlayerData(p2_name)
            
            all_matches.append((p1_name, p2_name, result))
    
    # Update game counts
    for p1_name, p2_name, _ in all_matches:
        players[p1_name].games += 1
        players[p2_name].games += 1
    
    # Group matches by player for batch processing (one rating period)
    player_matches: Dict[str, List[Tuple[Player, float]]] = {}
    
    for p1_name, p2_name, result in all_matches:
        if p1_name not in player_matches:
            player_matches[p1_name] = []
        if p2_name not in player_matches:
            player_matches[p2_name] = []
        
        # Add opponent and score from each player's perspective
        player_matches[p1_name].append((players[p2_name].player, result))
        player_matches[p2_name].append((players[p1_name].player, 1 - result))
    
    # Update all Glicko-2 ratings in one rating period
    for player_name, matches in player_matches.items():
        player_data = players[player_name]
        
        # Extract ratings, RDs, and outcomes for the glicko2 API
        rating_list = [opp.getRating() for opp, _ in matches]
        rd_list = [opp.getRd() for opp, _ in matches]
        outcome_list = [score for _, score in matches]
        
        player_data.player.update_player(rating_list, rd_list, outcome_list)
    
    return players


def main() -> None:
    """Main function to process match results and update Glicko-2 ratings."""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python glicko_updater.py path/to/results.csv")
        return
    
    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"File not found: {csv_path}")
        return
    
    print(f"Processing: {csv_path}")
    
    players = load_ratings()
    players = process_results(csv_path, players)
    save_ratings(players)
    
    print(f"\nGlicko-2 ratings updated for {len(players)} players")
    print(f"Total matches processed: {sum(p.games for p in players.values()) // 2}")


if __name__ == "__main__":
    main()
