# Contributing to MORALE CHECK Elo Tracker

Thanks for your interest in contributing! Here are some guidelines.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/mc_elo.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Install dependencies: `pip install -r requirements.txt && playwright install chromium`

## Code Style

- Follow PEP 8 for Python code
- Use meaningful variable names
- Add docstrings to functions
- Keep functions focused and single-purpose
- No emojis in code output

## Testing Changes

Before submitting:
1. Test scraping with a real BCP event
2. Verify Elo calculations are correct
3. Check that rankings display properly
4. Ensure no breaking changes to data format

## Submitting Changes

1. Commit your changes: `git commit -am "Add feature: description"`
2. Push to your fork: `git push origin feature/your-feature-name`
3. Open a Pull Request with a clear description

## Areas for Contribution

- **Faction Elo**: Calculate separate ratings per faction
- **Statistics**: Win rates, matchup analysis, player trends
- **Web UI**: Flask/FastAPI dashboard
- **Data Viz**: Charts and graphs for rankings over time
- **Testing**: Unit tests for core functionality
- **Documentation**: Examples, tutorials, tips

## Questions?

Open an issue or reach out to the maintainers.
