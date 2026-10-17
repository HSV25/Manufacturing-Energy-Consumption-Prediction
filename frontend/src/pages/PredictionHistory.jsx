import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import Modal from '../components/Modal';
import Alert from '../components/Alert';

export default function PredictionHistory() {
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [selectedMachine, setSelectedMachine] = useState('');
  const [selectedShift, setSelectedShift] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [machineTypes, setMachineTypes] = useState([]);
  const [shifts, setShifts] = useState([]);

  useEffect(() => {
    const loadFilterMasterData = async () => {
      try {
        const [machines, shs] = await Promise.all([
          api.getMachineTypes(),
          api.getShifts(),
        ]);
        setMachineTypes(machines || []);
        setShifts(shs || []);
      } catch (e) {
        console.warn('Failed to load filter dropdown master data:', e);
      }
    };
    loadFilterMasterData();
  }, []);

  // Detail Modal
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedPrediction, setSelectedPrediction] = useState(null);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {};
      if (selectedMachine) params.machine_type = selectedMachine;
      if (selectedShift) params.shift = selectedShift;
      const data = await api.getPredictions(params);
      setPredictions(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [selectedMachine, selectedShift]);

  const handleOpenDetail = (pred) => {
    setSelectedPrediction(pred);
    setDetailModalOpen(true);
  };

  const filtered = predictions.filter((p) => {
    const term = searchTerm.toLowerCase();
    return (
      (p.batchNumber && p.batchNumber.toLowerCase().includes(term)) ||
      (p.productName && p.productName.toLowerCase().includes(term)) ||
      p.machineTypeName.toLowerCase().includes(term) ||
      p.shiftName.toLowerCase().includes(term) ||
      String(p.id).includes(term)
    );
  });

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Prediction Audit History</h2>
          <p className="page-subtitle">Historical log of all machine learning inferences generated across Workflow A and Workflow B.</p>
        </div>
        <button className="btn btn-secondary" onClick={fetchHistory} title="Refresh log">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M23 4v6h-6" />
            <path d="M1 20v-6h6" />
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
          Refresh Log
        </button>
      </div>

      {error && <Alert type="danger" message={error} onClose={() => setError(null)} />}

      <div className="card">
        <div className="card-header" style={{ flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexGrow: 1, minWidth: '260px' }}>
            <input
              type="text"
              className="form-control"
              placeholder="Search by ID, batch, product..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div style={{ display: 'flex', gap: '12px' }}>
            <select
              className="form-control"
              style={{ width: '160px' }}
              value={selectedMachine}
              onChange={(e) => setSelectedMachine(e.target.value)}
            >
              <option value="">All Machines</option>
              {machineTypes.map((m) => (
                <option key={m.id} value={m.name}>
                  {m.name}
                </option>
              ))}
            </select>
            <select
              className="form-control"
              style={{ width: '140px' }}
              value={selectedShift}
              onChange={(e) => setSelectedShift(e.target.value)}
            >
              <option value="">All Shifts</option>
              {shifts.map((s) => (
                <option key={s.id} value={s.name}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '80px' }}>Audit ID</th>
                <th>Date &amp; Time</th>
                <th>Linked Batch</th>
                <th>Product Context</th>
                <th>Machine</th>
                <th>Shift</th>
                <th>Quantity</th>
                <th>Run Time</th>
                <th>Estimated Energy</th>
                <th>Actual Energy</th>
                <th>Model</th>
                <th style={{ textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="12" style={{ textAlign: 'center', padding: '32px' }}>
                    <div className="spinner spinner-primary"></div>
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan="12" className="empty-state">
                    <p className="empty-state-title">No prediction records found</p>
                    <p className="empty-state-text">
                      {searchTerm || selectedMachine || selectedShift
                        ? 'Try clearing your search or filter selections.'
                        : 'Submit your first prediction in "Predict Energy" or run one on a production batch.'}
                    </p>
                  </td>
                </tr>
              ) : (
                filtered.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <span style={{ fontWeight: 600, color: 'var(--neutral-500)' }}>#{item.id}</span>
                    </td>
                    <td style={{ fontSize: '0.82rem' }}>
                      <div>{new Date(item.createdAt).toLocaleDateString()}</div>
                      <div style={{ color: 'var(--neutral-400)' }}>
                        {new Date(item.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </div>
                    </td>
                    <td>
                      {item.batchNumber ? (
                        <span style={{ fontWeight: 600, color: 'var(--primary)' }}>
                          {item.batchNumber}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--neutral-400)', fontStyle: 'italic', fontSize: '0.82rem' }}>
                          Standalone (Pre-batch)
                        </span>
                      )}
                    </td>
                    <td>{item.productName || '—'}</td>
                    <td>
                      <span className="badge badge-neutral">{item.machineTypeName}</span>
                    </td>
                    <td>{item.shiftName}</td>
                    <td>{item.quantity} units</td>
                    <td>{item.machineHours} hrs</td>
                    <td>
                      <span className="badge badge-primary" style={{ fontSize: '0.85rem', padding: '4px 8px' }}>
                        ⚡ {item.estimatedEnergyKwh} kWh
                      </span>
                    </td>
                    <td>
                      {item.actualEnergyKwh != null ? (
                        <span style={{ fontWeight: 600, color: 'var(--success-text)' }}>
                          {item.actualEnergyKwh} kWh
                        </span>
                      ) : (
                        <span style={{ color: 'var(--neutral-400)', fontStyle: 'italic', fontSize: '0.82rem' }}>
                          — Pending
                        </span>
                      )}
                    </td>
                    <td>
                      <span style={{ fontSize: '0.78rem', color: 'var(--neutral-500)' }}>{item.modelVersion}</span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button className="btn btn-secondary btn-sm" onClick={() => handleOpenDetail(item)}>
                        Details
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Prediction Detail Modal */}
      <Modal
        isOpen={detailModalOpen}
        title={`Prediction Audit Record #${selectedPrediction?.id}`}
        onClose={() => setDetailModalOpen(false)}
        footer={
          <button className="btn btn-secondary" onClick={() => setDetailModalOpen(false)}>
            Close
          </button>
        }
      >
        {selectedPrediction && (
          <div>
            <div className="prediction-result-card" style={{ marginTop: 0, marginBottom: '20px' }}>
              <span className="prediction-result-title">Recorded Energy Estimate</span>
              <div className="prediction-value-big">
                {selectedPrediction.estimatedEnergyKwh}
                <span className="prediction-unit">kWh</span>
              </div>
              <div className="prediction-meta">
                <span>Model: {selectedPrediction.modelVersion}</span>
                <span>•</span>
                <span>Audit ID: #{selectedPrediction.id}</span>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', fontSize: '0.88rem' }}>
              <div>
                <span className="stat-label">Inference Timestamp</span>
                <p style={{ fontWeight: 600 }}>{new Date(selectedPrediction.createdAt).toLocaleString()}</p>
              </div>
              <div>
                <span className="stat-label">Associated Batch</span>
                <p style={{ fontWeight: 600, color: selectedPrediction.batchNumber ? 'var(--primary)' : 'var(--neutral-500)' }}>
                  {selectedPrediction.batchNumber || 'None (Workflow A Pre-batch)'}
                </p>
              </div>
              <div>
                <span className="stat-label">Actual Energy Consumed</span>
                <p style={{ fontWeight: 600, color: selectedPrediction.actualEnergyKwh != null ? 'var(--success-text)' : 'var(--neutral-400)' }}>
                  {selectedPrediction.actualEnergyKwh != null ? `${selectedPrediction.actualEnergyKwh} kWh` : 'Not recorded yet (Pending post-run)'}
                </p>
              </div>
              <div>
                <span className="stat-label">Machine Type Snapshot</span>
                <p style={{ fontWeight: 600 }}>{selectedPrediction.machineTypeName}</p>
              </div>
              <div>
                <span className="stat-label">Shift Snapshot</span>
                <p style={{ fontWeight: 600 }}>{selectedPrediction.shiftName}</p>
              </div>
              <div>
                <span className="stat-label">Units Produced</span>
                <p style={{ fontWeight: 600 }}>{selectedPrediction.quantity} units</p>
              </div>
              <div>
                <span className="stat-label">Machine Run Time</span>
                <p style={{ fontWeight: 600 }}>{selectedPrediction.machineHours} hours</p>
              </div>
              <div>
                <span className="stat-label">Product Context</span>
                <p style={{ fontWeight: 600 }}>{selectedPrediction.productName || 'Not specified'}</p>
              </div>
              <div>
                <span className="stat-label">Model Pipeline Version</span>
                <p style={{ fontWeight: 600 }}>{selectedPrediction.modelVersion}</p>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
