"""
Domain services for SAP BusinessObjects 4.3 SP5 REST Web Services.
"""

from .webi_service import WebiService
from .universe_service import UniverseService
from .schedule_service import ScheduleService
from .admin_service import AdminService
from .infostore_service import InfostoreService

__all__ = [
    "WebiService",
    "UniverseService",
    "ScheduleService",
    "AdminService",
    "InfostoreService",
]
