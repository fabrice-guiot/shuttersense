/**
 * Connectors Page
 *
 * Manage remote storage connectors with CRUD operations
 */

import { useState } from 'react';
import {
  Box,
  Button,
  Typography,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
} from '@mui/material';
import { Add as AddIcon } from '@mui/icons-material';
import { useConnectors } from '../hooks/useConnectors';
import ConnectorList from '../components/connectors/ConnectorList';
import ConnectorForm from '../components/connectors/ConnectorForm';

function ConnectorsPage() {
  const {
    connectors,
    loading,
    error,
    createConnector,
    updateConnector,
    deleteConnector,
    testConnector,
  } = useConnectors();

  const [open, setOpen] = useState(false);
  const [editingConnector, setEditingConnector] = useState(null);
  const [formError, setFormError] = useState(null);

  const handleOpen = (connector = null) => {
    setEditingConnector(connector);
    setFormError(null);
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
    setEditingConnector(null);
    setFormError(null);
  };

  const handleSubmit = async (formData) => {
    setFormError(null);
    try {
      if (editingConnector) {
        await updateConnector(editingConnector.id, formData);
      } else {
        await createConnector(formData);
      }
      handleClose();
    } catch (err) {
      setFormError(err.userMessage || 'Operation failed');
    }
  };

  const handleDelete = async (id) => {
    try {
      await deleteConnector(id);
    } catch (err) {
      // Error already handled by hook
    }
  };

  const handleTest = async (id) => {
    return await testConnector(id);
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Remote Storage Connectors
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpen()}
        >
          New Connector
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <ConnectorList
        connectors={connectors}
        loading={loading}
        onEdit={handleOpen}
        onDelete={handleDelete}
        onTest={handleTest}
      />

      <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingConnector ? 'Edit Connector' : 'New Connector'}
        </DialogTitle>
        <DialogContent>
          {formError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {formError}
            </Alert>
          )}
          <ConnectorForm
            connector={editingConnector}
            onSubmit={handleSubmit}
            onCancel={handleClose}
          />
        </DialogContent>
      </Dialog>
    </Box>
  );
}

export default ConnectorsPage;
