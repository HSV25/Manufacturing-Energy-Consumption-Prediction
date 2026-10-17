import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'energy_prediction.db'}")
MODEL_PATH = os.getenv("MODEL_PATH", str(BASE_DIR / "artifacts" / "model.joblib"))
METRICS_PATH = os.getenv("METRICS_PATH", str(BASE_DIR / "artifacts" / "metrics.json"))
SAMPLE_DATA_PATH = os.getenv("SAMPLE_DATA_PATH", str(BASE_DIR / "data" / "sample_historical_production.csv"))

# CORS
cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000")
CORS_ORIGINS = [origin.strip() for origin in cors_raw.split(",") if origin.strip()]

# Server
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

MODEL_VERSION = "v1.1.0"
