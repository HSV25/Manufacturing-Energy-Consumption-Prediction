# Manufacturing-Energy-Consumption-Prediction
A machine-learning web application for predicting manufacturing energy consumption

# Manufacturing Energy Consumption Prediction System

## About the Project

This web application estimates the electrical energy needed for a
manufacturing production batch. It uses production quantity, machine
operating hours, machine type, and shift to predict energy consumption
in kilowatt-hours (kWh).

Users can also manage production information, record actual energy
usage, and view prediction history. The included dataset is synthetic
and is intended for development and demonstration.

## Features

-   View key information on the dashboard.
-   Add, view, update, and delete products, machine types, and shifts.
-   Create and manage production batches.
-   Predict energy consumption for new inputs or a saved batch.
-   Record actual energy consumption after production.
-   View prediction history and compare estimated and actual values when
    actual data is available.
-   Store application data in an SQLite database.

## Technology Used

-   **Frontend:** React, Vite, JavaScript, CSS
-   **Backend:** Python, FastAPI, Uvicorn
-   **Database:** SQLite, SQLAlchemy
-   **Machine learning:** scikit-learn, pandas, NumPy, Joblib
-   **Testing:** pytest, FastAPI TestClient

## Project Structure

``` text
.
├── backend/       # API, database models, ML code and tests
├── frontend/      # React user interface
├── data/          # Sample training dataset
├── artifacts/     # Saved model and evaluation metrics
├── scripts/       # Setup and project utility scripts
├── requirements.txt
└── README.md
```

## Requirements

Install the following before running the project:

-   Python 3.10--3.13
-   Node.js 18 or later
-   npm

The backend requirements pin scikit-learn to version `1.6.1`. Use the
version specified in `requirements.txt` so the saved model can be loaded
with the expected library version.

## Installation

Open a terminal in the project folder.

### 1. Install backend dependencies

``` powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

On macOS or Linux, activate the virtual environment with:

``` bash
source venv/bin/activate
```

### 2. Install frontend dependencies

``` powershell
cd frontend
npm install
cd ..
```

### 3. Prepare sample data

To load the demo records into the database, run:

``` powershell
python scripts/seed_data.py
```

Run this when you need demo data. Check the script before running it
against a database that already contains information.

## Run the Application

On Windows, you can use `scripts/start.bat` to start the application.

### Start the backend
From the project root, run:

``` powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

The backend will be available at:

-   API documentation: http://127.0.0.1:8000/docs
-   Health check: http://127.0.0.1:8000/health

### Start the frontend
Open a second terminal:

``` powershell
cd frontend
npm run dev
```

Open the local URL shown by Vite, normally http://localhost:5173.



## How Energy Prediction Works

The model uses these inputs:

-   `quantity`: number of units to produce
-   `machineHours`: machine operating time in hours
-   `machineType`: type of machine
-   `shift`: production shift

It predicts **estimated energy consumption in kWh**. The model was
trained using sample manufacturing data. Since this dataset is
synthetic, its evaluation results do not prove how accurately the system
would predict energy use in a real factory.

## Prediction API

The application provides a `POST /predict-energy` endpoint.

Example request:

``` json
{
  "quantity": 100,
  "machineHours": 8,
  "machineType": "CNC",
  "shift": "Morning"
}
```

The response includes the estimated energy value and its unit. For the
exact response fields, open the API documentation at
http://127.0.0.1:8000/docs after starting the backend.

## Database

The SQLite database stores information in these main tables:

-   `products`
-   `machine_types`
-   `shifts`
-   `production_batches`
-   `energy_predictions`

Actual energy consumption is stored separately from prediction records,
so the original estimate remains available for comparison.

## Run Tests

From the project root, run:

``` powershell
pytest backend/tests -v
```

To check the frontend build, run:

``` powershell
cd frontend
npm run build
```

## Limitations

-   The included training dataset is synthetic, not collected from real
    factory meters.
-   The model should be validated with real production data before it is
    used for operational decisions.
-   Each production batch is represented using one machine type.

## Possible Future Improvements

-   Train and evaluate the model using real factory energy readings.
-   Add electricity cost estimates based on current tariffs.
-   Support batches that pass through multiple machines.
-   Connect smart meters to record actual energy use automatically.

## Submission Contents

The project package should include the source code, dependency files,
sample dataset, saved model artifacts, tests, and this README. Do not
include passwords, private credentials, virtual environments, or
temporary cache files.
