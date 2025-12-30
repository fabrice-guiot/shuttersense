/**
 * Photo Admin Application
 *
 * Main application component with routing
 */

import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { AppBar, Toolbar, Typography, Button, Container, Box } from '@mui/material';
import { Storage as ConnectorIcon, Collections as CollectionIcon } from '@mui/icons-material';

// Page components
import ConnectorsPage from './pages/ConnectorsPage';
import CollectionsPage from './pages/CollectionsPage';

function App() {
  return (
    <BrowserRouter>
      <Box sx={{ flexGrow: 1 }}>
        <AppBar position="static">
          <Toolbar>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              Photo Admin
            </Typography>
            <Button
              color="inherit"
              component={Link}
              to="/connectors"
              startIcon={<ConnectorIcon />}
            >
              Connectors
            </Button>
            <Button
              color="inherit"
              component={Link}
              to="/collections"
              startIcon={<CollectionIcon />}
            >
              Collections
            </Button>
          </Toolbar>
        </AppBar>

        <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
          <Routes>
            <Route path="/" element={<CollectionsPage />} />
            <Route path="/connectors" element={<ConnectorsPage />} />
            <Route path="/collections" element={<CollectionsPage />} />
          </Routes>
        </Container>
      </Box>
    </BrowserRouter>
  );
}

export default App;
