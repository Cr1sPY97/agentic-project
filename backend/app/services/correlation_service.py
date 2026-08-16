import re
from typing import List, Tuple, Optional
from datetime import datetime, timezone, timedelta
from app.db.models import Incident


class CorrelationMatch:
    def __init__(self, related_incident: Incident, score: float, reason: str):
        self.related_incident = related_incident
        self.score = score
        self.reason = reason


class IncidentCorrelationEngine:
    """
    Deterministic correlation engine that identifies related or cascading incidents.
    Designed to easily allow vector/embedding-based semantic search extensions.
    """

    @classmethod
    def _normalize_text(cls, text: str) -> set:
        """Extract meaningful alphanumeric tokens, ignoring punctuation and digits."""
        tokens = re.findall(r"[a-zA-Z]{3,}", text.lower())
        stopwords = {"error", "exception", "failed", "service", "the", "and", "with", "from", "for"}
        return set(tokens) - stopwords

    @classmethod
    def find_correlations(
        cls,
        target_incident: Incident,
        candidate_incidents: List[Incident],
        threshold: float = 0.40,
    ) -> List[CorrelationMatch]:
        matches: List[CorrelationMatch] = []
        target_tokens = cls._normalize_text(f"{target_incident.title} {target_incident.error_message}")

        for candidate in candidate_incidents:
            if candidate.id == target_incident.id:
                continue

            score = 0.0
            reasons = []

            # 1. Service match
            if target_incident.service_name.lower() == candidate.service_name.lower():
                score += 0.35
                reasons.append("Identical service")

            # 2. Endpoint match
            if (
                target_incident.affected_endpoint
                and candidate.affected_endpoint
                and target_incident.affected_endpoint.lower() == candidate.affected_endpoint.lower()
            ):
                score += 0.25
                reasons.append("Identical endpoint")

            # 3. Environment match
            if target_incident.environment.lower() == candidate.environment.lower():
                score += 0.10

            # 4. Deployment version correlation
            if (
                target_incident.deployment_version
                and candidate.deployment_version
                and target_incident.deployment_version == candidate.deployment_version
            ):
                score += 0.20
                reasons.append(f"Shared deployment ({target_incident.deployment_version})")

            # 5. Error token similarity (Jaccard similarity on significant tokens)
            candidate_tokens = cls._normalize_text(f"{candidate.title} {candidate.error_message}")
            if target_tokens and candidate_tokens:
                intersection = target_tokens.intersection(candidate_tokens)
                union = target_tokens.union(candidate_tokens)
                jaccard = len(intersection) / len(union) if union else 0.0
                if jaccard >= 0.3:
                    score += round(jaccard * 0.35, 2)
                    reasons.append(f"Common error pattern ({len(intersection)} shared terms)")

            # 6. Temporal cascade proximity (within 30 mins)
            if target_incident.created_at and candidate.created_at:
                delta_minutes = abs((target_incident.created_at - candidate.created_at).total_seconds()) / 60.0
                if delta_minutes <= 30:
                    score += 0.15
                    reasons.append(f"Temporal cascade within {int(delta_minutes)}m")

            final_score = min(1.0, round(score, 2))
            if final_score >= threshold:
                reason_summary = "; ".join(reasons) if reasons else "Multi-factor similarity match"
                matches.append(CorrelationMatch(candidate, final_score, reason_summary))

        # Sort descending by correlation score
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches
