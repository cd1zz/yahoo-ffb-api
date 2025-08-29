"""
League-related models for Yahoo Fantasy Sports API.
"""

from typing import Any, Optional

from pydantic import Field

from .common import YahooResource, safe_float, safe_int, safe_str


class RosterPosition(YahooResource):
    """Fantasy league roster position configuration."""

    position: str = Field(description="Position type (QB, RB, WR, etc.)")
    position_type: Optional[str] = Field(None, description="Position type category")
    count: int = Field(description="Number of players at this position")
    is_starting_position: bool = Field(
        default=True, description="Whether this is a starting position"
    )


class PlayoffWeek(YahooResource):
    """Playoff week configuration."""

    week: int = Field(description="Week number")
    start: Optional[str] = Field(None, description="Start date")
    end: Optional[str] = Field(None, description="End date")


class StatModifier(YahooResource):
    """Scoring stat modifier."""

    stat_id: int = Field(description="Stat ID")
    value: float = Field(description="Point value for this stat")


class ScoringType(YahooResource):
    """League scoring type configuration."""

    type: str = Field(description="Scoring type (head-to-head, total points, etc.)")
    is_playoff_reseeding_enabled: Optional[bool] = Field(
        None, description="Playoff reseeding enabled"
    )
    playoff_weeks: Optional[list[PlayoffWeek]] = Field(
        None, description="Playoff week configuration"
    )


class LeagueSettings(YahooResource):
    """Fantasy league settings and configuration."""

    league_id: str = Field(description="League ID")
    league_key: str = Field(description="Unique league key")
    name: str = Field(description="League name")
    url: Optional[str] = Field(None, description="League URL")
    logo_url: Optional[str] = Field(None, description="League logo URL")
    password: Optional[str] = Field(None, description="League password (if public)")
    draft_status: Optional[str] = Field(None, description="Draft status")
    num_teams: int = Field(description="Number of teams in league")
    edit_key: Optional[str] = Field(None, description="Edit key for modifications")
    weekly_deadline: Optional[str] = Field(None, description="Weekly deadline")
    league_update_timestamp: Optional[str] = Field(
        None, description="Last update timestamp"
    )
    scoring_type: Optional[str] = Field(None, description="Scoring type")
    league_type: Optional[str] = Field(None, description="League type (private/public)")
    renew: Optional[str] = Field(None, description="League renewal key")
    renewed: Optional[str] = Field(None, description="Renewed from league key")
    iris_group_chat_id: Optional[str] = Field(None, description="Group chat ID")
    allow_add_to_dl_extra_pos: Optional[bool] = Field(
        None, description="Allow add to DL extra position"
    )
    is_pro_league: Optional[bool] = Field(None, description="Pro league status")
    is_cash_league: Optional[bool] = Field(None, description="Cash league status")
    current_week: Optional[int] = Field(None, description="Current week number")
    start_week: Optional[int] = Field(None, description="Start week")
    start_date: Optional[str] = Field(None, description="Season start date")
    end_week: Optional[int] = Field(None, description="End week")
    end_date: Optional[str] = Field(None, description="Season end date")
    game_code: Optional[str] = Field(None, description="Game code (nfl, nba, etc.)")
    season: Optional[str] = Field(None, description="Season year")

    # Roster settings
    roster_positions: list[RosterPosition] = Field(
        default_factory=list, description="Roster position requirements"
    )

    # Scoring settings
    stat_categories: Optional[list[dict[str, Any]]] = Field(
        None, description="Stat category definitions"
    )
    stat_modifiers: Optional[list[StatModifier]] = Field(
        None, description="Scoring modifiers"
    )

    # Waiver settings
    waiver_type: Optional[str] = Field(None, description="Waiver wire type")
    waiver_rule: Optional[str] = Field(None, description="Waiver wire rule")
    use_faab: Optional[bool] = Field(
        None, description="Use FAAB (Free Agent Acquisition Budget)"
    )
    draft_time: Optional[str] = Field(None, description="Draft time")
    draft_pick_time: Optional[str] = Field(None, description="Draft pick time limit")
    post_draft_players: Optional[str] = Field(
        None, description="Post-draft player status"
    )
    max_teams: Optional[int] = Field(None, description="Maximum teams allowed")
    waiver_time: Optional[str] = Field(None, description="Waiver processing time")
    trade_end_date: Optional[str] = Field(None, description="Trade deadline")
    trade_ratify_type: Optional[str] = Field(
        None, description="Trade ratification type"
    )
    trade_reject_time: Optional[str] = Field(None, description="Trade rejection time")

    @classmethod
    def from_api_data(cls, data: dict[str, Any]) -> "LeagueSettings":
        """Create LeagueSettings from Yahoo API response data."""

        # Extract settings from nested structure
        settings_data = data.get("settings", {})
        if isinstance(settings_data, list) and settings_data:
            settings_data = settings_data[0]

        # Parse roster positions
        roster_positions = []
        roster_data = settings_data.get("roster_positions", [])
        
        if isinstance(roster_data, list):
            # Handle Yahoo's structure: roster_positions is a list of {roster_position: {...}}
            for item in roster_data:
                if isinstance(item, dict) and "roster_position" in item:
                    pos_data = item["roster_position"]
                    roster_positions.append(
                        RosterPosition(
                            position=safe_str(pos_data.get("position", "")),
                            position_type=pos_data.get("position_type"),
                            count=safe_int(pos_data.get("count", 0)),
                            is_starting_position=bool(pos_data.get("is_starting_position", True)),
                        )
                    )
        elif isinstance(roster_data, dict):
            # Fallback for different structure
            positions_list = roster_data.get("roster_position", [])
            if not isinstance(positions_list, list):
                positions_list = [positions_list]

            for pos_data in positions_list:
                if isinstance(pos_data, dict):
                    roster_positions.append(
                        RosterPosition(
                            position=safe_str(pos_data.get("position", "")),
                            position_type=pos_data.get("position_type"),
                            count=safe_int(pos_data.get("count", 0)),
                            is_starting_position=bool(pos_data.get("is_starting_position", True)),
                        )
                    )

        # Parse stat modifiers/categories for scoring
        stat_modifiers = []
        stat_cats_data = settings_data.get("stat_categories", {})
        if isinstance(stat_cats_data, dict):
            stats_data = stat_cats_data.get("stats", {})
            if isinstance(stats_data, dict):
                stats_list = stats_data.get("stat", [])
                if not isinstance(stats_list, list):
                    stats_list = [stats_list]

                for stat_data in stats_list:
                    if isinstance(stat_data, dict):
                        stat_modifiers.append(
                            StatModifier(
                                stat_id=safe_int(stat_data.get("stat_id", 0)),
                                value=safe_float(stat_data.get("value", 0.0)),
                            )
                        )

        # Handle logo_url which can be False or a string
        logo_url = data.get("logo_url")
        if logo_url is False or logo_url is None:
            logo_url = None
        else:
            logo_url = safe_str(logo_url)

        # Handle url which can be False or a string  
        url = data.get("url")
        if url is False or url is None:
            url = None
        else:
            url = safe_str(url)

        return cls(
            league_id=safe_str(data.get("league_id", "")),
            league_key=safe_str(data.get("league_key", "")),
            name=safe_str(data.get("name", "")),
            url=url,
            logo_url=logo_url,
            password=data.get("password"),
            draft_status=data.get("draft_status"),
            num_teams=safe_int(data.get("num_teams", 0)),
            edit_key=data.get("edit_key"),
            weekly_deadline=data.get("weekly_deadline"),
            league_update_timestamp=data.get("league_update_timestamp"),
            scoring_type=data.get("scoring_type"),
            league_type=data.get("league_type"),
            renew=data.get("renew"),
            renewed=data.get("renewed"),
            iris_group_chat_id=data.get("iris_group_chat_id"),
            allow_add_to_dl_extra_pos=data.get("allow_add_to_dl_extra_pos"),
            is_pro_league=data.get("is_pro_league"),
            is_cash_league=data.get("is_cash_league"),
            current_week=safe_int(data.get("current_week")),
            start_week=safe_int(data.get("start_week")),
            start_date=data.get("start_date"),
            end_week=safe_int(data.get("end_week")),
            end_date=data.get("end_date"),
            game_code=data.get("game_code"),
            season=data.get("season"),
            roster_positions=roster_positions,
            stat_modifiers=stat_modifiers,
            waiver_type=settings_data.get("waiver_type"),
            waiver_rule=settings_data.get("waiver_rule"),
            use_faab=settings_data.get("use_faab"),
            draft_time=settings_data.get("draft_time"),
            draft_pick_time=settings_data.get("draft_pick_time"),
            post_draft_players=settings_data.get("post_draft_players"),
            max_teams=safe_int(settings_data.get("max_teams")),
            waiver_time=settings_data.get("waiver_time"),
            trade_end_date=settings_data.get("trade_end_date"),
            trade_ratify_type=settings_data.get("trade_ratify_type"),
            trade_reject_time=settings_data.get("trade_reject_time"),
        )


class LeagueStandings(YahooResource):
    """League standings information."""

    league_key: str = Field(description="League key")
    teams: list[dict[str, Any]] = Field(
        default_factory=list, description="Team standings data"
    )


class League(YahooResource):
    """Complete league information."""

    league_key: str = Field(description="Unique league key")
    league_id: str = Field(description="League ID")
    name: str = Field(description="League name")
    url: Optional[str] = Field(None, description="League URL")
    logo_url: Optional[str] = Field(None, description="League logo URL")
    draft_status: Optional[str] = Field(None, description="Draft status")
    num_teams: int = Field(description="Number of teams")
    scoring_type: Optional[str] = Field(None, description="Scoring type")
    league_type: Optional[str] = Field(None, description="League type")
    season: Optional[str] = Field(None, description="Season year")
    game_code: Optional[str] = Field(None, description="Game code")

    # Optional detailed settings (loaded separately)
    settings: Optional[LeagueSettings] = Field(
        None, description="Detailed league settings"
    )

    @classmethod
    def from_api_data(cls, data: dict[str, Any]) -> "League":
        """Create League from Yahoo API response data."""
        # Handle logo_url which can be False or a string
        logo_url = data.get("logo_url")
        if logo_url is False or logo_url is None:
            logo_url = None
        else:
            logo_url = safe_str(logo_url)
            
        return cls(
            league_key=safe_str(data.get("league_key", "")),
            league_id=safe_str(data.get("league_id", "")),
            name=safe_str(data.get("name", "")),
            url=safe_str(data.get("url")) if data.get("url") else None,
            logo_url=logo_url,
            draft_status=safe_str(data.get("draft_status")) if data.get("draft_status") else None,
            num_teams=safe_int(data.get("num_teams", 0)),
            scoring_type=safe_str(data.get("scoring_type")) if data.get("scoring_type") else None,
            league_type=safe_str(data.get("league_type")) if data.get("league_type") else None,
            season=safe_str(data.get("season")) if data.get("season") else None,
            game_code=safe_str(data.get("game_code")) if data.get("game_code") else None,
        )
