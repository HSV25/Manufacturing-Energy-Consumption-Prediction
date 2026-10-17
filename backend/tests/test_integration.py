import pytest


def test_workflow_a_predict_before_batch(client):
    """
    Workflow A:
    1. User makes prediction for planned batch inputs before creating the batch.
    2. Prediction is computed and persisted with production_batch_id as null.
    3. User subsequently creates the production batch.
    """
    # 1. Predict
    pred_payload = {
        "quantity": 120,
        "machineHours": 7.5,
        "machineType": "CNC",
        "shift": "Morning",
    }
    pred_res = client.post("/predict-energy", json=pred_payload)
    assert pred_res.status_code == 200
    pred_data = pred_res.json()
    assert pred_data["estimatedEnergy"] > 0
    pred_id = pred_data["predictionId"]

    # Verify prediction record exists with null production_batch_id
    history_res = client.get(f"/api/predictions/{pred_id}")
    assert history_res.status_code == 200
    assert history_res.json()["productionBatchId"] is None

    # 2. User creates the batch
    prods = client.get("/api/products").json()
    machines = client.get("/api/machine-types").json()
    shifts = client.get("/api/shifts").json()

    batch_payload = {
        "batchNumber": "WORKFLOW-A-BATCH",
        "productId": prods[0]["id"],
        "quantity": 120,
        "machineHours": 7.5,
        "machineTypeId": machines[0]["id"],
        "shiftId": shifts[0]["id"],
        "productionDate": "2025-06-01",
    }
    batch_res = client.post("/api/production-batches", json=batch_payload)
    assert batch_res.status_code == 201


def test_workflow_b_predict_for_saved_batch_and_independent_actual_energy(client):
    """
    Workflow B:
    1. User creates a batch with actual energy as None.
    2. User requests energy prediction for the saved batch.
    3. Prediction is generated and linked to the batch.
    4. After production completes, user records actual energy consumed.
    5. Actual energy does not overwrite or alter the prediction audit record.
    """
    prods = client.get("/api/products").json()
    machines = client.get("/api/machine-types").json()
    shifts = client.get("/api/shifts").json()

    # 1. Create batch
    batch_payload = {
        "batchNumber": "WORKFLOW-B-BATCH",
        "productId": prods[0]["id"],
        "quantity": 250,
        "machineHours": 12.0,
        "machineTypeId": machines[0]["id"],
        "shiftId": shifts[0]["id"],
        "productionDate": "2025-06-02",
        "actualEnergyConsumedKwh": None,
    }
    batch_res = client.post("/api/production-batches", json=batch_payload)
    assert batch_res.status_code == 201
    batch_id = batch_res.json()["id"]

    # 2. Predict for batch
    predict_res = client.post(f"/api/production-batches/{batch_id}/predict")
    assert predict_res.status_code == 200
    pred_data = predict_res.json()
    predicted_kwh = pred_data["estimatedEnergy"]
    pred_id = pred_data["predictionId"]
    assert predicted_kwh > 0
    assert pred_id is not None

    # Verify link in prediction record
    pred_record = client.get(f"/api/predictions/{pred_id}").json()
    assert pred_record["productionBatchId"] == batch_id
    assert pred_record["batchNumber"] == "WORKFLOW-B-BATCH"

    # Verify batch actual energy is still None
    batch_check = client.get(f"/api/production-batches/{batch_id}").json()
    assert batch_check["actualEnergyConsumedKwh"] is None

    # 3. Post-production: Record actual energy consumed
    actual_kwh = 512.4
    update_res = client.put(f"/api/production-batches/{batch_id}", json={
        "actualEnergyConsumedKwh": actual_kwh
    })
    assert update_res.status_code == 200
    updated_batch = update_res.json()
    assert updated_batch["actualEnergyConsumedKwh"] == actual_kwh

    # 4. Crucial Check: Prediction audit record is preserved and not overwritten!
    pred_record_after = client.get(f"/api/predictions/{pred_id}").json()
    assert pred_record_after["estimatedEnergyKwh"] == predicted_kwh
    assert pred_record_after["estimatedEnergyKwh"] != actual_kwh


def test_dashboard_stats_endpoint(client):
    """Test dashboard stats calculation and aggregations."""
    res = client.get("/api/dashboard/stats")
    assert res.status_code == 200
    stats = res.json()
    assert "totalProducts" in stats
    assert "totalMachineTypes" in stats
    assert "totalShifts" in stats
    assert "totalBatches" in stats
    assert "completedBatches" in stats
    assert "pendingBatches" in stats
    assert "totalPredictions" in stats
    assert "recentPredictions" in stats
    assert "recentBatches" in stats
