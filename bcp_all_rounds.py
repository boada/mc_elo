"""
Scrape all rounds from a BCP event using the round parameter on placings tab.
Uses polite scraping practices: delays between requests, proper headers.
Automatically assigns event numbers and maintains clean directory structure.
"""
from playwright.sync_api import sync_playwright
from typing import List, Dict, Optional
import csv
from pathlib import Path
import time
import random
import re
from event_manager import EventManager


def clean_player_name(name: str) -> str:
    """Clean player name: remove parentheticals and normalize casing."""
    # Remove anything in parentheses
    name = re.sub(r'\s*\([^)]*\)', '', name)
    # Remove extra whitespace
    name = ' '.join(name.split())
    # Title case
    name = name.title()
    # Handle special cases
    name = re.sub(r'\bMc([a-z])', lambda m: 'Mc' + m.group(1).upper(), name)
    name = re.sub(r"\bO'([a-z])", lambda m: "O'" + m.group(1).upper(), name)
    return name


def scrape_team_roster(event_id: str, team_name: str, page, known_players: Optional[set] = None) -> Dict[str, str]:
    """Scrape team roster and factions from roster page, handling pagination."""
    # Use roster page instead of placings - clearer structure and team affiliations
    url = f"https://www.bestcoastpairings.com/event/{event_id}?active_tab=roster"
    print(f"\nFetching {team_name} roster: {url}")
    
    page.goto(url, wait_until="load", timeout=60000)
    
    # Polite delay
    delay = random.uniform(2.0, 4.0)
    print(f"   Waiting {delay:.1f}s (polite scraping)...")
    time.sleep(delay)
    
    player_factions = {}
    # Candidates: known players found under a non-MC team.
    # Dict[name, list[(team, faction)]] — collected across ALL pages before resolving.
    override_candidates: Dict[str, list] = {}
    page_num = 1
    
    while True:
        # Parse current page
        page_text = page.inner_text('body')
        lines = page_text.split('\n')
        
        # Roster page format: 
        # "First Last - TEAM NAME"
        # (empty line)
        # "Faction"
        # (empty line)
        # "CHECKED IN" or "DROPPED"
        
        current_page_count = 0
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Look for "Player Name - TEAM NAME" pattern
            if f" - {team_name}" in line:
                # Extract player name (everything before " - TEAM")
                player_name = line.split(f" - {team_name}")[0].strip()
                cleaned_name = clean_player_name(player_name)
                
                # Look ahead for faction (skip next empty line, then get faction)
                faction = "Unknown"
                if i + 2 < len(lines):
                    potential_faction = lines[i + 2].strip()
                    # Make sure it's not a status line
                    if potential_faction and potential_faction not in ["CHECKED IN", "DROPPED", "View List", ""]:
                        faction = potential_faction
                
                player_factions[cleaned_name] = faction
                current_page_count += 1

        # Second pass: collect known players listed under a different team,
        # or with no team at all.
        # Do NOT add to player_factions yet — accumulate across all pages first
        # so we can detect ambiguous name collisions before committing.
        if known_players:
            for i, raw_line in enumerate(lines):
                raw_stripped = raw_line.strip()
                if not raw_stripped:
                    continue

                faction = "Unknown"
                if i + 2 < len(lines):
                    potential_faction = lines[i + 2].strip()
                    if potential_faction and potential_faction not in ["CHECKED IN", "DROPPED", "View List", ""]:
                        faction = potential_faction

                if ' - ' in raw_stripped:
                    # Has a team listed — check if it's a known player under a different team
                    parts = raw_stripped.rsplit(' - ', 1)
                    if len(parts) != 2:
                        continue
                    potential_name = clean_player_name(parts[0].strip())
                    their_team = parts[1].strip()
                    if (
                        potential_name in known_players
                        and potential_name not in player_factions
                        and their_team != team_name
                    ):
                        if potential_name not in override_candidates:
                            override_candidates[potential_name] = []
                        if (their_team, faction) not in override_candidates[potential_name]:
                            override_candidates[potential_name].append((their_team, faction))
                else:
                    # No team listed — check for exact name match against known players
                    potential_name = clean_player_name(raw_stripped)
                    if (
                        potential_name in known_players
                        and potential_name not in player_factions
                    ):
                        if potential_name not in override_candidates:
                            override_candidates[potential_name] = []
                        if ("(no team)", faction) not in override_candidates[potential_name]:
                            override_candidates[potential_name].append(("(no team)", faction))

        print(f"   Page {page_num}: Found {current_page_count} {team_name} players")
        
        # Check if there's a next page button
        try:
            # Look for pagination indicators
            if " of " in page_text:
                # Parse "1-32 of 88" format
                import re
                match = re.search(r'(\d+)-(\d+) of (\d+)', page_text)
                if match:
                    current_end = int(match.group(2))
                    total = int(match.group(3))
                    
                    if current_end < total:
                        # There are more pages, try to click next
                        # Look for next button or page navigation
                        try:
                            # Try clicking a "next" button or arrow
                            next_selectors = [
                                'button[aria-label="Go to next page"]',
                                'button:has-text("›")',
                                'button:has-text("Next")',
                                '[aria-label="next page"]',
                            ]
                            
                            clicked = False
                            for selector in next_selectors:
                                try:
                                    page.click(selector, timeout=2000)
                                    clicked = True
                                    break
                                except:
                                    continue
                            
                            if clicked:
                                # Wait for new page to load
                                time.sleep(2.0)
                                page.wait_for_load_state("load", timeout=30000)
                                page_num += 1
                                
                                # Polite delay between pages
                                delay = random.uniform(1.5, 3.0)
                                print(f"   Pausing {delay:.1f}s before next page...")
                                time.sleep(delay)
                                continue
                            else:
                                print(f"   Could not find next page button, stopping pagination")
                                break
                        except Exception as e:
                            print(f"   Error navigating to next page: {e}")
                            break
                    else:
                        # We're on the last page
                        break
                else:
                    # Couldn't parse pagination info
                    break
            else:
                # No pagination detected
                break
        except Exception as e:
            print(f"   Pagination navigation failed: {e}")
            break
    
    print(f"   Total: Found {len(player_factions)} {team_name} players across {page_num} page(s)")

    # Reconcile override candidates collected across all pages.
    # Only process players not already found under the correct team.
    for name, hits in override_candidates.items():
        if name in player_factions:
            # Already found them as a legit MC member; ignore any other-team hits.
            continue
        if len(hits) == 1:
            their_team, faction = hits[0]
            player_factions[name] = faction
            if their_team == "(no team)":
                print(f"   WARNING: Known player '{name}' has no team listed. Including anyway.")
            else:
                print(f"   WARNING: Known player '{name}' is listed under '{their_team}', not '{team_name}'. Including anyway.")
        else:
            teams_listed = ", ".join(f"'{t}'" for t, _ in hits)
            print(f"   WARNING: Known player '{name}' appears under {len(hits)} different teams ({teams_listed}).")
            print(f"            Cannot auto-resolve — skipping '{name}'. Add them manually to the CSV if needed.")

    if player_factions:
        for player in sorted(player_factions.keys()):
            print(f"      {player}: {player_factions[player]}")
    
    return player_factions


def scrape_round(event_id: str, event_num: int, round_num: int, page, player_factions: Optional[Dict[str, str]] = None) -> List[Dict[str, str]]:
    """Scrape a single round by parsing body text. Handles pagination."""
    results = []

    url = f"https://www.bestcoastpairings.com/event/{event_id}?active_tab=pairings&round={round_num}"
    print(f"\nRound {round_num}: {url}")

    page.goto(url, wait_until="domcontentloaded", timeout=60000)

    delay = random.uniform(2.0, 4.0)
    print(f"   Waiting {delay:.1f}s (polite scraping)...")
    time.sleep(delay)

    page_num = 1

    while True:
        page_text = page.inner_text('body')

        if f"Round {round_num}" not in page_text and "Win:" not in page_text:
            if page_num == 1:
                print(f"   WARNING: No matches found")
            break

        current_page_matches = parse_matches_from_text(
            page_text, event_num, event_id, round_num, player_factions
        )
        results.extend(current_page_matches)
        print(f"   Page {page_num}: Extracted {len(current_page_matches)} team matches")

        # Check for next page
        match = re.search(r'(\d+)-(\d+) of (\d+)', page_text)
        if match:
            current_end = int(match.group(2))
            total = int(match.group(3))
            if current_end < total:
                next_selectors = [
                    'button[aria-label="Go to next page"]',
                    'button:has-text("›")',
                    'button:has-text("Next")',
                    '[aria-label="next page"]',
                ]
                clicked = False
                for selector in next_selectors:
                    try:
                        page.click(selector, timeout=2000)
                        clicked = True
                        break
                    except:
                        continue
                if clicked:
                    time.sleep(2.0)
                    page.wait_for_load_state("domcontentloaded", timeout=30000)
                    page_num += 1
                    delay = random.uniform(1.5, 2.5)
                    time.sleep(delay)
                    continue
        break

    total_msg = f"   Total: {len(results)} team matches"
    if page_num > 1:
        total_msg += f" (across {page_num} pages)"
    print(total_msg)
    return results


def parse_matches_from_text(
    page_text: str,
    event_num: int,
    event_id: str,
    round_num: int,
    player_factions: Optional[Dict[str, str]],
) -> List[Dict]:
    """
    Parse match results from BCP round page body text.

    BCP page text format (one match):
        [table number e.g. "01"]
        [player 1 name]
        [player 1 faction]
        Win: XX  or  Loss: XX
        View List
        [player 2 name]
        [player 2 faction]
        Win: XX  or  Loss: XX
        View List
    """
    STATUS_TOKENS = {"CHECKED IN", "DROPPED", "View List", "TABLE", "Items per page"}
    NAV_TOKENS = {
        "Play", "Organize", "Leaderboards", "Subscribe", "Login",
        "Overview", "Roster", "Pairings", "Placings",
        "COOKIE CONSENT", "Accept All", "Essential Only", "Cookie Settings",
        "Quick Links", "Home", "Events", "Subscription", "Store Finder",
        "Ticketing", "Patch Notes", "Partners", "Privacy Policy",
    }

    lines = [l.strip() for l in page_text.split('\n') if l.strip()]

    # Find where the round content starts
    start_idx = 0
    for i, line in enumerate(lines):
        if line == f"Round {round_num}":
            start_idx = i
            break

    results = []
    i = start_idx

    while i < len(lines):
        line = lines[i]

        # Detect result line for player 1
        if not (line.startswith("Win:") or line.startswith("Loss:")):
            i += 1
            continue

        p1_result_text = line
        # Walk backwards to find p1 faction and name (skip "View List" etc.)
        p1_faction = "Unknown"
        p1_name = None
        j = i - 1
        while j >= start_idx:
            candidate = lines[j]
            if candidate in STATUS_TOKENS or candidate in NAV_TOKENS:
                j -= 1
                continue
            if candidate.startswith("Win:") or candidate.startswith("Loss:"):
                break
            if re.match(r'^\d+$', candidate):  # table number
                break
            if p1_faction == "Unknown":
                p1_faction = candidate
                j -= 1
                continue
            p1_name = candidate
            break
        j -= 1

        if not p1_name:
            i += 1
            continue

        # Walk forward to find player 2 name, faction, result
        # Skip "View List" and blank tokens
        k = i + 1
        p2_name = None
        p2_faction = "Unknown"
        p2_result_text = None

        while k < len(lines):
            candidate = lines[k]
            if candidate in STATUS_TOKENS or candidate in NAV_TOKENS:
                k += 1
                continue
            if candidate.startswith("Win:") or candidate.startswith("Loss:"):
                p2_result_text = candidate
                break
            if re.match(r'^\d+$', candidate):  # next table number, bail
                break
            if p2_name is None:
                p2_name = candidate
                k += 1
                continue
            p2_faction = candidate
            k += 1

        if not p2_name or not p2_result_text:
            i += 1
            continue

        p1_clean = clean_player_name(p1_name)
        p2_clean = clean_player_name(p2_name)

        # Team filter
        if player_factions and (p1_clean not in player_factions or p2_clean not in player_factions):
            i = k + 1
            continue

        if p1_result_text.startswith("Win:"):
            result = "1"
        elif p1_result_text.startswith("Loss:"):
            result = "0"
        else:
            result = "0.5"

        match_data = {
            "event_num": event_num,
            "event_id": event_id,
            "round": round_num,
            "player1": p1_clean,
            "player2": p2_clean,
            "result": result,
        }
        if player_factions:
            match_data["player1_faction"] = player_factions.get(p1_clean, p1_faction)
            match_data["player2_faction"] = player_factions.get(p2_clean, p2_faction)

        results.append(match_data)
        i = k + 1

    return results


def scrape_all_rounds(event_id: str, event_num: int, num_rounds: int, team_name: Optional[str] = None, headless: bool = True, output_path: Optional[Path] = None, completed_rounds: Optional[set] = None) -> List[Dict[str, str]]:
    """Scrape all rounds from a BCP event, optionally filtering for team matches only."""
    all_results = []
    if completed_rounds is None:
        completed_rounds = set()
    
    with sync_playwright() as p:
        print(f"Launching browser...")
        browser = p.chromium.launch(headless=headless)
        
        # Set realistic browser context with proper user agent
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        
        try:
            # Load known players from ratings.json to catch misregistered team members
            known_players: Optional[set] = None
            ratings_path = Path("ratings.json")
            if ratings_path.exists():
                import json
                with open(ratings_path, encoding="utf-8") as f:
                    known_players = set(json.load(f).keys())

            # Get team roster and factions if filtering requested
            player_factions = None
            if team_name:
                player_factions = scrape_team_roster(event_id, team_name, page, known_players)
                if not player_factions:
                    print(f"\nWARNING: No players found for team '{team_name}'")
                    print("Proceeding without team filter...\n")
            
            # Determine CSV fieldnames upfront for checkpointing
            base_fields = ["event_num", "event_id", "round", "player1", "player2", "result"]
            fieldnames = base_fields + ["player1_faction", "player2_faction"] if player_factions else base_fields

            for round_num in range(1, num_rounds + 1):
                if round_num in completed_rounds:
                    print(f"\nRound {round_num}: already scraped, skipping (checkpoint)")
                    continue

                round_results = scrape_round(event_id, event_num, round_num, page, player_factions)
                all_results.extend(round_results)

                # Write this round immediately (checkpoint)
                if output_path is not None:
                    append_round_results(round_results, output_path, fieldnames)
                
                # Extra delay between rounds (except after the last one)
                if round_num < num_rounds:
                    delay = random.uniform(3.0, 5.0)
                    print(f"   Pausing {delay:.1f}s before next round...")
                    time.sleep(delay)
            
            print(f"\nTotal: {len(all_results)} matches across {num_rounds} rounds")
            
        finally:
            context.close()
            browser.close()
            print(f"Browser closed")
    
    return all_results


def save_results(results: List[Dict[str, str]], output_path: Path):
    """Save results to CSV."""
    if not results:
        return
    
    # Determine fieldnames based on what's in the results
    base_fields = ["event_num", "event_id", "round", "player1", "player2", "result"]
    has_factions = "player1_faction" in results[0]
    
    if has_factions:
        fieldnames = base_fields + ["player1_faction", "player2_faction"]
    else:
        fieldnames = base_fields
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved to {output_path}")


def load_completed_rounds(output_path: Path) -> set:
    """Return set of round numbers already written to the checkpoint CSV."""
    if not output_path.exists():
        return set()
    completed = set()
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                completed.add(int(row["round"]))
    except Exception:
        pass
    return completed


def append_round_results(results: List[Dict], output_path: Path, fieldnames: list):
    """Append a single round's results to the CSV (checkpointing)."""
    if not results:
        return
    file_exists = output_path.exists()
    with open(output_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(results)
    print(f"   Checkpoint saved to {output_path}")


def main():
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python bcp_all_rounds.py <event_id> <num_rounds> [team_name]")
        print("\nExamples:")
        print("  python bcp_all_rounds.py kxuw1i2Xdykm 3")
        print("  python bcp_all_rounds.py abc123xyz 5 'OTHER TEAM'")
        print("  python bcp_all_rounds.py abc123xyz 5 none  (scrape all matches)")
        print("\nThe scraper will automatically:")
        print("  - Assign the next event number")
        print("  - Clean player names")
        print("  - Filter for MORALE CHECK team matches only (default)")
        print("  - Save to data/events/event_XXX.csv")
        print("  - Update event registry")
        return
    
    event_id = sys.argv[1]
    num_rounds = int(sys.argv[2])
    team_name = sys.argv[3] if len(sys.argv) > 3 else "MORALE CHECK"
    
    # Allow explicit "none" to disable team filtering
    if team_name.lower() == "none":
        team_name = None
    
    # Initialize event manager and get event number
    manager = EventManager()
    event_num = manager.add_event(event_id, num_rounds)
    
    # Create events directory
    events_dir = Path("data/events")
    events_dir.mkdir(parents=True, exist_ok=True)
    
    output = events_dir / f"event_{event_num:03d}.csv"

    # Checkpointing: detect rounds already scraped
    completed_rounds = load_completed_rounds(output)
    if completed_rounds:
        print(f"   Checkpoint found: rounds {sorted(completed_rounds)} already in {output}")
        remaining = set(range(1, num_rounds + 1)) - completed_rounds
        if not remaining:
            print(f"   All {num_rounds} rounds already scraped. Nothing to do.")
            print(f"\nTo update Elo ratings with all events:")
            print(f"  python update_elo.py")
            return
        print(f"   Resuming from round {min(remaining)}...\n")
    
    print(f"\nScraping BCP Event #{event_num}")
    print(f"   BCP ID: {event_id}")
    print(f"   Rounds: {num_rounds}")
    if team_name:
        print(f"   Team Filter: {team_name}")
    print(f"   Output: {output}\n")
    
    results = scrape_all_rounds(
        event_id, event_num, num_rounds, team_name,
        output_path=output, completed_rounds=completed_rounds,
    )
    
    if results or completed_rounds:
        print(f"\nEvent #{event_num} scraped successfully!")
        print(f"\nTo update Elo ratings with all events:")
        print(f"  python update_elo.py")
    else:
        print(f"\nWARNING: No results found")


if __name__ == "__main__":
    main()
