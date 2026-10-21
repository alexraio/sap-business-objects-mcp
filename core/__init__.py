"""
Core networking, authentication, and exception handling for SAP BusinessObjects.
"""

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
]
