from typing import Dict, List
from pydantic import BaseModel


class ServiceStats(BaseModel):
    service_name: str
    incident_count: int
    critical_count: int


class IncidentDashboardStats(BaseModel):
    total_incidents: int
    open_incidents: int
    investigating_incidents: int
    mitigated_incidents: int
    resolved_incidents: int
    closed_incidents: int
    critical_incidents: int
    high_incidents: int
    medium_incidents: int
    low_incidents: int
    by_severity: Dict[str, int]
    by_status: Dict[str, int]
    by_environment: Dict[str, int]
    top_affected_services: List[ServiceStats]
    average_resolution_time_minutes: float
    ai_assisted_count: int
