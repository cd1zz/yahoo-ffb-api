"""
Team-related endpoints for Yahoo Fantasy Sports API.
"""

from typing import Any, Optional, Union, TYPE_CHECKING

from ..http import YahooHTTP
from ..models.common import extract_list_items, extract_nested_value
from ..models.team import RosterPlayer, Team, TeamStandings
from ..models.matchup import Matchup, TeamScore
from ..models.roster import TeamRoster

if TYPE_CHECKING:
    from ..models.detailed_matchup import DetailedMatchup


class TeamsAPI:
    """API wrapper for team-related endpoints."""

    def __init__(self, http_client: YahooHTTP):
        self.http = http_client

    def get_team(self, team_key: str) -> Team:
        """
        Get basic team information.

        Args:
            team_key: Team key (e.g., 'nfl.l.12345.t.1')

        Returns:
            Team object with basic information
        """

        path = f"team/{team_key}"

        try:
            response = self.http.get(path)

            # Extract team data from response
            team_data = extract_nested_value(response, "fantasy_content", "team")
            if not team_data or not isinstance(team_data, list):
                raise ValueError("Invalid team response structure")

            # Yahoo returns team data as array containing another array of properties
            team_properties_array = team_data[0] if team_data else []
            
            if not isinstance(team_properties_array, list):
                raise ValueError("Invalid team properties structure")

            # Convert array of properties to dictionary
            team_info = {}
            for prop in team_properties_array:
                if isinstance(prop, dict):
                    team_info.update(prop)

            return Team.from_api_data(team_info)

        except Exception as e:
            raise RuntimeError(f"Failed to fetch team {team_key}: {e}") from e

    def get_team_roster(
        self, team_key: str, week: Optional[int] = None, date: Optional[str] = None
    ) -> list[RosterPlayer]:
        """
        Get team roster for a specific week or date.

        Args:
            team_key: Team key (e.g., 'nfl.l.12345.t.1')
            week: Week number (current week if not specified)
            date: Specific date (YYYY-MM-DD format)

        Returns:
            List of RosterPlayer objects
        """

        path = f"team/{team_key}/roster"
        params = {}

        if week is not None:
            params["week"] = str(week)
        elif date is not None:
            params["date"] = date

        try:
            response = self.http.get(path, params)

            # Extract roster data from response
            team_data = extract_nested_value(response, "fantasy_content", "team")
            if not team_data or not isinstance(team_data, list):
                raise ValueError("Invalid roster response structure")

            team_info = team_data[0] if team_data else {}
            roster_data = team_info.get("roster", {})

            if not roster_data:
                return []

            # Extract players from roster
            players_data = roster_data.get("players", {})
            players_list = extract_list_items(players_data, "player")

            roster = []
            for player_data in players_list:
                if isinstance(player_data, dict):
                    roster_player = RosterPlayer.from_api_data(player_data)
                    roster.append(roster_player)

            return roster

        except Exception as e:
            raise RuntimeError(f"Failed to fetch roster for {team_key}: {e}") from e

    def get_team_stats(
        self, team_key: str, week: Optional[int] = None, stat_type: str = "week"
    ) -> dict[str, Any]:
        """
        Get team statistics.

        Args:
            team_key: Team key (e.g., 'nfl.l.12345.t.1')
            week: Week number (for weekly stats)
            stat_type: Type of stats ("week", "season", "average")

        Returns:
            Dictionary with team statistics
        """

        path = f"team/{team_key}/stats"
        params = {"type": stat_type}

        if week is not None:
            params["week"] = str(week)

        try:
            response = self.http.get(path, params)

            # Extract stats data from response
            team_data = extract_nested_value(response, "fantasy_content", "team")
            if not team_data or not isinstance(team_data, list):
                raise ValueError("Invalid team stats response structure")

            team_info = team_data[0] if team_data else {}
            stats_data = team_info.get("team_stats", {})

            return stats_data

        except Exception as e:
            raise RuntimeError(f"Failed to fetch stats for {team_key}: {e}") from e

    def get_team_standings(self, team_key: str) -> TeamStandings:
        """
        Get team standings information.

        Args:
            team_key: Team key (e.g., 'nfl.l.12345.t.1')

        Returns:
            TeamStandings object
        """

        path = f"team/{team_key}/standings"

        try:
            response = self.http.get(path)

            # Extract standings data from response
            team_data = extract_nested_value(response, "fantasy_content", "team")
            if not team_data or not isinstance(team_data, list):
                raise ValueError("Invalid team standings response structure")

            team_info = team_data[0] if team_data else {}

            return TeamStandings.from_api_data(team_info)

        except Exception as e:
            raise RuntimeError(f"Failed to fetch standings for {team_key}: {e}") from e

    def get_team_matchup(
        self, team_key: str, week: Optional[int] = None
    ) -> dict[str, Any]:
        """
        Get team's matchup information for a specific week.

        Args:
            team_key: Team key (e.g., 'nfl.l.12345.t.1')
            week: Week number (current week if not specified)

        Returns:
            Dictionary with matchup information
        """

        path = f"team/{team_key}/matchups"
        params = {}

        if week is not None:
            params["weeks"] = str(week)

        try:
            response = self.http.get(path, params)

            # Extract matchup data from response
            team_data = extract_nested_value(response, "fantasy_content", "team")
            if not team_data or not isinstance(team_data, list):
                raise ValueError("Invalid matchups response structure")

            team_info = team_data[0] if team_data else {}
            matchups_data = team_info.get("matchups", {})

            return matchups_data

        except Exception as e:
            raise RuntimeError(f"Failed to fetch matchups for {team_key}: {e}") from e

    def get_starting_lineup(
        self, team_key: str, week: Optional[int] = None
    ) -> list[RosterPlayer]:
        """
        Get team's starting lineup (non-bench players).

        Args:
            team_key: Team key (e.g., 'nfl.l.12345.t.1')
            week: Week number (current week if not specified)

        Returns:
            List of RosterPlayer objects in starting positions
        """

        roster = self.get_team_roster(team_key, week)

        # Filter to only starting players
        starters = [player for player in roster if player.is_starter]

        return starters

    def get_bench_players(
        self, team_key: str, week: Optional[int] = None
    ) -> list[RosterPlayer]:
        """
        Get team's bench players.

        Args:
            team_key: Team key (e.g., 'nfl.l.12345.t.1')
            week: Week number (current week if not specified)

        Returns:
            List of RosterPlayer objects on bench
        """

        roster = self.get_team_roster(team_key, week)

        # Filter to only bench players
        bench = [player for player in roster if not player.is_starter]

        return bench

    def get_team_summary(
        self, team_key: str, week: Optional[int] = None
    ) -> dict[str, Any]:
        """
        Get comprehensive team summary.

        Args:
            team_key: Team key (e.g., 'nfl.l.12345.t.1')
            week: Week number for roster/stats (current week if not specified)

        Returns:
            Dictionary with complete team information
        """

        try:
            # Get team info and roster
            team = self.get_team(team_key)
            roster = self.get_team_roster(team_key, week)

            # Separate starters and bench
            starters = [p for p in roster if p.is_starter]
            bench = [p for p in roster if not p.is_starter]

            # Try to get standings (may fail for some leagues)
            standings = None
            try:
                standings = self.get_team_standings(team_key)
            except Exception:
                pass

            return {
                "team": team,
                "roster_size": len(roster),
                "starters_count": len(starters),
                "bench_count": len(bench),
                "roster": roster,
                "starters": starters,
                "bench": bench,
                "standings": standings,
            }

        except Exception as e:
            raise RuntimeError(f"Failed to get team summary for {team_key}: {e}") from e

    def export_roster_csv_data(
        self, team_key: str, week: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """
        Export roster data in CSV-friendly format.

        Args:
            team_key: Team key (e.g., 'nfl.l.12345.t.1')
            week: Week number (current week if not specified)

        Returns:
            List of dictionaries with flattened roster data
        """

        try:
            roster = self.get_team_roster(team_key, week)

            csv_data = []
            for roster_player in roster:
                player = roster_player.player

                row = {
                    "player_key": player.player_key,
                    "player_name": player.name,
                    "position": player.primary_position,
                    "eligible_positions": ",".join(player.eligible_positions),
                    "selected_position": roster_player.selected_position,
                    "is_starter": roster_player.is_starter,
                    "team_abbr": player.team_abbr,
                    "team_name": player.team_name,
                    "uniform_number": player.uniform_number,
                    "status": player.status,
                    "injury_note": player.injury_note,
                }
                csv_data.append(row)

            return csv_data

        except Exception as e:
            raise RuntimeError(
                f"Failed to export roster CSV data for {team_key}: {e}"
            ) from e

    def get_team_matchup_detailed(
        self, team_key: str, week: int
    ) -> Optional[Matchup]:
        """
        Get detailed matchup information for a specific team and week.

        Args:
            team_key: Team key (e.g., 'nfl.l.12345.t.1')
            week: Week number

        Returns:
            Matchup object with detailed team and opponent data, or None if not found
        """

        try:
            path = f"team/{team_key}/matchups"
            params = {"weeks": str(week)}
            
            response = self.http.get(path, params)

            # Extract matchup data
            team_data = extract_nested_value(response, "fantasy_content", "team")
            if not team_data or not isinstance(team_data, list):
                return None

            team_info = team_data[0] if team_data else {}
            matchups_data = team_info.get("matchups", {})

            # Find the specific week's matchup
            if isinstance(matchups_data, dict):
                for matchup_key, matchup_data in matchups_data.items():
                    if matchup_key == "count":
                        continue
                    
                    # Check if this is the right week
                    matchup_week = matchup_data.get("matchup", {}).get("week")
                    if matchup_week == str(week) or matchup_week == week:
                        return Matchup.from_api_data(matchup_data, week)

            return None

        except Exception as e:
            raise RuntimeError(
                f"Failed to fetch detailed matchup for {team_key} week {week}: {e}"
            ) from e

    def get_team_weekly_scores(
        self, 
        team_key: str, 
        weeks: Optional[Union[list[int], range]] = None
    ) -> list[TeamScore]:
        """
        Get a team's scores across multiple weeks.

        Args:
            team_key: Team key (e.g., 'nfl.l.12345.t.1')
            weeks: Week numbers to get scores for (default: weeks 1-14)

        Returns:
            List of TeamScore objects
        """

        if weeks is None:
            weeks = range(1, 15)  # Regular season weeks

        weekly_scores = []
        
        for week in weeks:
            try:
                matchup = self.get_team_matchup_detailed(team_key, week)
                if matchup:
                    # Find which team in the matchup corresponds to our team_key
                    if matchup.team1.team_key == team_key:
                        weekly_scores.append(matchup.team1)
                    elif matchup.team2.team_key == team_key:
                        weekly_scores.append(matchup.team2)
                        
            except Exception as e:
                print(f"Warning: Failed to get week {week} score for {team_key}: {e}")
                continue
        
        return weekly_scores

    def get_team_season_record(self, team_key: str) -> dict[str, Any]:
        """
        Get a team's complete season record and performance.

        Args:
            team_key: Team key (e.g., 'nfl.l.12345.t.1')

        Returns:
            Dictionary with wins, losses, ties, total points, average points
        """

        weekly_scores = self.get_team_weekly_scores(team_key)
        
        if not weekly_scores:
            return {
                "wins": 0,
                "losses": 0,
                "ties": 0,
                "games_played": 0,
                "total_points": 0.0,
                "average_points": 0.0,
                "highest_score": 0.0,
                "lowest_score": 0.0
            }

        # Calculate record by getting opponent data for each week
        wins = losses = ties = 0
        total_points = 0.0
        scores = []
        
        for team_score in weekly_scores:
            total_points += team_score.points
            scores.append(team_score.points)
            
            # Get the matchup to determine win/loss/tie
            try:
                matchup = self.get_team_matchup_detailed(team_key, team_score.week)
                if matchup and matchup.status == "postevent":
                    if matchup.is_tied:
                        ties += 1
                    elif matchup.winner_team_key == team_key:
                        wins += 1
                    else:
                        losses += 1
            except:
                continue

        games_played = len(weekly_scores)
        average_points = total_points / games_played if games_played > 0 else 0.0
        
        return {
            "wins": wins,
            "losses": losses, 
            "ties": ties,
            "games_played": games_played,
            "total_points": total_points,
            "average_points": average_points,
            "highest_score": max(scores) if scores else 0.0,
            "lowest_score": min(scores) if scores else 0.0
        }

    def get_team_matchup_history(
        self, 
        team_key: str,
        opponent_team_key: str,
        weeks: Optional[Union[list[int], range]] = None
    ) -> list[dict[str, Any]]:
        """
        Get head-to-head matchup history between two teams.

        Args:
            team_key: First team key
            opponent_team_key: Second team key 
            weeks: Week numbers to check (default: weeks 1-17)

        Returns:
            List of historical matchup results
        """

        if weeks is None:
            weeks = range(1, 18)  # Full season including playoffs

        matchup_history = []
        
        for week in weeks:
            try:
                matchup = self.get_team_matchup_detailed(team_key, week)
                if matchup:
                    # Check if this matchup involves the opponent
                    opponent = matchup.get_team_opponent(team_key)
                    if opponent and opponent.team_key == opponent_team_key:
                        team_score = matchup.team1 if matchup.team1.team_key == team_key else matchup.team2
                        
                        matchup_history.append({
                            "week": week,
                            "team_points": team_score.points,
                            "opponent_points": opponent.points,
                            "margin": team_score.points - opponent.points,
                            "result": "W" if team_score.points > opponent.points 
                                    else "L" if team_score.points < opponent.points 
                                    else "T",
                            "is_playoffs": matchup.is_playoffs
                        })
                        
            except Exception as e:
                print(f"Warning: Failed to check week {week} matchup history: {e}")
                continue
        
        return matchup_history

    def calculate_team_strength_of_schedule(
        self, 
        team_key: str,
        weeks: Optional[Union[list[int], range]] = None
    ) -> dict[str, float]:
        """
        Calculate strength of schedule based on opponent scoring averages.

        Args:
            team_key: Team key (e.g., 'nfl.l.12345.t.1')
            weeks: Week numbers to analyze (default: weeks 1-14)

        Returns:
            Dictionary with strength of schedule metrics
        """

        if weeks is None:
            weeks = range(1, 15)

        opponent_scores = []
        total_games = 0
        
        for week in weeks:
            try:
                matchup = self.get_team_matchup_detailed(team_key, week)
                if matchup and matchup.status == "postevent":
                    opponent = matchup.get_team_opponent(team_key)
                    if opponent:
                        opponent_scores.append(opponent.points)
                        total_games += 1
                        
            except Exception as e:
                print(f"Warning: Failed to analyze week {week} for SOS: {e}")
                continue
        
        if not opponent_scores:
            return {
                "average_opponent_score": 0.0,
                "total_opponent_points": 0.0,
                "games_analyzed": 0
            }

        return {
            "average_opponent_score": sum(opponent_scores) / len(opponent_scores),
            "total_opponent_points": sum(opponent_scores),
            "games_analyzed": total_games
        }

    def get_team_roster(self, team_key: str, week: int) -> TeamRoster:
        """
        Get team roster with player statistics for a specific week.

        Args:
            team_key: Team key (e.g., 'nfl.l.12345.t.1')
            week: Week number

        Returns:
            TeamRoster object with all player statistics
        """

        path = f"team/{team_key}/roster/players/stats"
        params = {"week": str(week)}

        try:
            response = self.http.get(path, params)

            # Extract team and roster data
            team_data = extract_nested_value(response, "fantasy_content", "team")
            if not team_data or not isinstance(team_data, list):
                raise ValueError("Invalid team roster response structure")

            # Get team basic info from first element
            team_properties = team_data[0] if isinstance(team_data[0], list) else []
            team_info = {}
            for prop in team_properties:
                if isinstance(prop, dict):
                    team_info.update(prop)

            # Get roster data from second element (if present)
            roster_data = {}
            if len(team_data) > 1 and isinstance(team_data[1], dict):
                roster_data = team_data[1]

            team_name = team_info.get("name", "Unknown Team")
            return TeamRoster.from_api_data(roster_data, team_key, team_name, week)

        except Exception as e:
            raise RuntimeError(f"Failed to fetch team roster for {team_key} week {week}: {e}") from e

    def get_multiple_team_rosters(self, team_keys: list[str], week: int) -> dict[str, TeamRoster]:
        """
        Get rosters for multiple teams for a specific week.

        Args:
            team_keys: List of team keys
            week: Week number

        Returns:
            Dictionary mapping team keys to TeamRoster objects
        """

        rosters = {}
        
        for team_key in team_keys:
            try:
                roster = self.get_team_roster(team_key, week)
                rosters[team_key] = roster
            except Exception as e:
                print(f"Warning: Failed to fetch roster for {team_key}: {e}")
                continue
        
        return rosters

    def get_detailed_matchup(self, team1_key: str, team2_key: str, week: int) -> "DetailedMatchup":
        """
        Get detailed head-to-head matchup comparison between two teams.

        Args:
            team1_key: First team key
            team2_key: Second team key  
            week: Week number

        Returns:
            DetailedMatchup object with position-by-position comparison
        """
        
        from ..models.detailed_matchup import DetailedMatchup
        
        try:
            # Get rosters for both teams
            team1_roster = self.get_team_roster(team1_key, week)
            team2_roster = self.get_team_roster(team2_key, week)
            
            # Create detailed matchup
            return DetailedMatchup.create(
                team1_roster=team1_roster,
                team2_roster=team2_roster,
                week=week,
                matchup_id=f"{team1_key}_vs_{team2_key}_week_{week}"
            )
            
        except Exception as e:
            raise RuntimeError(f"Failed to create detailed matchup for {team1_key} vs {team2_key} week {week}: {e}") from e
