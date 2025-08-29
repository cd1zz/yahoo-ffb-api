"""
League-related endpoints for Yahoo Fantasy Sports API.
"""

from typing import Any, Optional, Union

from ..http import YahooHTTP
from ..models.common import extract_list_items, extract_nested_value
from ..models.league import League, LeagueSettings
from ..models.matchup import WeeklyScoreboard, SeasonResults


class LeaguesAPI:
    """API wrapper for league-related endpoints."""

    def __init__(self, http_client: YahooHTTP):
        self.http = http_client

    def get_league(self, league_key: str) -> League:
        """
        Get basic league information.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')

        Returns:
            League object with basic information
        """

        path = f"league/{league_key}"

        try:
            response = self.http.get(path)

            # Extract league data from response
            league_data = extract_nested_value(response, "fantasy_content", "league")
            if not league_data or not isinstance(league_data, list):
                raise ValueError("Invalid league response structure")

            # Yahoo returns league data as array with single item
            league_info = league_data[0] if league_data else {}

            return League.from_api_data(league_info)

        except Exception as e:
            raise RuntimeError(f"Failed to fetch league {league_key}: {e}") from e

    def get_league_settings(self, league_key: str) -> LeagueSettings:
        """
        Get detailed league settings including scoring and roster configuration.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')

        Returns:
            LeagueSettings object with detailed configuration
        """

        path = f"league/{league_key}/settings"

        try:
            response = self.http.get(path)

            # Extract league data from response
            league_data = extract_nested_value(response, "fantasy_content", "league")
            if not league_data or not isinstance(league_data, list) or len(league_data) < 2:
                raise ValueError("Invalid league settings response structure")

            # Yahoo returns league array with 2 items:
            # [0] = league info, [1] = settings data
            settings_container = league_data[1]
            
            # Pass the settings container to the model (it expects "settings" key)
            return LeagueSettings.from_api_data(settings_container)

        except Exception as e:
            raise RuntimeError(
                f"Failed to fetch league settings for {league_key}: {e}"
            ) from e

    def get_league_standings(self, league_key: str) -> list[dict[str, Any]]:
        """
        Get league standings.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')

        Returns:
            List of team standings data
        """

        path = f"league/{league_key}/standings"

        try:
            response = self.http.get(path)

            # Extract standings data
            league_data = extract_nested_value(response, "fantasy_content", "league")
            if not league_data or not isinstance(league_data, list):
                raise ValueError("Invalid standings response structure")

            league_info = league_data[0] if league_data else {}
            standings_data = league_info.get("standings", {})

            if not standings_data:
                return []

            # Extract teams from standings
            teams_data = standings_data.get("teams", {})
            teams_list = extract_list_items(teams_data, "team")

            standings = []
            for team_data in teams_list:
                if isinstance(team_data, dict):
                    standings.append(team_data)

            return standings

        except Exception as e:
            raise RuntimeError(
                f"Failed to fetch standings for {league_key}: {e}"
            ) from e

    def get_league_teams(self, league_key: str) -> list[str]:
        """
        Get team keys for all teams in the league.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')

        Returns:
            List of team keys
        """

        path = f"league/{league_key}/teams"

        try:
            response = self.http.get(path)

            # Extract teams data - Yahoo returns league array with 2 items:
            # [0] = league info, [1] = teams data
            league_data = extract_nested_value(response, "fantasy_content", "league")
            if not league_data or not isinstance(league_data, list) or len(league_data) < 2:
                raise ValueError("Invalid teams response structure")

            # Teams data is in the second item
            teams_container = league_data[1]
            teams_data = teams_container.get("teams", {})

            if not teams_data:
                return []

            team_keys = []
            
            # Iterate through numbered team entries (skip 'count' key)
            for key, team_container in teams_data.items():
                if key.isdigit():
                    team_array = team_container.get("team", [])
                    if isinstance(team_array, list) and len(team_array) > 0:
                        # Team data is nested: team -> [0] -> [array of properties]
                        team_properties = team_array[0] if isinstance(team_array[0], list) else team_array
                        
                        # Extract team_key from the properties array
                        for prop in team_properties:
                            if isinstance(prop, dict) and "team_key" in prop:
                                team_keys.append(prop["team_key"])
                                break

            return team_keys

        except Exception as e:
            raise RuntimeError(f"Failed to fetch teams for {league_key}: {e}") from e

    def get_league_scoreboard(
        self, league_key: str, week: Optional[int] = None
    ) -> dict[str, Any]:
        """
        Get league scoreboard for a specific week.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')
            week: Week number (current week if not specified)

        Returns:
            Scoreboard data dictionary
        """

        path = f"league/{league_key}/scoreboard"
        params = {}

        if week is not None:
            params["week"] = str(week)

        try:
            response = self.http.get(path, params)

            # Extract scoreboard data
            league_data = extract_nested_value(response, "fantasy_content", "league")
            if not league_data or not isinstance(league_data, list):
                raise ValueError("Invalid scoreboard response structure")

            league_info = league_data[0] if league_data else {}
            scoreboard_data = league_info.get("scoreboard", {})

            return scoreboard_data

        except Exception as e:
            raise RuntimeError(
                f"Failed to fetch scoreboard for {league_key}: {e}"
            ) from e

    def get_weekly_scoreboard(
        self, league_key: str, week: int
    ) -> WeeklyScoreboard:
        """
        Get structured weekly scoreboard with all matchups for a specific week.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')
            week: Week number

        Returns:
            WeeklyScoreboard object with parsed matchup data
        """

        path = f"league/{league_key}/scoreboard"
        params = {"week": str(week)}

        try:
            response = self.http.get(path, params)

            # Extract scoreboard data - Yahoo returns league array with metadata and scoreboard
            league_data = extract_nested_value(response, "fantasy_content", "league")
            if not league_data or not isinstance(league_data, list):
                raise ValueError("Invalid scoreboard response structure")

            # Find scoreboard data in the league array (usually the second element)
            scoreboard_data = None
            for league_item in league_data:
                if isinstance(league_item, dict) and "scoreboard" in league_item:
                    scoreboard_data = league_item
                    break
            
            if not scoreboard_data:
                raise ValueError("No scoreboard data found in response")
            
            return WeeklyScoreboard.from_api_data(scoreboard_data, league_key, week)

        except Exception as e:
            raise RuntimeError(
                f"Failed to fetch weekly scoreboard for {league_key} week {week}: {e}"
            ) from e

    def get_multiple_weeks_scoreboard(
        self, league_key: str, weeks: Union[list[int], range]
    ) -> dict[int, WeeklyScoreboard]:
        """
        Get scoreboard data for multiple weeks.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')
            weeks: List or range of week numbers

        Returns:
            Dictionary mapping week numbers to WeeklyScoreboard objects
        """

        scoreboards = {}
        
        for week in weeks:
            try:
                scoreboard = self.get_weekly_scoreboard(league_key, week)
                scoreboards[week] = scoreboard
            except Exception as e:
                print(f"Warning: Failed to fetch week {week}: {e}")
                continue
        
        return scoreboards

    def get_season_results(
        self, 
        league_key: str, 
        start_week: int = 1, 
        end_week: int = 17,
        regular_season_only: bool = True
    ) -> SeasonResults:
        """
        Get complete season results with all weekly scoreboards.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')
            start_week: First week to include (default: 1)
            end_week: Last week to include (default: 17)
            regular_season_only: Whether to include only regular season (weeks 1-14)

        Returns:
            SeasonResults object with all weekly data
        """

        if regular_season_only:
            end_week = min(end_week, 14)

        # Get league info for season
        league = self.get_league(league_key)
        season = league.season or "2024"

        # Create season results container
        season_results = SeasonResults(
            league_key=league_key,
            season=season
        )

        # Fetch all weekly scoreboards
        weeks_range = range(start_week, end_week + 1)
        weekly_scoreboards = self.get_multiple_weeks_scoreboard(league_key, weeks_range)
        
        for week, scoreboard in weekly_scoreboards.items():
            season_results.add_week(scoreboard)

        return season_results

    def get_team_weekly_performance(
        self, 
        league_key: str, 
        team_key: str, 
        weeks: Optional[Union[list[int], range]] = None
    ) -> list[dict[str, Any]]:
        """
        Get a specific team's performance across multiple weeks.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')
            team_key: Team key (e.g., 'nfl.l.12345.t.1')
            weeks: Week numbers to analyze (default: weeks 1-14)

        Returns:
            List of weekly performance dictionaries
        """

        if weeks is None:
            weeks = range(1, 15)  # Regular season weeks

        performance = []
        
        for week in weeks:
            try:
                scoreboard = self.get_weekly_scoreboard(league_key, week)
                matchup = scoreboard.get_matchup_by_team(team_key)
                
                if matchup:
                    team_score = scoreboard.get_team_score(team_key)
                    opponent = matchup.get_team_opponent(team_key)
                    
                    if team_score and opponent:
                        performance.append({
                            "week": week,
                            "team_points": team_score.points,
                            "opponent_points": opponent.points,
                            "opponent_name": opponent.team_name,
                            "margin": team_score.points - opponent.points,
                            "result": "W" if team_score.points > opponent.points 
                                    else "L" if team_score.points < opponent.points 
                                    else "T",
                            "is_playoffs": matchup.is_playoffs
                        })
                        
            except Exception as e:
                print(f"Warning: Failed to get week {week} data for {team_key}: {e}")
                continue
        
        return performance

    def calculate_league_margins(
        self, league_key: str, weeks: Optional[Union[list[int], range]] = None
    ) -> list[dict[str, Any]]:
        """
        Calculate victory margins for all matchups across specified weeks.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')
            weeks: Week numbers to analyze (default: weeks 1-14)

        Returns:
            List of matchup results with margins
        """

        if weeks is None:
            weeks = range(1, 15)  # Regular season weeks

        margins = []
        
        for week in weeks:
            try:
                scoreboard = self.get_weekly_scoreboard(league_key, week)
                
                for matchup in scoreboard.matchups:
                    if not matchup.is_tied and matchup.status == "postevent":
                        winner = matchup.get_winning_team()
                        loser = matchup.get_losing_team()
                        
                        if winner and loser:
                            margins.append({
                                "week": week,
                                "winner_team": winner.team_name,
                                "winner_points": winner.points,
                                "loser_team": loser.team_name,
                                "loser_points": loser.points,
                                "margin": matchup.margin_of_victory,
                                "is_playoffs": matchup.is_playoffs
                            })
                            
            except Exception as e:
                print(f"Warning: Failed to process margins for week {week}: {e}")
                continue
        
        return margins

    def get_high_scoring_weeks(
        self, 
        league_key: str, 
        weeks: Optional[Union[list[int], range]] = None,
        min_score: float = 100.0
    ) -> list[dict[str, Any]]:
        """
        Get weeks where teams scored above a certain threshold.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')
            weeks: Week numbers to analyze (default: weeks 1-14)
            min_score: Minimum score threshold

        Returns:
            List of high-scoring performances
        """

        if weeks is None:
            weeks = range(1, 15)

        high_scores = []
        
        for week in weeks:
            try:
                scoreboard = self.get_weekly_scoreboard(league_key, week)
                
                for matchup in scoreboard.matchups:
                    for team in [matchup.team1, matchup.team2]:
                        if team.points >= min_score:
                            high_scores.append({
                                "week": week,
                                "team_name": team.team_name,
                                "points": team.points,
                                "opponent_name": matchup.get_team_opponent(team.team_key).team_name,
                                "opponent_points": matchup.get_team_opponent(team.team_key).points,
                                "margin": abs(team.points - matchup.get_team_opponent(team.team_key).points),
                                "result": "W" if team.points > matchup.get_team_opponent(team.team_key).points else "L"
                            })
                            
            except Exception as e:
                print(f"Warning: Failed to process high scores for week {week}: {e}")
                continue
        
        return sorted(high_scores, key=lambda x: x["points"], reverse=True)

    def get_league_transactions(
        self,
        league_key: str,
        transaction_types: Optional[list[str]] = None,
        count: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """
        Get recent transactions for the league.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')
            transaction_types: Types to filter by (e.g., ['add', 'drop', 'trade'])
            count: Maximum number of transactions to return

        Returns:
            List of transaction data dictionaries
        """

        path = f"league/{league_key}/transactions"
        params = {}

        if transaction_types:
            params["types"] = ",".join(transaction_types)
        if count is not None:
            params["count"] = str(count)

        try:
            response = self.http.get(path, params)

            # Extract transactions data
            league_data = extract_nested_value(response, "fantasy_content", "league")
            if not league_data or not isinstance(league_data, list):
                raise ValueError("Invalid transactions response structure")

            league_info = league_data[0] if league_data else {}
            transactions_data = league_info.get("transactions", {})

            if not transactions_data:
                return []

            # Extract individual transactions
            transactions_list = extract_list_items(transactions_data, "transaction")

            transactions = []
            for txn_data in transactions_list:
                if isinstance(txn_data, dict):
                    transactions.append(txn_data)

            return transactions

        except Exception as e:
            raise RuntimeError(
                f"Failed to fetch transactions for {league_key}: {e}"
            ) from e

    def is_draft_complete(self, league_key: str) -> bool:
        """
        Check if the league's draft is complete.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')

        Returns:
            True if draft is complete, False otherwise
        """

        try:
            league = self.get_league(league_key)
            return league.draft_status == "postdraft"

        except Exception as e:
            raise RuntimeError(
                f"Failed to check draft status for {league_key}: {e}"
            ) from e

    def get_league_summary(self, league_key: str) -> dict[str, Any]:
        """
        Get a comprehensive summary of league information.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')

        Returns:
            Dictionary with league summary data
        """

        try:
            # Get basic league info and settings in parallel operations
            league = self.get_league(league_key)
            settings = self.get_league_settings(league_key)
            team_keys = self.get_league_teams(league_key)

            return {
                "league": league,
                "settings": settings,
                "team_count": len(team_keys),
                "team_keys": team_keys,
                "is_draft_complete": league.draft_status == "postdraft",
            }

        except Exception as e:
            raise RuntimeError(
                f"Failed to get league summary for {league_key}: {e}"
            ) from e
