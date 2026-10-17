import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import Modal from '../components/Modal';
import Alert from '../components/Alert';

export default function Products() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  // Modal states
  const [modalOpen, setModalOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [currentId, setCurrentId] = useState(null);
  const [formData, setFormData] = useState({ name: '', description: '' });
  const [formSubmitting, setFormSubmitting] = useState(false);

  // Delete confirmation
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [productToDelete, setProductToDelete] = useState(null);
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);

  const fetchProducts = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getProducts();
      setProducts(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  const handleOpenAdd = () => {
    setIsEditing(false);
    setCurrentId(null);
    setFormData({ name: '', description: '' });
    setError(null);
    setModalOpen(true);
  };

  const handleOpenEdit = (product) => {
    setIsEditing(true);
    setCurrentId(product.id);
    setFormData({ name: product.name, description: product.description || '' });
    setError(null);
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setError('Product name cannot be empty.');
      return;
    }

    try {
      setFormSubmitting(true);
      setError(null);
      if (isEditing) {
        await api.updateProduct(currentId, formData);
        setSuccess(`Product '${formData.name}' updated successfully.`);
      } else {
        await api.createProduct(formData);
        setSuccess(`Product '${formData.name}' created successfully.`);
      }
      setModalOpen(false);
      fetchProducts();
    } catch (err) {
      setError(err.message);
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleOpenDelete = (product) => {
    setProductToDelete(product);
    setError(null);
    setDeleteModalOpen(true);
  };

  const confirmDelete = async () => {
    if (!productToDelete) return;
    try {
      setDeleteSubmitting(true);
      setError(null);
      await api.deleteProduct(productToDelete.id);
      setSuccess(`Product '${productToDelete.name}' deleted successfully.`);
      setDeleteModalOpen(false);
      setProductToDelete(null);
      fetchProducts();
    } catch (err) {
      setError(err.message);
      setDeleteModalOpen(false);
    } finally {
      setDeleteSubmitting(false);
    }
  };

  const filtered = products.filter((p) =>
    p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (p.description && p.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Products Master Data</h2>
          <p className="page-subtitle">Configure manufactured parts and items required for production batches.</p>
        </div>
        <button className="btn btn-primary" onClick={handleOpenAdd}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          Add Product
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
              placeholder="Search products..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <span style={{ fontSize: '0.85rem', color: 'var(--neutral-500)' }}>
            Total: <strong>{products.length}</strong> items
          </span>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '80px' }}>ID</th>
                <th>Name</th>
                <th>Description</th>
                <th style={{ width: '160px' }}>Created Date</th>
                <th style={{ width: '140px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center', padding: '32px' }}>
                    <div className="spinner spinner-primary"></div>
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan="5" className="empty-state">
                    <p className="empty-state-title">No products found</p>
                    <p className="empty-state-text">
                      {searchTerm ? 'Try a different search query' : 'Click "Add Product" to create your first item.'}
                    </p>
                  </td>
                </tr>
              ) : (
                filtered.map((prod) => (
                  <tr key={prod.id}>
                    <td>#{prod.id}</td>
                    <td style={{ fontWeight: 600, color: 'var(--neutral-900)' }}>{prod.name}</td>
                    <td>{prod.description || <span style={{ color: 'var(--neutral-400)' }}>No description</span>}</td>
                    <td style={{ fontSize: '0.82rem' }}>
                      {new Date(prod.createdAt).toLocaleDateString()}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div className="actions-cell" style={{ justifyContent: 'flex-end' }}>
                        <button className="btn btn-secondary btn-sm" onClick={() => handleOpenEdit(prod)}>
                          Edit
                        </button>
                        <button className="btn btn-danger btn-sm" onClick={() => handleOpenDelete(prod)}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add / Edit Modal */}
      <Modal
        isOpen={modalOpen}
        title={isEditing ? 'Edit Product' : 'Add New Product'}
        onClose={() => setModalOpen(false)}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setModalOpen(false)} disabled={formSubmitting}>
              Cancel
            </button>
            <button className="btn btn-primary" onClick={handleSubmit} disabled={formSubmitting}>
              {formSubmitting ? 'Saving...' : isEditing ? 'Save Changes' : 'Create Product'}
            </button>
          </>
        }
      >
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>
              Product Name <span className="required">*</span>
            </label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. Industrial Gearbox Housing"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              autoFocus
            />
          </div>
          <div className="form-group">
            <label>Description (Optional)</label>
            <textarea
              rows="3"
              className="form-control"
              placeholder="Provide technical or manufacturing details..."
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
              {deleteSubmitting ? 'Deleting...' : 'Delete Product'}
            </button>
          </>
        }
      >
        <p style={{ color: 'var(--neutral-700)', lineHeight: '1.6' }}>
          Are you sure you want to delete product <strong>'{productToDelete?.name}'</strong>?
        </p>
        <p style={{ color: 'var(--neutral-500)', fontSize: '0.85rem', marginTop: '8px' }}>
          Note: If this product is referenced by any existing production batch, deletion will be safely restricted by database integrity constraints.
        </p>
      </Modal>
    </div>
  );
}
