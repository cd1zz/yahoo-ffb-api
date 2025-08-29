# Yahoo Fantasy Football API SDK

A lightweight Python SDK and service layer to interact programmatically with the Yahoo Fantasy Sports API, focusing on fantasy football. This SDK simplifies the complex OAuth2 flow and API calls by providing typed models, endpoint wrappers, and polling utilities for live draft data.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **OAuth2 Authentication**: Simplified 3-legged OAuth flow with automatic token refresh
- **Typed Models**: Pydantic models for all API responses with validation
- **Comprehensive API Coverage**: Users, leagues, teams, players, drafts, and more
- **Real-time Draft Monitoring**: Poll for live draft picks with callbacks
- **CLI Interface**: Command-line tools for common operations
- **Export Utilities**: Export data for integration with tools like Footballguys
- **Robust Error Handling**: Automatic retries with exponential backoff
- **Rate Limit Handling**: Built-in rate limiting and respectful API usage

## Quick Start

### Installation

```bash
pip install yahoo-ffb-api
```

### Setup

1. **Create Yahoo App**: Go to [Yahoo Developer Apps](https://developer.yahoo.com/apps/create/) and create a new app
2. **Configure Environment**: Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```
YAHOO_CLIENT_ID=your_client_id_here
YAHOO_CLIENT_SECRET=your_client_secret_here
YAHOO_REDIRECT_URI=http://127.0.0.1:8765/callback
YAHOO_SCOPE=fspt-r
```

3. **Authenticate**: Run the authentication flow:

```bash
yfa auth
```

This opens your browser for Yahoo login and saves the token locally.

### Basic Usage

```python
from yfa import YahooFantasyClient

# Initialize client (loads config from environment)
with YahooFantasyClient() as client:
    # Get your NFL leagues
    leagues_info = client.get_user_leagues("nfl")
    print(f"Found {leagues_info['total_leagues']} leagues")
    
    # Get league details
    league_key = leagues_info['leagues'][0]['league_key']
    summary = client.quick_league_summary(league_key)
    print(f"League: {summary['name']}")
    print(f"Teams: {summary['num_teams']}")
    print(f"Draft Status: {summary['draft_status']}")
    
    # Get draft results
    if summary['draft_complete']:
        draft_picks = client.drafts.get_draft_picks(league_key)
        print(f"Total picks: {len(draft_picks)}")
        
        # Show recent picks
        for pick in draft_picks[-5:]:
            print(f"Pick {pick.pick}: {pick.player_key} to {pick.team_key}")
```

## CLI Usage

The SDK includes a comprehensive CLI for common operations:

```bash
# List your leagues
yfa leagues --game-code nfl

# Get league information  
yfa league-info nfl.l.12345

# View league settings
yfa settings nfl.l.12345

# Watch draft picks in real-time
yfa draft-picks nfl.l.12345 --watch --interval 10

# Export complete draft results
yfa export-draft nfl.l.12345 --output draft_results.json

# List teams
yfa teams nfl.l.12345

# Get weekly scoreboard for specific week
yfa weekly-scoreboard nfl.l.12345 5 --detailed

# Comprehensive season analysis with skins games and survivor pool
yfa season-analysis nfl.l.12345 --start-week 1 --end-week 14 --export season_summary.json

# Analyze specific team's weekly performance
yfa team-performance nfl.l.12345 nfl.l.12345.t.1 --weeks "1-14"

# Victory margin analysis for skins games
yfa margin-analysis nfl.l.12345 --weeks "1-14" --min-margin 20.0
```

### Historical Data Access

Most CLI commands support the `--year` parameter for historical analysis. **Important**: League IDs change each season, so you must first discover the correct league keys for each year.

```bash
# Step 1: Find actual league IDs for the target year
yfa leagues --year 2024

# Step 2: Use the correct league ID from step 1
yfa weekly-scoreboard 449.l.123456 5 --year 2024

# Historical team performance with correct league IDs
yfa team-performance 449.l.123456 449.l.123456.t.1 --year 2024

# Compare seasons using actual league IDs
yfa season-analysis 449.l.123456 --year 2024 --export 2024_results.json
yfa season-analysis 461.l.789012 --year 2025 --export 2025_results.json
```

### Week-Specific Data Access

Commands that support both `--year` and `--week` parameters for precise historical queries:

```bash
# Get league info for specific week and year
yfa league-info 449.l.123456 --year 2024 --week 8

# View settings context for specific week  
yfa settings 414.l.234567 --year 2022 --week 12 --format json

# Historical team rosters for specific week
yfa teams 449.l.123456 --year 2024 --week 5

# Draft results with weekly context
yfa draft-picks 414.l.234567 --year 2022 --week 1
```

> **Developer Note**: Historical data support follows a consistent pattern using the `HistoricalContext` class. See `CLAUDE.md` for implementation guidelines when adding new commands.

> **Important**: League IDs are unique per season. A league that is `461.l.789012` in 2025 might be `449.l.123456` in 2024 and `414.l.234567` in 2022. Always use `yfa leagues --year XXXX` to find the correct league IDs for historical analysis.

## API Coverage

### Endpoints Supported

- **Users & Games**: Discover available games and leagues
- **Leagues**: Settings, standings, teams, transactions, **weekly scoreboards, season analysis**
- **Teams**: Roster management, stats, **detailed matchups, weekly performance tracking**
- **Players**: Search, stats, availability by league
- **Drafts**: Results, live monitoring, analysis

### Models Available

- **League**: Configuration, settings, scoring rules
- **Team**: Basic info, roster, standings
- **Player**: Details, stats, eligibility, ownership
- **Draft**: Picks, results, analysis
- **Scoring**: Categories, modifiers, calculations
- **Matchup**: Weekly team vs team results, margins, playoff status
- **WeeklyScoreboard**: Complete week results with all matchups
- **SeasonResults**: Full season tracking with analytics

## Advanced Usage

### Weekly Matchup Analysis

```python
from yfa import YahooFantasyClient
from yfa.analysis import WeeklyAnalyzer

with YahooFantasyClient() as client:
    # Get detailed weekly scoreboard
    scoreboard = client.leagues.get_weekly_scoreboard("nfl.l.12345", week=5)
    
    # Find highest scoring team
    highest_scorer = scoreboard.get_highest_score()
    print(f"Week 5 high score: {highest_scorer.team_name} ({highest_scorer.points})")
    
    # Get skins-eligible matchups (20+ point margins)
    skins_matchups = scoreboard.get_matchups_by_margin(20.0)
    for matchup in skins_matchups:
        winner = matchup.get_winning_team()
        print(f"Skins eligible: {winner.team_name} by {matchup.margin_of_victory} points")

### Season-Long Analysis

```python
# Get complete season results
season_results = client.leagues.get_season_results("nfl.l.12345", 1, 14)

# Initialize analyzer for advanced metrics
analyzer = WeeklyAnalyzer(min_skins_margin=20.0)

# Calculate skins game winners with rolling pot
skins_winners = analyzer.calculate_skins_winners(season_results, weekly_pot=10.0)
print("Skins Winners:", skins_winners)

# Calculate survivor pool results
survivor_results = analyzer.calculate_survivor_results(season_results)
print(f"Survivor Winner: {survivor_results['winner']}")

# Generate power rankings based on recent performance
power_rankings = analyzer.calculate_power_rankings(season_results)
for i, team in enumerate(power_rankings[:3], 1):
    print(f"#{i}: {team['team_name']} (Power Rating: {team['power_rating']})")

### Team Performance Tracking

```python
# Get specific team's weekly performance
performance = client.leagues.get_team_weekly_performance(
    "nfl.l.12345", 
    "nfl.l.12345.t.1",
    weeks=range(1, 15)
)

for week_data in performance:
    result = "W" if week_data["margin"] > 0 else "L" if week_data["margin"] < 0 else "T"
    print(f"Week {week_data['week']}: {week_data['team_points']:.1f} vs "
          f"{week_data['opponent_name']} {week_data['opponent_points']:.1f} ({result})")

# Get team's complete season record
record = client.teams.get_team_season_record("nfl.l.12345.t.1")
print(f"Record: {record['wins']}-{record['losses']}-{record['ties']}")
print(f"Avg Points: {record['average_points']:.1f}")

### Victory Margin Analysis

```python
# Calculate all victory margins for the season
margins = client.leagues.calculate_league_margins("nfl.l.12345", range(1, 15))

# Find biggest blowouts
biggest_margins = sorted(margins, key=lambda x: x["margin"], reverse=True)[:5]
for margin_data in biggest_margins:
    print(f"Week {margin_data['week']}: {margin_data['winner_team']} "
          f"beat {margin_data['loser_team']} by {margin_data['margin']:.1f}")

# Export comprehensive season analysis
analyzer = WeeklyAnalyzer()
summary = analyzer.export_season_summary(season_results, "season_analysis.json")
print(f"Season analysis exported with {len(summary['team_records'])} teams")
```

### Real-time Draft Monitoring

```python
def on_new_pick(pick):
    print(f"NEW PICK: Round {pick.round}, Pick {pick.pick}")
    print(f"Player: {pick.player_key}")
    print(f"Team: {pick.team_key}")

# Watch draft with custom callback
client.drafts.watch_draft_picks(
    league_key="nfl.l.12345",
    callback=on_new_pick,
    poll_interval=10
)
```

### Exporting Data

```python
# Export league settings for Footballguys integration
from yfa.transforms.footballguys import create_fbg_league_export

league_settings = client.leagues.get_league_settings("nfl.l.12345")
fbg_export = create_fbg_league_export(league_settings)

print("Footballguys Compatible Settings:")
print(f"Scoring: {fbg_export['scoring_settings']}")
print(f"Roster: {fbg_export['roster_settings']}")
```

### Custom HTTP Configuration  

```python
from yfa import Settings, YahooFantasyClient

# Custom settings
settings = Settings(
    client_id="your_client_id",
    client_secret="your_client_secret",
    token_path="./custom_tokens.json",
    user_agent="MyApp/1.0"
)

client = YahooFantasyClient(settings)
```

## Integration with Footballguys

The SDK includes transform utilities for integrating with Footballguys Draft Dominator:

```python
from yfa.transforms.footballguys import (
    to_fbg_scoring_format,
    to_fbg_roster_format, 
    create_fbg_player_export
)

# Convert league settings
settings = client.leagues.get_league_settings(league_key)
fbg_scoring = to_fbg_scoring_format(settings)
fbg_roster = to_fbg_roster_format(settings)

# Export player pool
available_players = client.players.get_available_players(league_key)
fbg_players = create_fbg_player_export(available_players)
```

## Error Handling

The SDK includes robust error handling with automatic retries:

```python
from yfa.exceptions import YahooAPIError
import httpx

try:
    league = client.leagues.get_league("invalid.key")
except httpx.HTTPStatusError as e:
    if e.response.status_code == 404:
        print("League not found")
    elif e.response.status_code == 403:
        print("Access denied - check permissions")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/CraigFreyman/yahoo-ffb-api.git
cd yahoo-ffb-api

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check yfa/
mypy yfa/

# Format code
black yfa/
```

### Testing

The SDK includes comprehensive tests with VCR.py for recording HTTP interactions:

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m "not integration"  # Skip integration tests
pytest -m auth  # Only auth tests

# Run with coverage
pytest --cov=yfa --cov-report=html
```

## Documentation

- [Yahoo Fantasy Sports API Guide](https://developer.yahoo.com/fantasysports/guide/)
- [API Reference Documentation](https://developer.yahoo.com/fantasysports/guide/index.html)
- [OAuth2 Setup Guide](https://wernull.com/2016/01/getting-started-with-the-yahoo-fantasy-sports-api/)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run tests and linting (`pytest && ruff check`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## Support

- **Issues**: [GitHub Issues](https://github.com/CraigFreyman/yahoo-ffb-api/issues)
- **Documentation**: [GitHub Wiki](https://github.com/CraigFreyman/yahoo-ffb-api/wiki)
- **Discussions**: [GitHub Discussions](https://github.com/CraigFreyman/yahoo-ffb-api/discussions)

## Roadmap

- [ ] **Write Operations**: Add/drop players, trades, waivers
- [ ] **Streaming Support**: WebSocket or SSE for real-time updates
- [ ] **Multi-Sport Support**: Extend beyond NFL to NBA, MLB, NHL
- [ ] **Advanced Analytics**: Built-in statistical analysis tools
- [ ] **GUI Interface**: Web-based dashboard for league management
- [ ] **Plugin System**: Extensible architecture for custom integrations

## Changelog

### v0.1.0 (Initial Release)
- OAuth2 authentication with automatic refresh
- Complete read-only API coverage
- CLI interface with all major commands
- Pydantic models for type safety
- Real-time draft monitoring
- Footballguys integration utilities
- Comprehensive test suite
