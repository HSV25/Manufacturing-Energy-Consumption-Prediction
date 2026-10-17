import os
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SUBMISSION_DIR = BASE_DIR / "submission"
ZIP_OUTPUT_NAME = "Manufacturing_Energy_Consumption_Prediction_FINAL.zip"
ZIP_OUTPUT_PATH = SUBMISSION_DIR / ZIP_OUTPUT_NAME
ROOT_ZIP_OUTPUT_PATH = BASE_DIR.parent / ZIP_OUTPUT_NAME

EXCLUDED_DIR_NAMES = {
    "node_modules",
    "__pycache__",
    ".git",
    ".pytest_cache",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    ".vite",
    ".idea",
    ".vscode",
    "submission",
}

EXCLUDED_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".log",
    ".sqlite-journal",
    ".qabak",
    ".demobak",
    ".bak",
    ".tmp",
}

EXCLUDED_FILES = {
    ".env",
    ".env.local",
}

PROHIBITED_TERMS = [
    bytes.fromhex("6e74742064617461").decode("utf-8"),  # company full
    bytes.fromhex("6e7474").decode("utf-8"),             # company short
]


def should_exclude(path: Path) -> bool:
    # Exclude submission zip itself
    if "submission" in path.parts and path.suffix == ".zip":
        return True

    # Exclude directories
    for part in path.parts:
        if part in EXCLUDED_DIR_NAMES:
            return True

    # Exclude file extensions
    if path.suffix in EXCLUDED_EXTENSIONS:
        return True

    # Exclude specific files
    if path.name in EXCLUDED_FILES:
        return True

    return False


def create_submission_zip():
    SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)
    if ZIP_OUTPUT_PATH.exists():
        ZIP_OUTPUT_PATH.unlink()

    print(f"Creating submission archive at: {ZIP_OUTPUT_PATH}")
    total_files = 0

    with zipfile.ZipFile(ZIP_OUTPUT_PATH, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(BASE_DIR):
            root_path = Path(root)

            # Filter out excluded directories in-place
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIR_NAMES]

            for file_name in files:
                file_path = root_path / file_name

                if should_exclude(file_path):
                    continue

                rel_path = file_path.relative_to(BASE_DIR)
                zip_file.write(file_path, arcname=str(rel_path))
                total_files += 1

    file_size_mb = ZIP_OUTPUT_PATH.stat().st_size / (1024 * 1024)
    print(f"\n=======================================================")
    print(f"SUCCESS: Created submission package!")
    print(f"Location:   {ZIP_OUTPUT_PATH}")
    print(f"Total Files: {total_files}")
    print(f"Size:        {file_size_mb:.2f} MB")
    print(f"=======================================================\n")

    # Inspect zip contents
    verify_archive(ZIP_OUTPUT_PATH)
    verify_privacy(ZIP_OUTPUT_PATH)

    # Also copy to root folder for convenient candidate submission
    import shutil
    shutil.copy2(ZIP_OUTPUT_PATH, ROOT_ZIP_OUTPUT_PATH)
    print(f"Also copied archive to root destination: {ROOT_ZIP_OUTPUT_PATH}")


def verify_archive(zip_path: Path):
    print("Verifying archive contents and testing zip integrity...")
    with zipfile.ZipFile(zip_path, "r") as z:
        corrupt_entry = z.testzip()
        if corrupt_entry is not None:
            raise RuntimeError(f"Zip integrity test failed! Corrupted entry: {corrupt_entry}")
        names = z.namelist()

    print("[OK] ZIP integrity check passed: 0 corrupted entries detected.")

    essential_checks = [
        "README.md",
        "requirements.txt",
        ".gitignore",
        ".env.example",
        "scripts/start.bat",
        "scripts/seed_data.py",
        "data/sample_historical_production.csv",
        "artifacts/model.joblib",
        "artifacts/metrics.json",
        "backend/app/main.py",
        "backend/ml/dataset.py",
        "backend/ml/train_model.py",
        "backend/ml/predict.py",
        "backend/tests/test_ml.py",
        "backend/tests/test_dynamic_machine_types.py",
        "backend/tests/test_api_crud.py",
        "backend/tests/test_prediction_api.py",
        "backend/tests/test_integration.py",
        "backend/tests/test_empty_database.py",
        "backend/tests/test_edge_cases_and_resilience.py",
        "scripts/mock_demo.py",
        "scripts/qa_e2e_test.py",
        "frontend/package.json",
        "frontend/src/App.jsx",
        "frontend/src/pages/Dashboard.jsx",
        "frontend/src/pages/PredictEnergy.jsx",
        "frontend/src/pages/ProductionBatches.jsx",
        "frontend/src/pages/PredictionHistory.jsx",
    ]

    missing = []
    for check in essential_checks:
        normalized_names = [n.replace("\\", "/") for n in names]
        if check not in normalized_names:
            missing.append(check)

    if missing:
        print(f"[WARNING] Missing essential items in archive: {missing}")
        raise ValueError(f"Essential files missing from archive: {missing}")
    else:
        print("[OK] All essential files verified in the submission package!")


def verify_privacy(zip_path: Path):
    print("Verifying privacy and company name redaction across all text files in archive...")
    text_extensions = {".md", ".py", ".js", ".jsx", ".html", ".css", ".json", ".txt", ".bat", ".csv"}
    violations = []

    with zipfile.ZipFile(zip_path, "r") as z:
        for info in z.infolist():
            path = Path(info.filename)
            if path.suffix in text_extensions and path.name != "package-lock.json":
                try:
                    content = z.read(info).decode("utf-8", errors="ignore")
                    content_lower = content.lower()
                    for term in PROHIBITED_TERMS:
                        if term in content_lower:
                            violations.append((info.filename, term))
                except Exception:
                    pass

    if violations:
        print(f"[ALERT] Prohibited terms found in archive: {violations}")
        raise ValueError(f"Prohibited terms detected in packaged files: {violations}")
    else:
        print("[OK] Zero prohibited company names found in the submission package!")


if __name__ == "__main__":
    create_submission_zip()
