import { Chip, Tooltip } from '@mui/material';
import { CheckCircle, Error, Warning } from '@mui/icons-material';

function CollectionStatus({ collection }) {
  if (collection.is_accessible) {
    return (
      <Tooltip title="Collection is accessible">
        <Chip
          icon={<CheckCircle />}
          label="Accessible"
          color="success"
          size="small"
        />
      </Tooltip>
    );
  }

  const errorMessage = collection.last_error || 'Accessibility unknown';

  return (
    <Tooltip title={errorMessage}>
      <Chip
        icon={<Error />}
        label="Not Accessible"
        color="error"
        size="small"
      />
    </Tooltip>
  );
}

export default CollectionStatus;
