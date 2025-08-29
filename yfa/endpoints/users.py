"""
User and game discovery endpoints for Yahoo Fantasy Sports API.
"""

from typing import Optional

from ..http import YahooHTTP
from ..models.common import GameInfo, extract_list_items, extract_nested_value


class UsersAPI:
    """API wrapper for user-related endpoints."""

    def __init__(self, http_client: YahooHTTP):
        self.http = http_client

    def get_user_games(self, game_codes: Optional[list[str]] = None) -> list[GameInfo]:
        """
        Get games available to the current user.

        Args:
            game_codes: Optional list of game codes to filter by (e.g., ['nfl', 'nba'])

        Returns:
            List of GameInfo objects
        """

        # Build the endpoint path
        if game_codes:
            games_filter = ";game_codes=" + ",".join(game_codes)
        else:
            games_filter = ""

        path = f"users;use_login=1/games{games_filter}"

        try:
            response = self.http.get(path)

            # Extract games from response
            games_data = extract_nested_value(
                response, "fantasy_content", "users", "user", "games"
            )
            if not games_data:
                return []

            # Handle both single game and multiple games
            games_list = extract_list_items(games_data, "game")

            games = []
            for game_data in games_list:
                if isinstance(game_data, dict):
                    game_info = GameInfo(
                        game_key=game_data.get("game_key", ""),
                        game_id=int(game_data.get("game_id", 0)),
                        name=game_data.get("name", ""),
                        code=game_data.get("code", ""),
                        type=game_data.get("type", ""),
                        url=game_data.get("url"),
                        season=game_data.get("season"),
                        is_registration_over=game_data.get("is_registration_over"),
                        is_game_over=game_data.get("is_game_over"),
                        is_offseason=game_data.get("is_offseason"),
                    )
                    games.append(game_info)

            return games

        except Exception as e:
            raise RuntimeError(f"Failed to fetch user games: {e}") from e

    def get_user_leagues(self, game_codes: Optional[list[str]] = None, year: Optional[int] = None) -> list[str]:
        """
        Get league keys for leagues the user participates in.

        Args:
            game_codes: Optional list of game codes to filter by
            year: Optional season year

        Returns:
            List of league keys (e.g., ['nfl.l.12345', 'nfl.l.67890'])
        """

        # Transform game code to game_id if year is specified
        if game_codes and len(game_codes) == 1 and year:
            game_code = game_codes[0]
            if game_code == "nfl":
                # Map year to game_id for NFL
                year_to_game_id = {
                    2025: "461",
                    2024: "449", 
                    2023: "423",
                    2022: "414",
                    2021: "406",
                    2020: "399",
                    2019: "390",
                    2018: "380"
                }
                if year in year_to_game_id:
                    game_key = year_to_game_id[year]
                else:
                    game_key = game_code  # Fallback to original
            else:
                game_key = game_code  # Non-NFL games use original code
        elif game_codes and len(game_codes) == 1:
            game_key = game_codes[0]
        else:
            game_key = "nfl"  # Default fallback

        # Build the endpoint path
        path = f"users;use_login=1/games;game_keys={game_key}/leagues"

        try:
            response = self.http.get(path)

            # Navigate the nested response structure from debug output:
            # fantasy_content -> users -> "0" -> user -> [0] (guid), [1] (games)
            fantasy_content = response.get("fantasy_content", {})
            users_dict = fantasy_content.get("users", {})
            
            if not users_dict or "0" not in users_dict:
                return []
            
            user_array = users_dict["0"].get("user", [])
            if len(user_array) < 2:
                return []
            
            # The games data is in the second element of the user array
            games_container = user_array[1].get("games", {})
            if not games_container or "0" not in games_container:
                return []
            
            game_array = games_container["0"].get("game", [])
            if len(game_array) < 2:
                return []
            
            # The leagues data is in the second element of the game array  
            leagues_container = game_array[1].get("leagues", {})
            if not leagues_container:
                return []

            # Extract league keys from the leagues structure
            league_keys = []
            
            # Iterate through all leagues in the container
            for key, value in leagues_container.items():
                if key == "count":
                    continue
                    
                league_data = value.get("league", [])
                if isinstance(league_data, list) and len(league_data) > 0:
                    # The first element contains league info including league_key
                    league_info = league_data[0]
                    if isinstance(league_info, dict) and "league_key" in league_info:
                        league_keys.append(league_info["league_key"])

            return league_keys

        except Exception as e:
            raise RuntimeError(f"Failed to fetch user leagues: {e}") from e

    def get_nfl_leagues(self, season: Optional[str] = None) -> list[str]:
        """
        Get NFL league keys for the user.

        Args:
            season: Optional season year (e.g., '2023')

        Returns:
            List of NFL league keys
        """

        if season:
            game_code = f"nfl.{season}"
        else:
            game_code = "nfl"

        return self.get_user_leagues([game_code])

    def discover_current_leagues(self) -> dict[str, list[str]]:
        """
        Discover all current leagues across all games for the user.

        Returns:
            Dictionary mapping game codes to list of league keys
        """

        try:
            # Get all available games
            games = self.get_user_games()

            leagues_by_game = {}

            for game in games:
                # Skip if game is over or in offseason
                if game.is_game_over or game.is_offseason:
                    continue

                # Get leagues for this game
                game_leagues = self.get_user_leagues([game.code])

                if game_leagues:
                    leagues_by_game[game.code] = game_leagues

            return leagues_by_game

        except Exception as e:
            raise RuntimeError(f"Failed to discover current leagues: {e}") from e
