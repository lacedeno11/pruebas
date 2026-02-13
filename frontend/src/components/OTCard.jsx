import React, { useState } from 'react'
import { useDraggable } from '@dnd-kit/core'
import { formatRelativeTime, getProjectTypeColor, getProjectTypeBgColor } from '../services/api'
import './OTCard.css'

/**
 * Detail Modal Component
 */
function OTDetailModal({ ot, onClose }) {
  if (!ot) return null

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>OT Details - {ot.external_id}</h2>
          <button className="modal-close" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="modal-body">
          <div className="detail-section">
            <h3>Basic Information</h3>
            <div className="detail-row">
              <label>External ID:</label>
              <span>{ot.external_id}</span>
            </div>
            <div className="detail-row">
              <label>Status:</label>
              <span className="badge" style={{ backgroundColor: getStatusColor(ot.status) }}>
                {ot.status}
              </span>
            </div>
            <div className="detail-row">
              <label>Project Type:</label>
              <span
                className="project-badge"
                style={{
                  backgroundColor: getProjectTypeBgColor(ot.project_type),
                  color: getProjectTypeColor(ot.project_type),
                }}
              >
                {ot.project_type}
              </span>
            </div>
          </div>

          <div className="detail-section">
            <h3>Client Information</h3>
            <div className="detail-row">
              <label>Client ID:</label>
              <span>{ot.cliente_id || 'N/A'}</span>
            </div>
            <div className="detail-row">
              <label>Login:</label>
              <span>{ot.login || 'N/A'}</span>
            </div>
          </div>

          <div className="detail-section">
            <h3>Location</h3>
            <div className="detail-row">
              <label>Latitude:</label>
              <span>{ot.lat?.toFixed(6) || 'N/A'}</span>
            </div>
            <div className="detail-row">
              <label>Longitude:</label>
              <span>{ot.long?.toFixed(6) || 'N/A'}</span>
            </div>
            {ot.error_geo && (
              <div className="detail-row error">
                <span>⚠️ Geographic coordinates are invalid</span>
              </div>
            )}
          </div>

          <div className="detail-section">
            <h3>Assignment</h3>
            <div className="detail-row">
              <label>Assigned Crew:</label>
              <span>{ot.cuadrilla?.name || 'Unassigned'}</span>
            </div>
          </div>

          <div className="detail-section">
            <h3>Timeline</h3>
            <div className="detail-row">
              <label>Created:</label>
              <span title={ot.created_at}>{formatRelativeTime(ot.created_at)}</span>
            </div>
            <div className="detail-row">
              <label>Last Updated:</label>
              <span title={ot.updated_at}>{formatRelativeTime(ot.updated_at)}</span>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button onClick={onClose} className="btn btn-secondary">
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

/**
 * OT Card Component
 * Represents a single work order in the Kanban board
 */
export default function OTCard({ ot }) {
  const [showDetailModal, setShowDetailModal] = useState(false)

  // Setup drag functionality
  const { attributes, listeners, setNodeRef, isDragging, transform } = useDraggable({
    id: ot.id,
  })

  // Get status color (matching column colors)
  const getStatusColor = (status) => {
    const statusColors = {
      PREPLANIFICADA: '#9e9e9e',
      PLANIFICADA: '#2196f3',
      ASIGNADO_TAREA: '#4caf50',
      DETENIDA: '#ff9800',
      FINALIZADA: '#66bb6a',
      ANULADA: '#f44336',
    }
    return statusColors[status] || '#757575'
  }

  // Get project type color
  const projectTypeColor = getProjectTypeColor(ot.project_type)

  // Calculate relative time
  const createdTime = formatRelativeTime(ot.created_at)

  // Style for drag transform
  const style = transform
    ? {
        transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
        opacity: isDragging ? 0.5 : 1,
      }
    : {}

  return (
    <>
      <div
        ref={setNodeRef}
        className={`ot-card ${isDragging ? 'ot-card-dragging' : ''}`}
        style={{
          ...style,
          borderLeftColor: getStatusColor(ot.status),
        }}
        {...attributes}
        {...listeners}
        onClick={() => setShowDetailModal(true)}
      >
        {/* Card Header */}
        <div className="ot-card-header">
          <div className="ot-id">{ot.external_id}</div>
          {ot.error_geo && <span className="error-geo-icon" title="Geographic error">⚠️</span>}
        </div>

        {/* Project Type Badge */}
        <div className="ot-card-badges">
          <span
            className="project-badge"
            style={{
              backgroundColor: getProjectTypeBgColor(ot.project_type),
              color: projectTypeColor,
            }}
          >
            {ot.project_type}
          </span>
        </div>

        {/* Card Info */}
        <div className="ot-card-info">
          {ot.cliente_id && (
            <div className="info-row">
              <span className="info-label">Client:</span>
              <span className="info-value">{ot.cliente_id}</span>
            </div>
          )}

          {ot.login && (
            <div className="info-row">
              <span className="info-label">Login:</span>
              <span className="info-value">{ot.login}</span>
            </div>
          )}

          {ot.cuadrilla && (
            <div className="info-row">
              <span className="info-label">Crew:</span>
              <span className="info-value crew-name">{ot.cuadrilla.name}</span>
            </div>
          )}

          <div className="info-row">
            <span className="info-label">Created:</span>
            <span className="info-value">{createdTime}</span>
          </div>
        </div>

        {/* Click hint */}
        <div className="ot-card-hint">Click for details</div>
      </div>

      {/* Detail Modal */}
      {showDetailModal && (
        <OTDetailModal ot={ot} onClose={() => setShowDetailModal(false)} />
      )}
    </>
  )
}

