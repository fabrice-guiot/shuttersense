/**
 * Collection API service
 *
 * Handles all API calls related to photo collections
 */

import api from './api';

/**
 * List all collections with optional filters
 * @param {Object} filters - Optional filters
 * @param {string} filters.state - Filter by state (live, closed, archived)
 * @param {string} filters.type - Filter by type (local, s3, gcs, smb)
 * @param {boolean} filters.accessible_only - Only return accessible collections
 * @returns {Promise<Array>} List of collections
 */
export const listCollections = async (filters = {}) => {
  const params = {};
  if (filters.state) params.state = filters.state;
  if (filters.type) params.type = filters.type;
  if (filters.accessible_only) params.accessible_only = true;

  const response = await api.get('/collections', { params });
  return response.data;
};

/**
 * Get a single collection by ID
 * @param {number} id - Collection ID
 * @returns {Promise<Object>} Collection details
 */
export const getCollection = async (id) => {
  const response = await api.get(`/collections/${id}`);
  return response.data;
};

/**
 * Create a new collection
 * @param {Object} data - Collection data
 * @param {string} data.name - Collection name
 * @param {string} data.type - Collection type (local, s3, gcs, smb)
 * @param {string} data.location - Storage location path/URI
 * @param {string} data.state - Collection state (live, closed, archived)
 * @param {number} data.connector_id - Connector ID (required for remote, null for local)
 * @param {number} data.cache_ttl - Custom cache TTL in seconds (optional)
 * @param {Object} data.metadata - Optional metadata
 * @returns {Promise<Object>} Created collection
 */
export const createCollection = async (data) => {
  const response = await api.post('/collections', data);
  return response.data;
};

/**
 * Update an existing collection
 * @param {number} id - Collection ID
 * @param {Object} data - Fields to update
 * @param {string} data.name - New name (optional)
 * @param {string} data.location - New location (optional)
 * @param {string} data.state - New state (optional)
 * @param {number} data.cache_ttl - New cache TTL (optional)
 * @param {Object} data.metadata - New metadata (optional)
 * @returns {Promise<Object>} Updated collection
 */
export const updateCollection = async (id, data) => {
  const response = await api.put(`/collections/${id}`, data);
  return response.data;
};

/**
 * Delete a collection
 * @param {number} id - Collection ID
 * @param {boolean} force - Force delete even if results/jobs exist
 * @returns {Promise<Object|void>} Returns result info if collection has data, void if deleted
 * @throws {Error} 409 if results/jobs exist and force=false
 */
export const deleteCollection = async (id, force = false) => {
  const params = force ? { force_delete: force } : {};
  const response = await api.delete(`/collections/${id}`, { params });
  // If status is 200, return the result/job info
  if (response.status === 200) {
    return response.data;
  }
  // Status 204 means deleted successfully, no data to return
};

/**
 * Test collection accessibility
 * @param {number} id - Collection ID
 * @returns {Promise<Object>} Test result { is_accessible: boolean, file_count: number, error_message: string }
 */
export const testCollection = async (id) => {
  const response = await api.post(`/collections/${id}/test`);
  return response.data;
};

/**
 * Refresh collection cache
 * @param {number} id - Collection ID
 * @param {boolean} confirm - Confirm refresh if file count > threshold
 * @returns {Promise<Object>} Refresh result
 */
export const refreshCollection = async (id, confirm = false) => {
  const params = confirm ? { confirm: true } : {};
  const response = await api.post(`/collections/${id}/refresh`, null, { params });
  return response.data;
};
