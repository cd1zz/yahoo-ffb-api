"""
Player-related models for Yahoo Fantasy Sports API.
"""

from typing import Any, Optional

from pydantic import Field

from .common import YahooResource, safe_float, safe_int, safe_str


class PlayerStats(YahooResource):
    """Player statistics for a specific time period."""

    player_key: str = Field(description="Player key")
    week: Optional[int] = Field(None, description="Week number (for weekly stats)")
    season: Optional[str] = Field(None, description="Season year")
    stats: dict[str, float] = Field(
        default_factory=dict, description="Statistical categories and values"
    )

    @classmethod
    def from_api_data(cls, data: dict[str, Any]) -> "PlayerStats":
        """Create PlayerStats from Yahoo API response data."""

        # Parse stats from nested structure
        stats_dict = {}
        stats_data = data.get("player_stats", {})
        if isinstance(stats_data, dict):
            stats_list = stats_data.get("stats", {}).get("stat", [])
            if not isinstance(stats_list, list):
                stats_list = [stats_list]

            for stat in stats_list:
                if isinstance(stat, dict):
                    stat_id = stat.get("stat_id")
                    value = safe_float(stat.get("value", 0))
                    if stat_id is not None:
                        stats_dict[str(stat_id)] = value

        return cls(
            player_key=safe_str(data.get("player_key", "")),
            week=safe_int(data.get("week")) if data.get("week") is not None else None,
            season=data.get("season"),
            stats=stats_dict,
        )


class Player(YahooResource):
    """Fantasy player information."""

    player_key: str = Field(description="Unique player key")
    player_id: str = Field(description="Player ID")
    name: str = Field(description="Player full name")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    ascii_first: Optional[str] = Field(None, description="ASCII version of first name")
    ascii_last: Optional[str] = Field(None, description="ASCII version of last name")

    # Position and team info
    primary_position: Optional[str] = Field(None, description="Primary position")
    eligible_positions: list[str] = Field(
        default_factory=list, description="All eligible positions"
    )
    uniform_number: Optional[int] = Field(None, description="Jersey number")
    display_position: Optional[str] = Field(None, description="Display position")

    # Team info
    team_name: Optional[str] = Field(None, description="NFL/NBA team name")
    team_abbr: Optional[str] = Field(None, description="Team abbreviation")
    team_key: Optional[str] = Field(None, description="Team key")

    # Status and metadata
    status: Optional[str] = Field(None, description="Player status")
    status_full: Optional[str] = Field(None, description="Full status description")
    injury_note: Optional[str] = Field(None, description="Injury information")
    editorial_player_key: Optional[str] = Field(
        None, description="Editorial player key"
    )
    editorial_team_key: Optional[str] = Field(None, description="Editorial team key")
    editorial_team_full_name: Optional[str] = Field(
        None, description="Editorial team full name"
    )
    editorial_team_abbr: Optional[str] = Field(
        None, description="Editorial team abbreviation"
    )

    # Fantasy-specific
    bye_weeks: dict[str, int] = Field(
        default_factory=dict, description="Bye weeks by game"
    )
    headshot_url: Optional[str] = Field(None, description="Player headshot URL")
    image_url: Optional[str] = Field(None, description="Player image URL")
    url: Optional[str] = Field(None, description="Player page URL")

    # Ownership info (when available)
    percent_owned: Optional[float] = Field(
        None, description="Percent owned across Yahoo"
    )
    percent_started: Optional[float] = Field(
        None, description="Percent started across Yahoo"
    )
    ownership_type: Optional[str] = Field(
        None, description="Ownership type (available, waivers, etc.)"
    )

    @classmethod
    def from_api_data(cls, data: dict[str, Any]) -> "Player":
        """Create Player from Yahoo API response data."""

        # Parse eligible positions
        eligible_positions = []
        positions_data = data.get("eligible_positions", {})
        if isinstance(positions_data, dict):
            pos_list = positions_data.get("position", [])
            if not isinstance(pos_list, list):
                pos_list = [pos_list]
            eligible_positions = [safe_str(pos) for pos in pos_list if pos]

        # Parse bye weeks
        bye_weeks = {}
        bye_data = data.get("bye_weeks", {})
        if isinstance(bye_data, dict):
            week_list = bye_data.get("week", [])
            if not isinstance(week_list, list):
                week_list = [week_list]
            for week_info in week_list:
                if isinstance(week_info, dict):
                    game = week_info.get("game")
                    week = safe_int(week_info.get("week", 0))
                    if game:
                        bye_weeks[game] = week

        return cls(
            player_key=safe_str(data.get("player_key", "")),
            player_id=safe_str(data.get("player_id", "")),
            name=safe_str(
                data.get("name", {}).get("full", "")
                if isinstance(data.get("name"), dict)
                else data.get("name", "")
            ),
            first_name=(
                data.get("name", {}).get("first")
                if isinstance(data.get("name"), dict)
                else None
            ),
            last_name=(
                data.get("name", {}).get("last")
                if isinstance(data.get("name"), dict)
                else None
            ),
            ascii_first=(
                data.get("name", {}).get("ascii_first")
                if isinstance(data.get("name"), dict)
                else None
            ),
            ascii_last=(
                data.get("name", {}).get("ascii_last")
                if isinstance(data.get("name"), dict)
                else None
            ),
            primary_position=data.get("primary_position"),
            eligible_positions=eligible_positions,
            uniform_number=(
                safe_int(data.get("uniform_number"))
                if data.get("uniform_number") is not None
                else None
            ),
            display_position=data.get("display_position"),
            team_name=data.get("team_name"),
            team_abbr=data.get("team_abbr"),
            team_key=data.get("team_key"),
            status=data.get("status"),
            status_full=data.get("status_full"),
            injury_note=data.get("injury_note"),
            editorial_player_key=data.get("editorial_player_key"),
            editorial_team_key=data.get("editorial_team_key"),
            editorial_team_full_name=data.get("editorial_team_full_name"),
            editorial_team_abbr=data.get("editorial_team_abbr"),
            bye_weeks=bye_weeks,
            headshot_url=(
                data.get("headshot", {}).get("url")
                if isinstance(data.get("headshot"), dict)
                else None
            ),
            image_url=data.get("image_url"),
            url=data.get("url"),
            percent_owned=(
                safe_float(data.get("percent_owned", {}).get("value"))
                if isinstance(data.get("percent_owned"), dict)
                else None
            ),
            percent_started=(
                safe_float(data.get("percent_started", {}).get("value"))
                if isinstance(data.get("percent_started"), dict)
                else None
            ),
            ownership_type=(
                data.get("ownership", {}).get("ownership_type")
                if isinstance(data.get("ownership"), dict)
                else None
            ),
        )


class PlayerSearch(YahooResource):
    """Player search results."""

    query: str = Field(description="Search query")
    players: list[Player] = Field(
        default_factory=list, description="List of matching players"
    )
    total_results: int = Field(description="Total number of results")

    @classmethod
    def from_api_data(cls, query: str, data: dict[str, Any]) -> "PlayerSearch":
        """Create PlayerSearch from Yahoo API response data."""

        players = []
        players_data = data.get("players", {})
        if isinstance(players_data, dict):
            player_list = players_data.get("player", [])
            if not isinstance(player_list, list):
                player_list = [player_list]

            for player_data in player_list:
                if isinstance(player_data, dict):
                    players.append(Player.from_api_data(player_data))

        return cls(
            query=query,
            players=players,
            total_results=len(players),
        )
