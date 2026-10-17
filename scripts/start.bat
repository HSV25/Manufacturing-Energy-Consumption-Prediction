@echo off
REM ==============================================================================
REM Manufacturing Energy Consumption Prediction System - Windows Startup Script
REM ==============================================================================

echo ==============================================================================
echo [Energy Predictor] Starting Manufacturing Energy Consumption Prediction System
echo ==============================================================================

cd /d "%~dp0\.."

REM 1. Verify Python installation
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in system PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

REM 2. Verify Node.js and npm installation
where npm >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] npm is not installed or not in system PATH.
    echo Please install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)

REM 3. Verify Python dependencies
python -c "import fastapi, uvicorn, sklearn, sqlalchemy, pandas, joblib" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [INFO] Python dependencies missing or incomplete.
    echo [INFO] Installing backend dependencies from requirements.txt...
    python -m pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install Python dependencies.
        echo Please manually run: pip install -r requirements.txt
        pause
        exit /b 1
    )
)

REM 4. Verify or Train Machine Learning Model Artifact
python -c "from backend.ml.predict import predictor; exit(0 if predictor.is_ready() else 1)" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [INFO] Model artifact missing or incompatible with installed scikit-learn.
    echo [INFO] Training regression pipeline from data\sample_historical_production.csv...
    python backend\ml\train_model.py
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to train model.
        pause
        exit /b 1
    )
    echo [OK] Machine learning pipeline successfully fitted and saved.
) else (
    echo [OK] Trained ML model artifact verified and ready for inference.
)

REM 5. Initialize and Seed Database if needed
echo [INFO] Initializing SQLite database and verifying master data...
python scripts\seed_data.py
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Database initialization encountered a warning. Continuing startup...
)

REM 6. Start FastAPI Backend Server
echo [INFO] Starting FastAPI Backend on http://127.0.0.1:8000...
start "Energy Predictor - Backend API" cmd /k "python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000"

REM 7. Install Frontend Packages & Start React Dashboard
echo [INFO] Starting React Frontend on http://localhost:5173...
cd frontend
if not exist "node_modules" (
    echo [INFO] Installing frontend npm packages...
    call npm install
)
start "Energy Predictor - React UI" cmd /k "npm run dev"
cd ..

echo ==============================================================================
echo [Energy Predictor] Application services started!
echo   - Backend API & Interactive Docs: http://127.0.0.1:8000/docs
echo   - Health Check:                  http://127.0.0.1:8000/health
echo   - Frontend Dashboard:            http://localhost:5173
echo ==============================================================================
pause
