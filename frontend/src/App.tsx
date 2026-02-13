import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { useEffect } from 'react';

// Components will be imported once created
// import Dashboard from '@/components/Dashboard';

// Create a client for React Query
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
      <Toaster position="top-right" />
      
      {/* Main application content */}
      <div id="app">
        {/* Dashboard component will be rendered here once created */}
        <div className="min-h-screen bg-gray-50">
          <p className="p-8 text-center text-gray-600">
            Loading DERCAS PEI Dashboard...
          </p>
        </div>
      </div>
    </QueryClientProvider>
  );
}

export default App;

