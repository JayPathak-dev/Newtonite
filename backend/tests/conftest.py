"""Pytest fixtures and test environment configuration."""
import os
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models.user import User, SystemRole
from app.models.team import Team
from app.models.team_membership import TeamMembership, TeamRole
from app.models.work_item import WorkItem, WorkItemStatus, WorkItemPriority, WorkType, ApprovalStatus
from app.core.security import hash_password, create_access_token

# Use TEST_DATABASE_URL
test_engine = create_engine(
    settings.TEST_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Ensure all tables and sequences exist in test DB before running tests."""
    with test_engine.connect() as conn:
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS work_item_key_seq START WITH 1 INCREMENT BY 1"))
        conn.commit()
    Base.metadata.create_all(bind=test_engine)
    yield


@pytest.fixture(autouse=True)
def clean_tables():
    """Clean all tables before each test to maintain strict isolation."""
    with test_engine.connect() as conn:
        conn.execute(text("""
            TRUNCATE TABLE
                approval_records,
                activity_logs,
                comments,
                idempotency_records,
                work_items,
                team_memberships,
                users,
                teams
            RESTART IDENTITY CASCADE;
        """))
        conn.execute(text("SELECT setval('work_item_key_seq', 1, false)"))
        conn.commit()
    yield


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a database session for test setup and verification."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient that overrides the get_db dependency with test database session."""
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_env(db_session: Session):
    """Seed base teams and users for test scenarios."""
    pwd = hash_password("Password123!")

    # Teams
    payments_team = Team(name="Payments", description="Payments team", is_active=True)
    platform_team = Team(name="Platform", description="Platform team", is_active=True)
    ops_team = Team(name="Customer Operations", description="Ops team", is_active=True)
    db_session.add_all([payments_team, platform_team, ops_team])
    db_session.flush()

    # Users
    admin = User(name="Alex Admin", email="admin@test.com", password_hash=pwd, role=SystemRole.ADMIN, is_active=True)
    sarah = User(name="Sarah Approver", email="sarah@test.com", password_hash=pwd, role=SystemRole.USER, is_active=True)
    alex = User(name="Alex Member", email="alex@test.com", password_hash=pwd, role=SystemRole.USER, is_active=True)
    viewer = User(name="Valerie Viewer", email="viewer@test.com", password_hash=pwd, role=SystemRole.VIEWER, is_active=True)
    outsider = User(name="Oscar Outsider", email="outsider@test.com", password_hash=pwd, role=SystemRole.USER, is_active=True)

    db_session.add_all([admin, sarah, alex, viewer, outsider])
    db_session.flush()

    # Memberships
    # Sarah: Payments APPROVER
    m_sarah = TeamMembership(user_id=sarah.id, team_id=payments_team.id, team_role=TeamRole.APPROVER)
    # Alex: Payments MEMBER
    m_alex = TeamMembership(user_id=alex.id, team_id=payments_team.id, team_role=TeamRole.MEMBER)
    # Viewer: Payments & Platform MEMBER
    m_viewer = TeamMembership(user_id=viewer.id, team_id=payments_team.id, team_role=TeamRole.MEMBER)
    # Outsider: ONLY Customer Operations MEMBER
    m_outsider = TeamMembership(user_id=outsider.id, team_id=ops_team.id, team_role=TeamRole.MEMBER)

    db_session.add_all([m_sarah, m_alex, m_viewer, m_outsider])
    db_session.commit()

    return {
        "teams": {
            "payments": payments_team,
            "platform": platform_team,
            "ops": ops_team,
        },
        "users": {
            "admin": admin,
            "sarah": sarah,
            "alex": alex,
            "viewer": viewer,
            "outsider": outsider,
        },
    }


def make_auth_headers(user: User) -> dict:
    """Generate Authorization header for a user."""
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers(seeded_env):
    """Convenient auth headers for each user."""
    users = seeded_env["users"]
    return {
        "admin": make_auth_headers(users["admin"]),
        "sarah": make_auth_headers(users["sarah"]),
        "alex": make_auth_headers(users["alex"]),
        "viewer": make_auth_headers(users["viewer"]),
        "outsider": make_auth_headers(users["outsider"]),
    }
