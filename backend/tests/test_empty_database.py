"""
Tests verifying system behavior on a completely empty database.
Verifies that all endpoints return clean empty responses / safe errors
without 500 server crashes.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app


@pytest.fixture(scope="function")
def empty_db_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    session.close()


def test_empty_database_all_endpoints(empty_db_client):
    """Test that all endpoints handle an empty database safely."""
    # 1. Health check
    h = empty_db_client.get("/health")
    assert h.status_code == 200
    assert h.json()["status"] == "healthy"

    # 2. Dashboard stats with empty DB
    dash = empty_db_client.get("/api/dashboard/stats")
    assert dash.status_code == 200
    data = dash.json()
    assert data["totalProducts"] == 0
    assert data["totalMachineTypes"] == 0
    assert data["totalShifts"] == 0
    assert data["totalBatches"] == 0
    assert data["totalPredictions"] == 0
    assert data["averagePredictedEnergyKwh"] is None
    assert data["averageActualEnergyKwh"] is None
    assert data["recentPredictions"] == []
    assert data["recentBatches"] == []

    # 3. Model status with empty DB
    model_st = empty_db_client.get("/api/dashboard/model-status")
    assert model_st.status_code == 200
    m_data = model_st.json()
    assert m_data["configured_machine_types"] == []
    assert m_data["unsupported_configured_machines"] == []

    # 4. CRUD listings on empty DB
    assert empty_db_client.get("/api/products").json() == []
    assert empty_db_client.get("/api/machine-types").json() == []
    assert empty_db_client.get("/api/shifts").json() == []
    assert empty_db_client.get("/api/production-batches").json() == []
    assert empty_db_client.get("/api/predictions").json() == []

    # 5. Prediction when no machines exist in DB -> 400 Bad Request
    pred_res = empty_db_client.post("/predict-energy", json={
        "quantity": 100,
        "machineHours": 8,
        "machineType": "CNC",
        "shift": "Morning",
    })
    assert pred_res.status_code == 400
    assert "does not exist in the database" in pred_res.json()["detail"]
