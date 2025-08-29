"""
Main client for Yahoo Fantasy Sports API SDK.
"""

from typing import Any, Optional

from .auth import AuthClient, Token
from .config import Settings
from .endpoints.drafts import DraftsAPI
from .endpoints.leagues import LeaguesAPI
from .endpoints.players import PlayersAPI
from .endpoints.teams import TeamsAPI
from .endpoints.users import UsersAPI
from .http import YahooHTTP


class YahooFantasyClient:
    """
    Main client for Yahoo Fantasy Sports API.

    Provides access to all API endpoints through a unified interface.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the Yahoo Fantasy Sports API client.

        Args:
            settings: Configuration settings (will load from environment if not provided)
        """

        if settings is None:
            settings = Settings()

        self.settings = settings
        self.auth_client = AuthClient(settings)

        # These will be initialized when needed
        self._token: Optional[Token] = None
        self._http: Optional[YahooHTTP] = None
        self._users: Optional[UsersAPI] = None
        self._leagues: Optional[LeaguesAPI] = None
        self._teams: Optional[TeamsAPI] = None
        self._players: Optional[PlayersAPI] = None
        self._drafts: Optional[DraftsAPI] = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.close()

    def close(self) -> None:
        """Close HTTP connections and cleanup resources."""
        if self._http:
            self._http.close()

    @property
    def token(self) -> Token:
        """Get valid OAuth2 token, refreshing or re-authorizing as needed."""
        if self._token is None:
            self._token = self.auth_client.get_valid_token()
        return self._token

    @property
    def http(self) -> YahooHTTP:
        """Get HTTP client with valid authentication."""
        if self._http is None:
            self._http = YahooHTTP(self.settings, self.token, self.auth_client)
        return self._http

    @property
    def users(self) -> UsersAPI:
        """Access user and game discovery endpoints."""
        if self._users is None:
            self._users = UsersAPI(self.http)
        return self._users

    @property
    def leagues(self) -> LeaguesAPI:
        """Access league-related endpoints."""
        if self._leagues is None:
            self._leagues = LeaguesAPI(self.http)
        return self._leagues

    @property
    def teams(self) -> TeamsAPI:
        """Access team-related endpoints."""
        if self._teams is None:
            self._teams = TeamsAPI(self.http)
        return self._teams

    @property
    def players(self) -> PlayersAPI:
        """Access player-related endpoints."""
        if self._players is None:
            self._players = PlayersAPI(self.http)
        return self._players

    @property
    def drafts(self) -> DraftsAPI:
        """Access draft-related endpoints."""
        if self._drafts is None:
            self._drafts = DraftsAPI(self.http)
        return self._drafts

    def authenticate(self) -> Token:
        """
        Force authentication flow (useful for initial setup).

        Returns:
            Valid OAuth2 token
        """
        self._token = self.auth_client.authorize()
        self.auth_client.save_token(self._token)

        # Reset HTTP client to use new token
        if self._http:
            self._http.close()
            self._http = None

        return self._token

    def get_user_leagues(self, game_code: str = "nfl", year: Optional[int] = None) -> dict[str, Any]:
        """
        Quick method to get user's leagues for a game.

        Args:
            game_code: Game code (e.g., 'nfl', 'nba')
            year: Season year (optional)

        Returns:
            Dictionary with league information
        """

        league_keys = self.users.get_user_leagues([game_code], year)

        leagues_info = []
        for league_key in league_keys:
            try:
                league = self.leagues.get_league(league_key)
                leagues_info.append(
                    {
                        "league_key": league_key,
                        "name": league.name,
                        "num_teams": league.num_teams,
                        "draft_status": league.draft_status,
                    }
                )
            except Exception as e:
                print(f"Error getting info for league {league_key}: {e}")

        return {
            "game_code": game_code,
            "total_leagues": len(league_keys),
            "leagues": leagues_info,
        }

    def quick_league_summary(self, league_key: str) -> dict[str, Any]:
        """
        Get a quick summary of league information.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')

        Returns:
            Dictionary with league summary
        """

        try:
            # Get basic info
            league = self.leagues.get_league(league_key)
            settings = self.leagues.get_league_settings(league_key)

            # Get draft info if available
            draft_complete = False
            total_picks = 0
            try:
                if league.draft_status == "postdraft":
                    draft_results = self.drafts.get_draft_results(league_key)
                    draft_complete = True
                    total_picks = len(draft_results.draft_picks)
            except Exception:
                pass

            return {
                "league_key": league_key,
                "name": league.name,
                "num_teams": league.num_teams,
                "scoring_type": league.scoring_type,
                "draft_status": league.draft_status,
                "draft_complete": draft_complete,
                "total_draft_picks": total_picks,
                "roster_positions": len(settings.roster_positions),
                "season": league.season,
            }

        except Exception as e:
            raise RuntimeError(
                f"Failed to get league summary for {league_key}: {e}"
            ) from e
