import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import Modal from '../components/Modal';
import Alert from '../components/Alert';

export default function MachineTypes() {
  const [machineTypes, setMachineTypes] = useState([]);
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
  const [typeToDelete, setTypeToDelete] = useState(null);
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);

  const fetchMachineTypesAndModel = async () => {
    try {
      setLoading(true);
      setError(null);
      const [data, modelStatus] = await Promise.all([
        api.getMachineTypes(),
        api.getModelStatus().catch(() => null),
      ]);
      setMachineTypes(data);
      setModelInfo(modelStatus);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMachineTypesAndModel();
  }, []);

  const handleOpenAdd = () => {
    setIsEditing(false);
    setCurrentId(null);
    setFormData({ name: '', description: '' });
    setError(null);
    setModalOpen(true);
  };

  const handleOpenEdit = (machine) => {
    setIsEditing(true);
    setCurrentId(machine.id);
    setFormData({ name: machine.name, description: machine.description || '' });
    setError(null);
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setError('Machine type name cannot be empty.');
      return;
    }

    try {
      setFormSubmitting(true);
      setError(null);
      if (isEditing) {
        await api.updateMachineType(currentId, formData);
        setSuccess(`Machine Type '${formData.name}' updated successfully.`);
      } else {
        await api.createMachineType(formData);
        setSuccess(`Machine Type '${formData.name}' created in database. Note: Model retraining may be required to enable energy predictions for this machine.`);
      }
      setModalOpen(false);
      fetchMachineTypesAndModel();
    } catch (err) {
      setError(err.message);
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleOpenDelete = (machine) => {
    setTypeToDelete(machine);
    setError(null);
    setDeleteModalOpen(true);
  };

  const confirmDelete = async () => {
    if (!typeToDelete) return;
    try {
      setDeleteSubmitting(true);
      setError(null);
      await api.deleteMachineType(typeToDelete.id);
      setSuccess(`Machine Type '${typeToDelete.name}' deleted successfully.`);
      setDeleteModalOpen(false);
      setTypeToDelete(null);
      fetchMachineTypesAndModel();
    } catch (err) {
      setError(err.message);
      setDeleteModalOpen(false);
    } finally {
      setDeleteSubmitting(false);
    }
  };

  const handleRetrainModel = async () => {
    try {
      setRetraining(true);
      setError(null);
      setSuccess(null);
      const res = await api.retrainModel();
      setSuccess(`${res.message} (Version: ${res.model_version}, R²: ${res.metrics?.r2_score ?? 'N/A'})`);
      fetchMachineTypesAndModel();
    } catch (err) {
      setError(err.message);
    } finally {
      setRetraining(false);
    }
  };

  const isSupportedInModel = (machineName) => {
    if (!modelInfo?.supported_machine_types) return true;
    return modelInfo.supported_machine_types.some(
      (m) => m.toLowerCase() === machineName.toLowerCase()
    );
  };

  const filtered = machineTypes.filter((m) =>
    m.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (m.description && m.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Machine Types Master Data</h2>
          <p className="page-subtitle">Manage factory equipment categories (e.g. CNC, Lathe, Milling Machine) utilized in energy predictions.</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          {modelInfo?.retraining_required && (
            <button
              className="btn btn-warning"
              onClick={handleRetrainModel}
              disabled={retraining}
              title="Retrain model on newly configured machine types and shifts"
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
                  Retrain Model
                </>
              )}
            </button>
          )}
          <button className="btn btn-primary" onClick={handleOpenAdd}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            Add Machine Type
          </button>
        </div>
      </div>

      {error && <Alert type="danger" message={error} onClose={() => setError(null)} />}
      {success && <Alert type="success" message={success} onClose={() => setSuccess(null)} />}

      {/* Equipment Retraining Banner: Only shown if unsupported machines actually exist */}
      {modelInfo?.unsupported_configured_machines && modelInfo.unsupported_configured_machines.length > 0 && (
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
              Newly configured equipment ({modelInfo.unsupported_configured_machines.join(', ')}) is stored in SQLite but not yet represented in the active ML model ({modelInfo.model_version}). Click "Retrain Now" to teach the model how to predict energy for these machine types.
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

      {/* Shift Retraining Banner: Displayed if shifts need retraining while equipment is ready */}
      {(!modelInfo?.unsupported_configured_machines || modelInfo.unsupported_configured_machines.length === 0) &&
        modelInfo?.unsupported_configured_shifts && modelInfo.unsupported_configured_shifts.length > 0 && (
        <div style={{
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          border: '1px solid #3b82f6',
          borderRadius: '8px',
          padding: '14px 18px',
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px'
        }}>
          <div>
            <strong style={{ color: '#1d4ed8' }}>Operating Shifts Retraining Recommended:</strong>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.88rem', color: '#1e40af' }}>
              All current machine types are supported in the active ML model ({modelInfo.model_version}). However, newly configured shift(s) ({modelInfo.unsupported_configured_shifts.join(', ')}) require model retraining to enable energy inference for those working hours.
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
              placeholder="Search machine types..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <span style={{ fontSize: '0.85rem', color: 'var(--neutral-500)' }}>
            Total: <strong>{machineTypes.length}</strong> types
          </span>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '80px' }}>ID</th>
                <th>Machine Type</th>
                <th>Description</th>
                <th style={{ width: '160px' }}>ML Status</th>
                <th style={{ width: '140px' }}>Created Date</th>
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
                    <p className="empty-state-title">No machine types found</p>
                    <p className="empty-state-text">
                      {searchTerm ? 'Try a different search query' : 'Click "Add Machine Type" to register equipment.'}
                    </p>
                  </td>
                </tr>
              ) : (
                filtered.map((machine) => {
                  const supported = isSupportedInModel(machine.name);
                  return (
                    <tr key={machine.id}>
                      <td>#{machine.id}</td>
                      <td style={{ fontWeight: 600, color: 'var(--neutral-900)' }}>{machine.name}</td>
                      <td>{machine.description || <span style={{ color: 'var(--neutral-400)' }}>No description</span>}</td>
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
                        {new Date(machine.createdAt).toLocaleDateString()}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div className="actions-cell" style={{ justifyContent: 'flex-end' }}>
                          <button className="btn btn-secondary btn-sm" onClick={() => handleOpenEdit(machine)}>
                            Edit
                          </button>
                          <button className="btn btn-danger btn-sm" onClick={() => handleOpenDelete(machine)}>
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
        title={isEditing ? 'Edit Machine Type' : 'Add New Machine Type'}
        onClose={() => setModalOpen(false)}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setModalOpen(false)} disabled={formSubmitting}>
              Cancel
            </button>
            <button className="btn btn-primary" onClick={handleSubmit} disabled={formSubmitting}>
              {formSubmitting ? 'Saving...' : isEditing ? 'Save Changes' : 'Create Machine Type'}
            </button>
          </>
        }
      >
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>
              Machine Type Name <span className="required">*</span>
            </label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. CNC, Lathe, Milling Machine, GEARBOX"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              autoFocus
            />
            <span className="form-hint">Unique identifier for equipment category in SQLite.</span>
          </div>
          <div className="form-group">
            <label>Description (Optional)</label>
            <textarea
              className="form-control"
              rows="3"
              placeholder="Operational specs, cutting capabilities, power characteristics..."
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            ></textarea>
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
              {deleteSubmitting ? 'Deleting...' : 'Delete Machine Type'}
            </button>
          </>
        }
      >
        <p>
          Are you sure you want to delete machine type <strong>{typeToDelete?.name}</strong>?
        </p>
        <p className="form-hint" style={{ marginTop: '8px' }}>
          Database foreign key constraints will prevent deletion if this machine type is currently referenced by any production batch.
        </p>
      </Modal>
    </div>
  );
}
