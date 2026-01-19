import json
import csv
from pathlib import Path
from typing import Dict, Tuple

RATINGS_FILE: Path = Path("ratings.json")
DEFAULT_RATING: int = 1500
K_FACTOR: int = 32


def load_ratings() -> Dict[str, float]:
    """
    Load player ratings from the JSON file. If it doesn't exist, return an empty dict.

    Returns:
        Dict[str, float]: A dictionary of player names to their ELO ratings.
    """
    if RATINGS_FILE.exists():
        with open(RATINGS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_ratings(ratings: Dict[str, float]) -> None:
    """
    Save player ratings to the JSON file.

    Args:
        ratings (Dict[str, float]): The updated player ratings.
    """
    with open(RATINGS_FILE, "w") as f:
        json.dump(ratings, f, indent=2)


def expected_score(rating_a: float, rating_b: float) -> float:
    """
    Calculate the expected score for player A against player B.

    Args:
        rating_a (float): Rating of player A.
        rating_b (float): Rating of player B.

    Returns:
        float: Expected score (between 0 and 1) for player A.
    """
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def update_elo(rating_a: float, rating_b: float, result: float) -> Tuple[float, float]:
    """
    Update the ELO ratings for two players after a match.

    Args:
        rating_a (float): Current rating of player A.
        rating_b (float): Current rating of player B.
        result (float): Actual result from A's perspective (1 = win, 0.5 = draw, 0 = loss).

    Returns:
        Tuple[float, float]: New ratings for player A and player B.
    """
    expected_a = expected_score(rating_a, rating_b)
    expected_b = expected_score(rating_b, rating_a)

    new_a = rating_a + K_FACTOR * (result - expected_a)
    new_b = rating_b + K_FACTOR * ((1 - result) - expected_b)

    return new_a, new_b


def process_results(csv_path: Path, ratings: Dict[str, float]) -> Dict[str, float]:
    """
    Process a CSV file containing match results and update the ratings.

    Args:
        csv_path (Path): Path to the CSV file.
        ratings (Dict[str, float]): Current ratings to update.

    Returns:
        Dict[str, float]: Updated ratings.
    """
    with open(csv_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            p1 = row["player1"].strip()
            p2 = row["player2"].strip()
            result = float(row["result"])

            rating1 = ratings.get(p1, DEFAULT_RATING)
            rating2 = ratings.get(p2, DEFAULT_RATING)

            new_rating1, new_rating2 = update_elo(rating1, rating2, result)

            ratings[p1] = round(new_rating1, 2)
            ratings[p2] = round(new_rating2, 2)

    return ratings


def main() -> None:
    """
    Main function to load ratings, process the results, and save updated ratings.
    """
    import sys

    if len(sys.argv) != 2:
        print("Usage: python elo_updater.py path/to/results.csv")
        return

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"File not found: {csv_path}")
        return

    ratings = load_ratings()
    updated = process_results(csv_path, ratings)
    save_ratings(updated)
    print("✅ Ratings updated.")


if __name__ == "__main__":
    main()
