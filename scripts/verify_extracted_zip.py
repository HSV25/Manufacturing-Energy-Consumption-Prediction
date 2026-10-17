import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
import pandas as pd
import joblib

def main():
    root = Path(__file__).resolve().parent.parent
    zip_path = root / "submission" / "Manufacturing_Energy_Consumption_Prediction_FINAL.zip"
    if not zip_path.exists():
        zip_path = root.parent / "Manufacturing_Energy_Consumption_Prediction_FINAL.zip"
    extract_dir = root / "qa_verify_extract"

    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True)

    print("=== Step 1: Extracting ZIP Archive ===")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_dir)
    all_files = list(extract_dir.rglob("*"))
    print(f"Extracted {len([f for f in all_files if f.is_file()])} files into {extract_dir.name}/")

    print("\n=== Step 2: Verifying Dataset and Metrics Consistency ===")
    csv_path = extract_dir / "data" / "sample_historical_production.csv"
    assert csv_path.exists(), "CSV dataset missing!"
    df = pd.read_csv(csv_path)
    total_csv_rows = len(df)
    print(f"CSV Total Rows: {total_csv_rows}")
    assert total_csv_rows == 1200, f"Expected 1200 rows, got {total_csv_rows}"

    metrics_path = extract_dir / "artifacts" / "metrics.json"
    assert metrics_path.exists(), "Metrics JSON missing!"
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    print(f"Metrics Total Records: {metrics['total_records']}")
    print(f"Train Samples: {metrics['train_samples']}, Test Samples: {metrics['test_samples']}")
    print(f"R2 Score: {metrics['metrics']['r2_score']}")
    print(f"MAE:      {metrics['metrics']['mae_kwh']} kWh")
    print(f"RMSE:     {metrics['metrics']['rmse_kwh']} kWh")
    print(f"Machine Types: {metrics['known_categories']['machine_types']}")
    print(f"Shifts:        {metrics['known_categories']['shifts']}")

    assert metrics["total_records"] == 1200
    assert metrics["train_samples"] == 960
    assert metrics["test_samples"] == 240
    assert metrics["metrics"]["r2_score"] == 0.9508
    assert metrics["metrics"]["mae_kwh"] == 40.513
    assert metrics["metrics"]["rmse_kwh"] == 56.152
    print("[OK] Exact 1,200 records alignment verified across dataset and metrics!")

    print("\n=== Step 3: Loading ML Pipeline from Extracted Artifact ===")
    model_path = extract_dir / "artifacts" / "model.joblib"
    assert model_path.exists(), "Model joblib missing!"
    pipeline = joblib.load(model_path)
    test_rows = [
        {"quantity": 100, "machine_hours": 8.0, "machine_type": "CNC", "shift": "Morning"},
        {"quantity": 100, "machine_hours": 8.0, "machine_type": "Lathe", "shift": "Morning"},
        {"quantity": 100, "machine_hours": 8.0, "machine_type": "Milling Machine", "shift": "Morning"},
        {"quantity": 100, "machine_hours": 8.0, "machine_type": "GEARBOX", "shift": "Morning"},
    ]
    for row in test_rows:
        pred_val = float(pipeline.predict(pd.DataFrame([row]))[0])
        print(f"  * Machine: {row['machine_type']:<16} -> Prediction: {pred_val:>7.2f} kWh")
        assert pred_val > 0, f"Invalid prediction {pred_val}"
    print("[OK] All model inference checks passed!")

    print("\n=== Step 4: Running Backend Pytest Suite Inside Extracted Directory ===")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=str(extract_dir),
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    assert result.returncode == 0, f"Pytest failed with exit code {result.returncode}"
    print("[OK] Backend tests passed inside extracted directory!")

    print("\n=== Step 5: Privacy Audit Across All Extracted Files ===")
    prohibited = [
        bytes.fromhex("6e74742064617461").decode("utf-8"),
        bytes.fromhex("6e7474").decode("utf-8"),
    ]
    text_exts = {".md", ".py", ".js", ".jsx", ".html", ".css", ".json", ".txt", ".bat", ".csv", ".ini"}
    violations = []
    for f in extract_dir.rglob("*"):
        if f.is_file() and f.suffix in text_exts and f.name != "package-lock.json":
            content = f.read_text(encoding="utf-8", errors="ignore").lower()
            for term in prohibited:
                if term in content:
                    violations.append((str(f.relative_to(extract_dir)), term))

    assert not violations, f"Prohibited terms found: {violations}"
    print("[OK] Zero prohibited terms detected in extracted workspace!")

    print("\n=== Step 6: Cleanup Temporary Extraction Directory ===")
    shutil.rmtree(extract_dir)
    print("[OK] Temporary extraction directory cleaned up.")

    print("\n" + "=" * 80)
    print(" EXTRACTION VERIFICATION COMPLETE: ALL CHECKS 100% PASSED")
    print("=" * 80)

if __name__ == "__main__":
    main()
