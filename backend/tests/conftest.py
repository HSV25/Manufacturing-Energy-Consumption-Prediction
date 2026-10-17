import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models.product import Product
from backend.app.models.machine_type import MachineType
from backend.app.models.shift import Shift

# Use in-memory SQLite with StaticPool for thread-safe test isolation
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Provides a fresh database session for each test function."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    # Pre-seed basic master data for convenience
    p1 = Product(name="Test Gearbox", description="Gearbox component")
    p2 = Product(name="Test Valve", description="Valve component")
    m1 = MachineType(name="CNC", description="CNC Machine")
    m2 = MachineType(name="Lathe", description="Lathe Machine")
    m3 = MachineType(name="Milling Machine", description="Milling Machine")
    s1 = Shift(name="Morning", description="06:00 AM – 02:00 PM (06:00 – 14:00) Morning Shift")
    s2 = Shift(name="Afternoon", description="12:00 PM – 04:00 PM (12:00 – 16:00) Afternoon Shift")
    s3 = Shift(name="Evening", description="02:00 PM – 10:00 PM (14:00 – 22:00) Evening Shift")
    s4 = Shift(name="Night", description="10:00 PM – 06:00 AM (22:00 – 06:00) Overnight Shift")

    session.add_all([p1, p2, m1, m2, m3, s1, s2, s3, s4])
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Provides a FastAPI TestClient with the database dependency overridden."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
