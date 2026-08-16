from typing import Optional, Dict, Any
from app.db.models import SeverityEnum, EnvironmentEnum


class SeverityEngine:
    """
    Deterministic rule-based severity calculator.
    Evaluates infrastructure impact, affected users, error rates, service criticality, and environment.
    """

    CRITICAL_SERVICES = {
        "payment",
        "payments",
        "payment-gateway",
        "auth",
        "auth-service",
        "authentication",
        "checkout",
        "billing",
        "order",
        "order-service",
        "database",
        "core-api",
        "user-service",
    }

    SYSTEMIC_KEYWORDS = [
        "out of memory",
        "oom",
        "deadlock",
        "connection pool exhausted",
        "database connection",
        "data loss",
        "segfault",
        "panic",
        "cascade failure",
        "disk full",
    ]

    HIGH_KEYWORDS = [
        "timeout",
        "500 internal server error",
        "connection refused",
        "circuit breaker",
        "rate limit exceeded",
        "nullpointerexception",
        "unhandled exception",
    ]

    @classmethod
    def calculate_severity(
        cls,
        service_name: str,
        environment: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        error_frequency: int = 1,
        affected_users: int = 0,
        request_metadata: Optional[Dict[str, Any]] = None,
    ) -> SeverityEnum:
        score = 0
        service_lower = service_name.lower().strip()
        env_lower = environment.lower().strip()
        combined_text = f"{error_message} {stack_trace or ''}".lower()

        # 1. Environment weighting
        if env_lower == EnvironmentEnum.PRODUCTION.value or env_lower == "prod":
            score += 25
        elif env_lower == EnvironmentEnum.STAGING.value or env_lower == "stage":
            score += 10

        # 2. Affected users weighting
        if affected_users >= 1000:
            score += 40
        elif affected_users >= 250:
            score += 25
        elif affected_users >= 50:
            score += 15
        elif affected_users > 0:
            score += 5

        # 3. Error frequency / velocity weighting
        if error_frequency >= 500:
            score += 30
        elif error_frequency >= 100:
            score += 20
        elif error_frequency >= 20:
            score += 10
        elif error_frequency > 1:
            score += 5

        # 4. Critical service weighting
        if any(crit in service_lower for crit in cls.CRITICAL_SERVICES):
            score += 25

        # 5. Symptom / keyword analysis
        if any(keyword in combined_text for keyword in cls.SYSTEMIC_KEYWORDS):
            score += 25
        elif any(keyword in combined_text for keyword in cls.HIGH_KEYWORDS):
            score += 12

        # 6. Score classification
        if score >= 75:
            return SeverityEnum.CRITICAL
        elif score >= 48:
            return SeverityEnum.HIGH
        elif score >= 24:
            return SeverityEnum.MEDIUM
        else:
            return SeverityEnum.LOW
