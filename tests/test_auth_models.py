"""
Unit tests for AuthCredentials data model and SecretStr protection.
"""

from pydantic import SecretStr

from core.auth.models import AuthCredentials


class TestAuthCredentialsModel:
    def test_auth_credentials_creation(self):
        creds = AuthCredentials(
            username="john.doe",
            password=SecretStr("super_secret_pwd"),
            api_url="http://boserver:8080/biprws",
            auth_type="secEnterprise",
        )
        assert creds.username == "john.doe"
        assert creds.get_password() == "super_secret_pwd"
        assert creds.api_url == "http://boserver:8080/biprws"
        assert creds.auth_type == "secEnterprise"

    def test_auth_credentials_masked_repr(self):
        """Ensures password is never leaked in repr() or str()."""
        creds = AuthCredentials(
            username="alessio.ballarin",
            password=SecretStr("MyVerySensitivePassword123!"),
            api_url="http://localhost:8080/biprws",
        )
        repr_str = repr(creds)
        str_str = str(creds)

        assert "MyVerySensitivePassword123!" not in repr_str
        assert "MyVerySensitivePassword123!" not in str_str
        assert "**********" in repr_str or "**********" in str_str

    def test_auth_credentials_default_auth_type(self):
        creds = AuthCredentials(
            username="admin",
            password=SecretStr("secret"),
        )
        assert creds.auth_type == "secEnterprise"
        assert creds.api_url is None
