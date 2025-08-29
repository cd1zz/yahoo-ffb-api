"""
Draft-related models for Yahoo Fantasy Sports API.
"""

from typing import Any, Optional

from pydantic import Field

from .common import YahooResource, safe_int, safe_str


class DraftPick(YahooResource):
    """Individual draft pick information."""

    pick: int = Field(description="Overall pick number")
    round: int = Field(description="Draft round")
    team_key: str = Field(description="Team that made the pick")
    player_key: str = Field(description="Player that was picked")
    cost: Optional[int] = Field(None, description="Cost in auction drafts")

    # Additional player info (when available)
    player_name: Optional[str] = Field(None, description="Player full name")
    player_position: Optional[str] = Field(None, description="Player position")
    player_team: Optional[str] = Field(None, description="NFL/NBA team")
    
    # Additional team info (when available)
    team_name: Optional[str] = Field(None, description="Fantasy team name")

    @classmethod
    def from_api_data(cls, data: dict[str, Any]) -> "DraftPick":
        """Create DraftPick from Yahoo API response data."""
        return cls(
            pick=safe_int(data.get("pick", 0)),
            round=safe_int(data.get("round", 0)),
            team_key=safe_str(data.get("team_key", "")),
            player_key=safe_str(data.get("player_key", "")),
            cost=safe_int(data.get("cost")) if data.get("cost") is not None else None,
            # Names will be populated separately by lookup
            player_name=data.get("player_name"),
            player_position=data.get("player_position"), 
            player_team=data.get("player_team"),
            team_name=data.get("team_name"),
        )


class DraftResult(YahooResource):
    """Complete draft results for a league."""

    league_key: str = Field(description="League key")
    draft_picks: list[DraftPick] = Field(
        default_factory=list, description="List of all draft picks"
    )
    is_draft_done: bool = Field(default=False, description="Whether draft is complete")

    @classmethod
    def from_api_data(cls, data: dict[str, Any]) -> "DraftResult":
        """Create DraftResult from Yahoo API response data."""

        # Extract draft results from nested structure
        draft_results = []

        # Yahoo API structure: fantasy_content -> league -> draft_results -> "0"/"1"/"2"/etc -> draft_result
        draft_data = data.get("draft_results", {})
        if isinstance(draft_data, dict):
            # Iterate through numbered keys ("0", "1", "2", etc.)
            for key, pick_data in draft_data.items():
                if key == "count":  # Skip the count field
                    continue
                    
                if isinstance(pick_data, dict) and "draft_result" in pick_data:
                    result = pick_data["draft_result"]
                    if isinstance(result, dict):
                        draft_results.append(DraftPick.from_api_data(result))

        return cls(
            league_key=safe_str(data.get("league_key", "")),
            draft_picks=draft_results,
            is_draft_done=len(draft_results) > 0,  # Simple heuristic
        )


class DraftAnalysis(YahooResource):
    """Analysis of draft picks and trends."""

    league_key: str = Field(description="League key")
    total_picks: int = Field(description="Total draft picks made")
    picks_by_position: dict[str, int] = Field(
        default_factory=dict, description="Pick count by position"
    )
    picks_by_round: dict[int, int] = Field(
        default_factory=dict, description="Pick count by round"
    )
    average_draft_position: dict[str, float] = Field(
        default_factory=dict, description="ADP by player"
    )

    @classmethod
    def from_draft_picks(
        cls, league_key: str, picks: list[DraftPick]
    ) -> "DraftAnalysis":
        """Create analysis from list of draft picks."""

        picks_by_position: dict[str, int] = {}
        picks_by_round: dict[int, int] = {}

        for pick in picks:
            # Count by position (if available)
            if pick.player_position:
                picks_by_position[pick.player_position] = (
                    picks_by_position.get(pick.player_position, 0) + 1
                )

            # Count by round
            picks_by_round[pick.round] = picks_by_round.get(pick.round, 0) + 1

        return cls(
            league_key=league_key,
            total_picks=len(picks),
            picks_by_position=picks_by_position,
            picks_by_round=picks_by_round,
        )
