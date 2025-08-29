"""
Tests for authentication functionality.
"""

import pytest
from unittest.mock import Mock, patch
import time

from yfa.auth import Token, AuthClient
from yfa.config import Settings


class TestToken:
    """Test Token model."""
    
    def test_token_creation(self):
        """Test creating a token."""
        token = Token(
            access_token="test_access",
            refresh_token="test_refresh",
            expires_at=time.time() + 3600,
            token_type="Bearer"
        )
        
        assert token.access_token == "test_access"
        assert token.refresh_token == "test_refresh"
        assert token.token_type == "Bearer"
        assert not token.is_expired
    
    def test_token_expiry_check(self):
        """Test token expiry detection."""
        # Expired token
        expired_token = Token(
            access_token="test",
            refresh_token="test",
            expires_at=time.time() - 3600,  # 1 hour ago
            token_type="Bearer"
        )
        
        assert expired_token.is_expired
        
        # Valid token
        valid_token = Token(
            access_token="test",
            refresh_token="test",
            expires_at=time.time() + 3600,  # 1 hour from now
            token_type="Bearer"
        )
        
        assert not valid_token.is_expired


class TestAuthClient:
    """Test AuthClient functionality."""
    
    def test_auth_client_creation(self, mock_settings):
        """Test creating auth client."""
        auth_client = AuthClient(mock_settings)
        
        assert auth_client.settings == mock_settings
    
    def test_get_authorization_url(self, mock_settings):
        """Test authorization URL generation."""
        auth_client = AuthClient(mock_settings)
        
        url = auth_client.get_authorization_url()
        
        assert "api.login.yahoo.com" in url
        assert "client_id=test_client_id" in url
        assert "redirect_uri=" in url
        assert "response_type=code" in url
        assert "scope=fspt-r" in url
    
    @patch('yfa.auth.httpx.post')
    def test_exchange_code(self, mock_post, mock_settings):
        """Test exchanging authorization code for token."""
        # Mock successful token response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        auth_client = AuthClient(mock_settings)
        token = auth_client._exchange_code("test_code")
        
        assert token.access_token == "new_access_token"
        assert token.refresh_token == "new_refresh_token"
        assert token.token_type == "Bearer"
        assert not token.is_expired
        
        # Verify the POST request
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "oauth2/get_token" in args[0]
        assert "Authorization" in kwargs["headers"]
        assert kwargs["data"]["grant_type"] == "authorization_code"
        assert kwargs["data"]["code"] == "test_code"
    
    @patch('yfa.auth.httpx.post')
    def test_refresh_token(self, mock_post, mock_settings, mock_token):
        """Test refreshing an expired token."""
        # Mock successful refresh response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "refreshed_access_token",
            "expires_in": 3600,
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        auth_client = AuthClient(mock_settings)
        original_refresh_token = mock_token.refresh_token
        
        refreshed_token = auth_client.refresh_token(mock_token)
        
        assert refreshed_token.access_token == "refreshed_access_token"
        assert refreshed_token.refresh_token == original_refresh_token  # Should remain same
        assert not refreshed_token.is_expired
        
        # Verify the POST request
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "oauth2/get_token" in args[0]
        assert kwargs["data"]["grant_type"] == "refresh_token"
        assert kwargs["data"]["refresh_token"] == original_refresh_token
    
    @patch('yfa.auth.json.dump')
    @patch('yfa.auth.open')
    @patch('yfa.auth.Path.mkdir')
    def test_save_token(self, mock_mkdir, mock_open, mock_json_dump, mock_settings, mock_token):
        """Test saving token to file."""
        auth_client = AuthClient(mock_settings)
        
        auth_client.save_token(mock_token)
        
        # Verify directory creation
        mock_mkdir.assert_called_once()
        
        # Verify file writing
        mock_open.assert_called_once()
        mock_json_dump.assert_called_once()
    
    @patch('yfa.auth.json.load')
    @patch('yfa.auth.open')
    @patch('yfa.auth.Path.exists')
    def test_load_token(self, mock_exists, mock_open, mock_json_load, mock_settings):
        """Test loading token from file."""
        # Mock file exists
        mock_exists.return_value = True
        
        # Mock token data
        mock_json_load.return_value = {
            "access_token": "loaded_access_token",
            "refresh_token": "loaded_refresh_token",
            "expires_at": time.time() + 3600,
            "token_type": "Bearer"
        }
        
        auth_client = AuthClient(mock_settings)
        token = auth_client.load_token()
        
        assert token is not None
        assert token.access_token == "loaded_access_token"
        assert token.refresh_token == "loaded_refresh_token"
        assert not token.is_expired
    
    @patch('yfa.auth.Path.exists')
    def test_load_token_file_not_exists(self, mock_exists, mock_settings):
        """Test loading token when file doesn't exist."""
        mock_exists.return_value = False
        
        auth_client = AuthClient(mock_settings)
        token = auth_client.load_token()
        
        assert token is None
