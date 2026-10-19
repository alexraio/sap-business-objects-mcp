"""
Core networking, authentication, and exception handling for SAP BusinessObjects.
"""

from .exceptions import (
    BOEError,
    BOEAuthError,
    BOENotFoundError,
    BOEProcessingError,
    BOEQueryError,
)

__all__ = [
    "BOEError",
    "BOEAuthError",
    "BOENotFoundError",
    "BOEProcessingError",
    "BOEQueryError",
]
