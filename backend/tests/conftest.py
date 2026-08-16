import sys
import os

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.db.models import User, RoleEnum
from app.core.security import get_password_hash, create_access_token
from app.main import app

# Use in-memory SQLite database for fast, isolated tests
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session() -> Generator:
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session) -> Generator:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session) -> User:
    user = User(
        username="test_admin",
        email="admin@test.io",
        hashed_password=get_password_hash("AdminPass123!"),
        role=RoleEnum.ADMIN.value,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def responder_user(db_session) -> User:
    user = User(
        username="test_responder",
        email="responder@test.io",
        hashed_password=get_password_hash("ResponderPass123!"),
        role=RoleEnum.RESPONDER.value,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def viewer_user(db_session) -> User:
    user = User(
        username="test_viewer",
        email="viewer@test.io",
        hashed_password=get_password_hash("ViewerPass123!"),
        role=RoleEnum.VIEWER.value,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_headers(admin_user) -> dict:
    token = create_access_token({"sub": admin_user.username, "user_id": admin_user.id, "role": admin_user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def responder_headers(responder_user) -> dict:
    token = create_access_token({"sub": responder_user.username, "user_id": responder_user.id, "role": responder_user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_headers(viewer_user) -> dict:
    token = create_access_token({"sub": viewer_user.username, "user_id": viewer_user.id, "role": viewer_user.role})
    return {"Authorization": f"Bearer {token}"}
