import { useState } from 'react';
import {
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, IconButton, Chip, CircularProgress, Box, Dialog,
  DialogTitle, DialogContent, DialogContentText, DialogActions, Button,
  FormControl, InputLabel, Select, MenuItem, FormControlLabel, Checkbox,
  Tooltip
} from '@mui/material';
import { Edit, Delete, FactCheck, Refresh } from '@mui/icons-material';
import CollectionStatus from './CollectionStatus';

function CollectionList({ collections, loading, onEdit, onDelete, onTest, onRefresh }) {
  const [deleteDialog, setDeleteDialog] = useState({ open: false, collection: null });
  const [stateFilter, setStateFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [accessibleOnly, setAccessibleOnly] = useState(false);

  const filteredCollections = collections.filter(c => {
    if (stateFilter && c.state !== stateFilter) return false;
    if (typeFilter && c.type !== typeFilter) return false;
    if (accessibleOnly && !c.is_accessible) return false;
    return true;
  });

  const handleDeleteClick = (collection) => {
    setDeleteDialog({ open: true, collection });
  };

  const handleDeleteConfirm = async () => {
    try {
      await onDelete(deleteDialog.collection.id, false);
      setDeleteDialog({ open: false, collection: null });
    } catch (err) {
      // Error handled by parent
    }
  };

  if (loading) {
    return <Box display="flex" justifyContent="center" p={4}><CircularProgress /></Box>;
  }

  return (
    <>
      <Box sx={{ mb: 2, display: 'flex', gap: 2 }}>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>State</InputLabel>
          <Select value={stateFilter} label="State" onChange={(e) => setStateFilter(e.target.value)}>
            <MenuItem value="">All</MenuItem>
            <MenuItem value="live">Live</MenuItem>
            <MenuItem value="closed">Closed</MenuItem>
            <MenuItem value="archived">Archived</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Type</InputLabel>
          <Select value={typeFilter} label="Type" onChange={(e) => setTypeFilter(e.target.value)}>
            <MenuItem value="">All</MenuItem>
            <MenuItem value="local">Local</MenuItem>
            <MenuItem value="s3">S3</MenuItem>
            <MenuItem value="gcs">GCS</MenuItem>
            <MenuItem value="smb">SMB</MenuItem>
          </Select>
        </FormControl>
        <FormControlLabel
          control={<Checkbox checked={accessibleOnly} onChange={(e) => setAccessibleOnly(e.target.checked)} />}
          label="Accessible Only"
        />
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>State</TableCell>
              <TableCell>Location</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredCollections.map((collection) => (
              <TableRow key={collection.id}>
                <TableCell>{collection.name}</TableCell>
                <TableCell>
                  <Chip
                    label={collection.type === 'local' ? 'Local' : collection.type.toUpperCase()}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  <Chip
                    label={collection.state.charAt(0).toUpperCase() + collection.state.slice(1)}
                    size="small"
                    color="primary"
                  />
                </TableCell>
                <TableCell>{collection.location}</TableCell>
                <TableCell><CollectionStatus collection={collection} /></TableCell>
                <TableCell align="right">
                  <Tooltip title="Test Collection">
                    <IconButton size="small" onClick={() => onTest(collection.id)}>
                      <FactCheck />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Refresh Collection">
                    <IconButton size="small" onClick={() => onRefresh(collection.id, false)}>
                      <Refresh />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Edit Collection">
                    <IconButton size="small" onClick={() => onEdit(collection)}>
                      <Edit />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete Collection">
                    <IconButton size="small" onClick={() => handleDeleteClick(collection)}>
                      <Delete />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={deleteDialog.open} onClose={() => setDeleteDialog({ open: false, collection: null })}>
        <DialogTitle>Delete Collection</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete "{deleteDialog.collection?.name}"?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog({ open: false, collection: null })}>Cancel</Button>
          <Button onClick={handleDeleteConfirm} color="error">Delete</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export default CollectionList;
