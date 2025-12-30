import { useState, useEffect } from 'react';
import {
  Box, TextField, Button, FormControl, InputLabel, Select, MenuItem, Typography
} from '@mui/material';

function CollectionForm({ collection, connectors, onSubmit, onCancel }) {
  const [formData, setFormData] = useState({
    name: '',
    type: 'local',
    location: '',
    state: 'live',
    connector_id: null,
    cache_ttl: '',
    metadata: {},
  });
  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (collection) {
      setFormData({
        name: collection.name || '',
        type: collection.type || 'local',
        location: collection.location || '',
        state: collection.state || 'live',
        connector_id: collection.connector_id || null,
        cache_ttl: collection.cache_ttl || '',
        metadata: collection.metadata || {},
      });
    }
  }, [collection]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setErrors(prev => ({ ...prev, [field]: null }));

    // Reset connector_id when switching to local
    if (field === 'type' && value === 'local') {
      setFormData(prev => ({ ...prev, connector_id: null }));
    }
  };

  const validate = () => {
    const newErrors = {};
    if (!formData.name.trim()) newErrors.name = 'Name is required';
    if (!formData.location.trim()) newErrors.location = 'Location is required';

    // Validate connector requirement
    if (['s3', 'gcs', 'smb'].includes(formData.type)) {
      if (!formData.connector_id) {
        newErrors.connector_id = 'Connector is required for remote collections';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validate()) {
      const submitData = { ...formData };
      if (formData.type === 'local') {
        submitData.connector_id = null;
      }
      onSubmit(submitData);
    }
  };

  const isRemote = ['s3', 'gcs', 'smb'].includes(formData.type);

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
      <TextField
        fullWidth
        label="Collection Name"
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
          onChange={(e) => handleChange('type', e.target.value)}
          disabled={!!collection}
        >
          <MenuItem value="local">Local Filesystem</MenuItem>
          <MenuItem value="s3">Amazon S3</MenuItem>
          <MenuItem value="gcs">Google Cloud Storage</MenuItem>
          <MenuItem value="smb">SMB/CIFS</MenuItem>
        </Select>
      </FormControl>

      {isRemote && (
        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel>Connector</InputLabel>
          <Select
            value={formData.connector_id || ''}
            label="Connector"
            onChange={(e) => handleChange('connector_id', e.target.value)}
            error={!!errors.connector_id}
          >
            {connectors
              .filter(c => c.type === formData.type && c.is_active)
              .map(c => (
                <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>
              ))}
          </Select>
          {errors.connector_id && <Typography color="error" variant="caption">{errors.connector_id}</Typography>}
        </FormControl>
      )}

      <TextField
        fullWidth
        label="Location"
        value={formData.location}
        onChange={(e) => handleChange('location', e.target.value)}
        error={!!errors.location}
        helperText={errors.location || (isRemote ? 'e.g., bucket-name/prefix' : 'e.g., /absolute/path/to/photos')}
        sx={{ mb: 2 }}
      />

      <FormControl fullWidth sx={{ mb: 2 }}>
        <InputLabel>State</InputLabel>
        <Select
          value={formData.state}
          label="State"
          onChange={(e) => handleChange('state', e.target.value)}
        >
          <MenuItem value="live">Live (1hr cache)</MenuItem>
          <MenuItem value="closed">Closed (24hr cache)</MenuItem>
          <MenuItem value="archived">Archived (7d cache)</MenuItem>
        </Select>
      </FormControl>

      <TextField
        fullWidth
        type="number"
        label="Cache TTL (seconds)"
        value={formData.cache_ttl}
        onChange={(e) => handleChange('cache_ttl', e.target.value)}
        helperText="Optional override for state-based default"
        sx={{ mb: 2 }}
      />

      <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end', mt: 3 }}>
        <Button onClick={onCancel}>Cancel</Button>
        <Button type="submit" variant="contained">
          {collection ? 'Update' : 'Create'}
        </Button>
      </Box>
    </Box>
  );
}

export default CollectionForm;
