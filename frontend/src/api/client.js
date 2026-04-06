/**
 * API Client Configuration
 * 
 * Centralizing the base URL and handling requests to our FastAPI backend.
 */

export const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api/v1';

export const apiClient = {
  get: async (endpoint) => {
    const response = await fetch(`${BASE_URL}${endpoint}`);
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  post: async (endpoint, data, isFormData = false) => {
    const config = {
      method: 'POST',
      body: isFormData ? data : JSON.stringify(data),
    };

    if (!isFormData) {
      config.headers = { 'Content-Type': 'application/json' };
    }

    const response = await fetch(`${BASE_URL}${endpoint}`, config);
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  delete: async (endpoint) => {
    const response = await fetch(`${BASE_URL}${endpoint}`, { method: 'DELETE' });
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `HTTP error! status: ${response.status}`);
    }
    return response.json();
  }
};
