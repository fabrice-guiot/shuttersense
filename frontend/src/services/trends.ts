/**
 * Trends API service
 *
 * Handles all API calls related to trend analysis data
 */

import api from './api'
import type {
  PhotoStatsTrendResponse,
  PhotoPairingTrendResponse,
  PipelineValidationTrendResponse,
  DisplayGraphTrendResponse,
  TrendSummaryResponse,
  TrendQueryParams,
  PipelineValidationTrendQueryParams,
  TrendSummaryQueryParams
} from '@/contracts/api/trends-api'

export interface DisplayGraphTrendQueryParams {
  pipeline_ids?: string
  from_date?: string
  to_date?: string
  limit?: number
}

/**
 * Filter out undefined values from params object to prevent
 * axios from serializing them as "undefined" strings
 */
function cleanParams<T extends object>(params: T): Partial<T> {
  return Object.fromEntries(
    Object.entries(params).filter(([_, value]) => value !== undefined)
  ) as Partial<T>
}

/**
 * Get PhotoStats trends (orphaned files over time)
 */
export const getPhotoStatsTrends = async (
  params: TrendQueryParams = {}
): Promise<PhotoStatsTrendResponse> => {
  const response = await api.get<PhotoStatsTrendResponse>('/trends/photostats', {
    params: cleanParams(params)
  })
  return response.data
}

/**
 * Get Photo Pairing trends (camera usage over time)
 */
export const getPhotoPairingTrends = async (
  params: TrendQueryParams = {}
): Promise<PhotoPairingTrendResponse> => {
  const response = await api.get<PhotoPairingTrendResponse>('/trends/photo-pairing', {
    params: cleanParams(params)
  })
  return response.data
}

/**
 * Get Pipeline Validation trends (consistency over time)
 */
export const getPipelineValidationTrends = async (
  params: PipelineValidationTrendQueryParams = {}
): Promise<PipelineValidationTrendResponse> => {
  const response = await api.get<PipelineValidationTrendResponse>('/trends/pipeline-validation', {
    params: cleanParams(params)
  })
  return response.data
}

/**
 * Get Display Graph trends (pipeline path enumeration over time)
 */
export const getDisplayGraphTrends = async (
  params: DisplayGraphTrendQueryParams = {}
): Promise<DisplayGraphTrendResponse> => {
  const response = await api.get<DisplayGraphTrendResponse>('/trends/display-graph', {
    params: cleanParams(params)
  })
  return response.data
}

/**
 * Get trend summary for dashboard
 */
export const getTrendSummary = async (
  params: TrendSummaryQueryParams = {}
): Promise<TrendSummaryResponse> => {
  const response = await api.get<TrendSummaryResponse>('/trends/summary', {
    params: cleanParams(params)
  })
  return response.data
}
