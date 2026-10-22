"""
Interactive CLI setup wizard for SAP BusinessObjects MCP credentials.
Allows users to securely store credentials in the OS Keyring using masked input (getpass).
"""

import argparse
import getpass
import json
import logging
import sys
from typing import Optional

import keyring
from keyring.errors import KeyringError

from .models import AuthCredentials
from .providers import (
    DEFAULT_SERVICE_NAME,
    KeyringCredentialProvider,
    get_user_config_path,
)

logger = logging.getLogger("BOEAuthCLI")


def save_user_credentials(
    username: str,
    password: str,
    api_url: Optional[str] = None,
    auth_type: str = "secEnterprise",
    service_name: str = DEFAULT_SERVICE_NAME,
) -> bool:
    """
    Saves user credentials safely: non-secret metadata to user config dir,
    and password securely to the OS Keyring.
    """
    try:
        # 1. Save password to OS Keyring
        keyring.set_password(service_name, username, password)
        keyring.set_password(service_name, "__active_user__", username)

        # 2. Save metadata (username, api_url, auth_type)
        config_path = get_user_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        metadata = {
            "username": username,
            "api_url": api_url,
            "auth_type": auth_type,
            "service_name": service_name,
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return True
    except Exception as e:
        print(f"\n❌ Error saving credentials to OS Keyring: {e}", file=sys.stderr)
        return False


def delete_user_credentials(service_name: str = DEFAULT_SERVICE_NAME) -> bool:
    """Deletes stored credentials from OS Keyring and removes local metadata."""
    success = True
    config_path = get_user_config_path()

    username = None
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                username = data.get("username")
            config_path.unlink()
            print("✓ Metadata configuration file deleted.")
        except Exception as e:
            print(f"⚠️ Failed to remove config file: {e}")
            success = False

    try:
        if username:
            try:
                keyring.delete_password(service_name, username)
                print(f"✓ Password for user '{username}' removed from OS Keyring.")
            except KeyringError:
                pass
        try:
            keyring.delete_password(service_name, "__active_user__")
        except KeyringError:
            pass
    except Exception as e:
        print(f"⚠️ Error removing credentials from Keyring: {e}")
        success = False

    return success


def test_stored_credentials() -> bool:
    """Tests currently stored credentials by attempting an authentication check against SAP BO."""
    provider = KeyringCredentialProvider()
    creds = provider.get_credentials()
    if not creds:
        print("❌ No credentials found in OS Keyring. Run `configure` first.")
        return False

    print(f"Found credentials for user: {creds.username}")
    print(f"Target API URL: {creds.api_url or 'Default (http://localhost:8080/biprws)'}")
    print(f"Auth Type: {creds.auth_type}")

    if not creds.api_url:
        print("⚠️ No API URL specified; testing skipped.")
        return True

    try:
        # Import dynamically to avoid circular dependencies
        from core.client import BOEClient

        print("\nVerifying credentials against SAP BusinessObjects BI Platform...")
        client = BOEClient(base_url=creds.api_url)
        token = client.set_logon_token(
            username=creds.username,
            password=creds.get_password(),
            auth=creds.auth_type,
        )
        if token:
            print(f"✅ Success! Session established. Obtained logon token: {token[:12]}...")
            client.bo_logoff()
            return True
        else:
            print("❌ Authentication failed: No token returned.")
            return False
    except Exception as e:
        print(f"❌ Connection or authentication failed: {e}")
        return False


def run_configure_wizard(interactive: bool = True) -> int:
    """Interactive CLI setup wizard for entering and storing SAP BO credentials securely."""
    print("=" * 70)
    print(" SAP BusinessObjects MCP - Secure Credential Configuration Wizard")
    print("=" * 70)
    print("This wizard stores your credentials in your operating system's secure")
    print("keychain (macOS Keychain, Windows Credential Manager, or Linux SecretService).")
    print("Your password will NOT be written in plaintext or logged.")
    print("-" * 70)

    # 1. Read existing config if present for defaults
    provider = KeyringCredentialProvider()
    existing: Optional[AuthCredentials] = provider.get_credentials()

    default_url = existing.api_url if existing and existing.api_url else "http://localhost:8080/biprws"
    default_user = existing.username if existing else ""
    default_auth = existing.auth_type if existing else "secEnterprise"

    try:
        # API URL
        prompt_url = f"SAP BO REST API URL [{default_url}]: "
        input_url = input(prompt_url).strip()
        api_url = input_url if input_url else default_url

        # Username
        prompt_user = f"SAP BO Username [{default_user}]: " if default_user else "SAP BO Username: "
        input_user = input(prompt_user).strip()
        username = input_user if input_user else default_user
        if not username:
            print("❌ Username is required.")
            return 1

        # Password (Masked)
        password = getpass.getpass("SAP BO Password (input will be hidden): ")
        if not password:
            if existing:
                print("Keeping existing stored password.")
                password = existing.get_password()
            else:
                print("❌ Password cannot be empty.")
                return 1

        # Auth Type
        prompt_auth = f"Authentication Type [{default_auth}]: "
        input_auth = input(prompt_auth).strip()
        auth_type = input_auth if input_auth else default_auth

        # Confirm & Save
        print("\nSaving credentials to OS Keyring...")
        success = save_user_credentials(
            username=username,
            password=password,
            api_url=api_url,
            auth_type=auth_type,
        )

        if success:
            print(f"✅ Credentials successfully stored in OS Keyring for user '{username}'.")
            print("You can now launch the MCP server without plaintext credentials in .env.")
            return 0
        else:
            print("❌ Failed to save credentials.")
            return 1

    except (KeyboardInterrupt, EOFError):
        print("\n\nOperation cancelled by user.")
        return 130


def main(args: Optional[list] = None) -> int:
    """CLI Entry point for managing auth credentials."""
    parser = argparse.ArgumentParser(
        description="SAP BusinessObjects MCP - Enterprise Authentication Management",
        prog="python -m core.auth.cli",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("configure", help="Interactively set SAP BO credentials in OS Keyring")
    subparsers.add_parser("test", help="Test stored credentials against SAP BO platform")
    subparsers.add_parser("clear", help="Remove stored credentials from OS Keyring")
    subparsers.add_parser("status", help="Show current authentication configuration status")

    parsed = parser.parse_args(args)

    if parsed.command == "configure" or parsed.command is None:
        return run_configure_wizard()
    elif parsed.command == "test":
        return 0 if test_stored_credentials() else 1
    elif parsed.command == "clear":
        return 0 if delete_user_credentials() else 1
    elif parsed.command == "status":
        from .providers import ChainedCredentialProvider

        cp = ChainedCredentialProvider()
        creds = cp.get_credentials()
        if creds:
            print(f"✓ Active credentials resolved for user: '{creds.username}'")
            print(f"  Target API URL: {creds.api_url or 'Default'}")
            print(f"  Auth Type: {creds.auth_type}")
        else:
            print("❌ No active credentials found in .env or OS Keyring.")
            print("Run `configure` to set up credentials.")
        return 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
