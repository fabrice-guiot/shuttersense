import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';
import { ThemeProvider, createTheme } from '@mui/material';
import './globals.css';

// MUI theme for legacy components (Collections/Connectors pages not yet migrated)
// TODO: Remove once all pages are migrated to shadcn/ui (Phase 6-7)
const theme = createTheme({
  palette: {
    mode: 'dark', // Match our dark theme
    primary: {
      main: '#3b82f6', // Match our --primary color
    },
    secondary: {
      main: '#6b7280', // Match our --secondary color
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <App />
    </ThemeProvider>
  </React.StrictMode>
);
