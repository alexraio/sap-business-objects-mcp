"""
Core networking, authentication, and exception handling for SAP BusinessObjects.
"""

from .auth import (
    AuthCredentials,
    ChainedCredentialProvider,
    CredentialProvider,
    EnvCredentialProvider,
    KeyringCredentialProvider,
)
from .exceptions import (
    BOEAuthError,
    BOEError,
    BOENotFoundError,
    BOEProcessingError,
    BOEQueryError,
)
from .models import (
    BatchDiagnosticsReport,
    ClusterDiagnosis,
    FailureCategory,
    PotentialCause,
)
from .session import SessionManager, UserSession

__all__ = [
    "BOEError",
    "BOEAuthError",
    "BOENotFoundError",
    "BOEProcessingError",
    "BOEQueryError",
    "FailureCategory",
    "PotentialCause",
    "ClusterDiagnosis",
    "BatchDiagnosticsReport",
    "AuthCredentials",
    "CredentialProvider",
    "EnvCredentialProvider",
    "KeyringCredentialProvider",
    "ChainedCredentialProvider",
    "SessionManager",
    "UserSession",
]
