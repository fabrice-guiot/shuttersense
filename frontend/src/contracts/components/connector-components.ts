/**
 * Connector Component Contracts
 *
 * Defines prop interfaces for connector-related components
 */

import type { Connector } from '../api/connector-api'
import type { ConnectorFormData } from '@/types/schemas/connector'

// ============================================================================
// ConnectorList Component
// ============================================================================

export interface ConnectorListProps {
  /**
   * List of connectors to display
   */
  connectors: Connector[]

  /**
   * Loading state (shows skeleton/spinner)
   */
  loading: boolean

  /**
   * Type filter selection ('ALL' or specific type)
   */
  typeFilter: 'ALL' | 'S3' | 'GCS' | 'SMB'

  /**
   * Active-only filter toggle
   */
  activeOnlyFilter: boolean

  /**
   * Callback when edit button clicked
   */
  onEdit: (connector: Connector) => void

  /**
   * Callback when delete button clicked
   */
  onDelete: (connector: Connector) => void

  /**
   * Callback when test connection button clicked
   */
  onTest: (connector: Connector) => void

  /**
   * Callback when type filter changes
   */
  onTypeFilterChange: (type: 'ALL' | 'S3' | 'GCS' | 'SMB') => void

  /**
   * Callback when active-only filter changes
   */
  onActiveOnlyFilterChange: (activeOnly: boolean) => void

  /**
   * Additional CSS classes
   */
  className?: string
}

/**
 * Filter options for connector type dropdown
 */
export const CONNECTOR_TYPE_FILTER_OPTIONS = [
  { value: 'ALL', label: 'All Types' },
  { value: 'S3', label: 'Amazon S3' },
  { value: 'GCS', label: 'Google Cloud Storage' },
  { value: 'SMB', label: 'SMB/CIFS' }
] as const

// ============================================================================
// ConnectorForm Component
// ============================================================================

export interface ConnectorFormProps {
  /**
   * Connector to edit (undefined for create mode)
   */
  connector?: Connector

  /**
   * Callback when form is submitted
   * Returns Promise for async operations
   */
  onSubmit: (data: ConnectorFormData) => Promise<void>

  /**
   * Callback when cancel button clicked
   */
  onCancel: () => void

  /**
   * Loading state during submission
   */
  loading?: boolean

  /**
   * Error message to display
   */
  error?: string | null

  /**
   * Additional CSS classes
   */
  className?: string
}

/**
 * Form mode determined by presence of connector prop
 */
export type ConnectorFormMode = 'create' | 'edit'

/**
 * Dynamic credential fields based on connector type
 */
export interface CredentialFieldConfig {
  type: 'text' | 'password' | 'textarea' | 'select'
  name: string
  label: string
  placeholder: string
  required: boolean
  helperText?: string
  options?: { value: string; label: string }[]
}

/**
 * S3 credential fields
 */
export const S3_CREDENTIAL_FIELDS: CredentialFieldConfig[] = [
  {
    type: 'text',
    name: 'aws_access_key_id',
    label: 'Access Key ID',
    placeholder: 'AKIAIOSFODNN7EXAMPLE',
    required: true,
    helperText: '16-128 characters'
  },
  {
    type: 'password',
    name: 'aws_secret_access_key',
    label: 'Secret Access Key',
    placeholder: 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
    required: true,
    helperText: 'Minimum 40 characters'
  },
  {
    type: 'select',
    name: 'region',
    label: 'AWS Region',
    placeholder: 'Select region',
    required: true,
    options: [
      { value: 'us-east-1', label: 'US East (N. Virginia)' },
      { value: 'us-east-2', label: 'US East (Ohio)' },
      { value: 'us-west-1', label: 'US West (N. California)' },
      { value: 'us-west-2', label: 'US West (Oregon)' },
      { value: 'eu-west-1', label: 'EU (Ireland)' },
      { value: 'eu-central-1', label: 'EU (Frankfurt)' },
      { value: 'ap-southeast-1', label: 'Asia Pacific (Singapore)' },
      { value: 'ap-northeast-1', label: 'Asia Pacific (Tokyo)' }
    ]
  },
  {
    type: 'text',
    name: 'bucket',
    label: 'Bucket Name (Optional)',
    placeholder: 'my-photo-bucket',
    required: false,
    helperText: 'Default bucket for this connector'
  }
]

/**
 * GCS credential fields
 */
export const GCS_CREDENTIAL_FIELDS: CredentialFieldConfig[] = [
  {
    type: 'textarea',
    name: 'service_account_json',
    label: 'Service Account JSON',
    placeholder: '{\n  "type": "service_account",\n  ...\n}',
    required: true,
    helperText: 'Paste the entire service account JSON key file'
  },
  {
    type: 'text',
    name: 'bucket',
    label: 'Bucket Name (Optional)',
    placeholder: 'my-photo-bucket',
    required: false,
    helperText: 'Default bucket for this connector'
  }
]

/**
 * SMB credential fields
 */
export const SMB_CREDENTIAL_FIELDS: CredentialFieldConfig[] = [
  {
    type: 'text',
    name: 'server',
    label: 'Server',
    placeholder: '192.168.1.100 or nas.local',
    required: true
  },
  {
    type: 'text',
    name: 'share',
    label: 'Share Name',
    placeholder: 'photos',
    required: true
  },
  {
    type: 'text',
    name: 'username',
    label: 'Username',
    placeholder: 'user',
    required: true
  },
  {
    type: 'password',
    name: 'password',
    label: 'Password',
    placeholder: '••••••••',
    required: true
  },
  {
    type: 'text',
    name: 'domain',
    label: 'Domain (Optional)',
    placeholder: 'WORKGROUP',
    required: false
  }
]

/**
 * Get credential fields for connector type
 */
export function getCredentialFields(
  type: 'S3' | 'GCS' | 'SMB'
): CredentialFieldConfig[] {
  switch (type) {
    case 'S3':
      return S3_CREDENTIAL_FIELDS
    case 'GCS':
      return GCS_CREDENTIAL_FIELDS
    case 'SMB':
      return SMB_CREDENTIAL_FIELDS
  }
}

// ============================================================================
// ConnectorTestButton Component
// ============================================================================

export interface ConnectorTestButtonProps {
  /**
   * Connector ID to test
   */
  connectorId: number

  /**
   * Callback when test is triggered
   * Returns Promise with test result
   */
  onTest: (connectorId: number) => Promise<{ success: boolean; message: string }>

  /**
   * Button variant (default: 'secondary')
   */
  variant?: 'default' | 'secondary' | 'outline' | 'ghost'

  /**
   * Button size
   */
  size?: 'sm' | 'md' | 'lg'

  /**
   * Additional CSS classes
   */
  className?: string
}
