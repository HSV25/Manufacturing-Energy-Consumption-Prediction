# Manufacturing Energy Consumption Prediction System - Frontend

This is the React frontend dashboard built with Vite for the Manufacturing Energy Consumption Prediction System.

## Features
- **Dashboard**: Key operational metrics, average energy consumption, recent batch and prediction activity.
- **Predict Energy (Workflow A)**: Direct ML inference calculator for estimating energy prior to batch creation.
- **Production Batches (Workflow B)**: Schedule manufacturing runs, trigger batch predictions, and log actual post-production electricity usage.
- **Prediction History**: Complete persistent audit log of all model predictions with equipment and shift snapshots.
- **Master Data CRUD**: Full Create, Read, Update, and Delete operations for Products, Machine Types, and Shifts with database integrity restrictions.

## Development Setup

```bash
# Install dependencies
npm install

# Start Vite dev server (runs on http://localhost:5173 with proxy to backend port 8000)
npm run dev

# Build production bundle
npm run build
```
