import { useState } from 'react';
import {
  Box, Button, Typography, Dialog, DialogTitle, DialogContent, Alert
} from '@mui/material';
import { Add as AddIcon } from '@mui/icons-material';
import { useCollections } from '../hooks/useCollections';
import { useConnectors } from '../hooks/useConnectors';
import CollectionList from '../components/collections/CollectionList';
import CollectionForm from '../components/collections/CollectionForm';

function CollectionsPage() {
  const {
    collections,
    loading,
    error,
    createCollection,
    updateCollection,
    deleteCollection,
    testCollection,
    refreshCollection,
  } = useCollections();

  const { connectors } = useConnectors();

  const [open, setOpen] = useState(false);
  const [editingCollection, setEditingCollection] = useState(null);
  const [formError, setFormError] = useState(null);

  const handleOpen = (collection = null) => {
    setEditingCollection(collection);
    setFormError(null);
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
    setEditingCollection(null);
    setFormError(null);
  };

  const handleSubmit = async (formData) => {
    setFormError(null);
    try {
      if (editingCollection) {
        await updateCollection(editingCollection.id, formData);
      } else {
        await createCollection(formData);
      }
      handleClose();
    } catch (err) {
      setFormError(err.userMessage || 'Operation failed');
    }
  };

  const handleDelete = async (id, force) => {
    try {
      await deleteCollection(id, force);
    } catch (err) {
      // Error handled by hook
    }
  };

  const handleTest = async (id) => {
    return await testCollection(id);
  };

  const handleRefresh = async (id, confirm) => {
    return await refreshCollection(id, confirm);
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Photo Collections
        </Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => handleOpen()}>
          New Collection
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <CollectionList
        collections={collections}
        loading={loading}
        onEdit={handleOpen}
        onDelete={handleDelete}
        onTest={handleTest}
        onRefresh={handleRefresh}
      />

      <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingCollection ? 'Edit Collection' : 'New Collection'}
        </DialogTitle>
        <DialogContent>
          {formError && <Alert severity="error" sx={{ mb: 2 }}>{formError}</Alert>}
          <CollectionForm
            collection={editingCollection}
            connectors={connectors}
            onSubmit={handleSubmit}
            onCancel={handleClose}
          />
        </DialogContent>
      </Dialog>
    </Box>
  );
}

export default CollectionsPage;
