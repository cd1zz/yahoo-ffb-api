"""
Detailed matchup models for head-to-head roster comparison.
"""

from typing import Any, Optional
from pydantic import Field
from .common import YahooResource
from .roster import PlayerStats, TeamRoster


class PositionMatchup(YahooResource):
    """Position-by-position comparison in a matchup."""
    
    position: str = Field(description="Position (QB, RB, WR, etc.)")
    team1_player: Optional[PlayerStats] = Field(None, description="Team 1 player at this position")
    team2_player: Optional[PlayerStats] = Field(None, description="Team 2 player at this position")
    
    @property
    def points_difference(self) -> float:
        """Calculate the points difference (positive means team1 won)."""
        team1_points = self.team1_player.points if self.team1_player else 0.0
        team2_points = self.team2_player.points if self.team2_player else 0.0
        return team1_points - team2_points
    
    @property
    def winner(self) -> Optional[str]:
        """Determine which team won this position."""
        if self.points_difference > 0:
            return "team1"
        elif self.points_difference < 0:
            return "team2"
        return None  # Tie


class DetailedMatchup(YahooResource):
    """Head-to-head matchup with detailed roster comparison."""
    
    # Basic matchup info
    week: int = Field(description="Week number")
    matchup_id: Optional[str] = Field(None, description="Matchup identifier")
    
    # Teams
    team1_roster: TeamRoster = Field(description="Team 1 complete roster")
    team2_roster: TeamRoster = Field(description="Team 2 complete roster") 
    
    # Position comparisons
    starter_matchups: list[PositionMatchup] = Field(default_factory=list, description="Starting position comparisons")
    bench_matchups: list[PositionMatchup] = Field(default_factory=list, description="Bench comparisons")
    
    @classmethod
    def create(cls, team1_roster: TeamRoster, team2_roster: TeamRoster, week: int, matchup_id: Optional[str] = None) -> "DetailedMatchup":
        """Create a DetailedMatchup from two team rosters."""
        
        # Create position-by-position comparisons for starters
        starter_matchups = []
        
        # Get all unique starting positions from both teams
        team1_positions = {}
        for player in team1_roster.starters:
            pos = player.selected_position
            if pos not in team1_positions:
                team1_positions[pos] = []
            team1_positions[pos].append(player)
        
        team2_positions = {}
        for player in team2_roster.starters:
            pos = player.selected_position
            if pos not in team2_positions:
                team2_positions[pos] = []
            team2_positions[pos].append(player)
        
        # Create matchups for each position
        all_positions = set(team1_positions.keys()) | set(team2_positions.keys())
        
        # Sort positions in logical order
        position_order = ['QB', 'RB', 'WR', 'TE', 'W/R/T', 'K', 'DEF', 'IR']
        sorted_positions = []
        for pos in position_order:
            if pos in all_positions:
                sorted_positions.extend([pos] * max(
                    len(team1_positions.get(pos, [])), 
                    len(team2_positions.get(pos, []))
                ))
                
        # Add any positions not in our standard order
        for pos in all_positions:
            if pos not in position_order:
                sorted_positions.extend([pos] * max(
                    len(team1_positions.get(pos, [])), 
                    len(team2_positions.get(pos, []))
                ))
        
        # Create position matchups
        position_counts = {}
        for pos in sorted_positions:
            if pos not in position_counts:
                position_counts[pos] = 0
            
            team1_players = team1_positions.get(pos, [])
            team2_players = team2_positions.get(pos, [])
            
            team1_player = team1_players[position_counts[pos]] if position_counts[pos] < len(team1_players) else None
            team2_player = team2_players[position_counts[pos]] if position_counts[pos] < len(team2_players) else None
            
            starter_matchups.append(PositionMatchup(
                position=pos,
                team1_player=team1_player,
                team2_player=team2_player
            ))
            
            position_counts[pos] += 1
        
        # Create bench comparisons (sorted by points)
        bench_matchups = []
        team1_bench = sorted(team1_roster.bench, key=lambda p: p.points, reverse=True)
        team2_bench = sorted(team2_roster.bench, key=lambda p: p.points, reverse=True)
        
        max_bench = max(len(team1_bench), len(team2_bench))
        for i in range(max_bench):
            bench_matchups.append(PositionMatchup(
                position="BN",
                team1_player=team1_bench[i] if i < len(team1_bench) else None,
                team2_player=team2_bench[i] if i < len(team2_bench) else None
            ))
        
        return cls(
            week=week,
            matchup_id=matchup_id,
            team1_roster=team1_roster,
            team2_roster=team2_roster,
            starter_matchups=starter_matchups,
            bench_matchups=bench_matchups
        )
    
    @property
    def team1_total_points(self) -> float:
        """Team 1 total points."""
        return self.team1_roster.total_points
    
    @property
    def team2_total_points(self) -> float:
        """Team 2 total points."""
        return self.team2_roster.total_points
    
    @property
    def points_difference(self) -> float:
        """Total points difference (positive means team1 won)."""
        return self.team1_total_points - self.team2_total_points
    
    @property
    def winner(self) -> Optional[str]:
        """Determine overall matchup winner."""
        if self.points_difference > 0:
            return self.team1_roster.team_name
        elif self.points_difference < 0:
            return self.team2_roster.team_name
        return None  # Tie
    
    def get_position_summary(self) -> dict[str, dict[str, int]]:
        """Get summary of positions won by each team."""
        summary = {"team1": 0, "team2": 0, "ties": 0}
        
        for matchup in self.starter_matchups:
            winner = matchup.winner
            if winner == "team1":
                summary["team1"] += 1
            elif winner == "team2":
                summary["team2"] += 1
            else:
                summary["ties"] += 1
        
        return summary
