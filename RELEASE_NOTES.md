# Release Notes

## Manufacturing Energy Consumption Prediction System

These release notes describe the main features and setup information for
the project package. Check the included source code and test results for
the exact behavior of the version you submit.


### Overview

This release contains a web application for estimating energy
consumption for manufacturing production batches. It combines a React
frontend, a Python API, an SQLite database, and a saved scikit-learn
regression model.

The project is intended for demonstration and assessment. The included
training data is synthetic and is not a replacement for measurements
from a real factory.

### Main Features

#### 1. Dashboard

-   Provides an overview of production and prediction information.
-   Displays summary values calculated from application data, where
    supported by the current implementation.

#### 2. Master Data Management

Users can manage the following records:

-   **Products:** Add, view, edit, and delete product records.
-   **Machine Types:** Maintain the machine types available to the
    application.
-   **Shifts:** Maintain production shift records.

Master data is used by the production batch and prediction workflows.

#### 3. Production Batch Management

-   Create and view production batches.
-   Record product, quantity, machine operating hours, machine type,
    shift, and production date.
-   Record actual energy consumption when it becomes available.
-   Validate key production inputs, such as positive quantities and
    machine hours, according to the application rules.

#### 4. Energy Prediction

-   Estimate energy consumption in kilowatt-hours (kWh).
-   Use production quantity, machine hours, machine type, and shift as
    model inputs.
-   Provide the `POST /predict-energy` API endpoint for a prediction
    request.
-   Save prediction history so results can be reviewed later.

Predictions are estimates. Actual energy usage may differ from the model
output.

#### 5. Prediction History

-   View saved prediction records.
-   Review estimated energy values.
-   Compare predictions with actual energy values when actual readings
    have been recorded.

#### 6. Machine Learning Model

-   Uses a supervised regression pipeline built with scikit-learn.
-   Processes numerical and categorical input features.
-   Includes a saved model artifact and evaluation metadata.
-   Pins scikit-learn to version `1.6.1` in the dependency configuration
    to support consistent model loading.

The sample dataset is synthetic. Reported metrics describe performance
on that dataset and should not be interpreted as proven accuracy on real
industrial equipment.

#### 7. Database

The application uses SQLite to store core application data. The
documented main tables are:

-   `products`
-   `machine_types`
-   `shifts`
-   `production_batches`
-   `energy_predictions`

#### 8. Testing

The project includes backend tests that can be run with:

``` powershell
pytest backend/tests -v
```

The frontend production build can be checked with:

``` powershell
cd frontend
npm run build
```

Run these checks against the exact source code and dependencies included
in the final submission package.

### Technology Stack

-   React and Vite
-   JavaScript and CSS
-   Python and FastAPI
-   Uvicorn
-   SQLite and SQLAlchemy
-   scikit-learn, pandas, NumPy, and Joblib
-   pytest

### Installation and Startup

Install the Python dependencies from the project root:

``` powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Install the frontend dependencies:

``` powershell
cd frontend
npm install
cd ..
```

Start the backend in one terminal:

``` powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in another terminal:

``` powershell
cd frontend
npm run dev
```

The frontend normally runs at `http://localhost:5173`. The API
documentation is available at `http://127.0.0.1:8000/docs` while the
backend is running.

On Windows, the project may also include `scripts/start.bat` as a
startup option.

### Known Limitations

-   The model is trained on synthetic data rather than real factory
    meter readings.
-   Prediction accuracy must be evaluated using representative
    real-world data before operational use.
-   The current model represents each batch with one machine type.
-   Estimated energy consumption is not a guarantee of actual
    consumption.

### Future Improvements

Potential future work includes:

-   Training and evaluating the model on verified factory measurements.
-   Adding electricity cost estimates.
-   Supporting production routes involving multiple machines.
-   Integrating smart meters for automatic energy readings.

### Package Contents

The release package should contain the application source code, backend
and frontend dependencies, sample data, saved model artifacts, tests,
setup scripts, and project documentation.

Before distributing the release, verify that the ZIP contains the latest
source code and required files, and excludes private credentials, local
virtual environments, temporary caches, and unrelated files.
