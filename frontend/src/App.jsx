import React, { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Link, Outlet } from 'react-router-dom'
import { fetchSystemInfo } from './services/api'
import KanbanBoard from './components/KanbanBoard'
import MapView from './components/MapView'
import AgentChat from './components/AgentChat'
import PlanningDashboard from './components/PlanningDashboard'
import './App.css'

/**
 * Navigation Layout Component
 * Provides header with navigation links and system info
 */
function NavLayout() {
  const [systemInfo, setSystemInfo] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadSystemInfo = async () => {
      try {
        const info = await fetchSystemInfo()
        setSystemInfo(info)
      } catch (error) {
        console.error('Failed to fetch system info:', error)
      } finally {
        setLoading(false)
      }
    }

    loadSystemInfo()
  }, [])

  return (
    <div className="app-container">
      <nav className="app-header">
        <div className="nav-brand">
          <h1 className="nav-logo">🚀 PEI Agéntico</h1>
          <span className="nav-subtitle">Work Order Management</span>
        </div>

        <div className="nav-links">
          <Link to="/" className="nav-link">
            📊 Dashboard
          </Link>
          <Link to="/map" className="nav-link">
            🗺️ Map
          </Link>
          <Link to="/chat" className="nav-link">
            💬 Chat
          </Link>
          <Link to="/planning" className="nav-link">
            📈 Planning
          </Link>
        </div>

        <div className="nav-status">
          {!loading && systemInfo && (
            <>
              <span
                className={`system-badge ${systemInfo.mode === 'MOCK' ? 'badge-warning' : 'badge-success'}`}
              >
                {systemInfo.mode === 'MOCK' ? '🔧 Mock Mode' : '✅ Production'}
              </span>
              <span className="system-version">v{systemInfo.version}</span>
            </>
          )}
          {loading && <span className="spinner"></span>}
        </div>
      </nav>

      <main className="app-main">
        <Outlet />
      </main>

      <footer className="app-footer">
        <p>&copy; 2024 PEI Agéntico - LangGraph-based Work Order Management</p>
      </footer>
    </div>
  )
}

/**
 * Main App Component
 * Sets up routing and provides the layout structure
 */
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<NavLayout />}>
          {/* Dashboard with Kanban Board */}
          <Route path="/" element={<KanbanBoard />} />

          {/* Map View */}
          <Route path="/map" element={<MapView />} />

          {/* Agent Chat */}
          <Route path="/chat" element={<AgentChat />} />

          {/* Planning Dashboard */}
          <Route path="/planning" element={<PlanningDashboard />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

