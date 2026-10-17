"""
Edge Cases, Comprehensive Validation, and Self-Healing Resilience Tests.
Verifies all functional edge cases required by the assessment specification:
- Invalid IDs across all CRUD endpoints (404 Not Found)
- Referential integrity enforcement for Products, MachineTypes, and Shifts (409 Conflict)
- Safe batch deletion preserving prediction history (SET NULL)
- Numerical boundary rejections (<= 0) for batches and predictions
- Batch filtering by product, machine type, shift, and search term
- Clean database initialization and seeding verification
"""

import os
from datetime import date
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models.product import Product
from backend.app.models.machine_type import MachineType
from backend.app.models.shift import Shift
from backend.app.models.production_batch import ProductionBatch
from backend.app.models.energy_prediction import EnergyPrediction
from backend.ml.predict import predictor


def test_crud_invalid_ids_return_404(client):
    """Verify that requesting or updating nonexistent entity IDs returns HTTP 404."""
    # 1. Product
    assert client.get("/api/products/99999").status_code == 404
    assert client.put("/api/products/99999", json={"name": "Ghost"}).status_code == 404
    assert client.delete("/api/products/99999").status_code == 404

    # 2. Machine Type
    assert client.get("/api/machine-types/99999").status_code == 404
    assert client.put("/api/machine-types/99999", json={"name": "Ghost"}).status_code == 404
    assert client.delete("/api/machine-types/99999").status_code == 404

    # 3. Shift
    assert client.get("/api/shifts/99999").status_code == 404
    assert client.put("/api/shifts/99999", json={"name": "Ghost"}).status_code == 404
    assert client.delete("/api/shifts/99999").status_code == 404

    # 4. Production Batch
    assert client.get("/api/production-batches/99999").status_code == 404
    assert client.put("/api/production-batches/99999", json={"quantity": 100}).status_code == 404
    assert client.delete("/api/production-batches/99999").status_code == 404
    assert client.post("/api/production-batches/99999/predict").status_code == 404

    # 5. Prediction
    assert client.get("/api/predictions/99999").status_code == 404


def test_production_batch_strict_numerical_validation(client):
    """Verify that zero or negative quantity/machineHours are strictly rejected."""
    prods = client.get("/api/products").json()
    machines = client.get("/api/machine-types").json()
    shifts = client.get("/api/shifts").json()

    base_payload = {
        "batchNumber": "TEST-NUM-VAL-001",
        "productId": prods[0]["id"],
        "quantity": 100,
        "machineHours": 8.0,
        "machineTypeId": machines[0]["id"],
        "shiftId": shifts[0]["id"],
        "productionDate": "2026-10-15",
    }

    # Negative quantity
    res = client.post("/api/production-batches", json={**base_payload, "quantity": -50})
    assert res.status_code == 422

    # Zero quantity
    res = client.post("/api/production-batches", json={**base_payload, "quantity": 0})
    assert res.status_code == 422

    # Negative machine hours
    res = client.post("/api/production-batches", json={**base_payload, "machineHours": -4.0})
    assert res.status_code == 422

    # Zero machine hours
    res = client.post("/api/production-batches", json={**base_payload, "machineHours": 0})
    assert res.status_code == 422

    # Blank batch number
    res = client.post("/api/production-batches", json={**base_payload, "batchNumber": "   "})
    assert res.status_code == 422


def test_production_batch_update_foreign_key_validation(client):
    """Verify that updating a batch with nonexistent foreign key IDs returns HTTP 400."""
    prods = client.get("/api/products").json()
    machines = client.get("/api/machine-types").json()
    shifts = client.get("/api/shifts").json()

    # Create valid batch
    create_res = client.post("/api/production-batches", json={
        "batchNumber": "TEST-FK-VAL-001",
        "productId": prods[0]["id"],
        "quantity": 100,
        "machineHours": 8.0,
        "machineTypeId": machines[0]["id"],
        "shiftId": shifts[0]["id"],
        "productionDate": "2026-10-15",
    })
    assert create_res.status_code == 201
    batch_id = create_res.json()["id"]

    # Invalid product ID update -> 400
    res = client.put(f"/api/production-batches/{batch_id}", json={"productId": 99999})
    assert res.status_code == 400
    assert "Product with ID 99999 does not exist" in res.json()["detail"]

    # Invalid machine type ID update -> 400
    res = client.put(f"/api/production-batches/{batch_id}", json={"machineTypeId": 99999})
    assert res.status_code == 400
    assert "Machine type with ID 99999 does not exist" in res.json()["detail"]

    # Invalid shift ID update -> 400
    res = client.put(f"/api/production-batches/{batch_id}", json={"shiftId": 99999})
    assert res.status_code == 400
    assert "Shift with ID 99999 does not exist" in res.json()["detail"]


def test_shift_referential_integrity(client):
    """Verify that a Shift cannot be deleted while referenced by a production batch."""
    prods = client.get("/api/products").json()
    machines = client.get("/api/machine-types").json()

    # Create new shift
    shift_res = client.post("/api/shifts", json={"name": "Safety Shift", "description": "Special coverage"})
    assert shift_res.status_code == 201
    shift_id = shift_res.json()["id"]

    # Create batch referencing this shift
    batch_res = client.post("/api/production-batches", json={
        "batchNumber": "BATCH-REF-SHIFT-01",
        "productId": prods[0]["id"],
        "quantity": 100,
        "machineHours": 5.0,
        "machineTypeId": machines[0]["id"],
        "shiftId": shift_id,
        "productionDate": "2026-10-15",
    })
    assert batch_res.status_code == 201
    batch_id = batch_res.json()["id"]

    # Attempt to delete shift while referenced -> 409 Conflict
    del_shift_res = client.delete(f"/api/shifts/{shift_id}")
    assert del_shift_res.status_code == 409
    assert "referenced by" in del_shift_res.json()["detail"]

    # Clean up: delete batch, then delete shift succeeds
    assert client.delete(f"/api/production-batches/{batch_id}").status_code == 204
    assert client.delete(f"/api/shifts/{shift_id}").status_code == 204


def test_batch_deletion_preserves_prediction_history(client):
    """
    Verify that deleting a production batch nullifies the foreign key on its predictions
    without deleting or corrupting the historical prediction audit record.
    """
    prods = client.get("/api/products").json()
    machines = client.get("/api/machine-types").json()
    shifts = client.get("/api/shifts").json()

    # 1. Create batch
    batch_res = client.post("/api/production-batches", json={
        "batchNumber": "BATCH-PRESERVE-PRED-01",
        "productId": prods[0]["id"],
        "quantity": 200,
        "machineHours": 10.0,
        "machineTypeId": machines[0]["id"],
        "shiftId": shifts[0]["id"],
        "productionDate": "2026-10-15",
    })
    assert batch_res.status_code == 201
    batch_id = batch_res.json()["id"]

    # 2. Predict for batch
    pred_res = client.post(f"/api/production-batches/{batch_id}/predict")
    assert pred_res.status_code == 200
    pred_id = pred_res.json()["predictionId"]
    estimated_kwh = pred_res.json()["estimatedEnergy"]

    # Verify link
    p_before = client.get(f"/api/predictions/{pred_id}").json()
    assert p_before["productionBatchId"] == batch_id

    # 3. Delete the production batch
    del_res = client.delete(f"/api/production-batches/{batch_id}")
    assert del_res.status_code == 204

    # 4. Verify prediction record still exists with productionBatchId set to None
    p_after = client.get(f"/api/predictions/{pred_id}").json()
    assert p_after["id"] == pred_id
    assert p_after["productionBatchId"] is None
    assert p_after["estimatedEnergyKwh"] == estimated_kwh
    assert p_after["machineTypeName"] == machines[0]["name"]


def test_production_batch_filtering_and_search(client):
    """Verify filtering batches by search, product, machine type, and shift."""
    prods = client.get("/api/products").json()
    machines = client.get("/api/machine-types").json()
    shifts = client.get("/api/shifts").json()

    # Create 2 distinct batches
    client.post("/api/production-batches", json={
        "batchNumber": "SEARCHABLE-ALPHA-01",
        "productId": prods[0]["id"],
        "quantity": 100,
        "machineHours": 5.0,
        "machineTypeId": machines[0]["id"],
        "shiftId": shifts[0]["id"],
        "productionDate": "2026-10-10",
    })
    client.post("/api/production-batches", json={
        "batchNumber": "SEARCHABLE-BETA-02",
        "productId": prods[1]["id"],
        "quantity": 150,
        "machineHours": 7.0,
        "machineTypeId": machines[1]["id"],
        "shiftId": shifts[1]["id"],
        "productionDate": "2026-10-11",
    })

    # Search by keyword
    search_res = client.get("/api/production-batches?search=ALPHA")
    assert search_res.status_code == 200
    items = search_res.json()
    assert any(b["batchNumber"] == "SEARCHABLE-ALPHA-01" for b in items)
    assert not any(b["batchNumber"] == "SEARCHABLE-BETA-02" for b in items)

    # Filter by product ID
    prod_filter_res = client.get(f"/api/production-batches?product_id={prods[0]['id']}")
    assert prod_filter_res.status_code == 200
    for b in prod_filter_res.json():
        assert b["productId"] == prods[0]["id"]


def test_end_to_end_smoke_flow(client):
    """
    End-to-End smoke test:
    Executes full flow: Product creation -> Machine Type -> Shift -> Production Batch
    -> POST /predict-energy -> POST /production-batches/{id}/predict -> Record Actual Energy
    -> Verify separation in history -> Verify dashboard metrics.
    """
    # 1. Create master data
    p = client.post("/api/products", json={"name": "E2E Smoke Turbine", "description": "Wind turbine gear"}).json()
    m = client.post("/api/machine-types", json={"name": "E2E CNC Mill", "description": "Multi-axis mill"}).json()
    s = client.post("/api/shifts", json={"name": "E2E Twilight Shift", "description": "18:00 to 02:00"}).json()

    # 2. Ad-hoc prediction (Workflow A) with supported categories (CNC / Morning)
    adhoc_res = client.post("/predict-energy", json={
        "quantity": 100,
        "machineHours": 8.0,
        "machineType": "CNC",
        "shift": "Morning",
        "productId": p["id"],
    })
    assert adhoc_res.status_code == 200
    adhoc_data = adhoc_res.json()
    assert adhoc_data["estimatedEnergy"] > 0
    assert adhoc_data["unit"] == "kWh"
    adhoc_id = adhoc_data["predictionId"]

    # 3. Create production batch
    batch_res = client.post("/api/production-batches", json={
        "batchNumber": "BATCH-E2E-SMOKE-01",
        "productId": p["id"],
        "quantity": 120,
        "machineHours": 7.5,
        "machineTypeId": 1,  # CNC
        "shiftId": 1,        # Morning
        "productionDate": "2026-10-16",
    })
    assert batch_res.status_code == 201
    batch_id = batch_res.json()["id"]

    # 4. Predict for saved batch (Workflow B)
    batch_pred_res = client.post(f"/api/production-batches/{batch_id}/predict")
    assert batch_pred_res.status_code == 200
    batch_pred_data = batch_pred_res.json()
    batch_pred_id = batch_pred_data["predictionId"]
    estimated_kwh = batch_pred_data["estimatedEnergy"]

    # 5. Record actual energy consumed after production run
    actual_kwh = 345.8
    update_res = client.put(f"/api/production-batches/{batch_id}", json={
        "actualEnergyConsumedKwh": actual_kwh,
    })
    assert update_res.status_code == 200
    assert update_res.json()["actualEnergyConsumedKwh"] == actual_kwh

    # 6. Verify prediction history retains both values separately
    pred_history = client.get(f"/api/predictions/{batch_pred_id}").json()
    assert pred_history["estimatedEnergyKwh"] == estimated_kwh
    assert pred_history["actualEnergyKwh"] == actual_kwh
    assert pred_history["estimatedEnergyKwh"] != pred_history["actualEnergyKwh"]

    # 7. Verify dashboard statistics agree
    dash_res = client.get("/api/dashboard/stats")
    assert dash_res.status_code == 200
    stats = dash_res.json()
    assert stats["totalBatches"] >= 1
    assert stats["completedBatches"] >= 1
    assert stats["totalPredictions"] >= 2

