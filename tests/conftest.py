"""
Test configuration and fixtures for Yahoo Fantasy Sports API SDK tests.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock settings for testing."""
    from yfa.config import Settings
    
    # Set mock environment variables using monkeypatch
    monkeypatch.setenv("YAHOO_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("YAHOO_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("YAHOO_REDIRECT_URI", "http://127.0.0.1:8765/callback")
    monkeypatch.setenv("YAHOO_SCOPE", "fspt-r")
    monkeypatch.setenv("YAHOO_TOKEN_PATH", "/tmp/test_tokens.json")
    monkeypatch.setenv("YAHOO_USER_AGENT", "test-yfa/0.1")
    
    # Create settings instance directly (will read from environment)
    return Settings()


@pytest.fixture
def mock_token():
    """Mock OAuth2 token for testing."""
    from yfa.auth import Token
    import time
    
    return Token(
        access_token="mock_access_token",
        refresh_token="mock_refresh_token",
        expires_at=time.time() + 3600,  # 1 hour from now
        token_type="Bearer"
    )


@pytest.fixture
def mock_http_client(mock_settings, mock_token):
    """Mock HTTP client for testing."""
    from yfa.http import YahooHTTP
    from yfa.auth import AuthClient
    
    auth_client = Mock(spec=AuthClient)
    
    return YahooHTTP(mock_settings, mock_token, auth_client)


@pytest.fixture
def sample_league_data():
    """Sample league data for testing."""
    return {
        "league_key": "nfl.l.12345",
        "league_id": "12345",
        "name": "Test League",
        "url": "https://football.fantasysports.yahoo.com/f1/12345",
        "draft_status": "postdraft",
        "num_teams": 12,
        "scoring_type": "head-to-head-points",
        "league_type": "private",
        "season": "2023",
        "game_code": "nfl"
    }


@pytest.fixture
def sample_league_settings_data():
    """Sample league settings data for testing."""
    return {
        "league_key": "nfl.l.12345",
        "league_id": "12345",
        "name": "Test League",
        "num_teams": 12,
        "settings": [{
            "roster_positions": {
                "roster_position": [
                    {"position": "QB", "count": 1},
                    {"position": "RB", "count": 2},
                    {"position": "WR", "count": 2},
                    {"position": "TE", "count": 1},
                    {"position": "W/R/T", "count": 1},
                    {"position": "K", "count": 1},
                    {"position": "DEF", "count": 1},
                    {"position": "BN", "count": 6}
                ]
            },
            "stat_categories": {
                "stats": {
                    "stat": [
                        {"stat_id": 4, "name": "Passing Yards", "value": 0.04},
                        {"stat_id": 5, "name": "Passing Touchdowns", "value": 6.0},
                        {"stat_id": 14, "name": "Rushing Yards", "value": 0.1},
                        {"stat_id": 15, "name": "Rushing Touchdowns", "value": 6.0},
                        {"stat_id": 22, "name": "Receptions", "value": 1.0}
                    ]
                }
            }
        }]
    }


@pytest.fixture
def sample_draft_results_data():
    """Sample draft results data for testing."""
    return {
        "league_key": "nfl.l.12345",
        "draft_results": {
            "draft_result": [
                {
                    "pick": 1,
                    "round": 1,
                    "team_key": "nfl.l.12345.t.1",
                    "player_key": "nfl.p.9001"
                },
                {
                    "pick": 2,
                    "round": 1,
                    "team_key": "nfl.l.12345.t.2", 
                    "player_key": "nfl.p.9002"
                },
                {
                    "pick": 3,
                    "round": 1,
                    "team_key": "nfl.l.12345.t.3",
                    "player_key": "nfl.p.9003"
                }
            ]
        }
    }


@pytest.fixture
def sample_player_data():
    """Sample player data for testing."""
    return {
        "player_key": "nfl.p.9001",
        "player_id": "9001",
        "name": {"full": "Josh Allen", "first": "Josh", "last": "Allen"},
        "primary_position": "QB",
        "eligible_positions": {"position": ["QB"]},
        "team_abbr": "BUF",
        "team_name": "Buffalo Bills",
        "uniform_number": 17,
        "status": "Healthy",
        "headshot": {"url": "https://example.com/headshot.jpg"}
    }


@pytest.fixture
def sample_team_data():
    """Sample team data for testing."""
    return {
        "team_key": "nfl.l.12345.t.1",
        "team_id": "1",
        "name": "Team 1",
        "url": "https://football.fantasysports.yahoo.com/f1/12345/1",
        "waiver_priority": 5,
        "managers": {
            "manager": [{
                "manager_id": "1",
                "nickname": "TestUser",
                "guid": "test_guid"
            }]
        }
    }


def load_fixture_data(filename: str):
    """Load test fixture data from JSON file."""
    import json
    
    fixture_path = TEST_DATA_DIR / filename
    
    if fixture_path.exists():
        with open(fixture_path, 'r') as f:
            return json.load(f)
    
    return None


# Skip tests that require network access by default
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring network access"
    )
    config.addinivalue_line(
        "markers", "auth: mark test as requiring valid authentication"
    )
