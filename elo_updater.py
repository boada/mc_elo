"""
Multi-system rating calculator for MORALE CHECK.
Calculates Elo, Glicko-2, and TrueSkill ratings from match results.
"""
import json
import csv
from pathlib import Path
from typing import Dict, Tuple
from glicko2 import Glicko2, WIN, DRAW, LOSS
import trueskill

RATINGS_FILE: Path = Path("ratings.json")

# Elo parameters
DEFAULT_ELO: int = 1500
K_FACTOR: int = 32

# Glicko-2 parameters (default values)
GLICKO2_ENV = Glicko2()

# TrueSkill parameters (using default Warhammer-appropriate values)
trueskill.setup(mu=25.0, sigma=25.0/3, beta=25.0/6, tau=25.0/300, draw_probability=0.05)


class PlayerRatings:
    """Container for a player's ratings across all systems."""
    
    def __init__(self, name: str):
        self.name = name
        self.elo = DEFAULT_ELO
        self.glicko2_player = GLICKO2_ENV.create_rating()
        self.trueskill_rating = trueskill.Rating()
        self.games = 0
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "elo": round(self.elo, 2),
            "glicko2": {
                "rating": round(self.glicko2_player.mu, 2),
                "rd": round(self.glicko2_player.phi, 2),
                "vol": round(self.glicko2_player.sigma, 6)
            },
            "trueskill": {
                "mu": round(self.trueskill_rating.mu, 2),
                "sigma": round(self.trueskill_rating.sigma, 2),
                "conservative": round(self.trueskill_rating.mu - 3 * self.trueskill_rating.sigma, 2)
            },
            "games": self.games
        }
    
    @classmethod
    def from_dict(cls, name: str, data: dict) -> 'PlayerRatings':
        """Load from saved data (for incremental updates)."""
        player = cls(name)
        player.elo = data.get("elo", DEFAULT_ELO)
        player.games = data.get("games", 0)
        
        # Glicko-2
        if "glicko2" in data:
            g2 = data["glicko2"]
            player.glicko2_player = GLICKO2_ENV.create_rating(
                mu=g2.get("rating", 1500),
                phi=g2.get("rd", 350),
                sigma=g2.get("vol", 0.06)
            )
        
        # TrueSkill
        if "trueskill" in data:
            ts = data["trueskill"]
            player.trueskill_rating = trueskill.Rating(
                mu=ts.get("mu", 25.0),
                sigma=ts.get("sigma", 25.0/3)
            )
        
        return player


def load_ratings() -> Dict[str, PlayerRatings]:
    """Load player ratings from JSON file."""
    if not RATINGS_FILE.exists():
        return {}
    
    with open(RATINGS_FILE, "r") as f:
        data = json.load(f)
    
    return {name: PlayerRatings.from_dict(name, ratings) 
            for name, ratings in data.items()}


def save_ratings(players: Dict[str, PlayerRatings]) -> None:
    """Save player ratings to JSON file."""
    data = {name: player.to_dict() for name, player in players.items()}
    
    with open(RATINGS_FILE, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def expected_score(rating_a: float, rating_b: float) -> float:
    """Calculate expected score for Elo system."""
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def update_elo(rating_a: float, rating_b: float, result: float) -> Tuple[float, float]:
    """Update Elo ratings after a match."""
    expected_a = expected_score(rating_a, rating_b)
    expected_b = expected_score(rating_b, rating_a)
    
    new_a = rating_a + K_FACTOR * (result - expected_a)
    new_b = rating_b + K_FACTOR * ((1 - result) - expected_b)
    
    return new_a, new_b


def process_results(csv_path: Path, players: Dict[str, PlayerRatings]) -> Dict[str, PlayerRatings]:
    """
    Process match results and update all rating systems.
    
    For Glicko-2, we batch all matches in a rating period, then update.
    For TrueSkill and Elo, we update incrementally.
    """
    # Track Glicko-2 matches for batch processing
    glicko_matches = []
    
    with open(csv_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            p1_name = row["player1"].strip()
            p2_name = row["player2"].strip()
            result = float(row["result"])
            
            # Initialize players if needed
            if p1_name not in players:
                players[p1_name] = PlayerRatings(p1_name)
            if p2_name not in players:
                players[p2_name] = PlayerRatings(p2_name)
            
            p1 = players[p1_name]
            p2 = players[p2_name]
            
            # Update game counts
            p1.games += 1
            p2.games += 1
            
            # ===== ELO UPDATE =====
            p1.elo, p2.elo = update_elo(p1.elo, p2.elo, result)
            
            # ===== TRUESKILL UPDATE =====
            # TrueSkill expects teams, so wrap each player
            if result == 1:  # Player 1 wins
                (new_r1,), (new_r2,) = trueskill.rate([(p1.trueskill_rating,)], 
                                                       [(p2.trueskill_rating,)])
            elif result == 0:  # Player 2 wins
                (new_r2,), (new_r1,) = trueskill.rate([(p2.trueskill_rating,)], 
                                                       [(p1.trueskill_rating,)])
            else:  # Draw
                (new_r1,), (new_r2,) = trueskill.rate([(p1.trueskill_rating,)], 
                                                       [(p2.trueskill_rating,)], 
                                                       ranks=[0, 0])
            
            p1.trueskill_rating = new_r1
            p2.trueskill_rating = new_r2
            
            # ===== GLICKO-2 BATCH =====
            # Store match for batch processing
            glicko_result = WIN if result == 1 else (LOSS if result == 0 else DRAW)
            glicko_matches.append((p1_name, p2_name, glicko_result))
    
    # Process Glicko-2 matches in batch (one rating period)
    # Group matches by player
    player_match_data = {}
    for p1_name, p2_name, result in glicko_matches:
        if p1_name not in player_match_data:
            player_match_data[p1_name] = []
        if p2_name not in player_match_data:
            player_match_data[p2_name] = []
        
        # Add match from p1's perspective
        player_match_data[p1_name].append((players[p2_name].glicko2_player, result))
        
        # Add match from p2's perspective (invert result)
        inverse_result = LOSS if result == WIN else (WIN if result == LOSS else DRAW)
        player_match_data[p2_name].append((players[p1_name].glicko2_player, inverse_result))
    
    # Update all Glicko-2 ratings
    for player_name, matches in player_match_data.items():
        player = players[player_name]
        opponents = [opp for opp, _ in matches]
        results = [res for _, res in matches]
        player.glicko2_player = GLICKO2_ENV.rate(player.glicko2_player, opponents, results)
    
    return players


def main() -> None:
    """Main function to process match results and update ratings."""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python elo_updater.py path/to/results.csv")
        return
    
    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"File not found: {csv_path}")
        return
    
    print(f"Processing: {csv_path}")
    
    players = load_ratings()
    players = process_results(csv_path, players)
    save_ratings(players)
    
    print(f"\nRatings updated for {len(players)} players")
    print(f"Total matches processed: {sum(p.games for p in players.values()) // 2}")


if __name__ == "__main__":
    main()
