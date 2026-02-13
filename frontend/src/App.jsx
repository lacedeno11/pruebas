import React, { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ToastContainer } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'
import KanbanBoard from './components/KanbanBoard'
import MapView from './components/MapView'
import ChatSidebar from './components/ChatSidebar'

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,
      gcTime: 60000,
      retry: 1,
      refetchOnWindowFocus: false
    }
  }
})

export function App() {
  const [activeTab, setActiveTab] = useState('kanban')
  const [systemMode, setSystemMode] = useState('MOCK')

  // Fetch system mode on mount
  React.useEffect(() => {
    const fetchSystemMode = async () => {
      try {
        const response = await fetch('/api/')
        if (response.ok) {
          const data = await response.json()
          setSystemMode(data.system_mode || 'MOCK')
        }
      } catch (error) {
        console.error('Failed to fetch system mode:', error)
        setSystemMode('MOCK')
      }
    }

    fetchSystemMode()
  }, [])

  return (
    <QueryClientProvider client={queryClient}>
      <div className="app-container">
        {/* Header */}
        <header className="app-header">
          <div className="header-content">
            <div className="header-title-section">
              <h1 className="header-title">
                🏢 PEI Platform - DERCAS TO-BE AGÉNTICO
              </h1>
              <p className="header-subtitle">
                Plataforma de Coordinación de Equipos de Instalación
              </p>
            </div>

            <div className="header-info">
              <div className="system-mode-indicator">
                <span className="system-mode-label">Mode:</span>
                <span className={`system-mode-badge system-mode-${systemMode.toLowerCase()}`}>
                  {systemMode}
                </span>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="app-main">
          {/* Navigation Tabs */}
          <nav className="app-tabs">
            <div className="tabs-container">
              <button
                className={`app-tab ${activeTab === 'kanban' ? 'active' : ''}`}
                onClick={() => setActiveTab('kanban')}
                aria-selected={activeTab === 'kanban'}
                role="tab"
              >
                <span className="tab-icon">📋</span>
                <span className="tab-label">Kanban Board</span>
              </button>

              <button
                className={`app-tab ${activeTab === 'map' ? 'active' : ''}`}
                onClick={() => setActiveTab('map')}
                aria-selected={activeTab === 'map'}
                role="tab"
              >
                <span className="tab-icon">🗺️</span>
                <span className="tab-label">Geographic View</span>
              </button>
            </div>

            <div className="tabs-info">
              <p className="tabs-description">
                {activeTab === 'kanban'
                  ? 'Drag and drop work orders between status columns'
                  : 'View work orders and team locations on the map'}
              </p>
            </div>
          </nav>

          {/* Tab Content */}
          <div className="app-content">
            {activeTab === 'kanban' && (
              <section className="tab-content tab-content-kanban" role="tabpanel">
                <KanbanBoard />
              </section>
            )}

            {activeTab === 'map' && (
              <section className="tab-content tab-content-map" role="tabpanel">
                <MapView />
              </section>
            )}
          </div>
        </main>

        {/* Chat Sidebar */}
        <ChatSidebar />

        {/* Global Toast Notifications */}
        <ToastContainer
          position="bottom-right"
          autoClose={3000}
          hideProgressBar={false}
          newestOnTop={true}
          closeOnClick
          rtl={false}
          pauseOnFocusLoss
          draggable
          pauseOnHover
          theme="light"
        />
      </div>

      {/* Global Styles */}
      <style>{appStyles}</style>
    </QueryClientProvider>
  )
}

// Global App Styles
const appStyles = `
* {
  box-sizing: border-box;
}

html, body, #root {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-color: #f5f5f5;
}

.app-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100vh;
  background-color: #f5f5f5;
}

/* Header Styling */
.app-header {
  background: linear-gradient(135deg, #1565c0 0%, #0d47a1 100%);
  color: white;
  padding: 16px 24px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  flex-shrink: 0;
}

.header-content {
  max-width: 1600px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
}

.header-title-section {
  flex: 1;
}

.header-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.5px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-subtitle {
  margin: 4px 0 0 0;
  font-size: 13px;
  opacity: 0.9;
  letter-spacing: 0.3px;
}

.header-info {
  display: flex;
  gap: 16px;
  align-items: center;
}

.system-mode-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.25);
}

.system-mode-label {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.system-mode-badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.system-mode-mock {
  background-color: #4caf50;
  color: white;
}

.system-mode-production {
  background-color: #ff9800;
  color: white;
}

/* Main Content Area */
.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: #f5f5f5;
}

/* Tabs Navigation */
.app-tabs {
  background-color: white;
  border-bottom: 2px solid #e0e0e0;
  padding: 0;
  flex-shrink: 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.tabs-container {
  max-width: 1600px;
  margin: 0 auto;
  width: 100%;
  display: flex;
  padding: 0 24px;
  gap: 4px;
}

.app-tab {
  padding: 14px 20px;
  background: none;
  border: none;
  border-bottom: 3px solid transparent;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  color: #666;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.app-tab:hover {
  color: #1565c0;
  background-color: #f5f5f5;
}

.app-tab.active {
  color: #1565c0;
  border-bottom-color: #1565c0;
}

.tab-icon {
  font-size: 16px;
}

.tab-label {
  letter-spacing: 0.3px;
}

.tabs-info {
  max-width: 1600px;
  margin: 0 auto;
  width: 100%;
  padding: 0 24px 8px 24px;
  border-bottom: 1px solid #e0e0e0;
}

.tabs-description {
  margin: 0;
  font-size: 12px;
  color: #999;
  letter-spacing: 0.3px;
}

/* Tab Content */
.app-content {
  flex: 1;
  overflow: auto;
  background-color: #f5f5f5;
  padding: 16px 24px;
}

.tab-content {
  max-width: 1600px;
  margin: 0 auto;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.tab-content-kanban {
  min-height: 600px;
}

.tab-content-map {
  min-height: 600px;
}

/* Responsive Design */
@media (max-width: 1024px) {
  .app-header {
    padding: 12px 16px;
  }

  .header-content {
    gap: 12px;
  }

  .header-title {
    font-size: 20px;
  }

  .header-subtitle {
    font-size: 12px;
  }

  .app-content {
    padding: 12px 16px;
  }

  .tabs-container {
    padding: 0 16px;
  }

  .tabs-info {
    padding: 0 16px 8px 16px;
  }

  .app-tab {
    padding: 12px 16px;
    font-size: 13px;
  }
}

@media (max-width: 768px) {
  .app-container {
    height: auto;
    min-height: 100vh;
  }

  .app-header {
    padding: 12px;
  }

  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .header-title {
    font-size: 18px;
  }

  .header-subtitle {
    font-size: 11px;
  }

  .header-info {
    width: 100%;
    justify-content: space-between;
  }

  .system-mode-indicator {
    font-size: 10px;
  }

  .app-main {
    min-height: auto;
  }

  .app-content {
    padding: 8px;
    min-height: 400px;
  }

  .tabs-container {
    padding: 0 12px;
    gap: 0;
  }

  .app-tab {
    padding: 10px 12px;
    font-size: 12px;
    flex: 1;
    justify-content: center;
  }

  .tab-label {
    display: none;
  }

  .tab-icon {
    font-size: 18px;
  }

  .tabs-info {
    padding: 0 12px 6px 12px;
    display: none;
  }
}

@media (max-width: 480px) {
  .app-header {
    padding: 8px;
  }

  .header-title {
    font-size: 14px;
    gap: 6px;
  }

  .header-subtitle {
    display: none;
  }

  .header-content {
    gap: 4px;
  }

  .system-mode-badge {
    font-size: 10px;
    padding: 2px 6px;
  }

  .system-mode-label {
    font-size: 10px;
  }

  .app-content {
    padding: 4px;
    min-height: 300px;
  }

  .tabs-container {
    padding: 0 8px;
  }

  .app-tab {
    padding: 8px 6px;
    font-size: 11px;
  }

  .tab-content {
    min-height: auto;
  }
}

/* Scrollbar Styling */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
}

::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #888;
}

/* Print Styles */
@media print {
  .app-header,
  .app-tabs,
  .chat-toggle-btn {
    display: none;
  }

  .app-main {
    flex: none;
    height: auto;
  }

  .app-content {
    padding: 0;
  }
}
`

export default App

