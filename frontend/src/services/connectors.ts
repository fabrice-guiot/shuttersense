/**
 * Connector API service
 *
 * Handles all API calls related to remote storage connectors
 */

import api from './api'
import { validateGuid } from '@/utils/guid'
import type {
  Connector,
  ConnectorCreateRequest,
  ConnectorUpdateRequest,
  ConnectorTestResponse,
  ConnectorStatsResponse
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
 * Get a single connector by GUID
 * Note: Credentials are NOT included in response for security
 * @param guid - External ID (con_xxx format)
 */
export const getConnector = async (guid: string): Promise<Connector> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'con'))
  const response = await api.get<Connector>(`/connectors/${safeGuid}`)
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
 * @param guid - External ID (con_xxx format)
 */
export const updateConnector = async (guid: string, data: ConnectorUpdateRequest): Promise<Connector> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'con'))
  const response = await api.put<Connector>(`/connectors/${safeGuid}`, data)
  return response.data
}

/**
 * Delete a connector
 * @param guid - External ID (con_xxx format)
 * @throws Error 409 if collections reference this connector
 */
export const deleteConnector = async (guid: string): Promise<void> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'con'))
  await api.delete(`/connectors/${safeGuid}`)
}

/**
 * Test connector connection
 * @param guid - External ID (con_xxx format)
 */
export const testConnector = async (guid: string): Promise<ConnectorTestResponse> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'con'))
  const response = await api.post<ConnectorTestResponse>(`/connectors/${safeGuid}/test`)
  return response.data
}

/**
 * Get connector statistics (KPIs)
 * Returns aggregated stats for all connectors
 */
export const getConnectorStats = async (): Promise<ConnectorStatsResponse> => {
  const response = await api.get<ConnectorStatsResponse>('/connectors/stats')
  return response.data
}
