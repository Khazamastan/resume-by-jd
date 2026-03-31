import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import ReactDOM from 'react-dom/client';

import App from './App';
import { ThemeSettingsProvider } from './theme/ThemeSettingsProvider';

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeSettingsProvider>
        <App />
      </ThemeSettingsProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);
