import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import Modal from '../components/Modal';
import Alert from '../components/Alert';

export default function ProductionBatches() {
  const [batches, setBatches] = useState([]);
  const [products, setProducts] = useState([]);
  const [machineTypes, setMachineTypes] = useState([]);
  const [shifts, setShifts] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  // Modals
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [predictResultModalOpen, setPredictResultModalOpen] = useState(false);

  const [selectedBatch, setSelectedBatch] = useState(null);
  const [predictionResult, setPredictionResult] = useState(null);
  const [predictingBatchId, setPredictingBatchId] = useState(null);
  const [batchPredictions, setBatchPredictions] = useState([]);
  const [loadingBatchPreds, setLoadingBatchPreds] = useState(false);

  // Form states
  const [formData, setFormData] = useState({
    batchNumber: '',
    productId: '',
    quantity: '',
    machineHours: '',
    machineTypeId: '',
    shiftId: '',
    productionDate: new Date().toISOString().split('T')[0],
    actualEnergyConsumedKwh: '',
  });
  const [formSubmitting, setFormSubmitting] = useState(false);

  const fetchMasterAndBatches = async () => {
    try {
      setLoading(true);
      setError(null);
      const [batchesData, prodsData, machinesData, shiftsData] = await Promise.all([
        api.getProductionBatches(),
        api.getProducts(),
        api.getMachineTypes(),
        api.getShifts(),
      ]);
      setBatches(batchesData);
      setProducts(prodsData);
      setMachineTypes(machinesData);
      setShifts(shiftsData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMasterAndBatches();
  }, []);

  const handleOpenCreate = () => {
    const nextBatchNum = `BATCH-2025-${String(batches.length + 1).padStart(3, '0')}`;
    setFormData({
      batchNumber: nextBatchNum,
      productId: products[0]?.id || '',
      quantity: 100,
      machineHours: 8,
      machineTypeId: machineTypes[0]?.id || '',
      shiftId: shifts[0]?.id || '',
      productionDate: new Date().toISOString().split('T')[0],
      actualEnergyConsumedKwh: '',
    });
    setError(null);
    setCreateModalOpen(true);
  };

  const handleOpenEdit = (batch) => {
    setSelectedBatch(batch);
    setFormData({
      batchNumber: batch.batchNumber,
      productId: batch.productId,
      quantity: batch.quantity,
      machineHours: batch.machineHours,
      machineTypeId: batch.machineTypeId,
      shiftId: batch.shiftId,
      productionDate: batch.productionDate,
      actualEnergyConsumedKwh: batch.actualEnergyConsumedKwh != null ? batch.actualEnergyConsumedKwh : '',
    });
    setError(null);
    setEditModalOpen(true);
  };

  const handleOpenDetail = async (batch) => {
    setSelectedBatch(batch);
    setDetailModalOpen(true);
    setLoadingBatchPreds(true);
    try {
      const preds = await api.getPredictions({ batch_id: batch.id });
      setBatchPredictions(preds);
    } catch (err) {
      console.warn('Failed to load batch predictions:', err);
      setBatchPredictions([]);
    } finally {
      setLoadingBatchPreds(false);
    }
  };

  const handleOpenDelete = (batch) => {
    setSelectedBatch(batch);
    setError(null);
    setDeleteModalOpen(true);
  };

  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    try {
      setFormSubmitting(true);
      setError(null);

      const payload = {
        batchNumber: formData.batchNumber.trim(),
        productId: Number(formData.productId),
        quantity: Number(formData.quantity),
        machineHours: Number(formData.machineHours),
        machineTypeId: Number(formData.machineTypeId),
        shiftId: Number(formData.shiftId),
        productionDate: formData.productionDate,
        actualEnergyConsumedKwh: formData.actualEnergyConsumedKwh !== '' ? Number(formData.actualEnergyConsumedKwh) : null,
      };

      await api.createProductionBatch(payload);
      setSuccess(`Production batch '${payload.batchNumber}' created successfully.`);
      setCreateModalOpen(false);
      fetchMasterAndBatches();
    } catch (err) {
      setError(err.message);
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    try {
      setFormSubmitting(true);
      setError(null);

      const payload = {
        batchNumber: formData.batchNumber.trim(),
        productId: Number(formData.productId),
        quantity: Number(formData.quantity),
        machineHours: Number(formData.machineHours),
        machineTypeId: Number(formData.machineTypeId),
        shiftId: Number(formData.shiftId),
        productionDate: formData.productionDate,
        actualEnergyConsumedKwh: formData.actualEnergyConsumedKwh !== '' ? Number(formData.actualEnergyConsumedKwh) : null,
      };

      await api.updateProductionBatch(selectedBatch.id, payload);
      setSuccess(`Production batch '${payload.batchNumber}' updated successfully.`);
      setEditModalOpen(false);
      fetchMasterAndBatches();
    } catch (err) {
      setError(err.message);
    } finally {
      setFormSubmitting(false);
    }
  };

  const confirmDelete = async () => {
    if (!selectedBatch) return;
    try {
      setFormSubmitting(true);
      setError(null);
      await api.deleteProductionBatch(selectedBatch.id);
      setSuccess(`Batch '${selectedBatch.batchNumber}' deleted successfully.`);
      setDeleteModalOpen(false);
      setSelectedBatch(null);
      fetchMasterAndBatches();
    } catch (err) {
      setError(err.message);
      setDeleteModalOpen(false);
    } finally {
      setFormSubmitting(false);
    }
  };

  // Workflow B: Predict Energy for an existing batch
  const handlePredictForBatch = async (batch) => {
    try {
      setPredictingBatchId(batch.id);
      setError(null);
      const res = await api.predictBatchEnergy(batch.id);
      setSelectedBatch(batch);
      setPredictionResult(res);
      setPredictResultModalOpen(true);
      setSuccess(`Prediction calculated for batch '${batch.batchNumber}'.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setPredictingBatchId(null);
    }
  };

  const filtered = batches.filter((b) =>
    b.batchNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (b.product && b.product.name.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Production Batches</h2>
          <p className="page-subtitle">Track shop-floor manufacturing runs, trigger ML energy predictions, and record verified energy consumption.</p>
        </div>
        <button className="btn btn-primary" onClick={handleOpenCreate}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          Create Batch
        </button>
      </div>

      {error && <Alert type="danger" message={error} onClose={() => setError(null)} />}
      {success && <Alert type="success" message={success} onClose={() => setSuccess(null)} />}

      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexGrow: 1, maxWidth: '400px' }}>
            <input
              type="text"
              className="form-control"
              placeholder="Search batches by ID or product..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <span style={{ fontSize: '0.85rem', color: 'var(--neutral-500)' }}>
            Showing <strong>{filtered.length}</strong> of <strong>{batches.length}</strong> batches
          </span>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Batch #</th>
                <th>Product</th>
                <th>Machine</th>
                <th>Shift</th>
                <th>Quantity</th>
                <th>Hours</th>
                <th>Date</th>
                <th>Actual Energy</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="10" style={{ textAlign: 'center', padding: '32px' }}>
                    <div className="spinner spinner-primary"></div>
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan="10" className="empty-state">
                    <p className="empty-state-title">No production batches found</p>
                    <p className="empty-state-text">
                      {searchTerm ? 'No batches match your search filter.' : 'Click "Create Batch" to start scheduling manufacturing.'}
                    </p>
                  </td>
                </tr>
              ) : (
                filtered.map((batch) => {
                  const isCompleted = batch.actualEnergyConsumedKwh != null;
                  return (
                    <tr key={batch.id}>
                      <td style={{ fontWeight: 600, color: 'var(--primary)' }}>
                        <a href="#view" onClick={(e) => { e.preventDefault(); handleOpenDetail(batch); }}>
                          {batch.batchNumber}
                        </a>
                      </td>
                      <td style={{ fontWeight: 500 }}>{batch.product?.name || '—'}</td>
                      <td>
                        <span className="badge badge-neutral">{batch.machineType?.name || '—'}</span>
                      </td>
                      <td>{batch.shift?.name || '—'}</td>
                      <td><strong>{batch.quantity}</strong> units</td>
                      <td>{batch.machineHours} hrs</td>
                      <td style={{ fontSize: '0.82rem' }}>{batch.productionDate}</td>
                      <td>
                        {isCompleted ? (
                          <span style={{ fontWeight: 600, color: 'var(--success-text)' }}>
                            {batch.actualEnergyConsumedKwh} kWh
                          </span>
                        ) : (
                          <span style={{ color: 'var(--neutral-400)', fontStyle: 'italic', fontSize: '0.85rem' }}>
                            Pending
                          </span>
                        )}
                      </td>
                      <td>
                        {isCompleted ? (
                          <span className="badge badge-success">Completed</span>
                        ) : (
                          <span className="badge badge-warning">In Progress</span>
                        )}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div className="actions-cell" style={{ justifyContent: 'flex-end' }}>
                          <button
                            className="btn btn-primary btn-sm"
                            onClick={() => handlePredictForBatch(batch)}
                            disabled={predictingBatchId === batch.id}
                            title="Workflow B: Predict Electricity using ML model"
                          >
                            {predictingBatchId === batch.id ? (
                              <span className="spinner" style={{ width: '12px', height: '12px' }}></span>
                            ) : (
                              '⚡ Predict'
                            )}
                          </button>
                          <button className="btn btn-secondary btn-sm" onClick={() => handleOpenEdit(batch)} title="Edit batch / record actual energy">
                            Edit
                          </button>
                          <button className="btn btn-danger btn-sm" onClick={() => handleOpenDelete(batch)}>
                            &times;
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Batch Modal */}
      <Modal
        isOpen={createModalOpen}
        title="Create Production Batch"
        onClose={() => setCreateModalOpen(false)}
        maxWidth="640px"
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setCreateModalOpen(false)} disabled={formSubmitting}>
              Cancel
            </button>
            <button className="btn btn-primary" onClick={handleCreateSubmit} disabled={formSubmitting}>
              {formSubmitting ? 'Creating...' : 'Create Batch'}
            </button>
          </>
        }
      >
        <form onSubmit={handleCreateSubmit}>
          <div className="form-grid">
            <div className="form-group">
              <label>Batch Number <span className="required">*</span></label>
              <input
                type="text"
                className="form-control"
                value={formData.batchNumber}
                onChange={(e) => setFormData({ ...formData, batchNumber: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label>Production Date <span className="required">*</span></label>
              <input
                type="date"
                className="form-control"
                value={formData.productionDate}
                onChange={(e) => setFormData({ ...formData, productionDate: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label>Product <span className="required">*</span></label>
            <select
              className="form-control"
              value={formData.productId}
              onChange={(e) => setFormData({ ...formData, productId: e.target.value })}
              required
            >
              <option value="">Select a product...</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          <div className="form-grid">
            <div className="form-group">
              <label>Machine Type <span className="required">*</span></label>
              <select
                className="form-control"
                value={formData.machineTypeId}
                onChange={(e) => setFormData({ ...formData, machineTypeId: e.target.value })}
                required
              >
                <option value="">Select machine type...</option>
                {machineTypes.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Shift <span className="required">*</span></label>
              <select
                className="form-control"
                value={formData.shiftId}
                onChange={(e) => setFormData({ ...formData, shiftId: e.target.value })}
                required
              >
                <option value="">Select shift...</option>
                {shifts.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-grid">
            <div className="form-group">
              <label>Quantity (Units) <span className="required">*</span></label>
              <input
                type="number"
                min="1"
                step="1"
                className="form-control"
                value={formData.quantity}
                onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
                required
              />
              <span className="form-hint">Must be greater than 0</span>
            </div>
            <div className="form-group">
              <label>Machine Hours <span className="required">*</span></label>
              <input
                type="number"
                min="0.1"
                step="0.1"
                className="form-control"
                value={formData.machineHours}
                onChange={(e) => setFormData({ ...formData, machineHours: e.target.value })}
                required
              />
              <span className="form-hint">Must be greater than 0</span>
            </div>
          </div>

          <div className="form-group">
            <label>Actual Energy Consumed (Optional - post production)</label>
            <input
              type="number"
              min="0"
              step="0.01"
              placeholder="Leave blank before manufacturing completes"
              className="form-control"
              value={formData.actualEnergyConsumedKwh}
              onChange={(e) => setFormData({ ...formData, actualEnergyConsumedKwh: e.target.value })}
            />
            <span className="form-hint">A batch can be created before actual energy is known.</span>
          </div>
        </form>
      </Modal>

      {/* Edit Batch Modal */}
      <Modal
        isOpen={editModalOpen}
        title={`Edit Batch ${selectedBatch?.batchNumber}`}
        onClose={() => setEditModalOpen(false)}
        maxWidth="640px"
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setEditModalOpen(false)} disabled={formSubmitting}>
              Cancel
            </button>
            <button className="btn btn-primary" onClick={handleEditSubmit} disabled={formSubmitting}>
              {formSubmitting ? 'Saving...' : 'Save Changes'}
            </button>
          </>
        }
      >
        <form onSubmit={handleEditSubmit}>
          <div className="form-grid">
            <div className="form-group">
              <label>Batch Number</label>
              <input
                type="text"
                className="form-control"
                value={formData.batchNumber}
                onChange={(e) => setFormData({ ...formData, batchNumber: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label>Production Date</label>
              <input
                type="date"
                className="form-control"
                value={formData.productionDate}
                onChange={(e) => setFormData({ ...formData, productionDate: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label>Product</label>
            <select
              className="form-control"
              value={formData.productId}
              onChange={(e) => setFormData({ ...formData, productId: e.target.value })}
              required
            >
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          <div className="form-grid">
            <div className="form-group">
              <label>Machine Type</label>
              <select
                className="form-control"
                value={formData.machineTypeId}
                onChange={(e) => setFormData({ ...formData, machineTypeId: e.target.value })}
                required
              >
                {machineTypes.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Shift</label>
              <select
                className="form-control"
                value={formData.shiftId}
                onChange={(e) => setFormData({ ...formData, shiftId: e.target.value })}
                required
              >
                {shifts.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-grid">
            <div className="form-group">
              <label>Quantity (Units)</label>
              <input
                type="number"
                min="1"
                step="1"
                className="form-control"
                value={formData.quantity}
                onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label>Machine Hours</label>
              <input
                type="number"
                min="0.1"
                step="0.1"
                className="form-control"
                value={formData.machineHours}
                onChange={(e) => setFormData({ ...formData, machineHours: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="form-group" style={{ backgroundColor: 'var(--neutral-100)', padding: '16px', borderRadius: '8px' }}>
            <label style={{ color: 'var(--neutral-900)', fontWeight: 700 }}>
              Actual Energy Consumed (kWh)
            </label>
            <input
              type="number"
              min="0"
              step="0.01"
              placeholder="Record post-production electricity usage"
              className="form-control"
              value={formData.actualEnergyConsumedKwh}
              onChange={(e) => setFormData({ ...formData, actualEnergyConsumedKwh: e.target.value })}
            />
            <span className="form-hint">
              Entering actual energy marks this batch as Completed. It will NEVER overwrite predicted energy.
            </span>
          </div>
        </form>
      </Modal>

      {/* Batch Details Modal */}
      <Modal
        isOpen={detailModalOpen}
        title={`Batch Details: ${selectedBatch?.batchNumber}`}
        onClose={() => setDetailModalOpen(false)}
        footer={
          <button className="btn btn-secondary" onClick={() => setDetailModalOpen(false)}>
            Close
          </button>
        }
      >
        {selectedBatch && (
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
              <div>
                <span className="stat-label">Product Name</span>
                <p style={{ fontWeight: 600 }}>{selectedBatch.product?.name}</p>
              </div>
              <div>
                <span className="stat-label">Production Date</span>
                <p style={{ fontWeight: 600 }}>{selectedBatch.productionDate}</p>
              </div>
              <div>
                <span className="stat-label">Machine Type</span>
                <p style={{ fontWeight: 600 }}>{selectedBatch.machineType?.name}</p>
              </div>
              <div>
                <span className="stat-label">Shift</span>
                <p style={{ fontWeight: 600 }}>{selectedBatch.shift?.name}</p>
              </div>
              <div>
                <span className="stat-label">Planned Quantity</span>
                <p style={{ fontWeight: 600 }}>{selectedBatch.quantity} units</p>
              </div>
              <div>
                <span className="stat-label">Machine Run Time</span>
                <p style={{ fontWeight: 600 }}>{selectedBatch.machineHours} hours</p>
              </div>
              <div>
                <span className="stat-label">Actual Energy Consumed</span>
                <p style={{ fontWeight: 700, color: selectedBatch.actualEnergyConsumedKwh ? 'var(--success-text)' : 'var(--neutral-400)' }}>
                  {selectedBatch.actualEnergyConsumedKwh != null ? `${selectedBatch.actualEnergyConsumedKwh} kWh` : 'Not recorded yet'}
                </p>
              </div>
              <div>
                <span className="stat-label">Status</span>
                <p>
                  {selectedBatch.actualEnergyConsumedKwh != null ? (
                    <span className="badge badge-success">Completed</span>
                  ) : (
                    <span className="badge badge-warning">In Progress</span>
                  )}
                </p>
              </div>
            </div>

            {/* Associated Prediction History */}
            <div style={{ borderTop: '1px solid var(--neutral-200)', paddingTop: '16px', marginBottom: '16px' }}>
              <span className="stat-label" style={{ display: 'block', marginBottom: '8px' }}>
                Associated ML Predictions ({batchPredictions.length})
              </span>
              {loadingBatchPreds ? (
                <div style={{ textAlign: 'center', padding: '12px' }}>
                  <span className="spinner spinner-primary" style={{ width: '16px', height: '16px' }}></span>
                </div>
              ) : batchPredictions.length === 0 ? (
                <p style={{ fontSize: '0.82rem', color: 'var(--neutral-400)', fontStyle: 'italic' }}>
                  No predictions run for this batch yet. Click "Run ML Prediction" below.
                </p>
              ) : (
                <div style={{ maxHeight: '150px', overflowY: 'auto' }}>
                  {batchPredictions.map((bp) => (
                    <div key={bp.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--neutral-50)', padding: '8px 12px', borderRadius: '6px', marginBottom: '6px', fontSize: '0.85rem' }}>
                      <div>
                        <strong>⚡ {bp.estimatedEnergyKwh} kWh</strong>
                        <span style={{ fontSize: '0.75rem', color: 'var(--neutral-400)', marginLeft: '8px' }}>
                          {new Date(bp.createdAt).toLocaleDateString()} {new Date(bp.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <span className="badge badge-neutral" style={{ fontSize: '0.72rem' }}>
                        {bp.modelVersion}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div style={{ borderTop: '1px solid var(--neutral-200)', paddingTop: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--neutral-500)' }}>Calculate updated estimate?</span>
              <button className="btn btn-primary btn-sm" onClick={() => { setDetailModalOpen(false); handlePredictForBatch(selectedBatch); }}>
                ⚡ Run ML Prediction
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Prediction Result Modal (Workflow B) */}
      <Modal
        isOpen={predictResultModalOpen}
        title="ML Prediction Result (Workflow B)"
        onClose={() => setPredictResultModalOpen(false)}
        footer={
          <button className="btn btn-primary" onClick={() => setPredictResultModalOpen(false)}>
            Done
          </button>
        }
      >
        {predictionResult && selectedBatch && (
          <div>
            <p style={{ color: 'var(--neutral-600)', fontSize: '0.9rem' }}>
              Estimated electricity consumption for batch <strong>{selectedBatch.batchNumber}</strong>:
            </p>

            <div className="prediction-result-card">
              <span className="prediction-result-title">Model Estimation</span>
              <div className="prediction-value-big">
                {predictionResult.estimatedEnergy}
                <span className="prediction-unit">kWh</span>
              </div>
              <div className="prediction-meta">
                <span>Model: {predictionResult.modelVersion}</span>
                <span>•</span>
                <span>Audit ID: #{predictionResult.predictionId}</span>
              </div>
            </div>

            <div style={{ marginTop: '20px', backgroundColor: 'var(--neutral-50)', padding: '14px', borderRadius: '8px', fontSize: '0.85rem', color: 'var(--neutral-600)' }}>
              <strong>Inference Summary:</strong>
              <div style={{ marginTop: '6px' }}>
                Machine: <strong>{selectedBatch.machineType?.name}</strong> | Shift: <strong>{selectedBatch.shift?.name}</strong> | Quantity: <strong>{selectedBatch.quantity}</strong> | Hours: <strong>{selectedBatch.machineHours}</strong>
              </div>
              <div style={{ marginTop: '6px', color: 'var(--neutral-500)' }}>
                ✓ This estimate has been recorded in the persistent prediction audit log linked to this batch.
              </div>
            </div>
          </div>
        )}
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={deleteModalOpen}
        title="Confirm Batch Deletion"
        onClose={() => setDeleteModalOpen(false)}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setDeleteModalOpen(false)} disabled={formSubmitting}>
              Cancel
            </button>
            <button className="btn btn-danger" onClick={confirmDelete} disabled={formSubmitting}>
              {formSubmitting ? 'Deleting...' : 'Delete Batch'}
            </button>
          </>
        }
      >
        <p style={{ color: 'var(--neutral-700)', lineHeight: '1.6' }}>
          Are you sure you want to delete production batch <strong>'{selectedBatch?.batchNumber}'</strong>?
        </p>
        <p style={{ color: 'var(--neutral-500)', fontSize: '0.85rem', marginTop: '8px' }}>
          Note: Historical predictions linked to this batch will be preserved for auditing with their batch reference cleared.
        </p>
      </Modal>
    </div>
  );
}
