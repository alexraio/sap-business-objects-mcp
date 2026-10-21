"""
Pydantic v2 Data Models and API Contracts for SAP BusinessObjects Intelligent Diagnostics.
Enforces strict schema validation, type safety, and structured diagnostic outputs.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class FailureCategory(str, Enum):
    """Standardized root cause failure classification for SAP BO batch executions."""

    NETWORK_TIMEOUT = "Infrastruttura / Timeout Rete"
    AUTH_CREDENTIALS = "Credenziali / Autenticazione DB"
    MISSING_PROMPTS = "Prompt Obbligatori Mancanti"
    DB_LOCK_CONCURRENCY = "Lock Tabelle / Concorrenza DB"
    SERVER_RESOURCE_OOM = "Saturazione Risorse / Memoria WACS-APS"
    CACHE_CORRUPTED = "Corruzione Cache Data Provider"
    BURSTING_RECIPIENT = "Errore Destinatari Dinamici Pubblicazione"
    UNKNOWN_GENERIC = "Eccezione Non Classificata"


class PotentialCause(BaseModel):
    """
    Detailed potential root cause ranked by probability.
    Contains technical explanation and actionable remediation steps.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    rank: int = Field(..., ge=1, le=3, description="Priority rank from 1 (highest) to 3")
    probability_score: float = Field(
        ..., ge=0.0, le=1.0, description="Estimated confidence/probability score from 0.0 to 1.0"
    )
    category: FailureCategory = Field(..., description="Standardized failure category")
    title: str = Field(..., min_length=1, description="Concise title of the potential root cause")
    technical_explanation: str = Field(
        ..., min_length=1, description="Detailed technical analysis linked to error signatures and log traces"
    )
    recommended_actions: List[str] = Field(
        ..., min_length=1, description="Step-by-step actionable remediation instructions for the system administrator"
    )


class ClusterDiagnosis(BaseModel):
    """
    Cluster of execution failures sharing the same error signature.
    Aggregates impacted instances and presents up to 3 ranked root causes.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    cluster_id: str = Field(..., description="Unique hash identifier for the error cluster")
    error_signature: str = Field(..., description="Normalized error message / signature")
    affected_count: int = Field(..., ge=1, description="Total number of failed instances in this cluster")
    sample_instance_ids: List[str] = Field(..., description="Sample instance IDs belonging to this cluster")
    sample_report_names: List[str] = Field(..., description="Names of sample reports affected by this failure")
    top_causes: List[PotentialCause] = Field(
        ..., max_length=3, description="Up to 3 most probable root causes ordered by probability score"
    )


class BatchDiagnosticsReport(BaseModel):
    """
    Complete executive and technical diagnostic report for nocturnal batch schedules and publications.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    scan_timestamp: str = Field(..., description="ISO 8601 timestamp of when the diagnostic scan was performed")
    hours_back: int = Field(..., ge=1, description="Time window in hours analyzed")
    kind: str = Field(default="All", description="Kind of objects scanned (Webi, Publication, or All)")
    folder_id: Optional[str] = Field(default=None, description="Repository folder ID filter if specified")
    total_failed_instances: int = Field(..., ge=0, description="Total number of failed instances intercepted")
    clusters_count: int = Field(..., ge=0, description="Total number of distinct error clusters identified")
    is_truncated: bool = Field(default=False, description="True if total failures exceeded max scan limit")
    clusters: List[ClusterDiagnosis] = Field(default_factory=list, description="List of deduplicated error clusters")
    executive_summary: str = Field(..., description="High-level executive summary of batch health and action items")
