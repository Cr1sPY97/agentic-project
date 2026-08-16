from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.db.database import init_db
from app.middleware.logging import RequestLoggingMiddleware
from app.services.incident_service import InvalidStatusTransitionError
from app.api.routes import (
    auth,
    users,
    incidents,
    analysis,
    stats,
    audit,
    health,
    seed,
)

# Initialize structured logging
setup_logging(level="DEBUG" if settings.DEBUG else "INFO")
logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database schema is initialized
    logger.info("Initializing database tables and indices...")
    init_db()
    logger.info("Database initialized successfully.")
    yield
    # Shutdown
    logger.info("Shutting down application...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="""
## Production AI-Powered Incident Response & Root Cause Analysis Platform

An enterprise-grade platform for automated SRE incident ingestion, deterministic severity classification,
incident correlation, and structured GenAI root cause analysis (RCA).

### Key Architectural Capabilities:
* **Deterministic & GenAI Dual Severity Engines**: Rule-based heuristic scoring compared against LLM reasoning.
* **Structured AI Diagnoses**: Pydantic validated output (Root Cause, Confidence Score, Evidence, Remediation Steps).
* **Incident Correlation**: Multi-signal similarity detection for cascade failure analysis.
* **Role-Based Access Control (RBAC)**: `ADMIN`, `RESPONDER`, and `VIEWER` roles via JWT.
* **Lifecycle State Machine**: Strict status transitions (`OPEN` -> `INVESTIGATING` -> `MITIGATED` -> `RESOLVED` -> `CLOSED`).
* **Observability & Audit Trail**: Correlation IDs (`X-Request-ID`), structured JSON logging, and immutable audit logs.
""",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 1. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Request Logging & Correlation ID Middleware
app.add_middleware(RequestLoggingMiddleware)


# 3. Centralized Exception Handlers
@app.exception_handler(InvalidStatusTransitionError)
async def invalid_status_transition_handler(request: Request, exc: InvalidStatusTransitionError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc), "error_type": "InvalidStatusTransitionError"},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc), "error_type": "ValueError"},
    )


# 4. Mount API Routes
app.include_router(health.router, prefix=f"{settings.API_V1_STR}/health", tags=["Health & Observability"])
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication & RBAC"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["User Management"])
app.include_router(incidents.router, prefix=f"{settings.API_V1_STR}/incidents", tags=["Incident Management"])
app.include_router(analysis.router, prefix=f"{settings.API_V1_STR}", tags=["AI Root Cause Analysis"])
app.include_router(stats.router, prefix=f"{settings.API_V1_STR}", tags=["Dashboard & Metrics"])
app.include_router(audit.router, prefix=f"{settings.API_V1_STR}/audit", tags=["Audit Trail"])
app.include_router(seed.router, prefix=f"{settings.API_V1_STR}/seed", tags=["Demo Data Management"])


@app.get("/", tags=["Root"])
def root_endpoint():
    return {
        "title": settings.PROJECT_NAME,
        "status": "online",
        "docs_url": "/docs",
        "health_check": f"{settings.API_V1_STR}/health",
    }
