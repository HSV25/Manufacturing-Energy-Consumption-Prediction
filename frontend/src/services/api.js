/**
 * Centralized API service for Manufacturing Energy Prediction System.
 * Connects directly to FastAPI backend endpoints.
 */

const API_BASE = ''; // Relies on Vite dev proxy or same origin in production

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  try {
    const response = await fetch(url, { ...options, headers });

    if (response.status === 204) {
      return null;
    }

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      let message = 'An unexpected server error occurred';
      if (data && data.detail) {
        if (Array.isArray(data.detail)) {
          // Format FastAPI validation error details
          message = data.detail.map(err => `${err.loc.join('.')}: ${err.msg}`).join(', ');
        } else {
          message = data.detail;
        }
      }
      const error = new Error(message);
      error.status = response.status;
      error.data = data;
      throw error;
    }

    return data;
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error('Unable to connect to the backend server. Please verify the FastAPI service is running on http://127.0.0.1:8000.');
    }
    throw err;
  }
}

export const api = {
  // System & ML status
  getHealth: () => request('/health'),
  getDashboardStats: () => request('/api/dashboard/stats'),
  getModelStatus: () => request('/api/dashboard/model-status'),
  retrainModel: () => request('/api/dashboard/retrain-model', { method: 'POST' }),

  // Products CRUD
  getProducts: () => request('/api/products'),
  getProduct: (id) => request(`/api/products/${id}`),
  createProduct: (data) => request('/api/products', { method: 'POST', body: JSON.stringify(data) }),
  updateProduct: (id, data) => request(`/api/products/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteProduct: (id) => request(`/api/products/${id}`, { method: 'DELETE' }),

  // Machine Types CRUD
  getMachineTypes: () => request('/api/machine-types'),
  getMachineType: (id) => request(`/api/machine-types/${id}`),
  createMachineType: (data) => request('/api/machine-types', { method: 'POST', body: JSON.stringify(data) }),
  updateMachineType: (id, data) => request(`/api/machine-types/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteMachineType: (id) => request(`/api/machine-types/${id}`, { method: 'DELETE' }),

  // Shifts CRUD
  getShifts: () => request('/api/shifts'),
  getShift: (id) => request(`/api/shifts/${id}`),
  createShift: (data) => request('/api/shifts', { method: 'POST', body: JSON.stringify(data) }),
  updateShift: (id, data) => request(`/api/shifts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteShift: (id) => request(`/api/shifts/${id}`, { method: 'DELETE' }),

  // Production Batches CRUD & Batch Prediction
  getProductionBatches: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/api/production-batches${query ? `?${query}` : ''}`);
  },
  getProductionBatch: (id) => request(`/api/production-batches/${id}`),
  createProductionBatch: (data) => request('/api/production-batches', { method: 'POST', body: JSON.stringify(data) }),
  updateProductionBatch: (id, data) => request(`/api/production-batches/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteProductionBatch: (id) => request(`/api/production-batches/${id}`, { method: 'DELETE' }),
  predictBatchEnergy: (id) => request(`/api/production-batches/${id}/predict`, { method: 'POST' }),

  // Prediction API (Workflow A)
  predictEnergy: (payload) => request('/predict-energy', { method: 'POST', body: JSON.stringify(payload) }),
  getPredictions: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/api/predictions${query ? `?${query}` : ''}`);
  },
  getPrediction: (id) => request(`/api/predictions/${id}`),
};
