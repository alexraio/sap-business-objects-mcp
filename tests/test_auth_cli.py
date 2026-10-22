"""
Unit tests for CLI configuration wizard and credential management commands.
"""

from unittest.mock import patch

from core.auth.cli import (
    delete_user_credentials,
    main,
    run_configure_wizard,
    save_user_credentials,
)


class TestAuthCLI:
    @patch("keyring.set_password")
    @patch("core.auth.cli.get_user_config_path")
    def test_save_user_credentials(self, mock_config_path, mock_set_pwd, tmp_path):
        target_file = tmp_path / "config.json"
        mock_config_path.return_value = target_file

        success = save_user_credentials(
            username="wizard_user",
            password="wizard_password",
            api_url="http://wizard-bo:8080/biprws",
            auth_type="secEnterprise",
        )

        assert success is True
        # Keyring stores the password for the user and active user pointer
        mock_set_pwd.assert_any_call("sap-business-objects-mcp", "wizard_user", "wizard_password")
        mock_set_pwd.assert_any_call("sap-business-objects-mcp", "__active_user__", "wizard_user")
        assert target_file.exists()

    @patch("keyring.delete_password")
    @patch("core.auth.cli.get_user_config_path")
    def test_delete_user_credentials(self, mock_config_path, mock_del_pwd, tmp_path):
        target_file = tmp_path / "config.json"
        target_file.write_text('{"username": "wizard_user"}', encoding="utf-8")
        mock_config_path.return_value = target_file

        success = delete_user_credentials()

        assert success is True
        assert not target_file.exists()
        mock_del_pwd.assert_any_call("sap-business-objects-mcp", "wizard_user")

    @patch("core.auth.cli.save_user_credentials")
    @patch("core.auth.cli.getpass.getpass")
    @patch("builtins.input")
    def test_run_configure_wizard_interactive(self, mock_input, mock_getpass, mock_save):
        # Simulate user answers:
        # 1. API URL -> "http://test-server:8080/biprws"
        # 2. Username -> "test.admin"
        # 3. Password -> "my_secret_pwd" (via getpass)
        # 4. Auth Type -> "secEnterprise"
        mock_input.side_effect = [
            "http://test-server:8080/biprws",
            "test.admin",
            "secEnterprise",
        ]
        mock_getpass.return_value = "my_secret_pwd"
        mock_save.return_value = True

        exit_code = run_configure_wizard()

        assert exit_code == 0
        mock_save.assert_called_once_with(
            username="test.admin",
            password="my_secret_pwd",
            api_url="http://test-server:8080/biprws",
            auth_type="secEnterprise",
        )

    @patch("core.auth.cli.test_stored_credentials")
    def test_cli_main_test_command(self, mock_test):
        mock_test.return_value = True
        code = main(["test"])
        assert code == 0
        mock_test.assert_called_once()

    @patch("core.auth.cli.delete_user_credentials")
    def test_cli_main_clear_command(self, mock_clear):
        mock_clear.return_value = True
        code = main(["clear"])
        assert code == 0
        mock_clear.assert_called_once()
