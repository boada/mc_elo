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


def scrape_team_roster(event_id: str, team_name: str, page) -> Dict[str, str]:
    """Scrape team roster and factions from roster page, handling pagination."""
    # Use roster page instead of placings - clearer structure and team affiliations
    url = f"https://www.bestcoastpairings.com/event/{event_id}?active_tab=roster"
    print(f"\nFetching {team_name} roster: {url}")
    
    page.goto(url, wait_until="networkidle", timeout=30000)
    
    # Polite delay
    delay = random.uniform(2.0, 4.0)
    print(f"   Waiting {delay:.1f}s (polite scraping)...")
    time.sleep(delay)
    
    player_factions = {}
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
                                page.wait_for_load_state("networkidle", timeout=10000)
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
    if player_factions:
        for player in sorted(player_factions.keys()):
            print(f"      {player}: {player_factions[player]}")
    
    return player_factions


def scrape_round(event_id: str, event_num: int, round_num: int, page, player_factions: Optional[Dict[str, str]] = None) -> List[Dict[str, str]]:
    """Scrape a single round, optionally filtering by team and capturing factions. Handles pagination."""
    results = []
    
    url = f"https://www.bestcoastpairings.com/event/{event_id}?round={round_num}"
    print(f"\nRound {round_num}: {url}")
    
    page.goto(url, wait_until="networkidle", timeout=30000)
    
    # Polite delay - wait 2-4 seconds to simulate human browsing
    delay = random.uniform(2.0, 4.0)
    print(f"   Waiting {delay:.1f}s (polite scraping)...")
    time.sleep(delay)
    
    # Check if round exists
    page_text = page.inner_text('body')
    if "Placings are up to date" not in page_text and "Round" not in page_text:
        return []
    
    page_num = 1
    
    while True:
        # Parse matches on current page
        match_links = page.query_selector_all('a.css-1dgqwoj')
        
        if not match_links:
            if page_num == 1:
                print(f"   WARNING: No matches found")
            break
        
        current_page_matches = 0
        for match_link in match_links:
            try:
                paragraphs = match_link.query_selector_all('p')
                texts = [p.inner_text().strip() for p in paragraphs if p.inner_text().strip()]
                
                if len(texts) >= 7:
                    player1_name = clean_player_name(texts[1])
                    player1_result_text = texts[3]
                    player2_name = clean_player_name(texts[5])
                    
                    # If filtering by team, only include matches between team members
                    if player_factions and (player1_name not in player_factions or player2_name not in player_factions):
                        continue
                    
                    if "Win:" in player1_result_text:
                        result = "1"
                    elif "Loss:" in player1_result_text:
                        result = "0"
                    else:
                        result = "0.5"
                    
                    match_data = {
                        "event_num": event_num,
                        "event_id": event_id,
                        "round": round_num,
                        "player1": player1_name,
                        "player2": player2_name,
                        "result": result
                    }
                    
                    # Add faction data if available
                    if player_factions:
                        match_data["player1_faction"] = player_factions.get(player1_name, "Unknown")
                        match_data["player2_faction"] = player_factions.get(player2_name, "Unknown")
                    
                    results.append(match_data)
                    current_page_matches += 1
                    
            except Exception as e:
                continue
        
        if page_num == 1:
            print(f"   Page {page_num}: Extracted {current_page_matches} team matches")
        else:
            print(f"   Page {page_num}: Extracted {current_page_matches} team matches")
        
        # Check for next page
        try:
            page_text = page.inner_text('body')
            
            # Look for pagination info
            if " of " in page_text:
                import re
                match = re.search(r'(\d+)-(\d+) of (\d+)', page_text)
                if match:
                    current_end = int(match.group(2))
                    total = int(match.group(3))
                    
                    if current_end < total:
                        # Try to click next button
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
                            page.wait_for_load_state("networkidle", timeout=10000)
                            page_num += 1
                            
                            # Polite delay between pages
                            delay = random.uniform(1.5, 2.5)
                            time.sleep(delay)
                            continue
                        else:
                            break
                    else:
                        break
                else:
                    break
            else:
                break
        except Exception as e:
            break
    
    total_msg = f"   Total: {len(results)} team matches"
    if page_num > 1:
        total_msg += f" (across {page_num} pages)"
    print(total_msg)
    return results


def scrape_all_rounds(event_id: str, event_num: int, num_rounds: int, team_name: Optional[str] = None, headless: bool = True) -> List[Dict[str, str]]:
    """Scrape all rounds from a BCP event, optionally filtering for team matches only."""
    all_results = []
    
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
            # Get team roster and factions if filtering requested
            player_factions = None
            if team_name:
                player_factions = scrape_team_roster(event_id, team_name, page)
                if not player_factions:
                    print(f"\nWARNING: No players found for team '{team_name}'")
                    print("Proceeding without team filter...\n")
            
            for round_num in range(1, num_rounds + 1):
                round_results = scrape_round(event_id, event_num, round_num, page, player_factions)
                all_results.extend(round_results)
                
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
    
    print(f"\nScraping BCP Event #{event_num}")
    print(f"   BCP ID: {event_id}")
    print(f"   Rounds: {num_rounds}")
    if team_name:
        print(f"   Team Filter: {team_name}")
    print(f"   Output: {output}\n")
    
    results = scrape_all_rounds(event_id, event_num, num_rounds, team_name)
    
    if results:
        save_results(results, output)
        print(f"\nEvent #{event_num} scraped successfully!")
        print(f"\nTo update Elo ratings with all events:")
        print(f"  python update_elo.py")
    else:
        print(f"\nWARNING: No results found")


if __name__ == "__main__":
    main()
