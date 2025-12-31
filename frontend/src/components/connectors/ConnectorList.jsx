import { useState } from 'react';
import {
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, IconButton, Chip, CircularProgress, Box, Dialog,
  DialogTitle, DialogContent, DialogContentText, DialogActions, Button,
  FormControl, InputLabel, Select, MenuItem, FormControlLabel, Checkbox,
  Tooltip
} from '@mui/material';
import { Edit, Delete, FactCheck } from '@mui/icons-material';

function ConnectorList({ connectors, loading, onEdit, onDelete, onTest }) {
  const [deleteDialog, setDeleteDialog] = useState({ open: false, connector: null });
  const [typeFilter, setTypeFilter] = useState('');
  const [activeOnly, setActiveOnly] = useState(false);

  const filteredConnectors = connectors.filter(c => {
    if (typeFilter && c.type !== typeFilter) return false;
    if (activeOnly && !c.is_active) return false;
    return true;
  });

  const handleDeleteClick = (connector) => {
    setDeleteDialog({ open: true, connector });
  };

  const handleDeleteConfirm = async () => {
    try {
      await onDelete(deleteDialog.connector.id);
      setDeleteDialog({ open: false, connector: null });
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
          <InputLabel>Type</InputLabel>
          <Select value={typeFilter} label="Type" onChange={(e) => setTypeFilter(e.target.value)}>
            <MenuItem value="">All</MenuItem>
            <MenuItem value="s3">S3</MenuItem>
            <MenuItem value="gcs">GCS</MenuItem>
            <MenuItem value="smb">SMB</MenuItem>
          </Select>
        </FormControl>
        <FormControlLabel
          control={<Checkbox checked={activeOnly} onChange={(e) => setActiveOnly(e.target.checked)} />}
          label="Active Only"
        />
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Last Validated</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredConnectors.map((connector) => (
              <TableRow key={connector.id}>
                <TableCell>{connector.name}</TableCell>
                <TableCell>
                  <Chip label={connector.type.toUpperCase()} size="small" />
                </TableCell>
                <TableCell>
                  <Chip
                    label={connector.is_active ? 'Active' : 'Inactive'}
                    color={connector.is_active ? 'success' : 'default'}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  {connector.last_validated
                    ? new Date(connector.last_validated).toLocaleString()
                    : 'Never'}
                </TableCell>
                <TableCell align="right">
                  <Tooltip title="Test Connection">
                    <IconButton size="small" onClick={() => onTest(connector.id)}>
                      <FactCheck />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Edit Connector">
                    <IconButton size="small" onClick={() => onEdit(connector)}>
                      <Edit />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete Connector">
                    <IconButton size="small" onClick={() => handleDeleteClick(connector)}>
                      <Delete />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={deleteDialog.open} onClose={() => setDeleteDialog({ open: false, connector: null })}>
        <DialogTitle>Delete Connector</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete "{deleteDialog.connector?.name}"?
            {deleteDialog.connector && ' If collections reference this connector, deletion will fail.'}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog({ open: false, connector: null })}>Cancel</Button>
          <Button onClick={handleDeleteConfirm} color="error">Delete</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export default ConnectorList;
