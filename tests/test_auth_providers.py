"""
Unit tests for Credential Providers: Env, Keyring, and Chained strategies.
"""

import json
from unittest.mock import MagicMock, patch

from keyring.errors import KeyringError

from core.auth.providers import (
    ChainedCredentialProvider,
    EnvCredentialProvider,
    KeyringCredentialProvider,
)


class TestEnvCredentialProvider:
    def test_get_credentials_when_env_present(self, monkeypatch):
        monkeypatch.setenv("SAP_BO_USERNAME", "env_user")
        monkeypatch.setenv("SAP_BO_PASSWORD", "env_pass123")
        monkeypatch.setenv("SAP_BO_REST_API_URL", "http://env-bo:8080/biprws")
        monkeypatch.setenv("SAP_BO_AUTH_TYPE", "secLDAP")

        provider = EnvCredentialProvider()
        creds = provider.get_credentials()

        assert creds is not None
        assert creds.username == "env_user"
        assert creds.get_password() == "env_pass123"
        assert creds.api_url == "http://env-bo:8080/biprws"
        assert creds.auth_type == "secLDAP"

    def test_get_credentials_when_env_missing(self, monkeypatch):
        monkeypatch.delenv("SAP_BO_USERNAME", raising=False)
        monkeypatch.delenv("SAP_BO_PASSWORD", raising=False)

        provider = EnvCredentialProvider()
        creds = provider.get_credentials()

        assert creds is None


class TestKeyringCredentialProvider:
    @patch("keyring.get_password")
    def test_get_credentials_with_active_user_in_keyring(self, mock_get_password, monkeypatch):
        monkeypatch.delenv("SAP_BO_USERNAME", raising=False)
        monkeypatch.delenv("SAP_BO_PASSWORD", raising=False)

        def mock_pwd_side_effect(service, user):
            if user == "__active_user__":
                return "keyring_user"
            if user == "keyring_user":
                return "keyring_secret_pass"
            return None

        mock_get_password.side_effect = mock_pwd_side_effect

        provider = KeyringCredentialProvider(service_name="test_service")
        # Ensure config file doesn't interfere
        provider._read_metadata_config = MagicMock(return_value={})

        creds = provider.get_credentials()

        assert creds is not None
        assert creds.username == "keyring_user"
        assert creds.get_password() == "keyring_secret_pass"

    @patch("keyring.get_password")
    def test_get_credentials_with_config_metadata(self, mock_get_password, monkeypatch, tmp_path):
        monkeypatch.delenv("SAP_BO_USERNAME", raising=False)
        monkeypatch.delenv("SAP_BO_PASSWORD", raising=False)
        monkeypatch.delenv("SAP_BO_REST_API_URL", raising=False)
        monkeypatch.delenv("SAP_BO_AUTH_TYPE", raising=False)

        config_data = {
            "username": "metadata_user",
            "api_url": "http://meta-bo:8080/biprws",
            "auth_type": "secWinAD",
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        mock_get_password.return_value = "meta_password"

        provider = KeyringCredentialProvider(service_name="test_service")
        provider._read_metadata_config = MagicMock(return_value=config_data)

        creds = provider.get_credentials()

        assert creds is not None
        assert creds.username == "metadata_user"
        assert creds.get_password() == "meta_password"
        assert creds.api_url == "http://meta-bo:8080/biprws"
        assert creds.auth_type == "secWinAD"

    @patch("keyring.get_password")
    def test_keyring_error_handled_gracefully(self, mock_get_password, monkeypatch):
        monkeypatch.setenv("SAP_BO_USERNAME", "user_headless")
        mock_get_password.side_effect = KeyringError("No recommended backend found")

        provider = KeyringCredentialProvider()
        creds = provider.get_credentials()

        assert creds is None


class TestChainedCredentialProvider:
    def test_chained_precedence_env_over_keyring(self, monkeypatch):
        # Env provides credentials
        monkeypatch.setenv("SAP_BO_USERNAME", "env_priority_user")
        monkeypatch.setenv("SAP_BO_PASSWORD", "env_pass")

        # Mock Keyring to return different user
        mock_keyring_provider = MagicMock()
        mock_keyring_provider.get_credentials.return_value = MagicMock(username="keyring_user")

        chained = ChainedCredentialProvider(
            providers=[
                EnvCredentialProvider(),
                mock_keyring_provider,
            ]
        )

        creds = chained.get_credentials()
        assert creds is not None
        assert creds.username == "env_priority_user"
        # Keyring provider was not even queried
        mock_keyring_provider.get_credentials.assert_not_called()

    def test_chained_fallback_to_keyring_when_env_empty(self, monkeypatch):
        monkeypatch.delenv("SAP_BO_USERNAME", raising=False)
        monkeypatch.delenv("SAP_BO_PASSWORD", raising=False)

        mock_keyring_creds = MagicMock()
        mock_keyring_creds.username = "keyring_fallback_user"

        mock_keyring_provider = MagicMock()
        mock_keyring_provider.get_credentials.return_value = mock_keyring_creds

        chained = ChainedCredentialProvider(
            providers=[
                EnvCredentialProvider(),
                mock_keyring_provider,
            ]
        )

        creds = chained.get_credentials()
        assert creds is not None
        assert creds.username == "keyring_fallback_user"
        mock_keyring_provider.get_credentials.assert_called_once()

    def test_chained_returns_none_when_all_empty(self, monkeypatch):
        monkeypatch.delenv("SAP_BO_USERNAME", raising=False)
        monkeypatch.delenv("SAP_BO_PASSWORD", raising=False)

        mock_keyring_provider = MagicMock()
        mock_keyring_provider.get_credentials.return_value = None

        chained = ChainedCredentialProvider(
            providers=[
                EnvCredentialProvider(),
                mock_keyring_provider,
            ]
        )

        creds = chained.get_credentials()
        assert creds is None
