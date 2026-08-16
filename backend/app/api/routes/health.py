from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import get_db
from app.core.config import settings
from app.ai.client import AIClientFactory

router = APIRouter()


@router.get("")
def health_check():
    """General service liveness check."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/db")
def health_check_db(db: Session = Depends(get_db)):
    """Database connectivity and query execution check."""
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unreachable: {str(exc)}",
        )


@router.get("/ai")
def health_check_ai():
    """AI engine readiness and configured provider status."""
    client = AIClientFactory.get_client()
    return {
        "status": "healthy",
        "provider": client.get_provider_name(),
        "model": client.get_model_name(),
        "prompt_version": settings.PROMPT_VERSION,
        "timeout_seconds": settings.AI_TIMEOUT_SECONDS,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
