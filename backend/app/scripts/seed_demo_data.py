from datetime import datetime, timezone, timedelta
from typing import List
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, init_db
from app.db.models import User, Incident, RoleEnum, SeverityEnum, StatusEnum, EnvironmentEnum
from app.core.security import get_password_hash
from app.services.incident_service import IncidentService
from app.schemas.incident import IncidentCreate

DEFAULT_USERS = [
    {
        "username": "admin",
        "email": "admin@incidentplatform.io",
        "password": "Password123!",
        "role": RoleEnum.ADMIN.value,
    },
    {
        "username": "responder_sarah",
        "email": "sarah.sre@incidentplatform.io",
        "password": "Password123!",
        "role": RoleEnum.RESPONDER.value,
    },
    {
        "username": "viewer_bob",
        "email": "bob.analyst@incidentplatform.io",
        "password": "Password123!",
        "role": RoleEnum.VIEWER.value,
    },
]

DEMO_INCIDENTS = [
    {
        "title": "Payment Gateway Connection Pool Exhaustion",
        "service_name": "payment-gateway",
        "environment": EnvironmentEnum.PRODUCTION,
        "severity": SeverityEnum.CRITICAL,
        "error_message": "sqlalchemy.exc.TimeoutError: QueuePool limit of size 20 overflow 10 reached, connection timed out, timeout 30.00",
        "stack_trace": """Traceback (most recent call last):
  File "/app/services/checkout.py", line 142, in process_transaction
    with db_session() as session:
  File "/usr/local/lib/python3.11/site-packages/sqlalchemy/pool/base.py", line 378, in connect
    return _ConnectionFairy._checkout(self)
  File "/usr/local/lib/python3.11/site-packages/sqlalchemy/pool/base.py", line 1120, in _checkout
    fairy = self._pool._do_get()
sqlalchemy.exc.TimeoutError: QueuePool limit of size 20 overflow 10 reached, connection timed out, timeout 30.00""",
        "logs": """2026-08-16T12:00:15Z [ERROR] [payment-gateway] Failed to acquire connection from pool for checkout_id=chk_89324
2026-08-16T12:00:18Z [WARN] [payment-gateway] Active DB connections 30/30 (saturation: 100%)
2026-08-16T12:00:22Z [ERROR] [payment-gateway] HTTP 500 returned on /api/v1/payments/charge""",
        "affected_endpoint": "/api/v1/payments/charge",
        "request_metadata": {"method": "POST", "http_version": "HTTP/2", "avg_latency_ms": 30210},
        "error_frequency": 650,
        "affected_users": 1840,
        "deployment_version": "v3.12.0",
        "additional_context": {"datacenter": "us-east-1", "cluster": "prod-k8s-core"},
    },
    {
        "title": "Authentication Service JWT Verification Latency Spike",
        "service_name": "auth-service",
        "environment": EnvironmentEnum.PRODUCTION,
        "severity": SeverityEnum.HIGH,
        "error_message": "JWKS key resolution timed out after 5000ms while verifying bearer token signature",
        "stack_trace": """Traceback (most recent call last):
  File "/app/middleware/auth.py", line 88, in verify_token
    key = jwks_client.get_signing_key_from_jwt(token)
  File "/usr/local/lib/python3.11/site-packages/jwt/jwks_client.py", line 64, in get_signing_key_from_jwt
    return self.get_signing_key(header.get("kid"))
jwt.exceptions.PyJWKClientConnectionError: Connection to https://idp.internal/keys timed out.""",
        "logs": """2026-08-16T12:05:01Z [ERROR] [auth-service] JWKS fetch timeout on idp.internal
2026-08-16T12:05:10Z [WARN] [auth-service] In-memory JWKS cache miss for key_id=kid_2026_q3
2026-08-16T12:05:14Z [ERROR] [auth-service] Rejection rate elevated to 42% on /api/v1/auth/verify""",
        "affected_endpoint": "/api/v1/auth/verify",
        "request_metadata": {"method": "GET", "client_type": "mobile_ios"},
        "error_frequency": 320,
        "affected_users": 950,
        "deployment_version": "v2.8.4",
        "additional_context": {"region": "eu-central-1"},
    },
    {
        "title": "Order Service HTTP 500 Spike Post-Deployment v2.4.1",
        "service_name": "order-service",
        "environment": EnvironmentEnum.PRODUCTION,
        "severity": SeverityEnum.HIGH,
        "error_message": "AttributeError: 'NoneType' object has no attribute 'discount_rate' in calculate_total",
        "stack_trace": """Traceback (most recent call last):
  File "/app/routes/orders.py", line 62, in create_order
    total = pricing_engine.calculate_total(cart, user.tier)
  File "/app/services/pricing.py", line 31, in calculate_total
    return cart.subtotal * (1 - user.tier.discount_rate)
AttributeError: 'NoneType' object has no attribute 'discount_rate'""",
        "logs": """2026-08-16T12:15:30Z [INFO] [order-service] Deployment v2.4.1 rolled out by CI/CD
2026-08-16T12:16:02Z [ERROR] [order-service] Unhandled AttributeError on /api/v1/orders for anonymous user session
2026-08-16T12:16:15Z [ERROR] [order-service] 500 error count reached 150 in 1 minute""",
        "affected_endpoint": "/api/v1/orders",
        "request_metadata": {"method": "POST", "payload_size_bytes": 1420},
        "error_frequency": 240,
        "affected_users": 420,
        "deployment_version": "v2.4.1",
        "additional_context": {"release_commit": "7a9b3f1", "deploy_type": "rolling"},
    },
    {
        "title": "Notification Worker Node Out-Of-Memory Crash",
        "service_name": "notification-service",
        "environment": EnvironmentEnum.PRODUCTION,
        "severity": SeverityEnum.MEDIUM,
        "error_message": "Process terminated by kernel OOM-killer: memory cgroup limit (1024MB) exceeded",
        "stack_trace": """[Kernel Log]
[18429.102931] oom-killer: gfp_mask=0x100cca(GFP_HIGHUSER_MOVABLE), order=0, oom_score_adj=998
[18429.102934] Task in /kubepods.slice/kubepods-burstable.slice/notification-worker killed as a result of limit reached
[18429.103010] Memory cgroup out of memory: Killed process 4128 (celery_worker) total-vm:1482012kB, anon-rss:1048576kB""",
        "logs": """2026-08-16T12:20:00Z [INFO] [notification-service] Processing bulk marketing blast campaign_id=camp_4829
2026-08-16T12:21:45Z [WARN] [notification-service] Memory usage: 980MB / 1024MB (95.7%)
2026-08-16T12:22:01Z [FATAL] [notification-service] Worker process disconnected unexpectedly""",
        "affected_endpoint": "/tasks/email-blast",
        "request_metadata": {"queue": "bulk-notifications", "batch_size": 250000},
        "error_frequency": 45,
        "affected_users": 80,
        "deployment_version": "v1.9.0",
        "additional_context": {"node": "worker-pool-m5-2xlarge"},
    },
    {
        "title": "Checkout Inventory Service Database Lock Contention",
        "service_name": "payment-gateway",
        "environment": EnvironmentEnum.PRODUCTION,
        "severity": SeverityEnum.HIGH,
        "error_message": "psycopg2.OperationalError: canceling statement due to statement timeout (deadlock detected with transaction 89324)",
        "stack_trace": """Traceback (most recent call last):
  File "/app/services/inventory.py", line 95, in reserve_stock
    session.execute("SELECT * FROM inventory WHERE item_id = :id FOR UPDATE", {"id": item_id})
psycopg2.OperationalError: canceling statement due to statement timeout (deadlock detected with transaction 89324)""",
        "logs": """2026-08-16T12:02:10Z [WARN] [payment-gateway] Transaction 89324 holding row lock on inventory SKU-998
2026-08-16T12:02:30Z [ERROR] [payment-gateway] Deadlock timeout triggered after 20000ms""",
        "affected_endpoint": "/api/v1/payments/charge",
        "request_metadata": {"method": "POST", "sku": "SKU-998"},
        "error_frequency": 180,
        "affected_users": 520,
        "deployment_version": "v3.12.0",
        "additional_context": {"correlated_with": "payment-gateway connection exhaustion"},
    },
    {
        "title": "External SMS Gateway Webhook Timeout",
        "service_name": "notification-service",
        "environment": EnvironmentEnum.STAGING,
        "severity": SeverityEnum.LOW,
        "error_message": "httpx.ConnectTimeout: HTTPSConnectionPool(host='api.smsvendor.mock', port=443): Max retries exceeded with url /v1/messages",
        "stack_trace": """Traceback (most recent call last):
  File "/app/adapters/sms.py", line 40, in send_sms
    response = client.post("https://api.smsvendor.mock/v1/messages", json=payload)
httpx.ConnectTimeout: Connection timed out after 10.0s""",
        "logs": """2026-08-16T12:30:00Z [WARN] [notification-service] SMS vendor staging mock endpoint unreachable
2026-08-16T12:30:10Z [INFO] [notification-service] Fallback queued message for retry in 60s""",
        "affected_endpoint": "/api/v1/sms/send",
        "request_metadata": {"vendor": "smsvendor-sandbox"},
        "error_frequency": 12,
        "affected_users": 5,
        "deployment_version": "v1.9.1",
        "additional_context": {"env": "staging"},
    },
]


def seed_database(db: Session) -> dict:
    init_db()

    # 1. Seed Users
    created_users = {}
    for u in DEFAULT_USERS:
        existing = db.query(User).filter(User.username == u["username"]).first()
        if not existing:
            user = User(
                username=u["username"],
                email=u["email"],
                hashed_password=get_password_hash(u["password"]),
                role=u["role"],
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            created_users[u["username"]] = user
        else:
            created_users[u["username"]] = existing

    # 2. Seed Incidents
    admin_user = created_users.get("admin")
    incident_service = IncidentService(db)
    seeded_incidents: List[Incident] = []

    for inc_data in DEMO_INCIDENTS:
        existing = db.query(Incident).filter(Incident.title == inc_data["title"]).first()
        if not existing:
            inc_create = IncidentCreate(**inc_data)
            created_inc = incident_service.create_incident(inc_create, creator=admin_user)
            seeded_incidents.append(created_inc)
        else:
            seeded_incidents.append(existing)

    return {
        "users_count": len(created_users),
        "incidents_count": len(seeded_incidents),
        "admin_username": "admin",
        "responder_username": "responder_sarah",
        "viewer_username": "viewer_bob",
        "default_password": "Password123!",
    }


if __name__ == "__main__":
    db = SessionLocal()
    try:
        res = seed_database(db)
        print(f"Database seeded successfully: {res}")
    finally:
        db.close()
