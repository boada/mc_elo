# Copilot Instructions for MORALE CHECK Elo Tracker

## Project Overview
This is an Elo rating tracker for MORALE CHECK, a local Warhammer 40k gaming club. It scrapes match results from Best Coast Pairings (BCP) and calculates player rankings using the Elo rating system.

## Key Technologies
- **Python 3.8+**: Main language
- **Playwright**: Browser automation for scraping JavaScript-rendered BCP pages
- **CSV**: Data storage format
- **JSON**: Event metadata and ratings storage

## Project Architecture

### Core Files
1. **bcp_all_rounds.py**: Main web scraper
   - Scrapes BCP event pages using Playwright
   - Extracts team roster and factions from placings page
   - Filters matches to only include team members
   - Implements polite scraping (2-5 second delays)
   - Outputs: `data/events/event_XXX.csv`

2. **event_manager.py**: Event metadata tracking
   - Automatically assigns sequential event numbers
   - Stores metadata in `data/events.json`
   - Tracks: event_num, event_id, num_rounds, scraped_date, csv_file

3. **elo_updater.py**: Core Elo calculation engine
   - K-factor: 32
   - Default rating: 1500
   - Standard Elo formula implementation
   - Reads any CSV with player1/player2/result columns

4. **update_elo.py**: Orchestration script
   - Combines all event CSVs into `data/all_events.csv`
   - Deletes old ratings.json to prevent ghost players
   - Runs elo_updater.py on combined data
   - Outputs: `ratings.json`

5. **show_rankings.py**: Display utility
   - Formats current rankings as markdown table
   - Displays win-loss records (W-L or W-D-L format)
   - Dynamic column widths based on longest player name
   - Discord-ready output

6. **name_cleaner.py**: Name normalization utilities
   - Title Case conversion
   - Removes parentheticals: "caelan (rolling ones) Fulkerson" → "Caelan Fulkerson"
   - Special handling for "Mc" and "O'" prefixes

### Data Flow
```
BCP Event → bcp_all_rounds.py → data/events/event_XXX.csv
                                         ↓
                                  update_elo.py
                                         ↓
                        data/all_events.csv + ratings.json
                                         ↓
                                  show_rankings.py
```

### CSV Schema
**Standard columns (always present):**
- `event_num`: int, sequential event number
- `event_id`: str, BCP event ID (e.g., "kxuw1i2Xdykm")
- `round`: int, round number
- `player1`: str, cleaned player name
- `player2`: str, cleaned player name
- `result`: float, 1=player1 win, 0=player1 loss, 0.5=draw

**Optional columns (when team filter used):**
- `player1_faction`: str, army/faction used (e.g., "Blood Angels")
- `player2_faction`: str, army/faction used

## BCP Scraping Details

### URL Patterns
- **Main placings**: `https://www.bestcoastpairings.com/event/{event_id}?active_tab=placings`
  - Shows team affiliations and factions
  - Pattern: "Player Name - TEAM NAME" (line N), empty line, "Faction" (line N+2)
  
- **Round pairings**: `https://www.bestcoastpairings.com/event/{event_id}?round={round_num}`
  - Shows match results
  - CSS selector: `a.css-1dgqwoj` for match cards
  - Result text: "Win: XX" or "Loss: XX"

### Scraping Best Practices
- **Polite scraping**: 2-4 second delays per page, 3-5 seconds between rounds
- **Realistic browser**: Chromium with proper user agent
- **Network idle**: Wait for `networkidle` state before parsing
- **Team filtering**: Only track matches where BOTH players are on team roster

## Coding Conventions

### Style Requirements
- **No emojis**: User preference - use text instead (e.g., "WARNING:" not "⚠️")
- **Simple output**: Clean, professional terminal output
- **Markdown for sharing**: Use markdown tables for Discord/sharing

### Name Cleaning Rules
1. Remove anything in parentheses: `\s*\([^)]*\)`
2. Collapse whitespace
3. Title Case with exceptions:
   - "Mc" prefix: McDonald → McDonald (not Mcdonald)
   - "O'" prefix: O'Brien → O'Brien (not O'brien)

### File Naming
- Event CSVs: `event_001.csv`, `event_002.csv` (zero-padded, 3 digits)
- Always use absolute paths in code
- Data directory structure:
  ```
  data/
  ├── events/
  │   ├── event_001.csv
  │   └── event_002.csv
  ├── events.json
  └── all_events.csv
  ```

## Common Workflows

### Scraping a New Event
```bash
python bcp_all_rounds.py <event_id> <num_rounds>
```
- MORALE CHECK team filtering is the default
- Automatically assigns next event number
- Fetches roster and factions
- Filters for team matches only
- Saves to `data/events/event_XXX.csv`
- Use `none` as third argument to disable filtering
- Use a different team name as third argument for other teams

### Updating Rankings
```bash
python update_elo.py
```
- Combines all event CSVs
- Recalculates all ratings from scratch
- Updates `ratings.json`

### Displaying Rankings
```bash
python show_rankings.py
```
- Shows markdown table for Discord

## Important Context

### Team Information
- **Team name**: "MORALE CHECK"
- **Game**: Warhammer 40k
- **Platform**: Best Coast Pairings (BCP)
- **Use case**: Track internal team Elo across events (both team-only and mixed tournaments)

### Why Team Filtering Matters
At larger tournaments, MORALE CHECK players might face non-team opponents. Team filtering ensures only intra-team matches affect the rankings. Example: If Mason plays Kevin (both MORALE CHECK) in round 3, that match counts. If Mason plays an external player in round 1, that match is ignored.

### Elo System Details
- **K-factor 32**: Standard for club-level play
- **Starting rating 1500**: Chess convention
- **Expected score formula**: E = 1 / (1 + 10^((opponent_rating - player_rating) / 400))
- **Rating update**: new_rating = old_rating + K * (actual_score - expected_score)

## Future Enhancement Ideas
- Faction-specific Elo (track ratings per army)
- Matchup analysis (faction vs faction win rates)
- Web dashboard (Flask/FastAPI + React)
- Player statistics (streaks, most played factions)
- Head-to-head records
- Rating history over time
- Graph visualizations

## Troubleshooting

### Common Issues
1. **"No players found for team"**: BCP page structure changed or wrong team name
2. **"No matches found"**: Round number too high or CSS selector changed
3. **Duplicate player names in ratings**: Old ratings.json needs to be deleted and recalculated

### Debugging Tools
- Use `headless=False` in Playwright to see browser
- Check BCP page source if selectors stop working
- Verify name cleaning with `name_cleaner.py`

## Development Guidelines
- Test with real BCP events before committing
- Verify Elo calculations match expected results
- Don't break CSV format (other scripts depend on it)
- Keep scraping polite (respect BCP servers)
- Maintain clean commit history
- Update requirements.txt if adding dependencies
