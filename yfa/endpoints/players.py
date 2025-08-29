"""
Player-related endpoints for Yahoo Fantasy Sports API.
"""

from typing import Any, Optional

from ..http import YahooHTTP
from ..models.common import extract_list_items, extract_nested_value
from ..models.player import Player, PlayerSearch, PlayerStats


class PlayersAPI:
    """API wrapper for player-related endpoints."""

    def __init__(self, http_client: YahooHTTP):
        self.http = http_client

    def get_player(self, player_key: str) -> Player:
        """
        Get detailed player information.

        Args:
            player_key: Player key (e.g., 'nfl.p.12345')

        Returns:
            Player object with detailed information
        """

        path = f"player/{player_key}"

        try:
            response = self.http.get(path)

            # Extract player data from response
            player_data = extract_nested_value(response, "fantasy_content", "player")
            if not player_data or not isinstance(player_data, list):
                raise ValueError("Invalid player response structure")

            # Yahoo returns player data as array with single item, which is itself a list of objects
            player_list = player_data[0] if player_data else []
            if not isinstance(player_list, list):
                raise ValueError("Expected player data to be a list of objects")
                
            # Flatten the list of objects into a single dictionary
            player_info = {}
            for item in player_list:
                if isinstance(item, dict):
                    player_info.update(item)

            return Player.from_api_data(player_info)

        except Exception as e:
            raise RuntimeError(f"Failed to fetch player {player_key}: {e}") from e

    def search_players(
        self,
        search_term: str,
        game_key: Optional[str] = None,
        position: Optional[str] = None,
        status: Optional[str] = None,
        start: Optional[int] = None,
        count: Optional[int] = None,
    ) -> PlayerSearch:
        """
        Search for players by name or other criteria.

        Args:
            search_term: Player name or search term
            game_key: Game key to search within (e.g., 'nfl')
            position: Position filter (QB, RB, WR, etc.)
            status: Status filter (A=Available, FA=Free Agent, W=Waivers, T=Taken)
            start: Starting index for pagination
            count: Number of results to return

        Returns:
            PlayerSearch object with matching players
        """

        # Build search path
        if game_key:
            path = f"league/{game_key}/players"
        else:
            path = "players"

        # Build search parameters
        params = {"search": search_term}

        if position:
            params["position"] = position
        if status:
            params["status"] = status
        if start is not None:
            params["start"] = str(start)
        if count is not None:
            params["count"] = str(count)

        try:
            response = self.http.get(path, params)

            # Extract players data from response
            if game_key:
                # League-specific search
                league_data = extract_nested_value(
                    response, "fantasy_content", "league"
                )
                if league_data and isinstance(league_data, list):
                    search_data = league_data[0]
                else:
                    search_data = {}
            else:
                # Global player search
                search_data = extract_nested_value(response, "fantasy_content") or {}

            return PlayerSearch.from_api_data(search_term, search_data)

        except Exception as e:
            raise RuntimeError(
                f"Failed to search players for '{search_term}': {e}"
            ) from e

    def get_player_stats(
        self,
        player_key: str,
        stat_type: str = "season",
        week: Optional[int] = None,
        season: Optional[str] = None,
    ) -> PlayerStats:
        """
        Get player statistics.

        Args:
            player_key: Player key (e.g., 'nfl.p.12345')
            stat_type: Type of stats ("season", "week", "average")
            week: Week number (for weekly stats)
            season: Season year (current season if not specified)

        Returns:
            PlayerStats object
        """

        path = f"player/{player_key}/stats"
        params = {"type": stat_type}

        if week is not None:
            params["week"] = str(week)
        if season:
            params["season"] = season

        try:
            response = self.http.get(path, params)

            # Extract player data from response
            player_data = extract_nested_value(response, "fantasy_content", "player")
            if not player_data or not isinstance(player_data, list):
                raise ValueError("Invalid player stats response structure")

            player_info = player_data[0] if player_data else {}

            return PlayerStats.from_api_data(player_info)

        except Exception as e:
            raise RuntimeError(
                f"Failed to fetch stats for player {player_key}: {e}"
            ) from e

    def get_league_players(
        self,
        league_key: str,
        position: Optional[str] = None,
        status: Optional[str] = None,
        start: Optional[int] = None,
        count: Optional[int] = 25,
    ) -> list[Player]:
        """
        Get players available in a specific league.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')
            position: Position filter (QB, RB, WR, etc.)
            status: Status filter (A=Available, FA=Free Agent, W=Waivers, T=Taken)
            start: Starting index for pagination
            count: Number of results to return (default: 25)

        Returns:
            List of Player objects
        """

        path = f"league/{league_key}/players"
        params = {}

        if position:
            params["position"] = position
        if status:
            params["status"] = status
        if start is not None:
            params["start"] = str(start)
        if count is not None:
            params["count"] = str(count)

        try:
            response = self.http.get(path, params)

            # Extract league data from response
            league_data = extract_nested_value(response, "fantasy_content", "league")
            if not league_data or not isinstance(league_data, list):
                raise ValueError("Invalid league players response structure")

            league_info = league_data[0] if league_data else {}
            players_data = league_info.get("players", {})

            if not players_data:
                return []

            # Extract individual players
            players_list = extract_list_items(players_data, "player")

            players = []
            for player_data in players_list:
                if isinstance(player_data, dict):
                    players.append(Player.from_api_data(player_data))

            return players

        except Exception as e:
            raise RuntimeError(
                f"Failed to fetch players for league {league_key}: {e}"
            ) from e

    def get_available_players(
        self, league_key: str, position: Optional[str] = None, count: Optional[int] = 25
    ) -> list[Player]:
        """
        Get available players (free agents) in a league.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')
            position: Position filter (QB, RB, WR, etc.)
            count: Number of results to return

        Returns:
            List of available Player objects
        """

        return self.get_league_players(
            league_key=league_key,
            position=position,
            status="A",  # Available
            count=count,
        )

    def get_waiver_players(
        self, league_key: str, position: Optional[str] = None, count: Optional[int] = 25
    ) -> list[Player]:
        """
        Get players on waivers in a league.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')
            position: Position filter (QB, RB, WR, etc.)
            count: Number of results to return

        Returns:
            List of Player objects on waivers
        """

        return self.get_league_players(
            league_key=league_key, position=position, status="W", count=count  # Waivers
        )

    def get_taken_players(
        self, league_key: str, position: Optional[str] = None, count: Optional[int] = 25
    ) -> list[Player]:
        """
        Get players that are owned by teams in a league.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')
            position: Position filter (QB, RB, WR, etc.)
            count: Number of results to return

        Returns:
            List of owned Player objects
        """

        return self.get_league_players(
            league_key=league_key, position=position, status="T", count=count  # Taken
        )

    def get_players_by_position(
        self,
        league_key: str,
        position: str,
        include_owned: bool = True,
        count: Optional[int] = 50,
    ) -> dict[str, list[Player]]:
        """
        Get players by position, categorized by availability.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')
            position: Position (QB, RB, WR, etc.)
            include_owned: Whether to include owned players
            count: Total number of players to fetch per category

        Returns:
            Dictionary with 'available', 'waivers', and optionally 'owned' lists
        """

        try:
            result = {}

            # Get available players
            result["available"] = self.get_available_players(
                league_key=league_key, position=position, count=count
            )

            # Get waiver players
            result["waivers"] = self.get_waiver_players(
                league_key=league_key, position=position, count=count
            )

            # Optionally get owned players
            if include_owned:
                result["owned"] = self.get_taken_players(
                    league_key=league_key, position=position, count=count
                )

            return result

        except Exception as e:
            raise RuntimeError(
                f"Failed to get {position} players for league {league_key}: {e}"
            ) from e

    def export_player_pool_csv_data(
        self,
        league_key: str,
        positions: Optional[list[str]] = None,
        include_owned: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Export player pool data in CSV-friendly format.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')
            positions: List of positions to include (all if not specified)
            include_owned: Whether to include owned players

        Returns:
            List of dictionaries with flattened player data
        """

        if positions is None:
            positions = ["QB", "RB", "WR", "TE", "K", "DEF"]

        csv_data = []

        try:
            for position in positions:
                players_by_status = self.get_players_by_position(
                    league_key=league_key,
                    position=position,
                    include_owned=include_owned,
                    count=100,
                )

                for status, players in players_by_status.items():
                    for player in players:
                        row = {
                            "player_key": player.player_key,
                            "player_name": player.name,
                            "position": player.primary_position,
                            "eligible_positions": ",".join(player.eligible_positions),
                            "team_abbr": player.team_abbr,
                            "team_name": player.team_name,
                            "uniform_number": player.uniform_number,
                            "status": player.status,
                            "availability": status,
                            "percent_owned": player.percent_owned,
                            "percent_started": player.percent_started,
                            "injury_note": player.injury_note,
                        }
                        csv_data.append(row)

            return csv_data

        except Exception as e:
            raise RuntimeError(
                f"Failed to export player pool CSV data for league {league_key}: {e}"
            ) from e
