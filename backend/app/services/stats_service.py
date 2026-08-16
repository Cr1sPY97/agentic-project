from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.db.models import Incident, StatusEnum, SeverityEnum, EnvironmentEnum, IncidentAnalysis
from app.schemas.stats import IncidentDashboardStats, ServiceStats


class StatsService:
    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_stats(self) -> IncidentDashboardStats:
        total = self.db.query(Incident).count()
        
        # Status breakdown
        status_counts = dict(
            self.db.query(Incident.status, func.count(Incident.id))
            .group_by(Incident.status)
            .all()
        )
        
        open_count = status_counts.get(StatusEnum.OPEN.value, 0)
        inv_count = status_counts.get(StatusEnum.INVESTIGATING.value, 0)
        mit_count = status_counts.get(StatusEnum.MITIGATED.value, 0)
        res_count = status_counts.get(StatusEnum.RESOLVED.value, 0)
        closed_count = status_counts.get(StatusEnum.CLOSED.value, 0)

        # Severity breakdown
        severity_counts = dict(
            self.db.query(Incident.severity, func.count(Incident.id))
            .group_by(Incident.severity)
            .all()
        )
        
        crit_count = severity_counts.get(SeverityEnum.CRITICAL.value, 0)
        high_count = severity_counts.get(SeverityEnum.HIGH.value, 0)
        med_count = severity_counts.get(SeverityEnum.MEDIUM.value, 0)
        low_count = severity_counts.get(SeverityEnum.LOW.value, 0)

        # Environment breakdown
        env_counts = dict(
            self.db.query(Incident.environment, func.count(Incident.id))
            .group_by(Incident.environment)
            .all()
        )

        # Top affected services
        service_aggregates = (
            self.db.query(
                Incident.service_name,
                func.count(Incident.id).label("total"),
                func.sum(
                    case(
                        (Incident.severity == SeverityEnum.CRITICAL.value, 1),
                        else_=0,
                    )
                ).label("critical_total"),
            )
            .group_by(Incident.service_name)
            .order_by(func.count(Incident.id).desc())
            .limit(10)
            .all()
        )

        top_services = [
            ServiceStats(
                service_name=row[0],
                incident_count=row[1],
                critical_count=int(row[2] or 0),
            )
            for row in service_aggregates
        ]

        # Calculate Average Resolution Time (MTTR)
        resolved_incidents = (
            self.db.query(Incident.created_at, Incident.resolved_at)
            .filter(Incident.resolved_at.isnot(None))
            .all()
        )
        if resolved_incidents:
            total_duration_mins = sum(
                (res - cre).total_seconds() / 60.0
                for cre, res in resolved_incidents
                if res and cre and res >= cre
            )
            avg_mttr = round(total_duration_mins / len(resolved_incidents), 1)
        else:
            avg_mttr = 0.0

        # AI-assisted count (distinct incidents analyzed)
        ai_assisted_count = (
            self.db.query(func.count(func.distinct(IncidentAnalysis.incident_id)))
            .scalar() or 0
        )

        return IncidentDashboardStats(
            total_incidents=total,
            open_incidents=open_count,
            investigating_incidents=inv_count,
            mitigated_incidents=mit_count,
            resolved_incidents=res_count,
            closed_incidents=closed_count,
            critical_incidents=crit_count,
            high_incidents=high_count,
            medium_incidents=med_count,
            low_incidents=low_count,
            by_severity=severity_counts,
            by_status=status_counts,
            by_environment=env_counts,
            top_affected_services=top_services,
            average_resolution_time_minutes=avg_mttr,
            ai_assisted_count=ai_assisted_count,
        )
