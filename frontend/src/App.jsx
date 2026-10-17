import React, { useState, useEffect } from 'react';
import { api } from './services/api';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import PredictEnergy from './pages/PredictEnergy';
import ProductionBatches from './pages/ProductionBatches';
import PredictionHistory from './pages/PredictionHistory';
import Products from './pages/Products';
import MachineTypes from './pages/MachineTypes';
import Shifts from './pages/Shifts';
import './App.css';

export default function App() {
  const [currentView, setCurrentView] = useState('dashboard');
  const [modelStatus, setModelStatus] = useState(null);
  const [systemOnline, setSystemOnline] = useState(false);

  useEffect(() => {
    const checkBackend = async () => {
      try {
        const [health, status] = await Promise.all([
          api.getHealth(),
          api.getModelStatus(),
        ]);
        setSystemOnline(health.status === 'healthy');
        setModelStatus(status);
      } catch (err) {
        console.warn('Backend server unreachable:', err.message);
        setSystemOnline(false);
      }
    };

    checkBackend();
    const interval = setInterval(checkBackend, 15000); // Poll status every 15s
    return () => clearInterval(interval);
  }, []);

  const renderCurrentView = () => {
    switch (currentView) {
      case 'dashboard':
        return <Dashboard setCurrentView={setCurrentView} />;
      case 'predict':
        return <PredictEnergy setCurrentView={setCurrentView} />;
      case 'batches':
        return <ProductionBatches setCurrentView={setCurrentView} />;
      case 'history':
        return <PredictionHistory setCurrentView={setCurrentView} />;
      case 'products':
        return <Products />;
      case 'machine-types':
        return <MachineTypes />;
      case 'shifts':
        return <Shifts />;
      default:
        return <Dashboard setCurrentView={setCurrentView} />;
    }
  };

  const getViewTitle = () => {
    switch (currentView) {
      case 'dashboard': return 'Operations Dashboard';
      case 'predict': return 'Predict Batch Energy';
      case 'batches': return 'Production Batches';
      case 'history': return 'Prediction History';
      case 'products': return 'Master Products';
      case 'machine-types': return 'Master Machine Types';
      case 'shifts': return 'Master Shifts';
      default: return 'Manufacturing System';
    }
  };

  return (
    <div className="app-layout">
      {/* Sidebar Navigation */}
      <Sidebar
        currentView={currentView}
        setCurrentView={setCurrentView}
        modelStatus={modelStatus}
      />

      {/* Main Content Area */}
      <div className="main-wrapper">
        <header className="topbar">
          <div className="topbar-title">
            {getViewTitle()}
          </div>
          <div className="topbar-meta">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  backgroundColor: systemOnline ? 'var(--success)' : 'var(--danger)',
                }}
              />
              <span style={{ fontSize: '0.82rem', color: systemOnline ? 'var(--neutral-700)' : 'var(--danger)' }}>
                {systemOnline ? 'API Connected (FastAPI)' : 'Connecting to API...'}
              </span>
            </div>
            <span style={{ fontSize: '0.82rem', color: 'var(--neutral-600)', fontWeight: 500 }}>
              Energy Consumption Predictor
            </span>
          </div>
        </header>

        <main className="page-content">
          {renderCurrentView()}
        </main>
      </div>
    </div>
  );
}
