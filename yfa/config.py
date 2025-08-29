"""
Configuration management for Yahoo Fantasy Sports API SDK.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Configuration settings for the Yahoo Fantasy Sports API SDK."""

    client_id: str = Field(description="Yahoo OAuth2 client ID")

    client_secret: str = Field(description="Yahoo OAuth2 client secret")

    redirect_uri: str = Field(
        default="https://localhost:8765/callback", description="OAuth2 redirect URI"
    )

    scope: str = Field(
        default="fspt-r", description="OAuth2 scope - fspt-r for read access"
    )

    token_path: str = Field(
        default_factory=lambda: str(Path.home() / ".yfa" / "tokens.json"),
        description="Path to store OAuth2 tokens",
    )

    user_agent: str = Field(
        default="yfa/0.1 (+https://github.com/CraigFreyman/yahoo-ffb-api)",
        description="User agent string for API requests",
    )

    class Config:
        env_prefix = "YAHOO_"
        case_sensitive = False

    def ensure_token_directory(self) -> None:
        """Ensure the token storage directory exists."""
        token_dir = Path(self.token_path).parent
        token_dir.mkdir(parents=True, exist_ok=True)

        # Set restrictive permissions on Unix-like systems
        if hasattr(os, "chmod"):
            try:
                os.chmod(token_dir, 0o700)
            except (OSError, NotImplementedError):
                pass  # Windows or permission error
