"""
Common models and utilities for Yahoo Fantasy Sports API.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class YahooResource(BaseModel):
    """Base class for Yahoo Fantasy Sports API resources."""

    class Config:
        """Pydantic configuration."""

        extra = "forbid"
        validate_assignment = True


class YahooError(BaseModel):
    """Yahoo API error model."""

    code: int = Field(description="Error code")
    message: str = Field(description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error description")


class GameInfo(YahooResource):
    """Yahoo Fantasy Sports game information."""

    game_key: str = Field(description="Game key (e.g., 'nfl.l.12345')")
    game_id: int = Field(description="Game ID")
    name: str = Field(description="Game name")
    code: str = Field(description="Game code (e.g., 'nfl')")
    type: str = Field(description="Game type")
    url: Optional[str] = Field(None, description="Game URL")
    season: Optional[str] = Field(None, description="Season year")
    is_registration_over: Optional[bool] = Field(
        None, description="Registration status"
    )
    is_game_over: Optional[bool] = Field(None, description="Game completion status")
    is_offseason: Optional[bool] = Field(None, description="Offseason status")


class UserInfo(YahooResource):
    """Yahoo user information."""

    guid: str = Field(description="User GUID")
    image_url: Optional[str] = Field(None, description="User profile image URL")


def extract_nested_value(data: dict[str, Any], *keys: str) -> Any:
    """
    Extract nested value from Yahoo API response structure.

    Yahoo's API often returns data wrapped in multiple layers:
    {"fantasy_content": {"users": [{"user": [{"guid": "..."}, {"games": ...}]}]}}

    Args:
        data: The response data dictionary
        *keys: Sequence of keys to traverse

    Returns:
        The extracted value or None if path doesn't exist
    """
    current = data

    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
        if current is None:
            return None

    return current


def extract_list_items(data: Any, item_key: str) -> list[dict[str, Any]]:
    """
    Extract items from Yahoo API list structure.

    Yahoo often wraps list items like: [{"item": {"key": "value"}}, ...]

    Args:
        data: List or single item from API response
        item_key: Key containing the actual item data

    Returns:
        List of extracted items
    """
    if not data:
        return []

    # Handle single item (not in list)
    if isinstance(data, dict):
        if item_key in data:
            return [data[item_key]]
        else:
            return [data]

    # Handle list of items
    if isinstance(data, list):
        items = []
        for item in data:
            if isinstance(item, dict) and item_key in item:
                items.append(item[item_key])
            else:
                items.append(item)
        return items

    return []


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to int with default fallback."""
    if value is None:
        return default

    try:
        if isinstance(value, str):
            # Handle empty strings
            if not value.strip():
                return default
            return int(value)
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float with default fallback."""
    if value is None:
        return default

    try:
        if isinstance(value, str):
            # Handle empty strings
            if not value.strip():
                return default
            return float(value)
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_str(value: Any, default: str = "") -> str:
    """Safely convert value to string with default fallback."""
    if value is None:
        return default

    return str(value)
