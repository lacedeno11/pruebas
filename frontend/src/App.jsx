import React, { useState } from 'react';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { OTProvider, useOT } from './contexts/OTContext';
import KanbanBoard from './components/KanbanBoard';
import Map from './components/Map';
import AgentChat from './components/AgentChat';

/**
 * Header - Application header with controls
 */
function Header({ viewMode, onViewModeChange, onSync, isSyncing }) {
  return (
    <header className="bg-gradient-to-r from-blue-600 to-blue-700 text-white px-6 py-4 shadow-lg">
      <div className="flex items-center justify-between gap-4">
        {/* Logo and Title */}
        <div className="flex items-center gap-3">
          <span className="text-2xl">🏗️</span>
          <h1 className="text-xl font-bold">
            PEI - Plataforma de Ejecución de Instalaciones
          </h1>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-4">
          {/* View Toggle Buttons */}
          <div className="flex gap-2 bg-blue-500/30 rounded-lg p-1">
            <button
              onClick={() => onViewModeChange('kanban')}
              className={`
                px-4 py-2 rounded font-medium transition-colors
                ${
                  viewMode === 'kanban'
                    ? 'bg-white text-blue-600'
                    : 'text-white hover:bg-blue-600'
                }
              `}
            >
              📋 Kanban
            </button>
            <button
              onClick={() => onViewModeChange('map')}
              className={`
                px-4 py-2 rounded font-medium transition-colors
                ${
                  viewMode === 'map'
                    ? 'bg-white text-blue-600'
                    : 'text-white hover:bg-blue-600'
                }
              `}
            >
              🗺️ Mapa
            </button>
          </div>

          {/* Sync Button */}
          <button
            onClick={onSync}
            disabled={isSyncing}
            className={`
              px-4 py-2 rounded font-medium transition-colors flex items-center gap-2
              ${
                isSyncing
                  ? 'bg-blue-400 text-white cursor-not-allowed opacity-75'
                  : 'bg-white text-blue-600 hover:bg-gray-100'
              }
            `}
          >
            {isSyncing ? (
              <>
                <span className="animate-spin">⏳</span>
                <span>Sincronizando...</span>
              </>
            ) : (
              <>
                <span>🔄</span>
                <span>Sincronizar</span>
              </>
            )}
          </button>
        </div>
      </div>
    </header>
  );
}

/**
 * AppContent - Main content component that uses context
 */
function AppContent() {
  const { syncOTs, loading } = useOT();
  const [viewMode, setViewMode] = useState('kanban');

  /**
   * Handle sync button click
   */
  const handleSync = async () => {
    try {
      await syncOTs();
    } catch (error) {
      console.error('Error syncing OTs:', error);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <Header
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        onSync={handleSync}
        isSyncing={loading}
      />

      {/* Main Content Area */}
      <main className="flex-1 overflow-auto">
        {viewMode === 'kanban' ? (
          <KanbanBoard />
        ) : (
          <div className="h-full w-full">
            <Map />
          </div>
        )}
      </main>

      {/* Agent Chat Sidebar */}
      <AgentChat />

      {/* Toast Notifications */}
      <ToastContainer
        position="bottom-right"
        autoClose={3000}
        hideProgressBar={false}
        newestOnTop={false}
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="light"
      />
    </div>
  );
}

/**
 * App - Main Application Component
 * Wraps everything in OTProvider for context management
 */
function App() {
  return (
    <OTProvider>
      <AppContent />
    </OTProvider>
  );
}

export default App;

