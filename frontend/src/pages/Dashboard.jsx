import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import StatCard from '../components/StatCard';
import Alert from '../components/Alert';

export default function Dashboard({ setCurrentView }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getDashboardStats();
      setStats(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  if (loading && !stats) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <div className="spinner spinner-primary" style={{ width: '32px', height: '32px' }}></div>
        <p style={{ marginTop: '12px', color: 'var(--neutral-500)' }}>Loading manufacturing metrics...</p>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Manufacturing Operations Dashboard</h2>
          <p className="page-subtitle">Real-time overview of production batches, energy predictions, and shop-floor assets.</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn btn-secondary" onClick={fetchStats} title="Refresh metrics">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M23 4v6h-6" />
              <path d="M1 20v-6h6" />
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
            Refresh
          </button>
          <button className="btn btn-primary" onClick={() => setCurrentView('predict')}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
            </svg>
            Predict Energy
          </button>
        </div>
      </div>

      {error && <Alert type="danger" message={error} onClose={() => setError(null)} />}

      {/* KPI Stats Grid */}
      <div className="stats-grid">
        <StatCard
          label="Total Predictions"
          value={stats?.totalPredictions}
          subtext="Model inference audits"
          color="blue"
          icon={
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
            </svg>
          }
        />
        <StatCard
          label="Production Batches"
          value={stats?.totalBatches}
          subtext={`${stats?.completedBatches ?? 0} completed, ${stats?.pendingBatches ?? 0} in progress`}
          color="purple"
          icon={
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
            </svg>
          }
        />
        <StatCard
          label="Avg Predicted Energy"
          value={stats?.averagePredictedEnergyKwh ? `${stats.averagePredictedEnergyKwh} kWh` : '—'}
          subtext="Calculated across all batches"
          color="teal"
          icon={
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 14 10" />
            </svg>
          }
        />
        <StatCard
          label="Avg Actual Energy"
          value={stats?.averageActualEnergyKwh ? `${stats.averageActualEnergyKwh} kWh` : '—'}
          subtext="Completed shop floor runs"
          color="green"
          icon={
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
          }
        />
      </div>

      {/* Master Data Snapshot Cards */}
      <div className="stats-grid" style={{ marginBottom: '28px' }}>
        <StatCard
          label="Catalog Products"
          value={stats?.totalProducts}
          subtext="Manufactured items"
          color="amber"
          icon={
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" />
            </svg>
          }
        />
        <StatCard
          label="Machine Types"
          value={stats?.totalMachineTypes}
          subtext="Configured workcenters"
          color="blue"
          icon={
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          }
        />
        <StatCard
          label="Active Shifts"
          value={stats?.totalShifts}
          subtext="Operating shift rosters"
          color="purple"
          icon={
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 2a7 7 0 1 0 7 7" />
            </svg>
          }
        />
      </div>

      {/* Two Column Section for Recent Activity */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(460px, 1fr))', gap: '24px' }}>
        
        {/* Recent Predictions */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Recent Energy Predictions</h3>
            <button className="btn btn-secondary btn-sm" onClick={() => setCurrentView('history')}>
              View All History
            </button>
          </div>
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Machine / Shift</th>
                  <th>Quantity / Hrs</th>
                  <th>Estimate</th>
                </tr>
              </thead>
              <tbody>
                {stats?.recentPredictions?.length === 0 ? (
                  <tr>
                    <td colSpan="4" style={{ textAlign: 'center', color: 'var(--neutral-400)', padding: '24px' }}>
                      No predictions recorded yet. Use 'Predict Energy' to create one.
                    </td>
                  </tr>
                ) : (
                  stats?.recentPredictions?.map((item) => (
                    <tr key={item.id}>
                      <td style={{ fontSize: '0.82rem' }}>
                        {new Date(item.createdAt).toLocaleDateString()} {new Date(item.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td>
                        <div style={{ fontWeight: 600 }}>{item.machineTypeName}</div>
                        <div style={{ fontSize: '0.78rem', color: 'var(--neutral-500)' }}>{item.shiftName} Shift</div>
                      </td>
                      <td>
                        <div>{item.quantity} units</div>
                        <div style={{ fontSize: '0.78rem', color: 'var(--neutral-500)' }}>{item.machineHours} hrs</div>
                      </td>
                      <td>
                        <span className="badge badge-primary" style={{ fontSize: '0.85rem', padding: '4px 8px' }}>
                          ⚡ {item.estimatedEnergyKwh} kWh
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recent Batches */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Recent Production Batches</h3>
            <button className="btn btn-secondary btn-sm" onClick={() => setCurrentView('batches')}>
              Manage Batches
            </button>
          </div>
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Batch Number</th>
                  <th>Product</th>
                  <th>Status</th>
                  <th>Actual Energy</th>
                </tr>
              </thead>
              <tbody>
                {stats?.recentBatches?.length === 0 ? (
                  <tr>
                    <td colSpan="4" style={{ textAlign: 'center', color: 'var(--neutral-400)', padding: '24px' }}>
                      No production batches created yet.
                    </td>
                  </tr>
                ) : (
                  stats?.recentBatches?.map((batch) => (
                    <tr key={batch.id}>
                      <td style={{ fontWeight: 600, color: 'var(--primary)' }}>
                        {batch.batchNumber}
                      </td>
                      <td>{batch.product?.name || '—'}</td>
                      <td>
                        {batch.actualEnergyConsumedKwh != null ? (
                          <span className="badge badge-success">Completed</span>
                        ) : (
                          <span className="badge badge-warning">In Progress</span>
                        )}
                      </td>
                      <td>
                        {batch.actualEnergyConsumedKwh != null ? (
                          <strong>{batch.actualEnergyConsumedKwh} kWh</strong>
                        ) : (
                          <span style={{ color: 'var(--neutral-400)', fontStyle: 'italic' }}>Pending</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}
