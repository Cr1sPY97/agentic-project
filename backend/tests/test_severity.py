from app.services.severity_service import SeverityEngine
from app.db.models import SeverityEnum


def test_severity_critical_calculation():
    severity = SeverityEngine.calculate_severity(
        service_name="payment-gateway",
        environment="production",
        error_message="sqlalchemy.exc.TimeoutError: QueuePool limit reached, connection pool exhausted",
        stack_trace="FATAL: remaining connection slots are reserved",
        error_frequency=600,
        affected_users=2000,
    )
    assert severity == SeverityEnum.CRITICAL


def test_severity_high_calculation():
    severity = SeverityEngine.calculate_severity(
        service_name="order-service",
        environment="production",
        error_message="500 Internal Server Error timeout during checkout",
        error_frequency=50,
        affected_users=100,
    )
    assert severity in (SeverityEnum.HIGH, SeverityEnum.CRITICAL)


def test_severity_low_calculation():
    severity = SeverityEngine.calculate_severity(
        service_name="analytics-collector",
        environment="development",
        error_message="Minor formatting warning on telemetry payload",
        error_frequency=1,
        affected_users=0,
    )
    assert severity == SeverityEnum.LOW
