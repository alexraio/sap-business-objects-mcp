"""
Data models and security contracts for SAP BusinessObjects authentication credentials.
Ensures zero-plaintext exposure of passwords using Pydantic SecretStr.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class AuthCredentials(BaseModel):
    """
    Secure container for SAP BusinessObjects BI Platform credentials.
    Protects user passwords from leaking into stdout, logs, or debugging dumps.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid", arbitrary_types_allowed=True)

    username: str = Field(..., min_length=1, description="SAP BO username/account")
    password: SecretStr = Field(..., description="Encrypted/masked SAP BO password")
    api_url: Optional[str] = Field(
        default=None, description="Optional SAP BO REST Web Services base URL (e.g. http://host:8080/biprws)"
    )
    auth_type: str = Field(
        default="secEnterprise", description="SAP BO authentication type (secEnterprise, secLDAP, secWinAD)"
    )

    def get_password(self) -> str:
        """Unmasks and returns the plain password string for API authorization requests."""
        return self.password.get_secret_value()

    def __repr__(self) -> str:
        return (
            f"AuthCredentials(username='{self.username}', password=SecretStr('**********'), "
            f"api_url='{self.api_url}', auth_type='{self.auth_type}')"
        )
