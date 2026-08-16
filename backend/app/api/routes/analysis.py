from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.database import get_db, SessionLocal
from app.db.models import User, RoleEnum
from app.schemas.analysis import (
    IncidentAnalysisResponse,
    AnalysisTriggerRequest,
)
from app.services.ai_analysis_service import AIAnalysisService
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.incident_repository import IncidentRepository
from app.api.dependencies import get_current_user, require_roles
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger("app.api.routes.analysis")


async def _run_async_analysis_task(incident_id: int, user_id: int, custom_context: str = ""):
    """Background task worker executing AI root cause diagnosis."""
    db = SessionLocal()
    try:
        from app.repositories.user_repository import UserRepository
        user = UserRepository(db).get_by_id(user_id)
        service = AIAnalysisService(db)
        await service.analyze_incident(incident_id, actor=user, custom_context=custom_context)
        logger.info(f"Background AI analysis successfully completed for incident {incident_id}")
    except Exception as exc:
        logger.error(f"Background AI analysis failed for incident {incident_id}: {exc}", exc_info=True)
    finally:
        db.close()


@router.post("/incidents/{incident_id}/analyze", response_model=IncidentAnalysisResponse, status_code=status.HTTP_200_OK)
async def trigger_ai_analysis(
    incident_id: int,
    background_tasks: BackgroundTasks,
    request_in: AnalysisTriggerRequest = AnalysisTriggerRequest(),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, RoleEnum.RESPONDER)),
    db: Session = Depends(get_db),
):
    """
    Trigger AI Root Cause Analysis (RCA) on an incident.
    Returns structured diagnosis, confidence score, evidence list, and remediation runbook.
    Supports asynchronous non-blocking execution via BackgroundTasks.
    """
    incident_repo = IncidentRepository(db)
    incident = incident_repo.get_by_id(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )

    if request_in.run_async:
        background_tasks.add_task(
            _run_async_analysis_task,
            incident_id=incident_id,
            user_id=current_user.id,
            custom_context=request_in.custom_context or "",
        )
        # If async requested, return previous analysis or placeholder acknowledgment
        latest = AnalysisRepository(db).get_latest_by_incident_id(incident_id)
        if latest:
            return latest
        # Or execute synchronously if no previous analysis
        service = AIAnalysisService(db)
        return await service.analyze_incident(
            incident_id=incident_id,
            actor=current_user,
            custom_context=request_in.custom_context,
        )

    service = AIAnalysisService(db)
    try:
        analysis = await service.analyze_incident(
            incident_id=incident_id,
            actor=current_user,
            custom_context=request_in.custom_context,
        )
        return analysis
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error(f"AI analysis execution failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI analysis failed: {str(exc)}",
        )


@router.get("/incidents/{incident_id}/analyses", response_model=List[IncidentAnalysisResponse])
def list_incident_analyses(
    incident_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all historical AI analyses for an incident."""
    analysis_repo = AnalysisRepository(db)
    return analysis_repo.get_by_incident_id(incident_id)


@router.get("/analyses/{analysis_id}", response_model=IncidentAnalysisResponse)
def get_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve single AI diagnosis by analysis ID."""
    analysis_repo = AnalysisRepository(db)
    analysis = analysis_repo.get_by_id(analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis {analysis_id} not found",
        )
    return analysis
