"""
Roster and player performance models for Yahoo Fantasy Sports API.
"""

from typing import Any, Optional, Union

from pydantic import Field

from .common import YahooResource, safe_float, safe_int, safe_str


class PlayerStats(YahooResource):
    """Individual player statistics for a specific week."""

    player_key: str = Field(description="Player key")
    player_id: str = Field(description="Player ID")
    name: str = Field(description="Player name")
    position: str = Field(description="Player position")
    team: Optional[str] = Field(None, description="NFL team abbreviation")
    
    # Fantasy performance
    points: float = Field(description="Fantasy points scored")
    projected_points: Optional[float] = Field(None, description="Projected fantasy points")
    
    # Roster status
    selected_position: str = Field(description="Position in fantasy lineup (QB, RB1, FLEX, BN, etc.)")
    is_starter: bool = Field(default=False, description="Whether player was in starting lineup")
    
    # Game performance stats (optional detailed stats)
    passing_yards: Optional[float] = Field(None, description="Passing yards")
    passing_tds: Optional[int] = Field(None, description="Passing touchdowns")
    rushing_yards: Optional[float] = Field(None, description="Rushing yards") 
    rushing_tds: Optional[int] = Field(None, description="Rushing touchdowns")
    receiving_yards: Optional[float] = Field(None, description="Receiving yards")
    receiving_tds: Optional[int] = Field(None, description="Receiving touchdowns")
    receptions: Optional[int] = Field(None, description="Receptions")
    
    @classmethod
    def from_api_data(cls, data: dict[str, Any]) -> "PlayerStats":
        """Create PlayerStats from Yahoo API response data."""
        
        # Handle Yahoo's complex nested player structure
        # data is the "player" array: [metadata_array, position_info, stats_info]
        player_key = ""
        player_id = ""
        player_name = ""
        position = ""
        team = ""
        points = 0.0
        projected_points = None
        selected_position = "BN"
        
        if isinstance(data, list) and len(data) >= 3:
            # Item 0: Player metadata array
            player_metadata = data[0] if isinstance(data[0], list) else []
            
            # Item 1: Selected position info
            position_info = data[1] if isinstance(data[1], dict) else {}
            
            # Item 2: Stats and points info
            stats_info = data[2] if len(data) > 2 and isinstance(data[2], dict) else {}
            
            # Extract basic player info from metadata array
            for item in player_metadata:
                if isinstance(item, dict):
                    if "player_key" in item:
                        player_key = item["player_key"]
                    elif "player_id" in item:
                        player_id = str(item["player_id"])
                    elif "name" in item:
                        if isinstance(item["name"], dict):
                            player_name = item["name"].get("full", "Unknown Player")
                        else:
                            player_name = str(item["name"])
                    elif "editorial_team_abbr" in item:
                        team = item["editorial_team_abbr"]
                    elif "display_position" in item:
                        position = item["display_position"]
            
            # Extract selected position
            if "selected_position" in position_info:
                sel_pos_array = position_info["selected_position"]
                if isinstance(sel_pos_array, list):
                    for pos_item in sel_pos_array:
                        if isinstance(pos_item, dict) and "position" in pos_item:
                            selected_position = pos_item["position"]
                            break
            
            # Extract points from stats info
            if "player_points" in stats_info:
                points_info = stats_info["player_points"]
                if isinstance(points_info, dict):
                    total_points = points_info.get("total")
                    if total_points is not None:
                        points = safe_float(total_points)
            
            # Extract projected points (if available)
            if "player_projected_points" in stats_info:
                proj_info = stats_info["player_projected_points"]
                if isinstance(proj_info, dict):
                    proj_total = proj_info.get("total")
                    if proj_total is not None:
                        projected_points = safe_float(proj_total)
        
        return cls(
            player_key=player_key,
            player_id=player_id,
            name=player_name,
            position=position,
            team=team,
            points=points,
            projected_points=projected_points,
            selected_position=selected_position,
            is_starter=not selected_position.startswith("BN")
        )


class TeamRoster(YahooResource):
    """Team roster with all players and their performance for a specific week."""

    team_key: str = Field(description="Team key")
    team_name: str = Field(description="Team name") 
    week: int = Field(description="Week number")
    
    # Player performance
    players: list[PlayerStats] = Field(default_factory=list, description="All players on roster")
    starters: list[PlayerStats] = Field(default_factory=list, description="Starting lineup players")
    bench: list[PlayerStats] = Field(default_factory=list, description="Bench players")
    
    # Team totals
    total_points: float = Field(description="Total team points for the week")
    starter_points: float = Field(description="Points from starting lineup only")
    bench_points: float = Field(description="Points from bench players")
    
    @classmethod
    def from_api_data(cls, data: dict[str, Any], team_key: str, team_name: str, week: int) -> "TeamRoster":
        """Create TeamRoster from Yahoo API roster response."""
        
        players = []
        starters = []
        bench = []
        
        # Extract roster data
        roster_data = data.get("roster", {})
        players_container = roster_data.get("0", {}).get("players", {})
        
        # Handle two different API response structures
        player_data_items = []
        
        if isinstance(players_container, list):
            # Structure A: players is an array of player objects
            player_data_items = players_container
        elif isinstance(players_container, dict):
            # Structure B: players is an object with numeric keys
            for player_key, player_data in players_container.items():
                if player_key == "count":
                    continue
                player_data_items.append(player_data)
        
        # Parse each player
        for player_data in player_data_items:
            if not player_data:
                continue
                
            try:
                if isinstance(player_data, dict) and "player" in player_data:
                    player_stats = PlayerStats.from_api_data(player_data["player"])
                    players.append(player_stats)
                    
                    if player_stats.is_starter:
                        starters.append(player_stats)
                    else:
                        bench.append(player_stats)
                        
            except Exception as e:
                print(f"Warning: Failed to parse player: {e}")
                continue
        
        # Calculate totals
        total_points = sum(player.points for player in players)
        starter_points = sum(player.points for player in starters)
        bench_points = sum(player.points for player in bench)
        
        return cls(
            team_key=team_key,
            team_name=team_name,
            week=week,
            players=players,
            starters=starters,
            bench=bench,
            total_points=total_points,
            starter_points=starter_points,
            bench_points=bench_points
        )
    
    def get_player_by_position(self, position: str) -> list[PlayerStats]:
        """Get all players at a specific position."""
        return [player for player in self.players if player.position == position]
    
    def get_starters_by_position(self) -> dict[str, list[PlayerStats]]:
        """Group starting players by their selected position."""
        positions = {}
        for player in self.starters:
            pos = player.selected_position
            if pos not in positions:
                positions[pos] = []
            positions[pos].append(player)
        return positions
    
    def get_top_performers(self, limit: int = 5) -> list[PlayerStats]:
        """Get top scoring players from the roster."""
        return sorted(self.players, key=lambda p: p.points, reverse=True)[:limit]
    
    def get_bench_outperformers(self) -> list[PlayerStats]:
        """Get bench players who outscored starters."""
        if not self.bench or not self.starters:
            return []
        
        min_starter_points = min(player.points for player in self.starters)
        return [player for player in self.bench if player.points > min_starter_points]
