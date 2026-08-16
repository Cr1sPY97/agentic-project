from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import User
from app.schemas.stats import IncidentDashboardStats
from app.services.stats_service import StatsService
from app.api.dependencies import get_current_user

router = APIRouter()


@router.get("/incidents/stats", response_model=IncidentDashboardStats)
def get_incident_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Dashboard metrics and statistics endpoint.
    Aggregates incident counts by severity, status, environment, top services, MTTR, and AI-assisted rates.
    """
    service = StatsService(db)
    return service.get_dashboard_stats()
