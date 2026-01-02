/**
 * Connector API service
 *
 * Handles all API calls related to remote storage connectors
 */

import api from './api'
import type {
  Connector,
  ConnectorCreateRequest,
  ConnectorUpdateRequest,
  ConnectorTestResponse
} from '@/contracts/api/connector-api'

/**
 * List all connectors with optional filters
 */
export const listConnectors = async (filters: Record<string, any> = {}): Promise<Connector[]> => {
  const params: Record<string, any> = {}
  if (filters.type) params.type = filters.type
  if (filters.active_only) params.active_only = true

  const response = await api.get<Connector[]>('/connectors', { params })
  return response.data
}

/**
 * Get a single connector by ID
 * Note: Credentials are NOT included in response for security
 */
export const getConnector = async (id: number): Promise<Connector> => {
  const response = await api.get<Connector>(`/connectors/${id}`)
  return response.data
}

/**
 * Create a new connector
 */
export const createConnector = async (data: ConnectorCreateRequest): Promise<Connector> => {
  const response = await api.post<Connector>('/connectors', data)
  return response.data
}

/**
 * Update an existing connector
 */
export const updateConnector = async (id: number, data: ConnectorUpdateRequest): Promise<Connector> => {
  const response = await api.put<Connector>(`/connectors/${id}`, data)
  return response.data
}

/**
 * Delete a connector
 * @throws Error 409 if collections reference this connector
 */
export const deleteConnector = async (id: number): Promise<void> => {
  await api.delete(`/connectors/${id}`)
}

/**
 * Test connector connection
 */
export const testConnector = async (id: number): Promise<ConnectorTestResponse> => {
  const response = await api.post<ConnectorTestResponse>(`/connectors/${id}/test`)
  return response.data
}
