import React, { useState, useEffect, useRef } from 'react'
import {
  fetchPlanningStatus,
  triggerAutoPlanning,
  triggerSync,
  fetchCuadrillas,
} from '../services/api'
import { toast } from 'react-toastify'
import './PlanningDashboard.css'

/**
 * Stat Card Component
 */
function StatCard({ label, value, unit = '' }) {
  return (
    <div className="stat-card">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {unit && <div className="stat-unit">{unit}</div>}
    </div>
  )
}

/**
 * Utilization Bar Component
 */
function UtilizationBar({ crew }) {
  const percentage = crew.utilization_percent || 0
  const getColor = (pct) => {
    if (pct >= 90) return '#f44336' // red
    if (pct >= 70) return '#ff9800' // orange
    if (pct >= 50) return '#fbc02d' // yellow
    return '#4caf50' // green
  }

  return (
    <div className="utilization-item">
      <div className="utilization-label">
        <span className="crew-name">{crew.crew_name}</span>
        <span className="utilization-percentage">{percentage.toFixed(1)}%</span>
      </div>
      <div className="utilization-bar">
        <div
          className="utilization-fill"
          style={{
            width: `${Math.min(percentage, 100)}%`,
            backgroundColor: getColor(percentage),
          }}
        />
      </div>
      <div className="utilization-details">
        <span>{crew.ots_assigned}/{crew.total_capacity} OTs</span>
        {crew.avg_distance_km && (
          <span className="avg-distance">⌀ {crew.avg_distance_km.toFixed(1)}km</span>
        )}
      </div>
    </div>
  )
}

/**
 * Status Distribution Component
 */
function StatusDistribution({ otsByStatus }) {
  const total = Object.values(otsByStatus).reduce((a, b) => a + b, 0)

  if (total === 0) {
    return (
      <div className="status-distribution">
        <p style={{ textAlign: 'center', color: '#999' }}>No OTs available</p>
      </div>
    )
  }

  const statusColors = {
    PREPLANIFICADA: '#9e9e9e',
    PLANIFICADA: '#2196f3',
    ASIGNADO_TAREA: '#4caf50',
    DETENIDA: '#ff9800',
    FINALIZADA: '#66bb6a',
    ANULADA: '#f44336',
  }

  return (
    <div className="status-distribution">
      <div className="status-bar">
        {Object.entries(otsByStatus).map(([status, count]) => (
          <div
            key={status}
            className="status-segment"
            style={{
              width: `${(count / total) * 100}%`,
              backgroundColor: statusColors[status],
              minWidth: count > 0 ? '20px' : '0px',
            }}
            title={`${status}: ${count}`}
          >
            {(count / total) * 100 > 5 && (
              <span className="status-label">{count}</span>
            )}
          </div>
        ))}
      </div>
      <div className="status-legend">
        {Object.entries(otsByStatus).map(([status, count]) => (
          <div key={status} className="legend-item">
            <div
              className="legend-color"
              style={{ backgroundColor: statusColors[status] }}
            />
            <span>{status}: {count}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/**
 * Main PlanningDashboard Component
 */
export default function PlanningDashboard() {
  // State management
  const [planningStatus, setPlanningStatus] = useState(null)
  const [cuadrillas, setCuadrillas] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshInterval, setRefreshInterval] = useState(30000) // 30 seconds
  const [autoRefresh, setAutoRefresh] = useState(true)
  const intervalRef = useRef(null)

  /**
   * Load planning status and cuadrillas
   */
  const loadPlanningData = async () => {
    try {
      const [statusData, cuadrillasData] = await Promise.all([
        fetchPlanningStatus(),
        fetchCuadrillas(),
      ])

      setPlanningStatus(statusData)
      setCuadrillas(Array.isArray(cuadrillasData) ? cuadrillasData : [])
    } catch (error) {
      console.error('Failed to load planning data:', error)
      toast.error('Failed to load planning data')
    } finally {
      setLoading(false)
    }
  }

  /**
   * Load data on mount and setup auto-refresh
   */
  useEffect(() => {
    loadPlanningData()

    // Setup auto-refresh interval
    if (autoRefresh) {
      intervalRef.current = setInterval(loadPlanningData, refreshInterval)
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [autoRefresh, refreshInterval])

  /**
   * Handle trigger auto planning
   */
  const handleAutoPlanning = async () => {
    try {
      setLoading(true)
      await triggerAutoPlanning()
      toast.success('Auto planning triggered successfully')
      await loadPlanningData()
    } catch (error) {
      console.error('Failed to trigger auto planning:', error)
      toast.error('Failed to trigger auto planning')
    } finally {
      setLoading(false)
    }
  }

  /**
   * Handle sync from TELCOS
   */
  const handleSync = async () => {
    try {
      setLoading(true)
      await triggerSync()
      toast.success('Sync from TELCOS triggered successfully')
      await loadPlanningData()
    } catch (error) {
      console.error('Failed to sync from TELCOS:', error)
      toast.error('Failed to sync from TELCOS')
    } finally {
      setLoading(false)
    }
  }

  /**
   * Handle manual refresh
   */
  const handleRefresh = async () => {
    try {
      setLoading(true)
      await loadPlanningData()
      toast.info('Planning data refreshed')
    } catch (error) {
      toast.error('Failed to refresh data')
    } finally {
      setLoading(false)
    }
  }

  /**
   * Export planning data to CSV
   */
  const handleExportCSV = () => {
    if (!planningStatus) {
      toast.warn('No data to export')
      return
    }

    // Create CSV content
    const rows = [
      ['PEI Agéntico Planning Report'],
      ['Generated:', new Date().toLocaleString()],
      [],
      ['OT Status Summary'],
      ['Status', 'Count'],
    ]

    Object.entries(planningStatus.ots_by_status || {}).forEach(([status, count]) => {
      rows.push([status, count])
    })

    rows.push([])
    rows.push(['Crew Utilization'])
    rows.push(['Crew Name', 'Assigned', 'Capacity', 'Utilization %', 'Avg Distance km'])

    planningStatus.crew_utilization?.forEach((crew) => {
      rows.push([
        crew.crew_name,
        crew.ots_assigned,
        crew.total_capacity,
        crew.utilization_percent.toFixed(1),
        crew.avg_distance_km ? crew.avg_distance_km.toFixed(2) : 'N/A',
      ])
    })

    // Convert to CSV string
    const csv = rows.map((row) => row.map((cell) => `"${cell}"`).join(',')).join('\n')

    // Create download link
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `pei-planning-${new Date().toISOString().split('T')[0]}.csv`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)

    toast.success('Planning data exported to CSV')
  }

  if (loading && !planningStatus) {
    return (
      <div className="dashboard-container">
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <div className="spinner"></div>
          <p>Loading planning dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard-container">
      {/* Header */}
      <div className="dashboard-header">
        <h1>📈 Planning Dashboard</h1>
        <div className="dashboard-actions">
          <button
            onClick={handleSync}
            className="btn btn-secondary"
            disabled={loading}
          >
            🔄 Sync TELCOS
          </button>
          <button
            onClick={handleAutoPlanning}
            className="btn btn-primary"
            disabled={loading}
          >
            ⚙️ Auto Plan
          </button>
          <button
            onClick={handleRefresh}
            className="btn btn-secondary"
            disabled={loading}
          >
            🔄 Refresh
          </button>
          <button
            onClick={handleExportCSV}
            className="btn btn-secondary"
            disabled={loading || !planningStatus}
          >
            📥 Export CSV
          </button>
        </div>
      </div>

      {/* Statistics Grid */}
      {planningStatus && (
        <>
          <div className="stats-grid">
            <StatCard
              label="Total OTs"
              value={planningStatus.total_ots}
            />
            <StatCard
              label="Assigned OTs"
              value={planningStatus.total_ots - planningStatus.pending_ots}
            />
            <StatCard
              label="Pending OTs"
              value={planningStatus.pending_ots}
            />
            <StatCard
              label="Active Crews"
              value={planningStatus.crew_utilization?.length || 0}
            />
            <StatCard
              label="Total Assignments"
              value={planningStatus.total_assignments}
            />
            <StatCard
              label="Avg Crew Utilization"
              value={
                planningStatus.crew_utilization?.length > 0
                  ? (
                      planningStatus.crew_utilization.reduce(
                        (sum, crew) => sum + crew.utilization_percent,
                        0
                      ) / planningStatus.crew_utilization.length
                    ).toFixed(1)
                  : 0
              }
              unit="%"
            />
          </div>

          {/* OT Status Distribution */}
          <div className="dashboard-section">
            <h2>OT Status Distribution</h2>
            <StatusDistribution otsByStatus={planningStatus.ots_by_status || {}} />
          </div>

          {/* Crew Utilization */}
          <div className="dashboard-section">
            <h2>Crew Utilization</h2>
            {planningStatus.crew_utilization && planningStatus.crew_utilization.length > 0 ? (
              <div className="utilization-bars">
                {planningStatus.crew_utilization.map((crew, index) => (
                  <UtilizationBar key={index} crew={crew} />
                ))}
              </div>
            ) : (
              <p style={{ textAlign: 'center', color: '#999' }}>No crews available</p>
            )}
          </div>

          {/* Auto-Refresh Controls */}
          <div className="dashboard-section refresh-controls">
            <label>
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
              Auto-refresh every {refreshInterval / 1000}s
            </label>
            <select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(parseInt(e.target.value))}
              disabled={!autoRefresh}
              className="refresh-interval-select"
            >
              <option value={10000}>10 seconds</option>
              <option value={30000}>30 seconds</option>
              <option value={60000}>1 minute</option>
              <option value={300000}>5 minutes</option>
            </select>
          </div>

          {/* Last Updated */}
          <div className="dashboard-footer">
            <p>
              Last updated: {new Date().toLocaleTimeString()}
              {autoRefresh && ' (auto-refresh enabled)'}
            </p>
          </div>
        </>
      )}
    </div>
  )
}

