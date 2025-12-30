/**
 * Connector API service
 *
 * Handles all API calls related to remote storage connectors
 */

import api from './api';

/**
 * List all connectors with optional filters
 * @param {Object} filters - Optional filters
 * @param {string} filters.type - Filter by connector type (s3, gcs, smb)
 * @param {boolean} filters.active_only - Only return active connectors
 * @returns {Promise<Array>} List of connectors
 */
export const listConnectors = async (filters = {}) => {
  const params = {};
  if (filters.type) params.type = filters.type;
  if (filters.active_only) params.active_only = true;

  const response = await api.get('/connectors', { params });
  return response.data;
};

/**
 * Get a single connector by ID
 * @param {number} id - Connector ID
 * @returns {Promise<Object>} Connector details (credentials NOT included)
 */
export const getConnector = async (id) => {
  const response = await api.get(`/connectors/${id}`);
  return response.data;
};

/**
 * Create a new connector
 * @param {Object} data - Connector data
 * @param {string} data.name - Connector name
 * @param {string} data.type - Connector type (s3, gcs, smb)
 * @param {Object} data.credentials - Type-specific credentials
 * @param {Object} data.metadata - Optional metadata
 * @returns {Promise<Object>} Created connector
 */
export const createConnector = async (data) => {
  const response = await api.post('/connectors', data);
  return response.data;
};

/**
 * Update an existing connector
 * @param {number} id - Connector ID
 * @param {Object} data - Fields to update
 * @param {string} data.name - New name (optional)
 * @param {Object} data.credentials - New credentials (optional)
 * @param {Object} data.metadata - New metadata (optional)
 * @param {boolean} data.is_active - Active status (optional)
 * @returns {Promise<Object>} Updated connector
 */
export const updateConnector = async (id, data) => {
  const response = await api.put(`/connectors/${id}`, data);
  return response.data;
};

/**
 * Delete a connector
 * @param {number} id - Connector ID
 * @returns {Promise<void>}
 * @throws {Error} 409 if collections reference this connector
 */
export const deleteConnector = async (id) => {
  await api.delete(`/connectors/${id}`);
};

/**
 * Test connector connection
 * @param {number} id - Connector ID
 * @returns {Promise<Object>} Test result { success: boolean, message: string }
 */
export const testConnector = async (id) => {
  const response = await api.post(`/connectors/${id}/test`);
  return response.data;
};
