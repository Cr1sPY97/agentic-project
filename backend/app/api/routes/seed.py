from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import User, RoleEnum
from app.scripts.seed_demo_data import seed_database
from app.api.dependencies import require_roles

router = APIRouter()


@router.post("", summary="Seed Demo Incidents and Users")
def seed_demo_data(
    current_user: User = Depends(require_roles(RoleEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Populate the database with realistic synthetic production incidents and role accounts.
    Restricted to ADMIN.
    """
    result = seed_database(db)
    return {
        "status": "success",
        "message": "Demo incidents and users seeded successfully.",
        "data": result,
    }
