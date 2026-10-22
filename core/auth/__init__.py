"""
Authentication and credential management package for SAP BusinessObjects MCP.
Provides secure credential models, OS Keyring integration, and CLI setup tools.
"""

from .cli import main as auth_cli_main
from .cli import run_configure_wizard, save_user_credentials
from .models import AuthCredentials
from .providers import (
    DEFAULT_SERVICE_NAME,
    ChainedCredentialProvider,
    CredentialProvider,
    EnvCredentialProvider,
    KeyringCredentialProvider,
    get_user_config_path,
)

__all__ = [
    "AuthCredentials",
    "CredentialProvider",
    "EnvCredentialProvider",
    "KeyringCredentialProvider",
    "ChainedCredentialProvider",
    "DEFAULT_SERVICE_NAME",
    "get_user_config_path",
    "run_configure_wizard",
    "save_user_credentials",
    "auth_cli_main",
]
