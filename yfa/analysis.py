"""
Weekly analysis utilities for fantasy football leagues.

Provides advanced analysis functions similar to the GitHub example repository,
including skins games, survivor pools, and comprehensive matchup tracking.
"""

from typing import Any, Dict, List, Optional, Union
from decimal import Decimal
import json
from pathlib import Path

from .models.matchup import WeeklyScoreboard, SeasonResults, TeamScore, Matchup


class WeeklyAnalyzer:
    """Analyzer for weekly fantasy football performance and special games."""
    
    def __init__(self, min_skins_margin: float = 20.0):
        """
        Initialize the analyzer.
        
        Args:
            min_skins_margin: Minimum victory margin for skins game eligibility
        """
        self.min_skins_margin = min_skins_margin

    def calculate_skins_winners(
        self, 
        season_results: SeasonResults,
        weekly_pot: float = 10.0
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Calculate skins game winners with rolling pot logic.

        Args:
            season_results: Complete season results
            weekly_pot: Base weekly pot amount

        Returns:
            Dictionary mapping team names to their skins wins
        """
        
        skins_winners = {}
        current_pot = weekly_pot

        for week_num in sorted(season_results.weekly_scoreboards.keys()):
            scoreboard = season_results.weekly_scoreboards[week_num]
            
            # Find potential winners (margin >= minimum)
            potential_winners = []
            
            for matchup in scoreboard.matchups:
                if (not matchup.is_tied and 
                    matchup.status == "postevent" and 
                    matchup.margin_of_victory >= self.min_skins_margin):
                    
                    winner = matchup.get_winning_team()
                    if winner:
                        potential_winners.append({
                            "team": winner,
                            "margin": matchup.margin_of_victory,
                            "matchup": matchup
                        })
            
            if not potential_winners:
                # No winner this week, pot rolls over
                current_pot += weekly_pot
                continue
            
            # Get winner with highest margin
            week_winner = max(potential_winners, key=lambda x: x["margin"])
            winning_team = week_winner["team"]
            
            # Record the win
            if winning_team.team_name not in skins_winners:
                skins_winners[winning_team.team_name] = []
            
            skins_winners[winning_team.team_name].append({
                "week": week_num,
                "margin": week_winner["margin"],
                "pot_amount": current_pot,
                "opponent": week_winner["matchup"].get_team_opponent(winning_team.team_key).team_name
            })
            
            # Reset pot for next week
            current_pot = weekly_pot

        return skins_winners

    def calculate_survivor_results(
        self, 
        season_results: SeasonResults,
        elimination_weeks: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Calculate survivor pool results by eliminating lowest scorer each week.

        Args:
            season_results: Complete season results
            elimination_weeks: Specific weeks to run elimination (default: all weeks)

        Returns:
            Dictionary with survivor results including winner and elimination history
        """
        
        if elimination_weeks is None:
            elimination_weeks = sorted(season_results.weekly_scoreboards.keys())

        # Get all teams from first week
        if not season_results.weekly_scoreboards:
            return {"winner": None, "eliminations": []}
        
        first_week = min(season_results.weekly_scoreboards.keys())
        first_scoreboard = season_results.weekly_scoreboards[first_week]
        
        active_teams = set()
        for matchup in first_scoreboard.matchups:
            active_teams.add(matchup.team1.team_name)
            active_teams.add(matchup.team2.team_name)

        eliminations = []
        
        for week in elimination_weeks:
            if len(active_teams) <= 1:
                break
                
            if week not in season_results.weekly_scoreboards:
                continue
                
            scoreboard = season_results.weekly_scoreboards[week]
            
            # Get scores for active teams only
            week_scores = {}
            for matchup in scoreboard.matchups:
                if matchup.team1.team_name in active_teams:
                    week_scores[matchup.team1.team_name] = matchup.team1.points
                if matchup.team2.team_name in active_teams:
                    week_scores[matchup.team2.team_name] = matchup.team2.points
            
            if not week_scores:
                continue
            
            # Eliminate lowest scorer
            eliminated_team = min(week_scores.items(), key=lambda x: x[1])
            active_teams.remove(eliminated_team[0])
            
            eliminations.append({
                "week": week,
                "eliminated_team": eliminated_team[0],
                "eliminated_score": eliminated_team[1],
                "remaining_teams": len(active_teams)
            })

        survivor_winner = next(iter(active_teams)) if len(active_teams) == 1 else None

        return {
            "winner": survivor_winner,
            "eliminations": eliminations,
            "final_active_teams": list(active_teams)
        }

    def calculate_power_rankings(
        self, 
        season_results: SeasonResults,
        weeks_to_analyze: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Calculate power rankings based on recent performance and strength of schedule.

        Args:
            season_results: Complete season results
            weeks_to_analyze: Specific weeks to include (default: last 4 weeks)

        Returns:
            List of teams ranked by power rating
        """
        
        if weeks_to_analyze is None:
            all_weeks = sorted(season_results.weekly_scoreboards.keys())
            weeks_to_analyze = all_weeks[-4:] if len(all_weeks) >= 4 else all_weeks

        team_stats = {}
        
        # Collect stats for each team
        for week in weeks_to_analyze:
            if week not in season_results.weekly_scoreboards:
                continue
                
            scoreboard = season_results.weekly_scoreboards[week]
            
            for matchup in scoreboard.matchups:
                for team in [matchup.team1, matchup.team2]:
                    if team.team_name not in team_stats:
                        team_stats[team.team_name] = {
                            "scores": [],
                            "opponent_scores": [],
                            "wins": 0,
                            "total_margin": 0.0
                        }
                    
                    opponent = matchup.get_team_opponent(team.team_key)
                    if opponent:
                        team_stats[team.team_name]["scores"].append(team.points)
                        team_stats[team.team_name]["opponent_scores"].append(opponent.points)
                        
                        if team.points > opponent.points:
                            team_stats[team.team_name]["wins"] += 1
                            
                        team_stats[team.team_name]["total_margin"] += (team.points - opponent.points)

        # Calculate power ratings
        power_rankings = []
        
        for team_name, stats in team_stats.items():
            if not stats["scores"]:
                continue
                
            avg_score = sum(stats["scores"]) / len(stats["scores"])
            avg_opponent_score = sum(stats["opponent_scores"]) / len(stats["opponent_scores"])
            win_percentage = stats["wins"] / len(stats["scores"]) if stats["scores"] else 0
            avg_margin = stats["total_margin"] / len(stats["scores"]) if stats["scores"] else 0
            
            # Power rating formula (can be customized)
            power_rating = (avg_score * 0.4 + 
                          (avg_score - avg_opponent_score) * 0.3 + 
                          win_percentage * 100 * 0.2 + 
                          avg_margin * 0.1)
            
            power_rankings.append({
                "team_name": team_name,
                "power_rating": round(power_rating, 2),
                "avg_score": round(avg_score, 2),
                "avg_opponent_score": round(avg_opponent_score, 2),
                "win_percentage": round(win_percentage, 3),
                "avg_margin": round(avg_margin, 2),
                "games_analyzed": len(stats["scores"])
            })

        # Sort by power rating
        return sorted(power_rankings, key=lambda x: x["power_rating"], reverse=True)

    def generate_weekly_report(
        self, 
        scoreboard: WeeklyScoreboard,
        include_matchup_details: bool = True
    ) -> str:
        """
        Generate a formatted weekly report.

        Args:
            scoreboard: Weekly scoreboard data
            include_matchup_details: Whether to include detailed matchup info

        Returns:
            Formatted report string
        """
        
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append(f"WEEK {scoreboard.week} RESULTS")
        lines.append(f"{'='*60}")
        
        # Sort matchups by highest scoring
        sorted_matchups = sorted(
            scoreboard.matchups,
            key=lambda m: max(m.team1.points, m.team2.points),
            reverse=True
        )
        
        for i, matchup in enumerate(sorted_matchups, 1):
            lines.append(f"\nMatchup {i}:")
            
            if matchup.is_tied:
                lines.append(f"  {matchup.team1.team_name}: {matchup.team1.points:.2f}")
                lines.append(f"  {matchup.team2.team_name}: {matchup.team2.points:.2f}")
                lines.append(f"  Result: TIE")
            else:
                winner = matchup.get_winning_team()
                loser = matchup.get_losing_team()
                
                lines.append(f"  🏆 {winner.team_name}: {winner.points:.2f}")
                lines.append(f"     {loser.team_name}: {loser.points:.2f}")
                lines.append(f"  Margin: {matchup.margin_of_victory:.2f}")
                
                if matchup.margin_of_victory >= self.min_skins_margin:
                    lines.append(f"  🎯 SKINS ELIGIBLE (margin >= {self.min_skins_margin})")

        # Weekly high score
        highest_team = scoreboard.get_highest_score()
        if highest_team:
            lines.append(f"\n🔥 HIGHEST SCORE: {highest_team.team_name} ({highest_team.points:.2f})")

        # Skins eligible matchups
        skins_matchups = scoreboard.get_matchups_by_margin(self.min_skins_margin)
        if skins_matchups:
            lines.append(f"\n🎯 SKINS ELIGIBLE VICTORIES:")
            for matchup in skins_matchups:
                winner = matchup.get_winning_team()
                lines.append(f"   {winner.team_name} by {matchup.margin_of_victory:.2f}")

        return "\n".join(lines)

    def export_season_summary(
        self, 
        season_results: SeasonResults,
        output_path: Optional[Union[str, Path]] = None
    ) -> Dict[str, Any]:
        """
        Export comprehensive season summary with all analysis.

        Args:
            season_results: Complete season results
            output_path: Optional path to save JSON summary

        Returns:
            Complete season summary dictionary
        """
        
        summary = {
            "league_key": season_results.league_key,
            "season": season_results.season,
            "total_weeks": len(season_results.weekly_scoreboards),
            "analysis_date": str(Path().resolve()),
        }

        # Basic stats
        all_teams = set()
        total_games = 0
        total_points = 0.0
        
        for scoreboard in season_results.weekly_scoreboards.values():
            for matchup in scoreboard.matchups:
                all_teams.add(matchup.team1.team_name)
                all_teams.add(matchup.team2.team_name)
                total_games += 1
                total_points += matchup.team1.points + matchup.team2.points

        summary["teams_count"] = len(all_teams)
        summary["total_games"] = total_games
        summary["average_game_score"] = round(total_points / (total_games * 2), 2) if total_games > 0 else 0

        # Advanced analysis
        summary["skins_results"] = self.calculate_skins_winners(season_results)
        summary["survivor_results"] = self.calculate_survivor_results(season_results)
        summary["power_rankings"] = self.calculate_power_rankings(season_results)

        # Team records
        team_records = {}
        for team_name in all_teams:
            record = season_results.get_team_record(team_name)
            total_points = season_results.get_team_total_points(team_name)
            
            team_records[team_name] = {
                **record,
                "total_points": round(total_points, 2),
                "avg_points": round(total_points / (record["wins"] + record["losses"] + record["ties"]), 2) if (record["wins"] + record["losses"] + record["ties"]) > 0 else 0
            }

        summary["team_records"] = team_records

        # Save to file if requested
        if output_path:
            output_file = Path(output_path)
            with output_file.open('w') as f:
                json.dump(summary, f, indent=2, default=str)

        return summary


def analyze_matchup_trends(season_results: SeasonResults) -> Dict[str, Any]:
    """
    Analyze trends in matchup results across the season.
    
    Args:
        season_results: Complete season results
        
    Returns:
        Dictionary with trend analysis
    """
    
    weekly_averages = []
    weekly_margins = []
    high_scoring_weeks = []
    
    for week_num in sorted(season_results.weekly_scoreboards.keys()):
        scoreboard = season_results.weekly_scoreboards[week_num]
        
        if not scoreboard.matchups:
            continue
            
        # Calculate weekly averages
        week_points = []
        week_margins = []
        
        for matchup in scoreboard.matchups:
            week_points.extend([matchup.team1.points, matchup.team2.points])
            if not matchup.is_tied:
                week_margins.append(matchup.margin_of_victory)
        
        if week_points:
            avg_score = sum(week_points) / len(week_points)
            weekly_averages.append({"week": week_num, "avg_score": avg_score})
            
            if avg_score >= 100:  # High scoring week threshold
                high_scoring_weeks.append(week_num)
        
        if week_margins:
            avg_margin = sum(week_margins) / len(week_margins)
            weekly_margins.append({"week": week_num, "avg_margin": avg_margin})

    return {
        "weekly_scoring_averages": weekly_averages,
        "weekly_margin_averages": weekly_margins,
        "high_scoring_weeks": high_scoring_weeks,
        "season_scoring_trend": "increasing" if len(weekly_averages) >= 2 and weekly_averages[-1]["avg_score"] > weekly_averages[0]["avg_score"] else "decreasing"
    }


def compare_teams_head_to_head(
    season_results: SeasonResults,
    team1_name: str,
    team2_name: str
) -> Dict[str, Any]:
    """
    Compare two teams' head-to-head performance.
    
    Args:
        season_results: Complete season results
        team1_name: First team name
        team2_name: Second team name
        
    Returns:
        Head-to-head comparison data
    """
    
    head_to_head = []
    team1_total = team2_total = 0.0
    team1_wins = team2_wins = ties = 0
    
    for week_num, scoreboard in season_results.weekly_scoreboards.items():
        for matchup in scoreboard.matchups:
            team1_in_matchup = None
            team2_in_matchup = None
            
            if matchup.team1.team_name == team1_name:
                team1_in_matchup = matchup.team1
            elif matchup.team2.team_name == team1_name:
                team1_in_matchup = matchup.team2
            
            if matchup.team1.team_name == team2_name:
                team2_in_matchup = matchup.team1
            elif matchup.team2.team_name == team2_name:
                team2_in_matchup = matchup.team2
            
            # Check if these teams played each other
            if (team1_in_matchup and team2_in_matchup and 
                matchup.team1.team_name in [team1_name, team2_name] and
                matchup.team2.team_name in [team1_name, team2_name]):
                
                team1_total += team1_in_matchup.points
                team2_total += team2_in_matchup.points
                
                if team1_in_matchup.points > team2_in_matchup.points:
                    team1_wins += 1
                    result = f"{team1_name} wins"
                elif team2_in_matchup.points > team1_in_matchup.points:
                    team2_wins += 1
                    result = f"{team2_name} wins"
                else:
                    ties += 1
                    result = "Tie"
                
                head_to_head.append({
                    "week": week_num,
                    f"{team1_name}_score": team1_in_matchup.points,
                    f"{team2_name}_score": team2_in_matchup.points,
                    "margin": abs(team1_in_matchup.points - team2_in_matchup.points),
                    "result": result
                })

    games_played = len(head_to_head)
    
    return {
        "matchups": head_to_head,
        "games_played": games_played,
        f"{team1_name}_wins": team1_wins,
        f"{team2_name}_wins": team2_wins,
        "ties": ties,
        f"{team1_name}_avg_score": round(team1_total / games_played, 2) if games_played > 0 else 0,
        f"{team2_name}_avg_score": round(team2_total / games_played, 2) if games_played > 0 else 0,
        "series_leader": team1_name if team1_wins > team2_wins else team2_name if team2_wins > team1_wins else "Tied"
    }
