"""
Team-related models for Yahoo Fantasy Sports API.
"""

from typing import Any, Optional

from pydantic import Field

from .common import YahooResource, safe_float, safe_int, safe_str
from .player import Player


class TeamStats(YahooResource):
    """Team statistics for a time period."""

    team_key: str = Field(description="Team key")
    week: Optional[int] = Field(None, description="Week number")
    season: Optional[str] = Field(None, description="Season year")
    points: dict[str, float] = Field(
        default_factory=dict, description="Points by category"
    )

    @classmethod
    def from_api_data(cls, data: dict[str, Any]) -> "TeamStats":
        """Create TeamStats from Yahoo API response data."""

        points_dict = {}
        stats_data = data.get("team_stats", {})
        if isinstance(stats_data, dict):
            stats_list = stats_data.get("stats", {}).get("stat", [])
            if not isinstance(stats_list, list):
                stats_list = [stats_list]

            for stat in stats_list:
                if isinstance(stat, dict):
                    stat_id = stat.get("stat_id")
                    value = safe_float(stat.get("value", 0))
                    if stat_id is not None:
                        points_dict[str(stat_id)] = value

        return cls(
            team_key=safe_str(data.get("team_key", "")),
            week=safe_int(data.get("week")) if data.get("week") is not None else None,
            season=data.get("season"),
            points=points_dict,
        )


class RosterPlayer(YahooResource):
    """Player on a team's roster with position info."""

    player: Player = Field(description="Player information")
    selected_position: str = Field(description="Position player is slotted in")
    is_starter: bool = Field(
        default=False, description="Whether player is in starting lineup"
    )

    @classmethod
    def from_api_data(cls, data: dict[str, Any]) -> "RosterPlayer":
        """Create RosterPlayer from Yahoo API response data."""

        # Extract player data
        player_data = data.get("player", {})
        if isinstance(player_data, list) and player_data:
            # Yahoo sometimes wraps player data in list
            player_data = player_data[0] if len(player_data) == 1 else {}

        player = Player.from_api_data(player_data)

        # Extract selected position
        selected_position = data.get("selected_position", {})
        if isinstance(selected_position, dict):
            position = selected_position.get("position", "")
        else:
            position = str(selected_position)

        is_starter = position not in ["BN", "IR", "IR+"]  # Common bench/IR positions

        return cls(
            player=player,
            selected_position=safe_str(position),
            is_starter=is_starter,
        )


class Team(YahooResource):
    """Fantasy team information."""

    team_key: str = Field(description="Unique team key")
    team_id: str = Field(description="Team ID")
    name: str = Field(description="Team name")
    url: Optional[str] = Field(None, description="Team page URL")
    team_logo: Optional[str] = Field(None, description="Team logo URL")
    waiver_priority: Optional[int] = Field(None, description="Current waiver priority")
    faab_balance: Optional[int] = Field(None, description="FAAB balance remaining")
    number_of_moves: Optional[int] = Field(None, description="Number of moves made")
    number_of_trades: Optional[int] = Field(None, description="Number of trades made")

    # Manager info
    managers: list[dict[str, Any]] = Field(
        default_factory=list, description="Team managers"
    )

    # League context
    league_key: Optional[str] = Field(None, description="League this team belongs to")

    # Roster (loaded separately)
    roster: Optional[list[RosterPlayer]] = Field(None, description="Current roster")

    @classmethod
    def from_api_data(cls, data: dict[str, Any]) -> "Team":
        """Create Team from Yahoo API response data."""

        # Parse managers
        managers = []
        managers_data = data.get("managers", [])
        if isinstance(managers_data, list):
            for manager_container in managers_data:
                if isinstance(manager_container, dict) and "manager" in manager_container:
                    manager_info = manager_container["manager"]
                    managers.append(manager_info)
        elif isinstance(managers_data, dict):
            # Fallback for different structure
            manager_list = managers_data.get("manager", [])
            if not isinstance(manager_list, list):
                manager_list = [manager_list]
            managers = manager_list

        return cls(
            team_key=safe_str(data.get("team_key", "")),
            team_id=safe_str(data.get("team_id", "")),
            name=safe_str(data.get("name", "")),
            url=data.get("url"),
            team_logo=data.get("team_logo"),
            waiver_priority=(
                safe_int(data.get("waiver_priority"))
                if data.get("waiver_priority") is not None
                else None
            ),
            faab_balance=(
                safe_int(data.get("faab_balance"))
                if data.get("faab_balance") is not None
                else None
            ),
            number_of_moves=(
                safe_int(data.get("number_of_moves"))
                if data.get("number_of_moves") is not None
                else None
            ),
            number_of_trades=(
                safe_int(data.get("number_of_trades"))
                if data.get("number_of_trades") is not None
                else None
            ),
            managers=managers,
        )


class TeamStandings(YahooResource):
    """Team standings information."""

    team: Team = Field(description="Team information")
    rank: int = Field(description="Current league rank")
    wins: int = Field(default=0, description="Wins")
    losses: int = Field(default=0, description="Losses")
    ties: int = Field(default=0, description="Ties")
    points_for: float = Field(default=0.0, description="Total points scored")
    points_against: float = Field(default=0.0, description="Total points against")

    @classmethod
    def from_api_data(cls, data: dict[str, Any]) -> "TeamStandings":
        """Create TeamStandings from Yahoo API response data."""

        # Extract team data
        team_data = data.get("team", {})
        if isinstance(team_data, list) and team_data:
            team_data = team_data[0]

        team = Team.from_api_data(team_data)

        # Extract standings data
        standings_data = data.get("team_standings", {})
        if isinstance(standings_data, dict):
            outcomes = standings_data.get("outcome_totals", {})
            points_data = standings_data.get("points_for", 0)
            points_against_data = standings_data.get("points_against", 0)

            return cls(
                team=team,
                rank=safe_int(standings_data.get("rank", 0)),
                wins=(
                    safe_int(outcomes.get("wins", 0))
                    if isinstance(outcomes, dict)
                    else 0
                ),
                losses=(
                    safe_int(outcomes.get("losses", 0))
                    if isinstance(outcomes, dict)
                    else 0
                ),
                ties=(
                    safe_int(outcomes.get("ties", 0))
                    if isinstance(outcomes, dict)
                    else 0
                ),
                points_for=safe_float(points_data),
                points_against=safe_float(points_against_data),
            )

        return cls(
            team=team,
            rank=0,
            wins=0,
            losses=0,
            ties=0,
            points_for=0.0,
            points_against=0.0,
        )
