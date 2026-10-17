import pytest
from datetime import date


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "model_ready" in data


# ===================== PRODUCT CRUD =====================

def test_product_crud_flow(client):
    # 1. Create
    create_res = client.post("/api/products", json={"name": "Alloy Wheel", "description": "Automotive alloy rim"})
    assert create_res.status_code == 201
    prod = create_res.json()
    assert prod["name"] == "Alloy Wheel"
    prod_id = prod["id"]

    # 2. Duplicate rejection
    dup_res = client.post("/api/products", json={"name": "Alloy Wheel"})
    assert dup_res.status_code == 409

    # 3. Read All
    list_res = client.get("/api/products")
    assert list_res.status_code == 200
    names = [p["name"] for p in list_res.json()]
    assert "Alloy Wheel" in names

    # 4. Read One
    get_res = client.get(f"/api/products/{prod_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Alloy Wheel"

    # 5. Update
    update_res = client.put(f"/api/products/{prod_id}", json={"description": "Updated alloy rim description"})
    assert update_res.status_code == 200
    assert update_res.json()["description"] == "Updated alloy rim description"

    # 6. Delete
    del_res = client.delete(f"/api/products/{prod_id}")
    assert del_res.status_code == 204

    # 7. Verify Deleted
    get_deleted = client.get(f"/api/products/{prod_id}")
    assert get_deleted.status_code == 404


def test_product_validation(client):
    # Empty name should fail
    res = client.post("/api/products", json={"name": "   "})
    assert res.status_code == 422


# ===================== MACHINE TYPE CRUD =====================

def test_machine_type_crud_flow(client):
    # 1. Create
    res = client.post("/api/machine-types", json={"name": "Stamping Press", "description": "Hydraulic stamping press"})
    assert res.status_code == 201
    mt_id = res.json()["id"]

    # 2. Duplicate rejection
    dup_res = client.post("/api/machine-types", json={"name": "Stamping Press"})
    assert dup_res.status_code == 409

    # 3. Read All
    list_res = client.get("/api/machine-types")
    assert list_res.status_code == 200
    assert any(m["id"] == mt_id for m in list_res.json())

    # 4. Update
    up_res = client.put(f"/api/machine-types/{mt_id}", json={"description": "Updated press"})
    assert up_res.status_code == 200
    assert up_res.json()["description"] == "Updated press"

    # 5. Delete
    del_res = client.delete(f"/api/machine-types/{mt_id}")
    assert del_res.status_code == 204


# ===================== SHIFT CRUD =====================

def test_shift_crud_flow(client):
    # 1. Create
    res = client.post("/api/shifts", json={"name": "Weekend Shift", "description": "Weekend coverage"})
    assert res.status_code == 201
    s_id = res.json()["id"]

    # 2. Duplicate rejection
    dup_res = client.post("/api/shifts", json={"name": "Weekend Shift"})
    assert dup_res.status_code == 409

    # 3. Read All
    list_res = client.get("/api/shifts")
    assert list_res.status_code == 200
    assert any(s["id"] == s_id for s in list_res.json())

    # 4. Update
    up_res = client.put(f"/api/shifts/{s_id}", json={"description": "Special weekend rotation"})
    assert up_res.status_code == 200
    assert up_res.json()["description"] == "Special weekend rotation"

    # 5. Delete
    del_res = client.delete(f"/api/shifts/{s_id}")
    assert del_res.status_code == 204


def test_shift_time_formatting_and_standardization(client):
    """Test that ambiguous shift descriptions (12:00 - 4:00) are standardized to unambiguous 12h/24h format."""
    # 1. Ambiguous afternoon format
    res = client.post("/api/shifts", json={
        "name": "Midday Shift",
        "description": "12:00 - 4:00",
    })
    assert res.status_code == 201
    data = res.json()
    assert "12:00 PM – 04:00 PM (12:00 – 16:00)" in data["description"]
    shift_id = data["id"]

    # 2. Overnight shift representation
    res_overnight = client.post("/api/shifts", json={
        "name": "Graveyard Shift",
        "description": "10:00 PM – 06:00 AM (22:00 – 06:00) Overnight Third Shift",
    })
    assert res_overnight.status_code == 201
    data_on = res_overnight.json()
    assert "10:00 PM – 06:00 AM" in data_on["description"]

    # Cleanup
    client.delete(f"/api/shifts/{shift_id}")
    client.delete(f"/api/shifts/{data_on['id']}")


# ===================== PRODUCTION BATCH CRUD =====================

def test_production_batch_crud_and_fk_enforcement(client):
    # Get IDs of pre-seeded master records
    prods = client.get("/api/products").json()
    machines = client.get("/api/machine-types").json()
    shifts = client.get("/api/shifts").json()

    prod_id = prods[0]["id"]
    machine_id = machines[0]["id"]
    shift_id = shifts[0]["id"]

    # 1. Create Batch with positive values
    payload = {
        "batchNumber": "TEST-BATCH-001",
        "productId": prod_id,
        "quantity": 150,
        "machineHours": 6.5,
        "machineTypeId": machine_id,
        "shiftId": shift_id,
        "productionDate": "2025-05-15",
        "actualEnergyConsumedKwh": None,
    }
    create_res = client.post("/api/production-batches", json=payload)
    assert create_res.status_code == 201
    batch = create_res.json()
    batch_id = batch["id"]
    assert batch["batchNumber"] == "TEST-BATCH-001"
    assert batch["quantity"] == 150
    assert batch["actualEnergyConsumedKwh"] is None

    # 2. Cannot delete Product while referenced
    del_prod_res = client.delete(f"/api/products/{prod_id}")
    assert del_prod_res.status_code == 409
    assert "referenced by" in del_prod_res.json()["detail"]

    # 3. Cannot delete Machine Type while referenced
    del_mt_res = client.delete(f"/api/machine-types/{machine_id}")
    assert del_mt_res.status_code == 409
    assert "referenced by" in del_mt_res.json()["detail"]

    # 4. Duplicate batch number rejection
    dup_res = client.post("/api/production-batches", json=payload)
    assert dup_res.status_code == 409

    # 5. Nonexistent FK rejection
    invalid_fk_payload = {**payload, "batchNumber": "TEST-BATCH-002", "productId": 9999}
    bad_fk_res = client.post("/api/production-batches", json=invalid_fk_payload)
    assert bad_fk_res.status_code == 400

    # 6. Read Batch
    get_res = client.get(f"/api/production-batches/{batch_id}")
    assert get_res.status_code == 200
    assert get_res.json()["product"]["name"] == prods[0]["name"]

    # 7. Update Actual Energy
    update_res = client.put(f"/api/production-batches/{batch_id}", json={"actualEnergyConsumedKwh": 285.75})
    assert update_res.status_code == 200
    assert update_res.json()["actualEnergyConsumedKwh"] == 285.75

    # 8. Delete Batch
    del_batch_res = client.delete(f"/api/production-batches/{batch_id}")
    assert del_batch_res.status_code == 204

    # 9. Now product can be deleted safely
    del_prod_after = client.delete(f"/api/products/{prod_id}")
    assert del_prod_after.status_code == 204
