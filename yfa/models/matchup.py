"""
Matchup and scoreboard models for Yahoo Fantasy Sports API.
"""

from typing import Any, Optional

from pydantic import Field

from .common import YahooResource


class TeamScore(YahooResource):
    """Individual team's score and performance for a specific week."""

    team_key: str = Field(description="Team key")
    team_id: str = Field(description="Team ID")
    team_name: str = Field(description="Team name")
    week: int = Field(description="Week number")
    points: float = Field(description="Points scored this week")
    projected_points: Optional[float] = Field(None, description="Projected points")
    
    # Roster performance details
    roster_positions: list[dict[str, Any]] = Field(
        default_factory=list, description="Starting roster and bench performance"
    )
    
    # Status information
    is_tied: bool = Field(default=False, description="Whether this matchup ended in a tie")
    is_playoffs: bool = Field(default=False, description="Whether this is a playoff game")
    
    @classmethod
    def from_api_data(cls, data: dict[str, Any]) -> "TeamScore":
        """Create TeamScore from Yahoo API response data."""
        
        # Handle Yahoo's complex nested team structure
        team_key = ""
        team_id = ""
        team_name = ""
        points = 0.0
        projected_points = None
        
        if isinstance(data, list) and len(data) >= 2:
            # First element contains team info array
            team_info_list = data[0] if isinstance(data[0], list) else []
            # Second element contains points and stats
            stats_info = data[1] if isinstance(data[1], dict) else {}
            
            # Extract team basic info from the array
            for item in team_info_list:
                if isinstance(item, dict):
                    if "team_key" in item:
                        team_key = item["team_key"]
                    elif "team_id" in item:
                        team_id = str(item["team_id"])
                    elif "name" in item:
                        team_name = item["name"]
            
            # Extract points from stats
            team_points_info = stats_info.get("team_points", {})
            if isinstance(team_points_info, dict):
                points = float(team_points_info.get("total", 0))
            
            # Extract projected points
            team_projected_info = stats_info.get("team_projected_points", {})
            if isinstance(team_projected_info, dict):
                projected_total = team_projected_info.get("total")
                if projected_total is not None:
                    projected_points = float(projected_total)
        
        return cls(
            team_key=team_key,
            team_id=team_id,
            team_name=team_name,
            week=0,  # Will be set by caller
            points=points,
            projected_points=projected_points,
            roster_positions=[],
            is_tied=False,
            is_playoffs=False
        )


class Matchup(YahooResource):
    """Individual matchup between two teams for a specific week."""

    week: int = Field(description="Week number")
    matchup_id: Optional[str] = Field(None, description="Unique matchup identifier")
    
    # Team information
    team1: TeamScore = Field(description="First team in matchup")
    team2: TeamScore = Field(description="Second team in matchup")
    
    # Matchup results
    winner_team_key: Optional[str] = Field(None, description="Winning team key")
    margin_of_victory: float = Field(default=0.0, description="Point margin of victory")
    is_tied: bool = Field(default=False, description="Whether matchup ended in tie")
    
    # Status and metadata
    status: str = Field(default="unknown", description="Matchup status (pregame, midevent, postevent)")
    is_playoffs: bool = Field(default=False, description="Whether this is a playoff matchup")
    playoff_tier: Optional[int] = Field(None, description="Playoff tier (1=championship, 2=3rd place, etc.)")
    is_consolation: bool = Field(default=False, description="Whether this is consolation bracket")
    
    @classmethod
    def from_api_data(cls, data: dict[str, Any], week: int) -> "Matchup":
        """Create Matchup from Yahoo API matchup data."""
        
        matchup_info = data.get("matchup", {}) if "matchup" in data else data
        
        # Extract teams data - it's nested in "0" -> "teams"
        teams_container = matchup_info.get("0", {})
        teams_data = teams_container.get("teams", {})
        
        # Extract individual team data  
        team1_data = teams_data.get("0", {}).get("team", [])
        team2_data = teams_data.get("1", {}).get("team", [])
        
        # Create team scores
        team1 = TeamScore.from_api_data(team1_data)
        team1.week = week
        
        team2 = TeamScore.from_api_data(team2_data) 
        team2.week = week
        
        # Determine winner and margin
        winner_team_key = matchup_info.get("winner_team_key")
        margin = abs(team1.points - team2.points)
        is_tied = bool(matchup_info.get("is_tied", 0)) or team1.points == team2.points
        
        # Extract status information
        status = matchup_info.get("status", "unknown")
        is_playoffs = bool(matchup_info.get("is_playoffs", 0))
        is_consolation = bool(matchup_info.get("is_consolation", 0))
        
        return cls(
            week=week,
            matchup_id=str(matchup_info.get("week", week)),  # Use week as ID if no specific ID
            team1=team1,
            team2=team2,
            winner_team_key=winner_team_key,
            margin_of_victory=margin,
            is_tied=is_tied,
            status=status,
            is_playoffs=is_playoffs,
            playoff_tier=None,
            is_consolation=is_consolation
        )
    
    def get_winning_team(self) -> Optional[TeamScore]:
        """Get the winning team, or None if tied."""
        if self.is_tied:
            return None
        return self.team1 if self.team1.points > self.team2.points else self.team2
    
    def get_losing_team(self) -> Optional[TeamScore]:
        """Get the losing team, or None if tied."""
        if self.is_tied:
            return None
        return self.team2 if self.team1.points > self.team2.points else self.team1
    
    def get_team_opponent(self, team_key: str) -> Optional[TeamScore]:
        """Get the opponent of the specified team."""
        if self.team1.team_key == team_key:
            return self.team2
        elif self.team2.team_key == team_key:
            return self.team1
        return None


class WeeklyScoreboard(YahooResource):
    """Complete scoreboard for all matchups in a specific week."""

    week: int = Field(description="Week number")
    league_key: str = Field(description="League key")
    
    # Matchup data
    matchups: list[Matchup] = Field(default_factory=list, description="All matchups for this week")
    
    # Week metadata
    is_current_week: bool = Field(default=False, description="Whether this is the current week")
    week_start: Optional[str] = Field(None, description="Week start date")
    week_end: Optional[str] = Field(None, description="Week end date")
    
    @classmethod
    def from_api_data(cls, data: dict[str, Any], league_key: str, week: int) -> "WeeklyScoreboard":
        """Create WeeklyScoreboard from Yahoo API scoreboard response."""
        
        # Extract scoreboard data - it's directly nested in the league data
        scoreboard_data = data.get("scoreboard", {})
        
        # Handle different response structures
        if "0" in scoreboard_data:
            scoreboard_info = scoreboard_data["0"]
        else:
            scoreboard_info = scoreboard_data
            
        matchups_data = scoreboard_info.get("matchups", {})
        
        matchups = []
        
        # Process each matchup
        if isinstance(matchups_data, dict):
            for matchup_key, matchup_data in matchups_data.items():
                if matchup_key == "count":  # Skip count field
                    continue
                    
                try:
                    # The matchup data is nested under "matchup" key
                    if isinstance(matchup_data, dict) and "matchup" in matchup_data:
                        matchup = Matchup.from_api_data(matchup_data, week)
                        matchups.append(matchup)
                except Exception as e:
                    # Log warning but continue processing other matchups
                    print(f"Warning: Failed to parse matchup {matchup_key}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        
        # Extract week metadata from the first matchup if available
        week_start = None
        week_end = None
        if matchups_data:
            # Get the first matchup data to extract week info
            first_matchup_key = next(
                (k for k in matchups_data.keys() if k != "count"), 
                None
            )
            if first_matchup_key:
                first_matchup = matchups_data[first_matchup_key]
                if isinstance(first_matchup, dict) and "matchup" in first_matchup:
                    matchup_info = first_matchup["matchup"]
                    week_start = matchup_info.get("week_start")
                    week_end = matchup_info.get("week_end")
        
        return cls(
            week=week,
            league_key=league_key,
            matchups=matchups,
            week_start=week_start,
            week_end=week_end
        )
    
    def get_matchup_by_team(self, team_key: str) -> Optional[Matchup]:
        """Get the matchup for a specific team."""
        for matchup in self.matchups:
            if matchup.team1.team_key == team_key or matchup.team2.team_key == team_key:
                return matchup
        return None
    
    def get_team_score(self, team_key: str) -> Optional[TeamScore]:
        """Get a team's score for this week."""
        matchup = self.get_matchup_by_team(team_key)
        if matchup:
            if matchup.team1.team_key == team_key:
                return matchup.team1
            elif matchup.team2.team_key == team_key:
                return matchup.team2
        return None
    
    def get_highest_score(self) -> Optional[TeamScore]:
        """Get the highest scoring team this week."""
        if not self.matchups:
            return None
            
        highest_team = None
        highest_points = -1.0
        
        for matchup in self.matchups:
            for team in [matchup.team1, matchup.team2]:
                if team.points > highest_points:
                    highest_points = team.points
                    highest_team = team
        
        return highest_team
    
    def get_matchups_by_margin(self, min_margin: float = 20.0) -> list[Matchup]:
        """Get matchups with victory margin >= specified threshold."""
        return [
            matchup for matchup in self.matchups 
            if not matchup.is_tied and matchup.margin_of_victory >= min_margin
        ]
    
    def get_playoff_matchups(self) -> list[Matchup]:
        """Get only playoff matchups."""
        return [matchup for matchup in self.matchups if matchup.is_playoffs]


class SeasonResults(YahooResource):
    """Complete season results with all weekly scoreboards."""
    
    league_key: str = Field(description="League key")
    season: str = Field(description="Season year")
    
    # Weekly data
    weekly_scoreboards: dict[int, WeeklyScoreboard] = Field(
        default_factory=dict, description="Scoreboard for each week (week number -> scoreboard)"
    )
    
    def add_week(self, scoreboard: WeeklyScoreboard) -> None:
        """Add a weekly scoreboard to the season results."""
        self.weekly_scoreboards[scoreboard.week] = scoreboard
    
    def get_team_record(self, team_key: str) -> dict[str, int]:
        """Get a team's win-loss record for the season."""
        wins = losses = ties = 0
        
        for week_num, scoreboard in self.weekly_scoreboards.items():
            matchup = scoreboard.get_matchup_by_team(team_key)
            if matchup and matchup.status == "postevent":
                if matchup.is_tied:
                    ties += 1
                elif matchup.winner_team_key == team_key:
                    wins += 1
                else:
                    losses += 1
        
        return {"wins": wins, "losses": losses, "ties": ties}
    
    def get_team_total_points(self, team_key: str) -> float:
        """Get a team's total points for the season."""
        total_points = 0.0
        
        for scoreboard in self.weekly_scoreboards.values():
            team_score = scoreboard.get_team_score(team_key)
            if team_score:
                total_points += team_score.points
                
        return total_points
    
    def get_team_weekly_scores(self, team_key: str) -> list[TeamScore]:
        """Get all weekly scores for a specific team."""
        scores = []
        
        for week_num in sorted(self.weekly_scoreboards.keys()):
            scoreboard = self.weekly_scoreboards[week_num]
            team_score = scoreboard.get_team_score(team_key)
            if team_score:
                scores.append(team_score)
        
        return scores
    
    def get_highest_weekly_scores(self) -> list[tuple[int, TeamScore]]:
        """Get the highest scoring team for each week."""
        highest_scores = []
        
        for week_num in sorted(self.weekly_scoreboards.keys()):
            scoreboard = self.weekly_scoreboards[week_num]
            highest_team = scoreboard.get_highest_score()
            if highest_team:
                highest_scores.append((week_num, highest_team))
        
        return highest_scores
