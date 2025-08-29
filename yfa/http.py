"""
HTTP client for Yahoo Fantasy Sports API with retry logic and rate limiting.
"""

from typing import Any, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from .auth import AuthClient, Token
from .config import Settings

# Yahoo Fantasy Sports API base URL
BASE_URL = "https://fantasysports.yahooapis.com/fantasy/v2"


def _is_retryable_error(exception: Exception) -> bool:
    """Check if an exception is retryable."""
    if isinstance(exception, httpx.HTTPStatusError):
        # Retry on server errors and rate limiting (including Yahoo's 999)
        return exception.response.status_code in (429, 500, 502, 503, 504, 999)

    if isinstance(exception, (httpx.ConnectError, httpx.TimeoutException)):
        return True

    return False


class YahooHTTP:
    """HTTP client for Yahoo Fantasy Sports API."""

    def __init__(self, settings: Settings, token: Token, auth_client: AuthClient):
        self.settings = settings
        self.token = token
        self.auth_client = auth_client

        # Create HTTP client with reasonable defaults
        self.client = httpx.Client(
            timeout=httpx.Timeout(20.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests."""
        return {
            "Authorization": f"Bearer {self.token.access_token}",
            "User-Agent": self.settings.user_agent,
            "Accept": "application/json",
        }

    def _refresh_token_if_needed(self) -> None:
        """Refresh token if it's expired or about to expire."""
        if self.token.is_expired:
            self.token = self.auth_client.refresh_token(self.token)
            self.auth_client.save_token(self.token)

    @retry(
        wait=wait_exponential_jitter(initial=0.5, max=8),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type(
            (
                httpx.HTTPStatusError,
                httpx.ConnectError,
                httpx.TimeoutException,
            )
        ),
        reraise=True,
    )
    def _make_request(
        self, method: str, path: str, params: Optional[dict[str, Any]] = None
    ) -> httpx.Response:
        """Make HTTP request with retry logic."""
        # Ensure we always request JSON format
        request_params = {"format": "json"}
        if params:
            request_params.update(params)

        url = f"{BASE_URL}/{path.lstrip('/')}"

        response = self.client.request(
            method=method,
            url=url,
            headers=self._get_headers(),
            params=request_params,
        )

        # Handle 401 Unauthorized - try refreshing token once
        if response.status_code == 401:
            self.token = self.auth_client.refresh_token(self.token)
            self.auth_client.save_token(self.token)

            # Retry request with new token
            response = self.client.request(
                method=method,
                url=url,
                headers=self._get_headers(),
                params=request_params,
            )

        # Only retry on specific status codes
        if _is_retryable_error(
            httpx.HTTPStatusError("", request=None, response=response)
        ):
            response.raise_for_status()

        response.raise_for_status()
        return response

    def get(self, path: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """
        Make GET request to Yahoo Fantasy API.

        Args:
            path: API endpoint path (without base URL)
            params: Query parameters

        Returns:
            JSON response as dictionary
        """
        self._refresh_token_if_needed()

        response = self._make_request("GET", path, params)

        try:
            return response.json()
        except ValueError as e:
            raise ValueError(f"Invalid JSON response: {e}") from e

    def get_raw(self, path: str, params: Optional[dict[str, Any]] = None) -> str:
        """
        Make GET request and return raw response text.

        Args:
            path: API endpoint path (without base URL)
            params: Query parameters

        Returns:
            Raw response text
        """
        self._refresh_token_if_needed()

        response = self._make_request("GET", path, params)
        return response.text

    def post(
        self,
        path: str,
        data: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Make POST request to Yahoo Fantasy API.

        Args:
            path: API endpoint path (without base URL)
            data: Request body data
            params: Query parameters

        Returns:
            JSON response as dictionary
        """
        self._refresh_token_if_needed()

        # For POST requests, we need to modify the request method
        request_params = {"format": "json"}
        if params:
            request_params.update(params)

        url = f"{BASE_URL}/{path.lstrip('/')}"

        response = self.client.post(
            url=url,
            headers=self._get_headers(),
            params=request_params,
            json=data,
        )

        # Handle 401 similar to GET
        if response.status_code == 401:
            self.token = self.auth_client.refresh_token(self.token)
            self.auth_client.save_token(self.token)

            response = self.client.post(
                url=url,
                headers=self._get_headers(),
                params=request_params,
                json=data,
            )

        response.raise_for_status()

        try:
            return response.json()
        except ValueError as e:
            raise ValueError(f"Invalid JSON response: {e}") from e
