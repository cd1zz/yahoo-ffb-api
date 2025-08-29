"""
Yahoo Fantasy Football API SDK

A lightweight Python SDK and service layer to interact programmatically with the Yahoo Fantasy Sports API,
focusing on fantasy football. Simplifies OAuth2 flow and API calls with typed models, endpoint wrappers,
and polling utilities for live draft data.
"""

__version__ = "0.1.0"
__author__ = "Craig Freyman"

from .auth import AuthClient, Token

# Main client for easy access
from .client import YahooFantasyClient
from .config import Settings
from .http import YahooHTTP

__all__ = [
    "Settings",
    "AuthClient",
    "Token",
    "YahooHTTP",
    "YahooFantasyClient",
]
