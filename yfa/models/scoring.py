"""
Scoring-related models for Yahoo Fantasy Sports API.
"""

from typing import Any, Optional

from pydantic import Field

from .common import YahooResource, safe_float, safe_int, safe_str


class StatCategory(YahooResource):
    """Statistical category definition."""

    stat_id: int = Field(description="Stat ID")
    name: str = Field(description="Stat name")
    display_name: Optional[str] = Field(None, description="Display name")
    sort_order: Optional[int] = Field(None, description="Sort order")
    position_type: Optional[str] = Field(
        None, description="Position type this stat applies to"
    )
    stat_position_types: Optional[list[str]] = Field(
        None, description="List of positions this stat applies to"
    )
    is_composite_stat: bool = Field(
        default=False, description="Whether this is a composite stat"
    )

    @classmethod
    def from_api_data(cls, data: dict[str, Any]) -> "StatCategory":
        """Create StatCategory from Yahoo API response data."""

        # Parse position types
        position_types = []
        pos_data = data.get("stat_position_types", {})
        if isinstance(pos_data, dict):
            types_list = pos_data.get("stat_position_type", [])
            if not isinstance(types_list, list):
                types_list = [types_list]
            position_types = [
                safe_str(t.get("position_type", ""))
                for t in types_list
                if isinstance(t, dict)
            ]

        return cls(
            stat_id=safe_int(data.get("stat_id", 0)),
            name=safe_str(data.get("name", "")),
            display_name=data.get("display_name"),
            sort_order=(
                safe_int(data.get("sort_order"))
                if data.get("sort_order") is not None
                else None
            ),
            position_type=data.get("position_type"),
            stat_position_types=position_types if position_types else None,
            is_composite_stat=bool(data.get("is_composite_stat", False)),
        )


class ScoringModifier(YahooResource):
    """Scoring modifier for a statistical category."""

    stat_id: int = Field(description="Stat ID")
    value: float = Field(description="Point value multiplier")

    @classmethod
    def from_api_data(cls, data: dict[str, Any]) -> "ScoringModifier":
        """Create ScoringModifier from Yahoo API response data."""
        return cls(
            stat_id=safe_int(data.get("stat_id", 0)),
            value=safe_float(data.get("value", 0.0)),
        )


class ScoringSettings(YahooResource):
    """Complete scoring settings for a league."""

    league_key: str = Field(description="League key")
    scoring_type: str = Field(
        description="Type of scoring (head-to-head, total points, etc.)"
    )
    stat_categories: list[StatCategory] = Field(
        default_factory=list, description="Available stat categories"
    )
    stat_modifiers: list[ScoringModifier] = Field(
        default_factory=list, description="Scoring modifiers"
    )
    uses_fractional_points: bool = Field(
        default=True, description="Whether fractional points are used"
    )
    uses_negative_points: bool = Field(
        default=False, description="Whether negative points are allowed"
    )

    @classmethod
    def from_api_data(cls, league_key: str, data: dict[str, Any]) -> "ScoringSettings":
        """Create ScoringSettings from Yahoo API response data."""

        # Parse stat categories
        stat_categories = []
        categories_data = data.get("stat_categories", {})
        if isinstance(categories_data, dict):
            stats_data = categories_data.get("stats", {})
            if isinstance(stats_data, dict):
                stat_list = stats_data.get("stat", [])
                if not isinstance(stat_list, list):
                    stat_list = [stat_list]

                for stat_data in stat_list:
                    if isinstance(stat_data, dict):
                        stat_categories.append(StatCategory.from_api_data(stat_data))

        # Parse stat modifiers
        stat_modifiers = []
        modifiers_data = data.get("stat_modifiers", {})
        if isinstance(modifiers_data, dict):
            stats_data = modifiers_data.get("stats", {})
            if isinstance(stats_data, dict):
                stat_list = stats_data.get("stat", [])
                if not isinstance(stat_list, list):
                    stat_list = [stat_list]

                for stat_data in stat_list:
                    if isinstance(stat_data, dict):
                        stat_modifiers.append(ScoringModifier.from_api_data(stat_data))

        return cls(
            league_key=league_key,
            scoring_type=safe_str(data.get("scoring_type", "")),
            stat_categories=stat_categories,
            stat_modifiers=stat_modifiers,
            uses_fractional_points=bool(data.get("uses_fractional_points", True)),
            uses_negative_points=bool(data.get("uses_negative_points", False)),
        )

    def get_modifier_value(self, stat_id: int) -> float:
        """Get the scoring modifier value for a stat ID."""
        for modifier in self.stat_modifiers:
            if modifier.stat_id == stat_id:
                return modifier.value
        return 0.0

    def get_category_name(self, stat_id: int) -> Optional[str]:
        """Get the category name for a stat ID."""
        for category in self.stat_categories:
            if category.stat_id == stat_id:
                return category.display_name or category.name
        return None

    def calculate_points(self, stats: dict[str, float]) -> float:
        """
        Calculate total fantasy points from raw stats.

        Args:
            stats: Dictionary mapping stat_id (as string) to raw value

        Returns:
            Total fantasy points
        """
        total_points = 0.0

        for stat_id_str, raw_value in stats.items():
            try:
                stat_id = int(stat_id_str)
                modifier_value = self.get_modifier_value(stat_id)
                total_points += raw_value * modifier_value
            except (ValueError, TypeError):
                continue

        return total_points


class PositionScoring(YahooResource):
    """Scoring settings specific to a position."""

    position: str = Field(description="Position (QB, RB, WR, etc.)")
    applicable_stats: list[int] = Field(
        default_factory=list, description="Stat IDs that apply to this position"
    )
    modifiers: dict[int, float] = Field(
        default_factory=dict, description="Stat ID to modifier mapping"
    )

    @classmethod
    def from_scoring_settings(
        cls, position: str, settings: ScoringSettings
    ) -> "PositionScoring":
        """Create PositionScoring from overall scoring settings."""

        applicable_stats = []
        modifiers = {}

        for category in settings.stat_categories:
            # Check if this stat applies to the position
            if category.position_type == position or (
                category.stat_position_types
                and position in category.stat_position_types
            ):

                applicable_stats.append(category.stat_id)

                # Get the modifier value
                modifier_value = settings.get_modifier_value(category.stat_id)
                if modifier_value != 0.0:
                    modifiers[category.stat_id] = modifier_value

        return cls(
            position=position,
            applicable_stats=applicable_stats,
            modifiers=modifiers,
        )
