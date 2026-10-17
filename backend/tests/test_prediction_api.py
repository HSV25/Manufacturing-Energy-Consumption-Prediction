import pytest


def test_official_predict_energy_endpoint(client):
    """Test mandatory official POST /predict-energy endpoint."""
    payload = {
        "quantity": 100,
        "machineHours": 8,
        "machineType": "CNC",
        "shift": "Morning",
    }
    response = client.post("/predict-energy", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "estimatedEnergy" in data
    assert isinstance(data["estimatedEnergy"], float)
    assert data["estimatedEnergy"] > 0
    assert data["unit"] == "kWh"
    assert "predictionId" in data
    assert data["predictionId"] is not None
    assert "createdAt" in data
    assert data["createdAt"] is not None

    # Verify prediction appears in prediction history with actualEnergyKwh as None (not zero)
    pred_id = data["predictionId"]
    history_res = client.get(f"/api/predictions/{pred_id}")
    assert history_res.status_code == 200
    h_data = history_res.json()
    assert h_data["quantity"] == 100
    assert h_data["machineHours"] == 8
    assert h_data["machineTypeName"] == "CNC"
    assert h_data["shiftName"] == "Morning"
    assert h_data["estimatedEnergyKwh"] == data["estimatedEnergy"]
    assert h_data["actualEnergyKwh"] is None, "Standalone pre-batch prediction actual energy must be None, not zero"


def test_predict_energy_invalid_inputs(client):
    """Test validation errors for invalid quantities or machine hours."""
    # Negative quantity
    res = client.post("/predict-energy", json={
        "quantity": -10,
        "machineHours": 8,
        "machineType": "CNC",
        "shift": "Morning",
    })
    assert res.status_code == 422

    # Zero machine hours
    res = client.post("/predict-energy", json={
        "quantity": 50,
        "machineHours": 0,
        "machineType": "CNC",
        "shift": "Morning",
    })
    assert res.status_code == 422

    # Missing shift
    res = client.post("/predict-energy", json={
        "quantity": 50,
        "machineHours": 5,
        "machineType": "CNC",
    })
    assert res.status_code == 422


def test_predict_energy_unseen_category(client):
    """Test that unconfigured machine type returns 400 and untrained machine type returns 422."""
    # 1. Unregistered machine type not in database
    res_not_in_db = client.post("/predict-energy", json={
        "quantity": 50,
        "machineHours": 5,
        "machineType": "NonExistentMachine",
        "shift": "Morning",
    })
    assert res_not_in_db.status_code == 400
    assert "does not exist in the database" in res_not_in_db.json()["detail"]

    # 2. Registered in DB but not trained in model
    client.post("/api/machine-types", json={"name": "PlasmaCutter9000", "description": "Experimental cutter"})
    res_untrained = client.post("/predict-energy", json={
        "quantity": 50,
        "machineHours": 5,
        "machineType": "PlasmaCutter9000",
        "shift": "Morning",
    })
    assert res_untrained.status_code == 422
    assert "not been trained for this category" in res_untrained.json()["detail"]


def test_prediction_history_listing_and_filtering(client):
    """Test listing and filtering of prediction history."""
    # Create two predictions with different machine types
    client.post("/predict-energy", json={"quantity": 100, "machineHours": 8, "machineType": "CNC", "shift": "Morning"})
    client.post("/predict-energy", json={"quantity": 80, "machineHours": 6, "machineType": "Lathe", "shift": "Evening"})

    # Query all
    all_res = client.get("/api/predictions")
    assert all_res.status_code == 200
    items = all_res.json()
    assert len(items) >= 2

    # Filter by machine type
    cnc_res = client.get("/api/predictions?machine_type=CNC")
    assert cnc_res.status_code == 200
    for item in cnc_res.json():
        assert "CNC" in item["machineTypeName"]


def test_prediction_history_actual_energy_separation(client):
    """Test that actual energy is displayed when batch completes, and never confused with predicted energy."""
    prods = client.get("/api/products").json()
    machines = client.get("/api/machine-types").json()
    shifts = client.get("/api/shifts").json()

    # 1. Create batch
    batch_res = client.post("/api/production-batches", json={
        "batchNumber": "AUDIT-BATCH-001",
        "productId": prods[0]["id"],
        "quantity": 200,
        "machineHours": 10.0,
        "machineTypeId": machines[0]["id"],
        "shiftId": shifts[0]["id"],
        "productionDate": "2025-07-01",
    })
    batch_id = batch_res.json()["id"]

    # 2. Predict for batch
    pred_res = client.post(f"/api/production-batches/{batch_id}/predict")
    assert pred_res.status_code == 200
    predicted_val = pred_res.json()["estimatedEnergy"]
    pred_id = pred_res.json()["predictionId"]

    # Before completion: actual energy is None
    h_before = client.get(f"/api/predictions/{pred_id}").json()
    assert h_before["actualEnergyKwh"] is None

    # 3. Post-production: record actual energy
    actual_measured = 412.35
    client.put(f"/api/production-batches/{batch_id}", json={
        "actualEnergyConsumedKwh": actual_measured,
    })

    # After completion: prediction history reflects actual energy while preserving estimated energy
    h_after = client.get(f"/api/predictions/{pred_id}").json()
    assert h_after["estimatedEnergyKwh"] == predicted_val
    assert h_after["actualEnergyKwh"] == actual_measured
    assert h_after["actualEnergyKwh"] != h_after["estimatedEnergyKwh"]


def test_predict_energy_afternoon_shift(client):
    """Test that predicting energy for the Afternoon shift succeeds seamlessly."""
    payload = {
        "quantity": 120,
        "machineHours": 6.5,
        "machineType": "CNC",
        "shift": "Afternoon",
    }
    response = client.post("/predict-energy", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["estimatedEnergy"] > 0
    assert data["unit"] == "kWh"
