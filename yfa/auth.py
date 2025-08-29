"""
OAuth2 authentication for Yahoo Fantasy Sports API.
"""

import base64
import json
import os
import ssl
import tempfile
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional

import httpx
from pydantic import BaseModel

from .config import Settings

# Yahoo OAuth2 endpoints
AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"


class Token(BaseModel):
    """OAuth2 token model."""

    access_token: str
    refresh_token: str
    expires_at: float
    token_type: str = "Bearer"

    @property
    def is_expired(self) -> bool:
        """Check if token is expired (with 60s buffer)."""
        return time.time() > (self.expires_at - 60)


class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth2 callback."""

    def __init__(self, code_holder: dict[str, str], *args, **kwargs):
        self.code_holder = code_holder
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        """Handle GET request to capture authorization code."""
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)

        if "code" in query_params:
            self.code_holder["code"] = query_params["code"][0]
            response_body = b"""
            <html>
                <head><title>Authorization Complete</title></head>
                <body>
                    <h1>Authorization Complete!</h1>
                    <p>You can close this tab and return to your application.</p>
                    <script>window.close();</script>
                </body>
            </html>
            """
        elif "error" in query_params:
            error = query_params.get("error", ["unknown"])[0]
            error_desc = query_params.get("error_description", [""])[0]
            self.code_holder["error"] = f"{error}: {error_desc}"
            response_body = f"""
            <html>
                <head><title>Authorization Error</title></head>
                <body>
                    <h1>Authorization Error</h1>
                    <p>Error: {error}</p>
                    <p>Description: {error_desc}</p>
                </body>
            </html>
            """.encode()
        else:
            response_body = b"No authorization code received."

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(response_body)

    def log_message(self, format: str, *args) -> None:
        """Suppress default logging."""
        pass


def _create_self_signed_cert():
    """Create a temporary self-signed certificate for HTTPS callback server."""
    try:
        import ssl
        import ipaddress
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime
        
        # Generate private key
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Create certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=1)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            ]),
            critical=False,
        ).sign(key, hashes.SHA256())
        
        # Write to temporary files
        cert_file = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pem')
        key_file = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.key')
        
        cert_file.write(cert.public_bytes(serialization.Encoding.PEM))
        key_file.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
        
        cert_file.close()
        key_file.close()
        
        return cert_file.name, key_file.name
    except ImportError:
        # Fallback: cryptography not available, use HTTP
        return None, None


def _create_basic_auth_header(client_id: str, client_secret: str) -> str:
    """Create Basic auth header for OAuth2 token requests."""
    credentials = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


class AuthClient:
    """Yahoo OAuth2 authentication client."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def get_authorization_url(self) -> str:
        """Generate authorization URL for user consent."""
        params = {
            "client_id": self.settings.client_id,
            "redirect_uri": self.settings.redirect_uri,
            "response_type": "code",
            "scope": self.settings.scope,
        }

        query_string = urllib.parse.urlencode(params)
        return f"{AUTH_URL}?{query_string}"

    def authorize(self) -> Token:
        """
        Complete OAuth2 authorization flow.

        Opens browser for user consent and starts local server to capture code.
        Returns access token.
        """
        # Extract port from redirect URI
        parsed_uri = urllib.parse.urlparse(self.settings.redirect_uri)
        port = parsed_uri.port or 8765
        host = parsed_uri.hostname or "localhost"

        # Start local server to capture authorization code
        code_holder: dict[str, str] = {}

        def handler_factory(*args, **kwargs):
            return CallbackHandler(code_holder, *args, **kwargs)

        server = HTTPServer((host, port), handler_factory)
        
        # Add HTTPS support if redirect URI uses HTTPS
        if parsed_uri.scheme == "https":
            try:
                cert_file, key_file = _create_self_signed_cert()
                if cert_file and key_file:
                    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                    context.load_cert_chain(cert_file, key_file)
                    server.socket = context.wrap_socket(server.socket, server_side=True)
                    print("Using HTTPS callback server with self-signed certificate")
                else:
                    print("Warning: Could not create HTTPS certificate, falling back to HTTP")
            except Exception as e:
                print(f"Warning: Could not enable HTTPS for callback server: {e}")
                print("Falling back to HTTP - you may need to update your redirect URI")

        # Start server in background thread
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        try:
            # Open authorization URL in browser
            auth_url = self.get_authorization_url()
            print(f"Opening browser for authorization: {auth_url}")
            webbrowser.open(auth_url)

            # Wait for authorization code
            print("Waiting for authorization...")
            timeout = 300  # 5 minutes timeout
            start_time = time.time()

            while "code" not in code_holder and "error" not in code_holder:
                if time.time() - start_time > timeout:
                    raise TimeoutError("Authorization timeout after 5 minutes")
                time.sleep(0.1)

            if "error" in code_holder:
                raise RuntimeError(f"Authorization failed: {code_holder['error']}")

            # Exchange code for token
            return self._exchange_code(code_holder["code"])

        finally:
            server.shutdown()
            server.server_close()

    def _exchange_code(self, code: str) -> Token:
        """Exchange authorization code for access token."""
        headers = {
            "Authorization": _create_basic_auth_header(
                self.settings.client_id, self.settings.client_secret
            ),
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.settings.redirect_uri,
        }

        response = httpx.post(TOKEN_URL, headers=headers, data=data, timeout=20)
        response.raise_for_status()

        token_data = response.json()

        return Token(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_at=time.time() + token_data["expires_in"],
            token_type=token_data.get("token_type", "Bearer"),
        )

    def refresh_token(self, token: Token) -> Token:
        """Refresh an expired access token."""
        headers = {
            "Authorization": _create_basic_auth_header(
                self.settings.client_id, self.settings.client_secret
            ),
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {
            "grant_type": "refresh_token",
            "refresh_token": token.refresh_token,
            "redirect_uri": self.settings.redirect_uri,
        }

        response = httpx.post(TOKEN_URL, headers=headers, data=data, timeout=20)
        response.raise_for_status()

        token_data = response.json()

        # Update token with new values
        token.access_token = token_data["access_token"]
        token.expires_at = time.time() + token_data["expires_in"]

        # Some implementations return new refresh token
        if "refresh_token" in token_data:
            token.refresh_token = token_data["refresh_token"]

        return token

    def save_token(self, token: Token) -> None:
        """Save token to file."""
        self.settings.ensure_token_directory()

        token_path = Path(self.settings.token_path)

        with open(token_path, "w") as f:
            json.dump(token.model_dump(), f, indent=2)

        # Set restrictive permissions on Unix-like systems
        if hasattr(os, "chmod"):
            try:
                os.chmod(token_path, 0o600)
            except (OSError, NotImplementedError):
                pass

    def load_token(self) -> Optional[Token]:
        """Load token from file."""
        token_path = Path(self.settings.token_path)

        if not token_path.exists():
            return None

        try:
            with open(token_path) as f:
                token_data = json.load(f)

            return Token(**token_data)

        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def get_valid_token(self) -> Token:
        """Get a valid token, refreshing or re-authorizing as needed."""
        token = self.load_token()

        if not token:
            print("No token found, starting authorization flow...")
            token = self.authorize()
            self.save_token(token)
            return token

        if token.is_expired:
            print("Token expired, refreshing...")
            try:
                token = self.refresh_token(token)
                self.save_token(token)
                return token
            except httpx.HTTPStatusError:
                print("Token refresh failed, re-authorizing...")
                token = self.authorize()
                self.save_token(token)
                return token

        return token
