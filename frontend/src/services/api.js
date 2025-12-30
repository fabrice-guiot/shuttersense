/**
 * Axios API instance configured for photo-admin backend
 *
 * Base configuration for all API calls to the FastAPI backend
 */

import axios from 'axios';

// Create Axios instance with default configuration
const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 30000, // 30 seconds for potentially long-running requests
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging (development only)
api.interceptors.request.use(
  (config) => {
    if (import.meta.env.DEV) {
      console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`);
    }
    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    if (import.meta.env.DEV) {
      console.log(`[API Response] ${response.status} ${response.config.url}`);
    }
    return response;
  },
  (error) => {
    // Enhanced error message extraction
    const errorMessage = error.response?.data?.detail ||
                        error.response?.data?.message ||
                        error.message ||
                        'An unexpected error occurred';

    console.error('[API Response Error]', {
      url: error.config?.url,
      status: error.response?.status,
      message: errorMessage,
    });

    // Attach user-friendly message to error object
    error.userMessage = errorMessage;

    return Promise.reject(error);
  }
);

export default api;
