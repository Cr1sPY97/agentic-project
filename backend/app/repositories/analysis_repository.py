from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.db.models import IncidentAnalysis


class AnalysisRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, analysis: IncidentAnalysis) -> IncidentAnalysis:
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def get_by_id(self, analysis_id: int) -> Optional[IncidentAnalysis]:
        return self.db.query(IncidentAnalysis).filter(IncidentAnalysis.id == analysis_id).first()

    def get_by_incident_id(self, incident_id: int) -> List[IncidentAnalysis]:
        return (
            self.db.query(IncidentAnalysis)
            .filter(IncidentAnalysis.incident_id == incident_id)
            .order_by(desc(IncidentAnalysis.created_at))
            .all()
        )

    def get_latest_by_incident_id(self, incident_id: int) -> Optional[IncidentAnalysis]:
        return (
            self.db.query(IncidentAnalysis)
            .filter(IncidentAnalysis.incident_id == incident_id)
            .order_by(desc(IncidentAnalysis.created_at))
            .first()
        )
