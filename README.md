# MORALE CHECK Elo Tracker

Track Elo ratings for your local gaming club using automated web scraping from Best Coast Pairings (BCP).

## Features

- **Automated Event Scraping**: Extract match results from BCP events with a single command
- **Team Filtering**: Track only matches between your team members at larger tournaments
- **Faction Tracking**: Capture which army/faction each player used in each match
- **Automatic Event Management**: Sequential event numbering and metadata tracking
- **Clean Name Handling**: Automatic name normalization and cleaning
- **Polite Scraping**: Built-in delays and realistic browser fingerprinting
- **Elo Calculations**: Standard Elo rating system (K-factor 32, default 1500)
- **Pretty Rankings**: Generate Discord-ready markdown tables

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/boada/mc_elo.git
   cd mc_elo
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

## Usage

### Scrape an Event

```bash
# MORALE CHECK team filter (default)
python bcp_all_rounds.py <event_id> <num_rounds>

# Different team name
python bcp_all_rounds.py <event_id> <num_rounds> "OTHER TEAM"

# No team filter (all matches)
python bcp_all_rounds.py <event_id> <num_rounds> none
```

**Example:**
```bash
python bcp_all_rounds.py kxuw1i2Xdykm 3
```

The scraper will:
- Automatically assign the next event number
- Fetch team roster and factions from BCP
- Extract all rounds with match results
- Filter for MORALE CHECK team-only matches (default)
- Save to `data/events/event_XXX.csv`

### Update Elo Rankings

```bash
python update_elo.py
```

This combines all event CSVs and recalculates current Elo ratings from scratch.
Note: Deletes existing `ratings.json` to prevent ghost players from filtered events.

### View Rankings

```bash
python show_rankings.py
```

Generates a markdown-formatted table with:
- Player rankings by Elo rating
- Win-loss records (W-L or W-D-L if draws exist)
- Dynamic column widths for clean display
- Ready to paste into Discord or other platforms

## Project Structure

```
mc_elo/
├── bcp_all_rounds.py      # Main web scraper
├── event_manager.py       # Event metadata tracking
├── elo_updater.py         # Elo calculation engine
├── update_elo.py          # Combine events and update ratings
├── show_rankings.py       # Display formatted rankings
├── name_cleaner.py        # Name normalization utilities
├── requirements.txt       # Python dependencies
├── data/
│   ├── events/           # Individual event CSVs
│   │   ├── event_001.csv
│   │   └── event_002.csv
│   ├── events.json       # Event metadata registry
│   └── all_events.csv    # Combined match history
└── ratings.json          # Current Elo ratings
```

## Data Format

### Event CSV Columns

- `event_num`: Sequential event number
- `event_id`: BCP event ID
- `round`: Round number
- `player1`: First player name (cleaned)
- `player2`: Second player name (cleaned)
- `result`: Match result (1 = player1 win, 0 = player1 loss, 0.5 = draw)
- `player1_faction`: Army/faction player1 used (if team filter enabled)
- `player2_faction`: Army/faction player2 used (if team filter enabled)

## How It Works

1. **Team Roster Extraction**: Scrapes the main placings page to get team roster and faction data
2. **Match Scraping**: Iterates through each round using the `?round=N` parameter
3. **Name Cleaning**: Normalizes names (Title Case, removes parentheticals)
4. **Team Filtering**: Only includes matches where both players are on the team
5. **Elo Calculation**: Standard Elo formula with K=32, starting rating=1500

## Best Practices

- **Polite Scraping**: The scraper includes 2-5 second delays between requests
- **Team Filtering**: Use team names to avoid polluting rankings with external matches
- **Sequential Events**: Events are numbered automatically to maintain chronological order
- **Backup Data**: The `data/` directory contains all match history

## Future Enhancements

- Faction-specific Elo ratings
- Matchup win rate analysis
- Player statistics and trends
- Web dashboard/UI
- Head-to-head records

## Requirements

- Python 3.8+
- Playwright (for web scraping)
- Access to BCP event pages

## License

MIT

## Credits

Built for the MORALE CHECK gaming club.
