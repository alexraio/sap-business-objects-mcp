"""
Credential provider implementations for SAP BusinessObjects MCP.
Implements hierarchical resolution: Environment Variables / .env -> OS Keyring -> None.
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

import keyring
import platformdirs
from keyring.errors import KeyringError
from pydantic import SecretStr

from .models import AuthCredentials

logger = logging.getLogger("BOEAuthProviders")

DEFAULT_SERVICE_NAME = "sap-business-objects-mcp"
APP_NAME = "sap-business-objects-mcp"


def get_user_config_path() -> Path:
    """Returns the path to the user's non-secret auth metadata config file."""
    config_dir = Path(platformdirs.user_config_dir(APP_NAME))
    return config_dir / "config.json"


class CredentialProvider(ABC):
    """Abstract Base Class for credential resolution strategies."""

    @abstractmethod
    def get_credentials(self) -> Optional[AuthCredentials]:
        """Resolves and returns AuthCredentials, or None if not available."""
        pass


class EnvCredentialProvider(CredentialProvider):
    """
    Resolves credentials from environment variables (e.g. .env or system environment).
    High priority (Priority 1) for local development and CI/CD pipelines.
    """

    def __init__(
        self,
        user_env: str = "SAP_BO_USERNAME",
        pwd_env: str = "SAP_BO_PASSWORD",
        url_env: str = "SAP_BO_REST_API_URL",
        auth_type_env: str = "SAP_BO_AUTH_TYPE",
    ):
        self.user_env = user_env
        self.pwd_env = pwd_env
        self.url_env = url_env
        self.auth_type_env = auth_type_env

    def get_credentials(self) -> Optional[AuthCredentials]:
        username = os.getenv(self.user_env)
        password = os.getenv(self.pwd_env)
        api_url = os.getenv(self.url_env)
        auth_type = os.getenv(self.auth_type_env, "secEnterprise")

        if username and password:
            return AuthCredentials(
                username=username.strip(),
                password=SecretStr(password),
                api_url=api_url.strip() if api_url else None,
                auth_type=auth_type.strip(),
            )
        return None


class KeyringCredentialProvider(CredentialProvider):
    """
    Resolves credentials securely from the OS native Keyring
    (macOS Keychain, Windows Credential Manager, Linux SecretService).
    Priority 2 for enterprise desktop and personal agent deployments.
    """

    def __init__(self, service_name: str = DEFAULT_SERVICE_NAME):
        self.service_name = service_name

    def _read_metadata_config(self) -> dict:
        """Reads non-secret user configuration (username, api_url, auth_type) from disk."""
        path = get_user_config_path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read auth config metadata from {path}: {e}")
        return {}

    def get_credentials(self) -> Optional[AuthCredentials]:
        try:
            # 1. Determine username, api_url, auth_type
            metadata = self._read_metadata_config()
            username = os.getenv("SAP_BO_USERNAME") or metadata.get("username")
            api_url = os.getenv("SAP_BO_REST_API_URL") or metadata.get("api_url")
            auth_type = os.getenv("SAP_BO_AUTH_TYPE") or metadata.get("auth_type", "secEnterprise")

            # If username is not known, check if an active user was stored in keyring directly
            if not username:
                username = keyring.get_password(self.service_name, "__active_user__")

            # Or try get_credential if supported by backend
            if not username and hasattr(keyring, "get_credential"):
                cred = keyring.get_credential(self.service_name, None)
                if cred and cred.username and cred.password:
                    return AuthCredentials(
                        username=cred.username,
                        password=SecretStr(cred.password),
                        api_url=api_url,
                        auth_type=auth_type,
                    )

            if not username:
                return None

            # 2. Retrieve password from OS Keyring
            password = keyring.get_password(self.service_name, username)
            if password:
                return AuthCredentials(
                    username=username,
                    password=SecretStr(password),
                    api_url=api_url,
                    auth_type=auth_type,
                )

        except KeyringError as e:
            logger.warning(f"OS Keyring error encountered while retrieving credentials: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error querying OS Keyring: {e}")

        return None


class ChainedCredentialProvider(CredentialProvider):
    """
    Chains multiple credential providers in order of priority.
    Default order: EnvCredentialProvider -> KeyringCredentialProvider.
    """

    def __init__(self, providers: Optional[List[CredentialProvider]] = None):
        self.providers: List[CredentialProvider] = providers or [
            EnvCredentialProvider(),
            KeyringCredentialProvider(),
        ]

    def get_credentials(self) -> Optional[AuthCredentials]:
        for provider in self.providers:
            creds = provider.get_credentials()
            if creds is not None:
                return creds
        return None
