import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { useEffect } from 'react';
import Dashboard from '@/components/Dashboard';

// Create a client for React Query with optimized settings
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000, // 30 seconds
    },
  },
});

function App() {
  // Set document title
  useEffect(() => {
    document.title = 'DERCAS PEI - Gestión Agéntica de OTs';
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      {/* Toast notifications */}
      <Toaster position="top-right" />
      
      {/* Main application */}
      <Dashboard />
    </QueryClientProvider>
  );
}

export default App;


