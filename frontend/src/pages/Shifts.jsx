import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import Modal from '../components/Modal';
import Alert from '../components/Alert';

export default function Shifts() {
  const [shifts, setShifts] = useState([]);
  const [modelInfo, setModelInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  // Retrain state
  const [retraining, setRetraining] = useState(false);

  // Modal states
  const [modalOpen, setModalOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [currentId, setCurrentId] = useState(null);
  const [formData, setFormData] = useState({ name: '', description: '' });
  const [formSubmitting, setFormSubmitting] = useState(false);

  // Delete confirmation
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [shiftToDelete, setShiftToDelete] = useState(null);
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);

  const fetchShiftsAndModel = async () => {
    try {
      setLoading(true);
      setError(null);
      const [data, modelStatus] = await Promise.all([
        api.getShifts(),
        api.getModelStatus().catch(() => null),
      ]);
      setShifts(data);
      setModelInfo(modelStatus);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchShiftsAndModel();
  }, []);

  const isSupportedInModel = (shiftName) => {
    if (!modelInfo?.supported_shifts) return true;
    return modelInfo.supported_shifts.some(
      (s) => s.toLowerCase() === shiftName.toLowerCase()
    );
  };

  const handleRetrainModel = async () => {
    try {
      setRetraining(true);
      setError(null);
      setSuccess(null);
      const res = await api.retrainModel();
      setSuccess(`${res.message} (Version: ${res.model_version}, R²: ${res.metrics?.r2_score ?? 'N/A'})`);
      fetchShiftsAndModel();
    } catch (err) {
      setError(err.message);
    } finally {
      setRetraining(false);
    }
  };

  const handleOpenAdd = () => {
    setIsEditing(false);
    setCurrentId(null);
    setFormData({ name: '', description: '' });
    setError(null);
    setModalOpen(true);
  };

  const handleOpenEdit = (shift) => {
    setIsEditing(true);
    setCurrentId(shift.id);
    setFormData({ name: shift.name, description: shift.description || '' });
    setError(null);
    setModalOpen(true);
  };

  const applyPreset = (presetName, presetDesc) => {
    setFormData({ name: presetName, description: presetDesc });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setError('Shift name cannot be empty.');
      return;
    }

    try {
      setFormSubmitting(true);
      setError(null);
      if (isEditing) {
        await api.updateShift(currentId, formData);
        setSuccess(`Shift '${formData.name}' updated successfully.`);
      } else {
        await api.createShift(formData);
        setSuccess(`Shift '${formData.name}' created successfully. Note: Model retraining may be required to enable energy predictions for this shift.`);
      }
      setModalOpen(false);
      fetchShiftsAndModel();
    } catch (err) {
      setError(err.message);
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleOpenDelete = (shift) => {
    setShiftToDelete(shift);
    setError(null);
    setDeleteModalOpen(true);
  };

  const confirmDelete = async () => {
    if (!shiftToDelete) return;
    try {
      setDeleteSubmitting(true);
      setError(null);
      await api.deleteShift(shiftToDelete.id);
      setSuccess(`Shift '${shiftToDelete.name}' deleted successfully.`);
      setDeleteModalOpen(false);
      setShiftToDelete(null);
      fetchShiftsAndModel();
    } catch (err) {
      setError(err.message);
      setDeleteModalOpen(false);
    } finally {
      setDeleteSubmitting(false);
    }
  };

  const filtered = shifts.filter((s) =>
    s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (s.description && s.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Shifts Master Data</h2>
          <p className="page-subtitle">Configure operating shifts (e.g. Morning, Afternoon, Evening, Night) with standardized 12h/24h time formatting.</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          {modelInfo?.unsupported_configured_shifts?.length > 0 && (
            <button
              className="btn btn-warning"
              onClick={handleRetrainModel}
              disabled={retraining}
              title="Retrain model on newly configured shifts"
            >
              {retraining ? (
                <>
                  <span className="spinner" style={{ width: '14px', height: '14px', marginRight: '6px' }}></span>
                  Retraining Model...
                </>
              ) : (
                <>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="23 4 23 10 17 10" />
                    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
                  </svg>
                  Retrain Model for New Shifts
                </>
              )}
            </button>
          )}
          <button className="btn btn-primary" onClick={handleOpenAdd}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            Add Shift
          </button>
        </div>
      </div>

      {error && <Alert type="danger" message={error} onClose={() => setError(null)} />}
      {success && <Alert type="success" message={success} onClose={() => setSuccess(null)} />}

      {/* Shift Retraining Banner */}
      {modelInfo?.unsupported_configured_shifts && modelInfo.unsupported_configured_shifts.length > 0 && (
        <div style={{
          backgroundColor: 'rgba(245, 158, 11, 0.1)',
          border: '1px solid #f59e0b',
          borderRadius: '8px',
          padding: '14px 18px',
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px'
        }}>
          <div>
            <strong style={{ color: '#b45309' }}>ML Model Retraining Required:</strong>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.88rem', color: '#78350f' }}>
              Newly configured operating shift(s) ({modelInfo.unsupported_configured_shifts.join(', ')}) are stored in SQLite but not yet represented in the active ML model ({modelInfo.model_version}). Click "Retrain Now" to include these shifts in predictions.
            </p>
          </div>
          <button
            className="btn btn-sm btn-primary"
            style={{ whiteSpace: 'nowrap' }}
            onClick={handleRetrainModel}
            disabled={retraining}
          >
            {retraining ? 'Retraining...' : 'Retrain Now'}
          </button>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexGrow: 1, maxWidth: '400px' }}>
            <input
              type="text"
              className="form-control"
              placeholder="Search shifts..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <span style={{ fontSize: '0.85rem', color: 'var(--neutral-500)' }}>
            Total: <strong>{shifts.length}</strong> shifts
          </span>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '70px' }}>ID</th>
                <th>Shift Name</th>
                <th>Description / Working Hours</th>
                <th style={{ width: '130px' }}>ML Status</th>
                <th style={{ width: '130px' }}>Created Date</th>
                <th style={{ width: '140px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', padding: '32px' }}>
                    <div className="spinner spinner-primary"></div>
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan="6" className="empty-state">
                    <p className="empty-state-title">No shifts found</p>
                    <p className="empty-state-text">
                      {searchTerm ? 'Try a different search query' : 'Click "Add Shift" to define factory working hours.'}
                    </p>
                  </td>
                </tr>
              ) : (
                filtered.map((shift) => {
                  const supported = isSupportedInModel(shift.name);
                  const isOvernight = shift.name.toLowerCase().includes('night') ||
                    (shift.description && /night|22:00|10:00\s*pm|overnight/i.test(shift.description));

                  return (
                    <tr key={shift.id}>
                      <td>#{shift.id}</td>
                      <td style={{ fontWeight: 600, color: 'var(--neutral-900)' }}>{shift.name}</td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                          <span>{shift.description || <span style={{ color: 'var(--neutral-400)' }}>No description</span>}</span>
                          {isOvernight && (
                            <span style={{ fontSize: '0.72rem', backgroundColor: '#ede9fe', color: '#6d28d9', padding: '2px 8px', borderRadius: '12px', fontWeight: 500 }}>
                              Overnight
                            </span>
                          )}
                        </div>
                      </td>
                      <td>
                        {supported ? (
                          <span className="badge badge-success" style={{ fontSize: '0.75rem' }}>
                            Model Ready
                          </span>
                        ) : (
                          <span className="badge badge-warning" style={{ fontSize: '0.75rem', backgroundColor: '#fef3c7', color: '#b45309', border: '1px solid #fde68a' }}>
                            Retrain Needed
                          </span>
                        )}
                      </td>
                      <td style={{ fontSize: '0.82rem' }}>
                        {new Date(shift.createdAt).toLocaleDateString()}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div className="actions-cell" style={{ justifyContent: 'flex-end' }}>
                          <button className="btn btn-secondary btn-sm" onClick={() => handleOpenEdit(shift)}>
                            Edit
                          </button>
                          <button className="btn btn-danger btn-sm" onClick={() => handleOpenDelete(shift)}>
                            Delete
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

      {/* Add / Edit Modal */}
      <Modal
        isOpen={modalOpen}
        title={isEditing ? 'Edit Shift' : 'Add New Shift'}
        onClose={() => setModalOpen(false)}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setModalOpen(false)} disabled={formSubmitting}>
              Cancel
            </button>
            <button className="btn btn-primary" onClick={handleSubmit} disabled={formSubmitting}>
              {formSubmitting ? 'Saving...' : isEditing ? 'Save Changes' : 'Create Shift'}
            </button>
          </>
        }
      >
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '16px', background: 'var(--neutral-50)', padding: '12px', borderRadius: '6px' }}>
            <span style={{ fontSize: '0.78rem', color: 'var(--neutral-600)', display: 'block', marginBottom: '8px', fontWeight: 600 }}>
              Quick Presets (Unambiguous 12h & 24h Formats):
            </span>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn btn-sm btn-secondary"
                style={{ fontSize: '0.75rem', padding: '4px 8px' }}
                onClick={() => applyPreset('Morning', '06:00 AM – 02:00 PM (06:00 – 14:00) Morning First Shift')}
              >
                Morning (06:00 AM – 02:00 PM)
              </button>
              <button
                type="button"
                className="btn btn-sm btn-secondary"
                style={{ fontSize: '0.75rem', padding: '4px 8px' }}
                onClick={() => applyPreset('Afternoon', '12:00 PM – 04:00 PM (12:00 – 16:00) Afternoon Production Shift')}
              >
                Afternoon (12:00 PM – 04:00 PM)
              </button>
              <button
                type="button"
                className="btn btn-sm btn-secondary"
                style={{ fontSize: '0.75rem', padding: '4px 8px' }}
                onClick={() => applyPreset('Evening', '02:00 PM – 10:00 PM (14:00 – 22:00) Evening Second Shift')}
              >
                Evening (02:00 PM – 10:00 PM)
              </button>
              <button
                type="button"
                className="btn btn-sm btn-secondary"
                style={{ fontSize: '0.75rem', padding: '4px 8px' }}
                onClick={() => applyPreset('Night', '10:00 PM – 06:00 AM (22:00 – 06:00) Overnight Third Shift')}
              >
                Night (10:00 PM – 06:00 AM)
              </button>
            </div>
          </div>

          <div className="form-group">
            <label>
              Shift Name <span className="required">*</span>
            </label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. Morning, Afternoon, Evening, Night"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              autoFocus
            />
          </div>
          <div className="form-group">
            <label>Description / Hours (Unambiguous 12h/24h Format)</label>
            <textarea
              rows="3"
              className="form-control"
              placeholder="e.g. 12:00 PM – 04:00 PM (12:00 – 16:00) Afternoon Production Shift"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            ></textarea>
            <span className="form-hint" style={{ fontSize: '0.78rem', color: 'var(--neutral-500)', marginTop: '4px', display: 'block' }}>
              Standard format: <code>HH:MM AM/PM – HH:MM AM/PM</code> (e.g. <code>10:00 PM – 06:00 AM</code> for overnight shifts). Ambiguous entries like <code>12:00 - 4:00</code> are automatically standardized.
            </span>
          </div>
        </form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={deleteModalOpen}
        title="Confirm Deletion"
        onClose={() => setDeleteModalOpen(false)}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setDeleteModalOpen(false)} disabled={deleteSubmitting}>
              Cancel
            </button>
            <button className="btn btn-danger" onClick={confirmDelete} disabled={deleteSubmitting}>
              {deleteSubmitting ? 'Deleting...' : 'Delete Shift'}
            </button>
          </>
        }
      >
        <p style={{ color: 'var(--neutral-700)', lineHeight: '1.6' }}>
          Are you sure you want to delete shift <strong>'{shiftToDelete?.name}'</strong>?
        </p>
        <p style={{ color: 'var(--neutral-500)', fontSize: '0.85rem', marginTop: '8px' }}>
          Note: If any production batch references this shift, deletion will be safely restricted.
        </p>
      </Modal>
    </div>
  );
}
