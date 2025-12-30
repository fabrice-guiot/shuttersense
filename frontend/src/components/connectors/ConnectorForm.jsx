import { useState, useEffect } from 'react';
import {
  Box, TextField, Button, FormControl, InputLabel, Select, MenuItem,
  Typography, Alert, CircularProgress
} from '@mui/material';

const CREDENTIAL_FIELDS = {
  s3: [
    { name: 'aws_access_key_id', label: 'AWS Access Key ID', type: 'text', required: true, minLength: 16 },
    { name: 'aws_secret_access_key', label: 'AWS Secret Access Key', type: 'password', required: true, minLength: 40 },
    { name: 'region', label: 'Region', type: 'text', required: true },
  ],
  gcs: [
    { name: 'service_account_json', label: 'Service Account JSON', type: 'textarea', required: true },
  ],
  smb: [
    { name: 'server', label: 'Server', type: 'text', required: true },
    { name: 'share', label: 'Share', type: 'text', required: true },
    { name: 'username', label: 'Username', type: 'text', required: true },
    { name: 'password', label: 'Password', type: 'password', required: true },
  ],
};

function ConnectorForm({ connector, onSubmit, onCancel }) {
  const [formData, setFormData] = useState({
    name: '',
    type: 's3',
    credentials: {},
    metadata: {},
  });
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (connector) {
      setFormData({
        name: connector.name || '',
        type: connector.type || 's3',
        credentials: {},
        metadata: connector.metadata || {},
      });
    }
  }, [connector]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setErrors(prev => ({ ...prev, [field]: null }));
  };

  const handleCredentialChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      credentials: { ...prev.credentials, [field]: value },
    }));
    setErrors(prev => ({ ...prev, [`credentials.${field}`]: null }));
  };

  const validate = () => {
    const newErrors = {};
    if (!formData.name.trim()) newErrors.name = 'Name is required';

    const fields = CREDENTIAL_FIELDS[formData.type] || [];
    fields.forEach(field => {
      const value = formData.credentials[field.name];
      if (field.required && !value) {
        newErrors[`credentials.${field.name}`] = `${field.label} is required`;
      } else if (field.minLength && value && value.length < field.minLength) {
        newErrors[`credentials.${field.name}`] = `Minimum ${field.minLength} characters`;
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validate()) {
      onSubmit(formData);
    }
  };

  const credentialFields = CREDENTIAL_FIELDS[formData.type] || [];

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
      <TextField
        fullWidth
        label="Connector Name"
        value={formData.name}
        onChange={(e) => handleChange('name', e.target.value)}
        error={!!errors.name}
        helperText={errors.name}
        sx={{ mb: 2 }}
      />

      <FormControl fullWidth sx={{ mb: 2 }}>
        <InputLabel>Type</InputLabel>
        <Select
          value={formData.type}
          label="Type"
          onChange={(e) => {
            handleChange('type', e.target.value);
            setFormData(prev => ({ ...prev, credentials: {} }));
          }}
          disabled={!!connector}
        >
          <MenuItem value="s3">Amazon S3</MenuItem>
          <MenuItem value="gcs">Google Cloud Storage</MenuItem>
          <MenuItem value="smb">SMB/CIFS</MenuItem>
        </Select>
      </FormControl>

      <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
        Credentials
      </Typography>

      {credentialFields.map(field => (
        <TextField
          key={field.name}
          fullWidth
          label={field.label}
          type={field.type === 'password' ? 'password' : 'text'}
          multiline={field.type === 'textarea'}
          rows={field.type === 'textarea' ? 4 : 1}
          value={formData.credentials[field.name] || ''}
          onChange={(e) => handleCredentialChange(field.name, e.target.value)}
          error={!!errors[`credentials.${field.name}`]}
          helperText={errors[`credentials.${field.name}`]}
          sx={{ mb: 2 }}
        />
      ))}

      {testResult && (
        <Alert severity={testResult.success ? 'success' : 'error'} sx={{ mb: 2 }}>
          {testResult.message}
        </Alert>
      )}

      <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end', mt: 3 }}>
        <Button onClick={onCancel}>Cancel</Button>
        <Button type="submit" variant="contained">
          {connector ? 'Update' : 'Create'}
        </Button>
      </Box>
    </Box>
  );
}

export default ConnectorForm;
