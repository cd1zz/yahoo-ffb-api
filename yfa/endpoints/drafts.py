"""
Draft-related endpoints for Yahoo Fantasy Sports API.
"""

import time
from typing import Any, Optional

from ..http import YahooHTTP
from ..models.common import extract_nested_value
from ..models.draft import DraftAnalysis, DraftPick, DraftResult


class DraftsAPI:
    """API wrapper for draft-related endpoints."""

    def __init__(self, http_client: YahooHTTP):
        self.http = http_client

    def get_draft_results(self, league_key: str) -> DraftResult:
        """
        Get complete draft results for a league.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')

        Returns:
            DraftResult object with all draft picks
        """

        path = f"league/{league_key}/draftresults"

        try:
            response = self.http.get(path)

            # Extract league data from response
            league_data = extract_nested_value(response, "fantasy_content", "league")
            if not league_data or not isinstance(league_data, list):
                raise ValueError("Invalid draft results response structure")

            # Yahoo returns league data as array with TWO items:
            # [0] = league metadata, [1] = draft results
            league_info = league_data[0] if league_data else {}
            draft_info = league_data[1] if len(league_data) > 1 else {}
            
            # Create a combined data structure for parsing
            draft_data = {
                "league_key": league_info.get("league_key", ""),
                "draft_results": draft_info.get("draft_results", {})
            }

            return DraftResult.from_api_data(draft_data)

        except Exception as e:
            raise RuntimeError(
                f"Failed to fetch draft results for {league_key}: {e}"
            ) from e

    def get_draft_picks(self, league_key: str, include_player_names: bool = False) -> list[DraftPick]:
        """
        Get list of draft picks for a league.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')
            include_player_names: Whether to fetch player names (default: False, requires many API calls)

        Returns:
            List of DraftPick objects sorted by pick order
        """

        draft_result = self.get_draft_results(league_key)

        # Sort by pick number to ensure correct order
        picks = sorted(draft_result.draft_picks, key=lambda p: p.pick)
        
        # Always enrich with team names (fast), optionally with player names (slow)
        picks = self._enrich_picks_with_names(league_key, picks, include_player_names)

        return picks

    def _enrich_picks_with_names(self, league_key: str, picks: list[DraftPick], include_player_names: bool = False) -> list[DraftPick]:
        """
        Enrich draft picks with team names and optionally player names.
        
        Args:
            league_key: League key for context
            picks: List of DraftPick objects to enrich
            include_player_names: Whether to lookup player names (slow)
            
        Returns:
            List of DraftPick objects with names populated
        """
        if not picks:
            return picks
            
        try:
            # Get unique team keys (always lookup team names - there are only ~12 teams)
            team_keys = list(set(pick.team_key for pick in picks))
            team_names = self._lookup_team_names(league_key, team_keys)
            
            # Optionally get player names (many more API calls)
            player_names = {}
            if include_player_names:
                player_keys = list(set(pick.player_key for pick in picks))
                player_names = self._lookup_player_names(player_keys)
            
            # Create enriched picks
            enriched_picks = []
            for pick in picks:
                player_info = player_names.get(pick.player_key, {})
                team_info = team_names.get(pick.team_key, {})
                
                # Create new DraftPick with names populated
                enriched_pick = DraftPick(
                    pick=pick.pick,
                    round=pick.round,
                    team_key=pick.team_key,
                    player_key=pick.player_key,
                    cost=pick.cost,
                    player_name=player_info.get('name') if include_player_names else None,
                    player_position=player_info.get('position') if include_player_names else None,
                    player_team=player_info.get('team') if include_player_names else None,
                    team_name=team_info.get('name', pick.team_key)
                )
                enriched_picks.append(enriched_pick)
                
            return enriched_picks
            
        except Exception as e:
            # If enrichment fails, return original picks
            return picks
    
    def _lookup_player_names(self, player_keys: list[str]) -> dict[str, dict[str, str]]:
        """
        Lookup player names for multiple player keys.
        
        Args:
            player_keys: List of player keys to lookup
            
        Returns:
            Dict mapping player_key -> {name, position, team}
        """
        player_info = {}
        
        # For now, do individual lookups - could be optimized with batch API calls
        from ..endpoints.players import PlayersAPI
        players_api = PlayersAPI(self.http)
        
        for i, player_key in enumerate(player_keys):
            try:
                player = players_api.get_player(player_key)
                player_info[player_key] = {
                    'name': player.name,
                    'position': player.display_position,  # Use display_position instead of primary_position
                    'team': player.editorial_team_abbr    # Use editorial_team_abbr instead of team_name
                }
            except Exception:
                # If lookup fails, use the key as fallback
                player_info[player_key] = {'name': player_key}
                
        return player_info
    
    def _lookup_team_names(self, league_key: str, team_keys: list[str]) -> dict[str, dict[str, str]]:
        """
        Lookup team names for multiple team keys.
        
        Args:
            league_key: League key for context
            team_keys: List of team keys to lookup
            
        Returns:
            Dict mapping team_key -> {name}
        """
        team_info = {}
        
        # For now, do individual lookups - could be optimized with batch API calls  
        from ..endpoints.teams import TeamsAPI
        teams_api = TeamsAPI(self.http)
        
        for team_key in team_keys:
            try:
                team = teams_api.get_team(team_key)
                team_info[team_key] = {
                    'name': team.name
                }
            except Exception:
                # If lookup fails, use the key as fallback
                team_info[team_key] = {'name': team_key}
                
        return team_info

    def get_recent_picks(self, league_key: str, limit: int = 10) -> list[DraftPick]:
        """
        Get the most recent draft picks.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')
            limit: Maximum number of recent picks to return

        Returns:
            List of most recent DraftPick objects
        """

        picks = self.get_draft_picks(league_key)

        # Return the last N picks (highest pick numbers)
        return picks[-limit:] if len(picks) > limit else picks

    def watch_draft_picks(
        self,
        league_key: str,
        callback: Optional[callable] = None,
        poll_interval: int = 10,
        timeout: Optional[int] = None,
        include_player_names: bool = False,
    ) -> None:
        """
        Watch for new draft picks in real-time via polling.

        Args:
            league_key: League key to watch
            callback: Function to call with new picks (pick: DraftPick) -> None
            poll_interval: Seconds between API polls (default: 10)
            timeout: Maximum seconds to watch (None = indefinite)
            include_player_names: Whether to lookup player/team names (slower)
        """

        seen_picks: set[int] = set()  # Track completed picks (with players)
        start_time = time.time()
        initial_display_done = False
        current_poll_interval = poll_interval  # Track current interval (may increase on rate limiting)
        consecutive_errors = 0  # Track consecutive rate limit errors

        # Get initial picks and show them (to provide draft context)
        try:
            initial_picks = self.get_draft_picks(league_key, include_player_names=include_player_names)
            
            # Only track picks that have actually been made (have a player)
            for pick in initial_picks:
                has_player = (hasattr(pick, 'player_key') and pick.player_key) or \
                           (hasattr(pick, 'player_name') and pick.player_name)
                if has_player:
                    seen_picks.add(pick.pick)

            # Show all initial picks to provide context
            if callback:
                for pick in initial_picks:
                    # Mark this as initial display somehow - let's add an attribute
                    pick._is_initial_display = True
                    callback(pick)

        except Exception as e:
            print(f"Error getting initial picks: {e}")
            return

        print(f"Watching draft for {league_key} (polling every {current_poll_interval}s)")

        while True:
            try:
                # Check timeout
                if timeout and (time.time() - start_time) > timeout:
                    print("Watch timeout reached")
                    break

                # Get current picks
                current_picks = self.get_draft_picks(league_key, include_player_names=include_player_names)
                
                # Reset error tracking on successful request
                consecutive_errors = 0
                current_poll_interval = poll_interval  # Reset to normal interval

                # Find new picks (picks that now have players but didn't before)
                new_picks = []
                for pick in current_picks:
                    has_player = (hasattr(pick, 'player_key') and pick.player_key) or \
                               (hasattr(pick, 'player_name') and pick.player_name)
                    
                    # This is a new pick if it has a player but wasn't tracked before
                    if has_player and pick.pick not in seen_picks:
                        new_picks.append(pick)
                        seen_picks.add(pick.pick)

                # Process new picks
                for pick in new_picks:
                    # Mark new picks as NOT initial display
                    pick._is_initial_display = False
                    if callback:
                        try:
                            callback(pick)
                        except Exception as callback_error:
                            print(f"[ERROR] Callback failed for pick {pick.pick}: {callback_error}")
                            import traceback
                            traceback.print_exc()

                # Provide polling feedback (always show for debugging)
                completed_picks = sum(1 for pick in current_picks 
                                    if (hasattr(pick, 'player_key') and pick.player_key) or 
                                       (hasattr(pick, 'player_name') and pick.player_name))
                
                # Check if draft is complete
                if completed_picks >= len(current_picks) and len(current_picks) > 0:
                    print(f"🎉 Draft complete! All {completed_picks} picks have been made.")
                    break
                
                if len(new_picks) == 0:
                    print(f"[{time.strftime('%H:%M:%S')}] Checked for new picks... (completed: {completed_picks}/{len(current_picks)}, seen: {len(seen_picks)})")
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] Found {len(new_picks)} new picks! (completed: {completed_picks}/{len(current_picks)}, seen: {len(seen_picks)})")

                # Sleep before next poll
                time.sleep(current_poll_interval)

            except KeyboardInterrupt:
                print("\nDraft watching stopped by user")
                break
            except Exception as e:
                error_message = str(e)
                print(f"[ERROR] Error during draft watching: {e}")
                print(f"[ERROR] Exception type: {type(e).__name__}")
                
                # Check if this is a rate limiting error (HTTP 999)
                if "999" in error_message or "Unknown HTTP Status" in error_message:
                    consecutive_errors += 1
                    # Exponential backoff for rate limiting, but cap it
                    current_poll_interval = min(poll_interval * (2 ** consecutive_errors), 120)  # Max 2 minutes
                    print(f"[WARNING] Yahoo rate limiting detected (HTTP 999). Error #{consecutive_errors}.")
                    print(f"[WARNING] Increasing poll interval to {current_poll_interval}s to reduce API pressure...")
                    time.sleep(current_poll_interval)
                else:
                    # For other errors, just continue with normal interval
                    consecutive_errors += 1
                    import traceback
                    traceback.print_exc()
                    time.sleep(current_poll_interval)

    def get_draft_analysis(self, league_key: str) -> DraftAnalysis:
        """
        Get analysis of draft picks and trends.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')

        Returns:
            DraftAnalysis object with statistics
        """

        picks = self.get_draft_picks(league_key)
        return DraftAnalysis.from_draft_picks(league_key, picks)

    def get_team_draft_picks(self, league_key: str, team_key: str) -> list[DraftPick]:
        """
        Get draft picks for a specific team.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')
            team_key: Team key (e.g., 'nfl.l.12345.t.1')

        Returns:
            List of DraftPick objects for the team
        """

        all_picks = self.get_draft_picks(league_key)

        # Filter picks by team
        team_picks = [pick for pick in all_picks if pick.team_key == team_key]

        return sorted(team_picks, key=lambda p: p.pick)

    def get_round_picks(self, league_key: str, round_num: int) -> list[DraftPick]:
        """
        Get all picks from a specific draft round.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')
            round_num: Round number to get picks for

        Returns:
            List of DraftPick objects from the specified round
        """

        all_picks = self.get_draft_picks(league_key)

        # Filter picks by round
        round_picks = [pick for pick in all_picks if pick.round == round_num]

        return sorted(round_picks, key=lambda p: p.pick)

    def is_draft_complete(
        self, league_key: str, expected_picks: Optional[int] = None
    ) -> bool:
        """
        Check if draft appears to be complete.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')
            expected_picks: Expected total picks (calculated if not provided)

        Returns:
            True if draft appears complete, False otherwise
        """

        try:
            picks = self.get_draft_picks(league_key)

            if not picks:
                return False

            # If expected picks not provided, try to estimate
            if expected_picks is None:
                # Get league settings to calculate expected picks
                from .leagues import LeaguesAPI

                leagues_api = LeaguesAPI(self.http)
                settings = leagues_api.get_league_settings(league_key)

                # Estimate based on roster positions and team count
                roster_size = len(settings.roster_positions)
                team_count = settings.num_teams
                expected_picks = roster_size * team_count

            return len(picks) >= expected_picks

        except Exception as e:
            print(f"Error checking draft completion: {e}")
            return False

    def export_draft_summary(self, league_key: str) -> dict[str, Any]:
        """
        Export comprehensive draft summary for analysis.

        Args:
            league_key: League key (e.g., 'nfl.l.12345')

        Returns:
            Dictionary with complete draft information
        """

        try:
            draft_result = self.get_draft_results(league_key)
            analysis = self.get_draft_analysis(league_key)

            # Group picks by team
            picks_by_team: dict[str, list[DraftPick]] = {}
            for pick in draft_result.draft_picks:
                if pick.team_key not in picks_by_team:
                    picks_by_team[pick.team_key] = []
                picks_by_team[pick.team_key].append(pick)

            # Sort each team's picks
            for team_key in picks_by_team:
                picks_by_team[team_key] = sorted(
                    picks_by_team[team_key], key=lambda p: p.pick
                )

            return {
                "league_key": league_key,
                "total_picks": analysis.total_picks,
                "is_complete": draft_result.is_draft_done,
                "picks_by_position": analysis.picks_by_position,
                "picks_by_round": analysis.picks_by_round,
                "picks_by_team": {
                    team_key: [pick.model_dump() for pick in picks]
                    for team_key, picks in picks_by_team.items()
                },
                "all_picks": [pick.model_dump() for pick in draft_result.draft_picks],
            }

        except Exception as e:
            raise RuntimeError(
                f"Failed to export draft summary for {league_key}: {e}"
            ) from e
