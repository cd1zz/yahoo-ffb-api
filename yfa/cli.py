"""
Command-line interface for Yahoo Fantasy Sports API SDK.
"""

import json
from typing import Optional
from functools import wraps

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .client import YahooFantasyClient
from .config import Settings

app = typer.Typer(
    name="yfa",
    help="Yahoo Fantasy Sports API SDK - Command Line Interface",
    no_args_is_help=True,
)
console = Console()


class HistoricalContext:
    """Helper class to manage year/week context for CLI commands."""
    
    @staticmethod
    def apply_transformations(league_key: str, year: Optional[int] = None, team_key: Optional[str] = None) -> tuple[str, Optional[str]]:
        """Apply year transformations to league and team keys."""
        # Note: This method is deprecated in favor of get_league_key_for_year
        # which provides better user experience with automatic league discovery
        
        if year is not None:
            console.print(f"[yellow]Note: For better experience, use league discovery instead of manual league keys[/yellow]")
            console.print(f"[yellow]Tip: Use 'yfa leagues --year {year}' to find correct league IDs[/yellow]")
        
        return league_key, team_key
    
    @staticmethod
    def build_context_string(year: Optional[int] = None, week: Optional[int] = None) -> str:
        """Build context string for display messages."""
        context_info = []
        if year is not None:
            context_info.append(f"Year: {year}")
        if week is not None:
            context_info.append(f"Week: {week}")
        return f" ({', '.join(context_info)})" if context_info else ""
    
    @staticmethod
    def display_fetching_message(entity_name: str, display_name: str, year: Optional[int] = None, week: Optional[int] = None) -> None:
        """Display standardized fetching message with context."""
        context_str = HistoricalContext.build_context_string(year, week)
        console.print(f"[yellow]Fetching {entity_name} for {display_name}{context_str}...[/yellow]")
    
    @staticmethod
    def handle_historical_error(e: Exception, year: Optional[int] = None, entity_type: str = "data") -> None:
        """Handle common errors when accessing historical data."""
        if "403" in str(e) or "Forbidden" in str(e):
            console.print(f"[red]Access denied to {entity_type}[/red]")
            if year:
                console.print(f"[yellow]League IDs change each season. The {entity_type} might have a different ID in {year}.[/yellow]")
                console.print(f"[dim]Use 'yfa leagues --year {year}' to find the correct league ID for {year}[/dim]")
            else:
                console.print(f"[dim]Try without --year parameter to check current season[/dim]")
        elif "404" in str(e) or "Not Found" in str(e):
            console.print(f"[red]{entity_type.capitalize()} not found[/red]")
            if year:
                console.print(f"[yellow]League IDs are unique per season. Use 'yfa leagues --year {year}' to find the correct league ID.[/yellow]")
        else:
            console.print(f"[red]Error accessing {entity_type}: {e}[/red]")
        raise typer.Exit(1)


def discover_user_leagues(client: YahooFantasyClient, year: int) -> list[dict]:
    """Discover user's leagues for a specific year."""
    try:
        # Get user's league keys for the year (NFL only)
        league_keys = client.users.get_user_leagues(["nfl"], year)
        
        # Get detailed info for each league
        leagues = []
        for league_key in league_keys:
            try:
                league = client.leagues.get_league(league_key)
                leagues.append({
                    'league_key': league.league_key,
                    'league_name': league.name,
                    'num_teams': league.num_teams,
                    'draft_status': league.draft_status
                })
            except Exception as e:
                console.print(f"[yellow]Warning: Could not get details for league {league_key}: {e}[/yellow]")
                continue
        
        return leagues
    except Exception as e:
        console.print(f"[yellow]Warning: Could not discover leagues for {year}: {e}[/yellow]")
        return []


def prompt_league_selection(leagues: list[dict]) -> str:
    """Prompt user to select from discovered leagues."""
    if not leagues:
        return None
        
    if len(leagues) == 1:
        # Auto-select if only one league
        league = leagues[0]
        console.print(f"[green]Auto-selected league: {league['league_name']} ({league['league_key']})[/green]")
        return league['league_key']
    
    # Multiple leagues - prompt for selection
    console.print(f"\n[bold]Found {len(leagues)} leagues:[/bold]")
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("#", style="dim", width=3)
    table.add_column("League Name", style="cyan")
    table.add_column("Teams", justify="center")
    table.add_column("Status")
    
    for i, league in enumerate(leagues, 1):
        table.add_row(
            str(i),
            league['league_name'],
            str(league['num_teams']),
            league['draft_status']
        )
    
    console.print(table)
    
    while True:
        try:
            choice = typer.prompt("\nSelect league number (1-{})".format(len(leagues)))
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(leagues):
                selected = leagues[choice_idx]
                console.print(f"[green]Selected: {selected['league_name']}[/green]")
                return selected['league_key']
            else:
                console.print("[red]Invalid selection. Please try again.[/red]")
        except (ValueError, typer.Abort):
            console.print("[red]Invalid input. Please try again.[/red]")


def get_league_key_for_year(client: YahooFantasyClient, year: int, league_key: str = None) -> str:
    """Get appropriate league key for the specified year."""
    if league_key:
        # Validate provided league key matches the year
        parts = league_key.split(".")
        if len(parts) >= 3:
            current_game_id = parts[0]
            year_to_game_id = {
                2025: "461", 2024: "449", 2023: "423", 2022: "414",
                2021: "406", 2020: "399", 2019: "390", 2018: "380"
            }
            expected_game_id = year_to_game_id.get(year)
            if expected_game_id and current_game_id != expected_game_id:
                console.print(f"[yellow]⚠️  League ID mismatch: {league_key} doesn't match {year}[/yellow]")
                console.print(f"[yellow]   Discovering correct leagues for {year}...[/yellow]")
                league_key = None  # Force discovery
    
    if not league_key:
        # Auto-discover leagues for the year
        leagues = discover_user_leagues(client, year)
        if not leagues:
            console.print(f"[red]No leagues found for {year}. Use 'yfa leagues --year {year}' to check available leagues.[/red]")
            raise typer.Exit(1)
        league_key = prompt_league_selection(leagues)
        if not league_key:
            raise typer.Exit(1)
    
    return league_key


def get_client() -> YahooFantasyClient:
    """Get configured client instance."""
    try:
        settings = Settings()
        return YahooFantasyClient(settings)
    except Exception as e:
        console.print(f"[red]Error creating client: {e}[/red]")
        raise typer.Exit(1)


def get_league_display_name(client: YahooFantasyClient, league_key: str) -> str:
    """Get league display name for status messages."""
    try:
        league = client.leagues.get_league(league_key)
        return f"{league.name} ({league_key})"
    except Exception:
        # Fallback to just the key if we can't get the name
        return league_key


@app.command()
def auth() -> None:
    """
    Authenticate with Yahoo Fantasy Sports API.
    Opens browser for OAuth2 consent and saves token locally.
    """

    console.print(
        "[yellow]Starting Yahoo Fantasy Sports API authentication...[/yellow]"
    )

    try:
        client = get_client()
        token = client.authenticate()

        console.print("[green]✓ Authentication successful![/green]")
        console.print(f"Token saved to: {client.settings.token_path}")
        console.print(f"Token expires at: {token.expires_at}")

    except Exception as e:
        console.print(f"[red]Authentication failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def verify() -> None:
    """Verify authentication and API access."""
    
    console.print("[yellow]Verifying authentication...[/yellow]")
    
    try:
        with get_client() as client:
            # Access the token property to trigger loading
            try:
                token = client.token
                if not token:
                    console.print("[red]✗ No authentication token found[/red]")
                    console.print("[yellow]Run 'yfa auth' to authenticate[/yellow]")
                    raise typer.Exit(1)
            except Exception as token_error:
                console.print(f"[red]✗ Failed to load token: {token_error}[/red]")
                console.print("[yellow]Run 'yfa auth' to authenticate[/yellow]")
                raise typer.Exit(1)
            
            # Try a simple API call to verify auth
            try:
                response = client.http.get("users;use_login=1")
                
                if response and response.get("fantasy_content", {}).get("users"):
                    console.print("[green]✓ Authentication successful![/green]")
                    
                    # Try to get user info
                    users_dict = response["fantasy_content"]["users"]
                    if "0" in users_dict:
                        user_array = users_dict["0"].get("user", [])
                        if len(user_array) > 0:
                            user_guid = user_array[0].get("guid", "Unknown")
                    
                else:
                    console.print("[red]✗ Authentication failed - Invalid response format[/red]")
                    raise typer.Exit(1)
                    
            except Exception as api_error:
                console.print(f"[red]✗ API call failed: {api_error}[/red]")
                console.print("[yellow]Your token may be expired. Try 'yfa auth' to re-authenticate[/yellow]")
                raise typer.Exit(1)
                
    except Exception as e:
        console.print(f"[red]✗ Client creation failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def leagues(
    game_code: str = typer.Option("nfl", help="Game code (nfl, nba, mlb, nhl)"),
    year: Optional[int] = typer.Option(None, help="Season year (defaults to current NFL season)"),
) -> None:
    """List your fantasy leagues for a specific game."""

    # Default to current NFL season (starts in previous calendar year)
    if year is None:
        import datetime
        current_year = datetime.datetime.now().year
        # NFL season runs Aug-Feb, so if we're before August, use previous year
        if datetime.datetime.now().month < 8:
            year = current_year - 1
        else:
            year = current_year

    console.print(f"[yellow]Fetching {game_code.upper()} leagues for {year} season...[/yellow]")

    try:
        with get_client() as client:
            leagues_info = client.get_user_leagues(game_code, year)

            if not leagues_info["leagues"]:
                console.print(f"[yellow]No {game_code.upper()} leagues found for {year} season.[/yellow]")
                console.print(f"[dim]Try a different year with: yfa leagues --year 2024[/dim]")
                return

            # Create table
            table = Table(title=f"{game_code.upper()} Fantasy Leagues ({year} Season)")
            table.add_column("League Key", style="cyan")
            table.add_column("Name", style="white")
            table.add_column("Teams", justify="center")
            table.add_column("Draft Status", justify="center")

            for league in leagues_info["leagues"]:
                table.add_row(
                    league["league_key"],
                    league["name"],
                    str(league["num_teams"]),
                    league["draft_status"] or "Unknown",
                )

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error fetching leagues: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def league_info(
    league_key: str = typer.Argument(help="League key (e.g., nfl.l.12345)"),
    year: Optional[int] = typer.Option(None, "--year", help="Season year (defaults to current season)"),
    week: Optional[int] = typer.Option(None, "--week", help="Specific week number for week-specific data")
) -> None:
    """Get detailed information about a league."""

    try:
        # Apply historical transformations
        league_key, _ = HistoricalContext.apply_transformations(league_key, year)
        
        with get_client() as client:
            league_display_name = get_league_display_name(client, league_key)
            HistoricalContext.display_fetching_message("league information", league_display_name, year, week)
            
            summary = client.quick_league_summary(league_key)

            # Create info panel
            info_text = f"""
[cyan]League:[/cyan] {summary['name']}
[cyan]Key:[/cyan] {summary['league_key']}
[cyan]Teams:[/cyan] {summary['num_teams']}
[cyan]Scoring:[/cyan] {summary['scoring_type'] or 'Unknown'}
[cyan]Season:[/cyan] {summary['season'] or 'Unknown'}
[cyan]Draft Status:[/cyan] {summary['draft_status']}
[cyan]Roster Positions:[/cyan] {summary['roster_positions']}
            """.strip()

            if summary["draft_complete"]:
                info_text += (
                    f"\n[cyan]Draft Picks:[/cyan] {summary['total_draft_picks']}"
                )

            panel = Panel(info_text, title="League Information", border_style="blue")
            console.print(panel)

    except Exception as e:
        console.print(f"[red]Error fetching league info: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def settings(
    league_key: str = typer.Argument(help="League key (e.g., nfl.l.12345)"),
    format: str = typer.Option("table", help="Output format (table, json)"),
    year: Optional[int] = typer.Option(None, "--year", help="Season year (defaults to current season)"),
    week: Optional[int] = typer.Option(None, "--week", help="Specific week number for week-specific data")
) -> None:
    """Get league settings including scoring and roster configuration."""

    try:
        # Apply historical transformations
        league_key, _ = HistoricalContext.apply_transformations(league_key, year)
            
        with get_client() as client:
            league_display_name = get_league_display_name(client, league_key)
            HistoricalContext.display_fetching_message("league settings", league_display_name, year, week)
            
            league_settings = client.leagues.get_league_settings(league_key)

            if format == "json":
                print(league_settings.model_dump_json(indent=2))
                return

            # Display roster positions
            roster_table = Table(title="Roster Positions")
            roster_table.add_column("Position", style="cyan")
            roster_table.add_column("Count", justify="center")
            roster_table.add_column("Starting", justify="center")

            for pos in league_settings.roster_positions:
                roster_table.add_row(
                    pos.position,
                    str(pos.count),
                    "✓" if pos.is_starting_position else "✗",
                )

            console.print(roster_table)

            # Display scoring modifiers if available
            if league_settings.stat_modifiers:
                scoring_table = Table(title="Scoring Settings")
                scoring_table.add_column("Stat ID", style="cyan")
                scoring_table.add_column("Points", justify="right")

                for modifier in league_settings.stat_modifiers[:10]:  # Show first 10
                    scoring_table.add_row(
                        str(modifier.stat_id), f"{modifier.value:+.2f}"
                    )

                if len(league_settings.stat_modifiers) > 10:
                    scoring_table.add_row(
                        "...", f"({len(league_settings.stat_modifiers) - 10} more)"
                    )

                console.print(scoring_table)

    except Exception as e:
        console.print(f"[red]Error fetching league settings: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def draft_picks(
    league_key: Optional[str] = typer.Option(None, "--league", "-l", help="League key (will auto-discover if not provided)"),
    watch: bool = typer.Option(
        False, "--watch", help="Watch for new picks in real-time"
    ),
    interval: int = typer.Option(10, "--interval", help="Polling interval in seconds"),
    recent: int = typer.Option(0, "--recent", help="Show only N most recent picks"),
    year: Optional[int] = typer.Option(None, "--year", help="Season year (defaults to current season)"),
    week: Optional[int] = typer.Option(None, "--week", help="Specific week number for week-specific data"),
    keys: bool = typer.Option(False, "--keys", help="Show raw player keys instead of names (faster)")
) -> None:
    """Get draft picks for a league."""

    try:
        # Determine the year to use
        if year is None:
            import datetime
            current_year = datetime.datetime.now().year
            # NFL season runs Aug-Feb, so if we're before August, use previous year
            if datetime.datetime.now().month < 8:
                year = current_year - 1
            else:
                year = current_year
        
        console.print(f"[dim]Analyzing {year} season data...[/dim]")
            
        with get_client() as client:
            # Get the appropriate league key for this year
            league_key = get_league_key_for_year(client, year, league_key)
            
            league_display_name = get_league_display_name(client, league_key)
            context_str = HistoricalContext.build_context_string(year, week)
            
            if watch:
                console.print(
                    f"[yellow]Watching draft picks for {league_display_name}{context_str} (polling every {interval}s)...[/yellow]"
                )
                console.print("[dim]Press Ctrl+C to stop watching[/dim]")

                def print_pick(pick):
                    # Check if this pick has been made (has a player)
                    has_player = (hasattr(pick, 'player_key') and pick.player_key) or \
                               (hasattr(pick, 'player_name') and pick.player_name)
                    
                    if has_player:
                        # Check if we should show names or keys
                        if not keys and hasattr(pick, 'player_name') and pick.player_name:
                            player_display = f"{pick.player_name}"
                            if hasattr(pick, 'player_position') and pick.player_position:
                                player_display += f" ({pick.player_position}"
                                if hasattr(pick, 'player_team') and pick.player_team:
                                    player_display += f", {pick.player_team}"
                                player_display += ")"
                        else:
                            player_display = pick.player_key
                    else:
                        # This is an unmade pick - show as waiting
                        player_display = "[Waiting for pick]"
                    
                    # Get team name if available
                    if not keys and hasattr(pick, 'team_name') and pick.team_name:
                        team_display = pick.team_name
                    else:
                        team_display = pick.team_key
                    
                    # Check if this is a new pick or initial display
                    is_new_pick = hasattr(pick, '_is_initial_display') and not pick._is_initial_display
                    
                    # Add NEW indicator for actual new picks during watching
                    if is_new_pick and has_player:
                        console.print(
                            f"[green]🆕 NEW: Round {pick.round}, Pick {pick.pick}[/green]: "
                            f"[cyan]{player_display}[/cyan] -> [blue]{team_display}[/blue]"
                        )
                    else:
                        console.print(
                            f"[green]Round {pick.round}, Pick {pick.pick}[/green]: "
                            f"[cyan]{player_display}[/cyan] -> [blue]{team_display}[/blue]"
                        )

                try:
                    client.drafts.watch_draft_picks(
                        league_key=league_key, callback=print_pick, poll_interval=interval,
                        include_player_names=not keys
                    )
                except KeyboardInterrupt:
                    console.print("\n[yellow]Draft watching stopped.[/yellow]")
                except Exception as e:
                    console.print(f"[red]Error watching draft: {e}[/red]")
                    raise typer.Exit(1)

            else:
                HistoricalContext.display_fetching_message("draft picks", league_display_name, year, week)

                picks = client.drafts.get_draft_picks(league_key, include_player_names=not keys)
                
                if not keys and len(picks) > 10:
                    console.print(f"[yellow]Looking up names for {len(picks)} draft picks... This may take a moment.[/yellow]")

                if not picks:
                    console.print("[yellow]No draft picks found.[/yellow]")
                    return

                # Filter to recent picks if requested
                if recent > 0:
                    picks = picks[-recent:]

                # Create table with better column names and widths
                has_names = not keys and any(pick.player_name for pick in picks[:5])  # Check if we actually got names
                
                if has_names:
                    table = Table(title=f"Draft Picks ({len(picks)} total)")
                    table.add_column("Pick", justify="right", style="cyan", width=4)
                    table.add_column("Round", justify="right", width=5)
                    table.add_column("Player", style="white", width=20)
                    table.add_column("Pos", style="yellow", width=3)
                    table.add_column("NFL Team", style="green", width=8)
                    table.add_column("Fantasy Team", style="blue", width=15)
                    table.add_column("Cost", justify="right", width=4)
                else:
                    table = Table(title=f"Draft Picks ({len(picks)} total)")
                    table.add_column("Pick", justify="right", style="cyan", width=4)
                    table.add_column("Round", justify="right", width=5)
                    table.add_column("Player Key", style="white", width=15)
                    table.add_column("Fantasy Team", style="blue", width=15)
                    table.add_column("Cost", justify="right", width=4)
                    if keys:
                        console.print("[dim]Tip: Remove --keys flag to lookup actual player names[/dim]")

                for pick in picks:
                    if has_names:
                        # Use names if available, fallback to keys
                        player_display = pick.player_name or pick.player_key
                        team_display = pick.team_name or pick.team_key
                        
                        # Truncate long names to fit columns
                        if len(player_display) > 20:
                            player_display = player_display[:17] + "..."
                        if len(team_display) > 15:
                            team_display = team_display[:12] + "..."
                        
                        table.add_row(
                            str(pick.pick),
                            str(pick.round),
                            player_display,
                            pick.player_position or "-",
                            pick.player_team or "-",
                            team_display,
                            str(pick.cost) if pick.cost is not None else "-",
                        )
                    else:
                        # Simple view with keys only
                        team_display = pick.team_name or pick.team_key
                        if len(team_display) > 15:
                            team_display = team_display[:12] + "..."
                            
                        table.add_row(
                            str(pick.pick),
                            str(pick.round),
                            pick.player_key,
                            team_display,
                            str(pick.cost) if pick.cost is not None else "-",
                        )

                console.print(table)

    except Exception as e:
        console.print(f"[red]Error fetching draft picks: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def export_draft(
    league_key: str = typer.Argument(help="League key (e.g., nfl.l.12345)"),
    output_file: Optional[str] = typer.Option(
        None, "--output", help="Output file path"
    ),
) -> None:
    """Export complete draft results to JSON."""

    try:
        with get_client() as client:
            league_display_name = get_league_display_name(client, league_key)
            console.print(f"[yellow]Exporting draft results for {league_display_name}...[/yellow]")
            
            draft_data = client.drafts.export_draft_summary(league_key)

            # Convert to JSON
            json_data = json.dumps(draft_data, indent=2, default=str)

            if output_file:
                with open(output_file, "w") as f:
                    f.write(json_data)
                console.print(f"[green]Draft data exported to {output_file}[/green]")
            else:
                print(json_data)

    except Exception as e:
        console.print(f"[red]Error exporting draft: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def teams(
    league_key: str = typer.Argument(help="League key (e.g., nfl.l.12345)"),
    year: Optional[int] = typer.Option(None, "--year", help="Season year (defaults to current season)"),
    week: Optional[int] = typer.Option(None, "--week", help="Specific week number for week-specific data")
) -> None:
    """List all teams in a league."""

    try:
        # Apply historical transformations
        league_key, _ = HistoricalContext.apply_transformations(league_key, year)
            
        with get_client() as client:
            league_display_name = get_league_display_name(client, league_key)
            HistoricalContext.display_fetching_message("teams", league_display_name, year, week)
            
            team_keys = client.leagues.get_league_teams(league_key)

            if not team_keys:
                console.print("[yellow]No teams found.[/yellow]")
                return

            # Get team details
            table = Table(title=f"League Teams ({len(team_keys)} total)")
            table.add_column("Team Key", style="cyan")
            table.add_column("Name", style="white")
            table.add_column("Managers")

            for team_key in team_keys:
                try:
                    team = client.teams.get_team(team_key)
                    manager_names = []
                    for manager in team.managers:
                        if isinstance(manager, dict) and "nickname" in manager:
                            manager_names.append(manager["nickname"])

                    table.add_row(
                        team_key, team.name, ", ".join(manager_names) or "Unknown"
                    )
                except Exception as e:
                    table.add_row(team_key, f"Error: {e}", "")

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error fetching teams: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def weekly_scoreboard(
    week: int = typer.Argument(help="Week number"),
    league_key: Optional[str] = typer.Option(None, "--league", "-l", help="League key (will auto-discover if not provided)"),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed matchup information"),
    year: Optional[int] = typer.Option(None, "--year", help="Season year (defaults to current season)")
) -> None:
    """Get weekly scoreboard with all matchups for a specific week."""
    
    with get_client() as client:
        try:
            # Determine the year to use
            if year is None:
                import datetime
                year = datetime.datetime.now().year
            
            # Get the appropriate league key for this year
            league_key = get_league_key_for_year(client, year, league_key)
            
            league_name = get_league_display_name(client, league_key)
            
            console.print(f"\n[cyan]Getting Week {week} scoreboard for {league_name}...[/cyan]")
            
            scoreboard = client.leagues.get_weekly_scoreboard(league_key, week)
            
            if not scoreboard.matchups:
                console.print(f"[yellow]No matchups found for week {week}[/yellow]")
                return

            console.print(f"\n[bold]Week {week} Results[/bold]")
            console.print(f"Total Matchups: {len(scoreboard.matchups)}")
            
            table = Table(show_header=True, header_style="bold blue")
            table.add_column("Matchup")
            table.add_column("Team 1", style="cyan")
            table.add_column("Score 1", justify="right")
            table.add_column("Team 2", style="cyan") 
            table.add_column("Score 2", justify="right")
            table.add_column("Result", style="bold")
            table.add_column("Margin", justify="right")

            for i, matchup in enumerate(scoreboard.matchups, 1):
                if matchup.is_tied:
                    result = "TIE"
                    margin = "0.00"
                else:
                    winner = matchup.get_winning_team()
                    result = f"{winner.team_name} wins" if winner else "Unknown"
                    margin = f"{matchup.margin_of_victory:.2f}"

                table.add_row(
                    f"#{i}",
                    matchup.team1.team_name,
                    f"{matchup.team1.points:.2f}",
                    matchup.team2.team_name,
                    f"{matchup.team2.points:.2f}",
                    result,
                    margin
                )

            console.print(table)
            
            # Show highest scorer
            highest_team = scoreboard.get_highest_score()
            if highest_team:
                console.print(f"\n[bold green]🔥 Week {week} High Score:[/bold green] {highest_team.team_name} ({highest_team.points:.2f})")

            # Show skins eligible if requested
            if detailed:
                skins_matchups = scoreboard.get_matchups_by_margin(20.0)
                if skins_matchups:
                    console.print(f"\n[bold yellow]🎯 Skins Eligible (20+ point margin):[/bold yellow]")
                    for matchup in skins_matchups:
                        winner = matchup.get_winning_team()
                        if winner:
                            console.print(f"   {winner.team_name} by {matchup.margin_of_victory:.2f} points")

        except Exception as e:
            console.print(f"[red]Error fetching weekly scoreboard: {e}[/red]")
            raise typer.Exit(1)


@app.command() 
def season_analysis(
    start_week: int = typer.Option(1, "--start-week", help="First week to analyze"),
    end_week: int = typer.Option(14, "--end-week", help="Last week to analyze"),
    league_key: Optional[str] = typer.Option(None, "--league", "-l", help="League key (will auto-discover if not provided)"),
    export: Optional[str] = typer.Option(None, "--export", help="Export results to JSON file"),
    year: Optional[int] = typer.Option(None, "--year", help="Season year (defaults to current season)")
) -> None:
    """Comprehensive season analysis including skins games and survivor results."""
    
    from .analysis import WeeklyAnalyzer
    
    with get_client() as client:
        try:
            # Determine the year to use
            if year is None:
                import datetime
                year = datetime.datetime.now().year
            
            # Get the appropriate league key for this year
            league_key = get_league_key_for_year(client, year, league_key)
            
            league_name = get_league_display_name(client, league_key)
            
            console.print(f"\n[cyan]Analyzing season for {league_name}...[/cyan]")
            console.print(f"Weeks {start_week}-{end_week}")
            
            # Get season results
            season_results = client.leagues.get_season_results(
                league_key, start_week, end_week, regular_season_only=True
            )
            
            if not season_results.weekly_scoreboards:
                console.print("[yellow]No weekly data found[/yellow]")
                return

            # Initialize analyzer
            analyzer = WeeklyAnalyzer(min_skins_margin=20.0)
            
            # Calculate skins winners
            console.print(f"\n[bold blue]🎯 Skins Game Results (20+ point margins)[/bold blue]")
            skins_winners = analyzer.calculate_skins_winners(season_results, weekly_pot=10.0)
            
            if skins_winners:
                skins_table = Table(show_header=True, header_style="bold blue")
                skins_table.add_column("Team", style="cyan")
                skins_table.add_column("Weeks Won", justify="center")
                skins_table.add_column("Total Winnings", justify="right")
                skins_table.add_column("Best Margin", justify="right")

                for team_name, wins in skins_winners.items():
                    total_winnings = sum(win["pot_amount"] for win in wins)
                    best_margin = max(win["margin"] for win in wins)
                    
                    skins_table.add_row(
                        team_name,
                        str(len(wins)),
                        f"${total_winnings:.2f}",
                        f"{best_margin:.2f}"
                    )

                console.print(skins_table)
            else:
                console.print("[yellow]No skins winners found[/yellow]")

            # Calculate survivor results
            console.print(f"\n[bold blue]🏆 Survivor Pool Results[/bold blue]")
            survivor_results = analyzer.calculate_survivor_results(season_results)
            
            if survivor_results["winner"]:
                console.print(f"[bold green]Winner: {survivor_results['winner']}[/bold green]")
            else:
                console.print("[yellow]No clear survivor winner yet[/yellow]")

            # Show recent eliminations
            recent_eliminations = survivor_results["eliminations"][-5:] if survivor_results["eliminations"] else []
            if recent_eliminations:
                console.print("\n[bold]Recent Eliminations:[/bold]")
                for elim in recent_eliminations:
                    console.print(f"Week {elim['week']}: {elim['eliminated_team']} ({elim['eliminated_score']:.2f} pts)")

            # Power rankings
            console.print(f"\n[bold blue]📊 Power Rankings (Last 4 Weeks)[/bold blue]")
            power_rankings = analyzer.calculate_power_rankings(season_results)
            
            if power_rankings:
                power_table = Table(show_header=True, header_style="bold blue")
                power_table.add_column("Rank", justify="center")
                power_table.add_column("Team", style="cyan")
                power_table.add_column("Power Rating", justify="right")
                power_table.add_column("Avg Score", justify="right")
                power_table.add_column("Win %", justify="right")

                for i, team_data in enumerate(power_rankings, 1):
                    power_table.add_row(
                        str(i),
                        team_data["team_name"],
                        f"{team_data['power_rating']:.1f}",
                        f"{team_data['avg_score']:.1f}",
                        f"{team_data['win_percentage']:.3f}"
                    )

                console.print(power_table)

            # Export if requested
            if export:
                summary = analyzer.export_season_summary(season_results, export)
                console.print(f"\n[green]Season analysis exported to: {export}[/green]")

        except Exception as e:
            console.print(f"[red]Error performing season analysis: {e}[/red]")
            raise typer.Exit(1)


@app.command()
def team_performance(
    league_key: str = typer.Argument(help="League key (e.g., nfl.l.12345)"),
    team_key: str = typer.Argument(help="Team key (e.g., nfl.l.12345.t.1)"),
    weeks: str = typer.Option("1-14", "--weeks", help="Week range (e.g., '1-14', '1,3,5')"),
    year: Optional[int] = typer.Option(None, "--year", help="Season year (defaults to current season)"),
    week: Optional[int] = typer.Option(None, "--week", help="Specific week number for week-specific data")
) -> None:
    """Analyze specific team's weekly performance and trends."""
    
    # Apply historical transformations
    league_key, team_key = HistoricalContext.apply_transformations(league_key, year, team_key)
    
    with get_client() as client:
        try:
            league_name = get_league_display_name(client, league_key)
            
            # Add context display with year/week info
            if year or week:
                context_str = HistoricalContext.build_context_string(year, week)
                console.print(f"[dim]Historical query{context_str}[/dim]")
            
            try:
                team = client.teams.get_team(team_key)
            except Exception as e:
                HistoricalContext.handle_historical_error(e, year, f"team {team_key}")
            
            console.print(f"\n[cyan]Analyzing performance for {team.name} in {league_name}...[/cyan]")
            
            # Parse weeks parameter
            if "-" in weeks:
                start, end = map(int, weeks.split("-"))
                week_list = list(range(start, end + 1))
            else:
                week_list = [int(w.strip()) for w in weeks.split(",")]

            # Get performance data
            performance = client.leagues.get_team_weekly_performance(league_key, team_key, week_list)
            
            if not performance:
                console.print(f"[yellow]No performance data found for the specified weeks[/yellow]")
                return

            # Performance table
            perf_table = Table(show_header=True, header_style="bold blue")
            perf_table.add_column("Week", justify="center")
            perf_table.add_column("Points", justify="right")
            perf_table.add_column("Opponent", style="cyan")
            perf_table.add_column("Opp Pts", justify="right")
            perf_table.add_column("Margin", justify="right")
            perf_table.add_column("Result", style="bold")

            total_points = 0.0
            wins = losses = ties = 0

            for week_data in performance:
                total_points += week_data["team_points"]
                
                if week_data["result"] == "W":
                    wins += 1
                    result_color = "[green]W[/green]"
                elif week_data["result"] == "L":
                    losses += 1
                    result_color = "[red]L[/red]"
                else:
                    ties += 1
                    result_color = "[yellow]T[/yellow]"

                margin_color = "[green]" if week_data["margin"] > 0 else "[red]" if week_data["margin"] < 0 else "[yellow]"

                perf_table.add_row(
                    str(week_data["week"]),
                    f"{week_data['team_points']:.2f}",
                    week_data["opponent_name"],
                    f"{week_data['opponent_points']:.2f}",
                    f"{margin_color}{week_data['margin']:+.2f}[/{margin_color.split('[')[1]}]",
                    result_color
                )

            console.print(perf_table)

            # Summary stats
            games_played = wins + losses + ties
            avg_points = total_points / games_played if games_played > 0 else 0
            win_pct = wins / games_played if games_played > 0 else 0

            console.print(f"\n[bold]Performance Summary:[/bold]")
            console.print(f"Record: {wins}-{losses}" + (f"-{ties}" if ties > 0 else ""))
            console.print(f"Win Percentage: {win_pct:.3f}")
            console.print(f"Total Points: {total_points:.2f}")
            console.print(f"Average Points: {avg_points:.2f}")

        except Exception as e:
            console.print(f"[red]Error analyzing team performance: {e}[/red]")
            raise typer.Exit(1)


@app.command()
def margin_analysis(
    league_key: str = typer.Argument(help="League key (e.g., nfl.l.12345)"),
    weeks: str = typer.Option("1-14", "--weeks", help="Week range to analyze"),
    min_margin: float = typer.Option(20.0, "--min-margin", help="Minimum margin for skins eligibility"),
    year: Optional[int] = typer.Option(None, "--year", help="Season year (defaults to current season)"),
    week: Optional[int] = typer.Option(None, "--week", help="Specific week number for week-specific data")
) -> None:
    """Analyze victory margins and identify skins game winners."""
    
    # Apply historical transformations
    league_key, _ = HistoricalContext.apply_transformations(league_key, year)
    
    with get_client() as client:
        try:
            league_name = get_league_display_name(client, league_key)
            
            console.print(f"\n[cyan]Analyzing victory margins for {league_name}...[/cyan]")
            
            # Parse weeks parameter
            if "-" in weeks:
                start, end = map(int, weeks.split("-"))
                week_list = list(range(start, end + 1))
            else:
                week_list = [int(w.strip()) for w in weeks.split(",")]

            # Get margin data
            margins = client.leagues.calculate_league_margins(league_key, week_list)
            
            if not margins:
                console.print(f"[yellow]No margin data found[/yellow]")
                return

            # Show all margins
            console.print(f"\n[bold]Victory Margins (Weeks {min(week_list)}-{max(week_list)})[/bold]")
            
            margin_table = Table(show_header=True, header_style="bold blue")
            margin_table.add_column("Week", justify="center")
            margin_table.add_column("Winner", style="green")
            margin_table.add_column("Winner Pts", justify="right")
            margin_table.add_column("Loser", style="red")
            margin_table.add_column("Loser Pts", justify="right")
            margin_table.add_column("Margin", justify="right")
            margin_table.add_column("Skins?", justify="center")

            skins_eligible = []

            for margin_data in sorted(margins, key=lambda x: x["margin"], reverse=True):
                is_skins = margin_data["margin"] >= min_margin
                if is_skins:
                    skins_eligible.append(margin_data)

                margin_table.add_row(
                    str(margin_data["week"]),
                    margin_data["winner_team"],
                    f"{margin_data['winner_points']:.2f}",
                    margin_data["loser_team"],
                    f"{margin_data['loser_points']:.2f}",
                    f"{margin_data['margin']:.2f}",
                    "🎯" if is_skins else ""
                )

            console.print(margin_table)

            # Skins summary
            if skins_eligible:
                console.print(f"\n[bold yellow]🎯 Skins Eligible Victories ({min_margin}+ points)[/bold yellow]")
                
                skins_counts = {}
                for skins_win in skins_eligible:
                    winner = skins_win["winner_team"]
                    if winner not in skins_counts:
                        skins_counts[winner] = []
                    skins_counts[winner].append(skins_win)

                skins_summary_table = Table(show_header=True, header_style="bold yellow")
                skins_summary_table.add_column("Team", style="cyan")
                skins_summary_table.add_column("Skins Wins", justify="center")
                skins_summary_table.add_column("Best Margin", justify="right")
                skins_summary_table.add_column("Weeks", justify="left")

                for team_name, wins in sorted(skins_counts.items(), key=lambda x: len(x[1]), reverse=True):
                    best_margin = max(win["margin"] for win in wins)
                    week_list = ", ".join(str(win["week"]) for win in wins)

                    skins_summary_table.add_row(
                        team_name,
                        str(len(wins)),
                        f"{best_margin:.2f}",
                        week_list
                    )

                console.print(skins_summary_table)
            else:
                console.print(f"[yellow]No skins eligible victories found (minimum margin: {min_margin})[/yellow]")

        except Exception as e:
            console.print(f"[red]Error analyzing margins: {e}[/red]")
            raise typer.Exit(1)


def prompt_team_selection(client: YahooFantasyClient, league_key: str) -> str:
    """Prompt user to select from teams in the league."""
    try:
        # Get all team keys in the league
        team_keys = client.leagues.get_league_teams(league_key)
        
        if not team_keys:
            console.print("[red]No teams found in league[/red]")
            return None
            
        if len(team_keys) == 1:
            # Auto-select if only one team
            console.print(f"[green]Auto-selected team: {team_keys[0]}[/green]")
            return team_keys[0]
        
        # Get detailed info for each team
        teams = []
        for team_key in team_keys:
            try:
                team = client.teams.get_team(team_key)
                teams.append(team)
            except Exception as e:
                # Fallback: create a minimal team object
                teams.append(type('Team', (), {
                    'team_key': team_key,
                    'name': f"Team {team_key.split('.')[-1]}",
                    'manager_nickname': 'Unknown',
                    'wins': None,
                    'losses': None
                })())
        
        # Multiple teams - prompt for selection
        console.print(f"\n[bold]Select a team:[/bold]")
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("#", style="dim", width=3)
        table.add_column("Team Name", style="cyan")
        table.add_column("Manager", style="white")
        table.add_column("Team Key", style="dim")
        
        for i, team in enumerate(teams, 1):
            table.add_row(
                str(i),
                team.name,
                getattr(team, 'manager_nickname', 'Unknown') or "Unknown",
                team.team_key
            )
        
        console.print(table)
        
        while True:
            try:
                choice = typer.prompt(f"\nSelect team number (1-{len(teams)})")
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(teams):
                    selected = teams[choice_idx]
                    console.print(f"[green]Selected: {selected.name}[/green]")
                    return selected.team_key
                else:
                    console.print("[red]Invalid selection. Please try again.[/red]")
            except (ValueError, typer.Abort):
                console.print("[red]Invalid input. Please try again.[/red]")
                
    except Exception as e:
        console.print(f"[red]Error getting teams: {e}[/red]")
        return None


@app.command()
def team_roster(
    week: int = typer.Argument(help="Week number"),
    team_key: Optional[str] = typer.Option(None, "--team", "-t", help="Team key (will prompt for selection if not provided)"),
    league_key: Optional[str] = typer.Option(None, "--league", "-l", help="League key (will auto-discover if not provided)"),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed player stats"),
    year: Optional[int] = typer.Option(None, "--year", help="Season year (defaults to current season)")
) -> None:
    """Display team roster with individual player point totals for a specific week."""
    
    with get_client() as client:
        try:
            # Determine the year to use
            if year is None:
                import datetime
                current_year = datetime.datetime.now().year
                # NFL season runs Aug-Feb, so if we're before August, use previous year
                if datetime.datetime.now().month < 8:
                    year = current_year - 1
                else:
                    year = current_year
            
            console.print(f"[dim]Analyzing {year} season data...[/dim]")
            
            # Get the appropriate league key for this year
            if not league_key:
                league_key = get_league_key_for_year(client, year, league_key)
            
            # Get team key if not provided
            if not team_key:
                team_key = prompt_team_selection(client, league_key)
                if not team_key:
                    raise typer.Exit(1)
            
            console.print(f"\n[cyan]Getting Week {week} roster for team {team_key}...[/cyan]")
            
            roster = client.teams.get_team_roster(team_key, week)
            
            # Check for empty/inactive teams
            if not roster.players or all(not player.name.strip() for player in roster.players):
                console.print(f"[yellow]⚠️  This team appears to be empty or inactive for week {week}.[/yellow]")
                console.print(f"[dim]Try a different team or check if this league is active.[/dim]")
                return
                
            if roster.total_points == 0 and len(roster.players) > 5:
                console.print(f"[yellow]⚠️  This team has 0 points - it may be inactive or week {week} hasn't been played yet.[/yellow]")

            console.print(f"\n[bold]{roster.team_name} - Week {week} Roster[/bold]")
            console.print(f"Total Points: {roster.total_points:.2f}")
            console.print(f"Starter Points: {roster.starter_points:.2f} | Bench Points: {roster.bench_points:.2f}")
            
            # Display starting lineup
            if roster.starters:
                console.print(f"\n[bold green]Starting Lineup ({len(roster.starters)} players)[/bold green]")
                starter_table = Table(show_header=True, header_style="bold blue")
                starter_table.add_column("Position", style="cyan")
                starter_table.add_column("Player", style="white")
                starter_table.add_column("Team", style="dim")
                starter_table.add_column("Points", justify="right", style="bold")
                if detailed:
                    starter_table.add_column("Projected", justify="right", style="dim")

                for player in sorted(roster.starters, key=lambda p: p.selected_position):
                    row = [
                        player.selected_position,
                        f"{player.name} ({player.position})",
                        player.team or "N/A",
                        f"{player.points:.2f}"
                    ]
                    if detailed:
                        proj = f"{player.projected_points:.2f}" if player.projected_points else "N/A"
                        row.append(proj)
                    
                    starter_table.add_row(*row)

                console.print(starter_table)
            
            # Display bench
            if roster.bench:
                console.print(f"\n[bold yellow]Bench ({len(roster.bench)} players)[/bold yellow]")
                bench_table = Table(show_header=True, header_style="bold blue")
                bench_table.add_column("Player", style="white")
                bench_table.add_column("Position", style="cyan")
                bench_table.add_column("Team", style="dim")
                bench_table.add_column("Points", justify="right")
                if detailed:
                    bench_table.add_column("Projected", justify="right", style="dim")

                for player in sorted(roster.bench, key=lambda p: p.points, reverse=True):
                    row = [
                        player.name,
                        player.position,
                        player.team or "N/A",
                        f"{player.points:.2f}"
                    ]
                    if detailed:
                        proj = f"{player.projected_points:.2f}" if player.projected_points else "N/A"
                        row.append(proj)
                    
                    bench_table.add_row(*row)

                console.print(bench_table)
            
            # Show bench players who outscored starters
            outperformers = roster.get_bench_outperformers()
            if outperformers:
                console.print(f"\n[bold red]💡 Bench players who outscored starters:[/bold red]")
                for player in outperformers:
                    console.print(f"   {player.name} ({player.position}): {player.points:.2f} points")

        except Exception as e:
            console.print(f"[red]Error fetching team roster: {e}[/red]")
            raise typer.Exit(1)


@app.command()
def head_to_head(
    week: int = typer.Argument(help="Week number"),
    league_key: Optional[str] = typer.Option(None, "--league", "-l", help="League key (will auto-discover if not provided)"),
    matchup_id: Optional[int] = typer.Option(None, "--matchup", "-m", help="Specific matchup number to show details"),
    year: Optional[int] = typer.Option(None, "--year", help="Season year (defaults to current season)")
) -> None:
    """Display head-to-head matchups for the week. Show all matchups or detailed view of one."""
    
    with get_client() as client:
        try:
            # Determine the year to use
            if year is None:
                import datetime
                current_year = datetime.datetime.now().year
                # NFL season runs Aug-Feb, so if we're before August, use previous year
                if datetime.datetime.now().month < 8:
                    year = current_year - 1
                else:
                    year = current_year
            
            console.print(f"[dim]Analyzing {year} season week {week} matchups...[/dim]")
            
            # Get the appropriate league key for this year
            if not league_key:
                league_key = get_league_key_for_year(client, year, league_key)
            
            # Get the weekly scoreboard to find all matchups
            console.print(f"[cyan]Getting Week {week} scoreboard...[/cyan]")
            scoreboard = client.leagues.get_weekly_scoreboard(league_key, week)
            
            if not scoreboard.matchups:
                console.print(f"[yellow]No matchups found for week {week}[/yellow]")
                return
            
            # If no specific matchup requested, show all matchups
            if matchup_id is None:
                console.print(f"\n[bold]Week {week} Matchups[/bold]")
                
                # Create matchups summary table
                matchup_table = Table(show_header=True, header_style="bold blue")
                matchup_table.add_column("#", style="dim", width=3)
                matchup_table.add_column("Team 1", style="green", min_width=18)
                matchup_table.add_column("Score", justify="right", style="green", width=8)
                matchup_table.add_column("Team 2", style="blue", min_width=18)
                matchup_table.add_column("Score", justify="right", style="blue", width=8)
                matchup_table.add_column("Winner", style="yellow", min_width=15)
                
                for i, matchup in enumerate(scoreboard.matchups, 1):
                    team1_name = matchup.team1.team_name
                    team2_name = matchup.team2.team_name
                    team1_points = f"{matchup.team1.points:.2f}"
                    team2_points = f"{matchup.team2.points:.2f}"
                    
                    # Determine winner by team name
                    if matchup.is_tied:
                        status = "TIE"
                    elif matchup.team1.points > matchup.team2.points:
                        status = team1_name
                    else:
                        status = team2_name
                    
                    matchup_table.add_row(
                        str(i),
                        team1_name,
                        team1_points,
                        team2_name,
                        team2_points,
                        status
                    )
                
                console.print(matchup_table)
                console.print(f"\n[dim]💡 Use --matchup <number> to see detailed position breakdown[/dim]")
                console.print(f"[dim]   Example: yfa head-to-head {week} --matchup 1[/dim]")
                return
            
            # Show detailed matchup
            if matchup_id < 1 or matchup_id > len(scoreboard.matchups):
                console.print(f"[red]Invalid matchup number. Choose 1-{len(scoreboard.matchups)}[/red]")
                return
            
            selected_matchup = scoreboard.matchups[matchup_id - 1]
            team1_key = selected_matchup.team1.team_key
            team2_key = selected_matchup.team2.team_key
            
            # Get detailed rosters for both teams
            console.print(f"[cyan]Building detailed matchup view...[/cyan]")
            detailed_matchup = client.teams.get_detailed_matchup(team1_key, team2_key, week)
            
            # Display detailed matchup header
            team1_name = detailed_matchup.team1_roster.team_name
            team2_name = detailed_matchup.team2_roster.team_name
            
            console.print(f"\n[bold]Matchup {matchup_id}: {team1_name} vs {team2_name} - Week {week}[/bold]")
            console.print(f"[green]{team1_name}: {detailed_matchup.team1_total_points:.2f}[/green] | [blue]{team2_name}: {detailed_matchup.team2_total_points:.2f}[/blue]")
            
            winner = detailed_matchup.winner
            if winner:
                margin = abs(detailed_matchup.points_difference)
                console.print(f"[bold yellow]Winner: {winner} by {margin:.2f} points[/bold yellow]")
            else:
                console.print("[bold yellow]Tie game![/bold yellow]")
            
            # Position summary
            pos_summary = detailed_matchup.get_position_summary()
            console.print(f"[dim]Positions won: {team1_name} {pos_summary['team1']}, {team2_name} {pos_summary['team2']}, Ties {pos_summary['ties']}[/dim]")
            
            # Create side-by-side starting lineup table
            console.print(f"\n[bold green]Starting Lineups[/bold green]")
            starter_table = Table(show_header=True, header_style="bold blue")
            starter_table.add_column("Position", style="cyan", width=8)
            starter_table.add_column(f"{team1_name}", style="white", min_width=25)
            starter_table.add_column("Pts", justify="right", style="green", width=7)
            starter_table.add_column(f"{team2_name}", style="white", min_width=25)
            starter_table.add_column("Pts", justify="right", style="blue", width=7)
            starter_table.add_column("Diff", justify="center", style="yellow", width=8)
            
            for pos_matchup in detailed_matchup.starter_matchups:
                team1_player = pos_matchup.team1_player
                team2_player = pos_matchup.team2_player
                
                team1_display = f"{team1_player.name} ({team1_player.team})" if team1_player else "—"
                team1_points = f"{team1_player.points:.2f}" if team1_player else "0.00"
                
                team2_display = f"{team2_player.name} ({team2_player.team})" if team2_player else "—"
                team2_points = f"{team2_player.points:.2f}" if team2_player else "0.00"
                
                diff = pos_matchup.points_difference
                if abs(diff) < 0.01:
                    diff_display = "TIE"
                    diff_style = "dim"
                elif diff > 0:
                    diff_display = f"←+{diff:.2f}"
                    diff_style = "green"
                else:
                    diff_display = f"{diff:.2f}->"
                    diff_style = "blue"
                
                starter_table.add_row(
                    pos_matchup.position,
                    team1_display,
                    team1_points,
                    team2_display,
                    team2_points,
                    f"[{diff_style}]{diff_display}[/{diff_style}]"
                )
            
            console.print(starter_table)
            
            # Bench comparison (top 3 from each)
            if detailed_matchup.bench_matchups:
                console.print(f"\n[bold yellow]Top Bench Players[/bold yellow]")
                bench_table = Table(show_header=True, header_style="bold blue")
                bench_table.add_column("Rank", style="dim", width=4)
                bench_table.add_column(f"{team1_name} Bench", style="white", min_width=25)
                bench_table.add_column("Pts", justify="right", style="green", width=7)
                bench_table.add_column(f"{team2_name} Bench", style="white", min_width=25)
                bench_table.add_column("Pts", justify="right", style="blue", width=7)
                
                for i, pos_matchup in enumerate(detailed_matchup.bench_matchups[:3], 1):
                    team1_player = pos_matchup.team1_player
                    team2_player = pos_matchup.team2_player
                    
                    team1_display = f"{team1_player.name} ({team1_player.position}, {team1_player.team})" if team1_player else "—"
                    team1_points = f"{team1_player.points:.2f}" if team1_player else "0.00"
                    
                    team2_display = f"{team2_player.name} ({team2_player.position}, {team2_player.team})" if team2_player else "—"
                    team2_points = f"{team2_player.points:.2f}" if team2_player else "0.00"
                    
                    bench_table.add_row(
                        str(i),
                        team1_display,
                        team1_points,
                        team2_display,
                        team2_points
                    )
                
                console.print(bench_table)
            
            # Summary totals
            console.print(f"\n[bold]Final Breakdown:[/bold]")
            console.print(f"  {team1_name}: [green]{detailed_matchup.team1_roster.starter_points:.2f}[/green] (starters) + [dim]{detailed_matchup.team1_roster.bench_points:.2f}[/dim] (bench) = [bold]{detailed_matchup.team1_total_points:.2f}[/bold]")
            console.print(f"  {team2_name}: [blue]{detailed_matchup.team2_roster.starter_points:.2f}[/blue] (starters) + [dim]{detailed_matchup.team2_roster.bench_points:.2f}[/dim] (bench) = [bold]{detailed_matchup.team2_total_points:.2f}[/bold]")

        except Exception as e:
            console.print(f"[red]Error creating head-to-head matchup: {e}[/red]")
            raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show version information."""

    from . import __author__, __version__

    info_text = f"""
[cyan]Yahoo Fantasy Football API SDK[/cyan]
[white]Version:[/white] {__version__}
[white]Author:[/white] {__author__}
[white]Homepage:[/white] https://github.com/CraigFreyman/yahoo-ffb-api
    """.strip()

    panel = Panel(info_text, title="Version Info", border_style="blue")
    console.print(panel)


if __name__ == "__main__":
    app()
