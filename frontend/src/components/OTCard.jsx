import React from 'react'
import { useDraggable } from '@dnd-kit/core'
import { OTStatus, ProjectType, StatusColors, ProjectTypeColors } from '../types/index'

export function OTCard({ ot }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: ot.id,
    data: ot
  })

  const style = {
    transform: transform ? `translate3d(${transform.x}px, ${transform.y}px, 0)` : undefined,
    opacity: isDragging ? 0.5 : 1,
    cursor: isDragging ? 'grabbing' : 'grab'
  }

  const statusColor = StatusColors[ot.status] || '#888888'
  const projectTypeColor = ProjectTypeColors[ot.project_type] || '#888888'

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="ot-card"
      data-ot-id={ot.id}
    >
      <div className="ot-card-header">
        <h3 className="ot-card-title">{ot.external_id}</h3>
        <button
          className="ot-card-close"
          onClick={(e) => e.stopPropagation()}
          aria-label="Close"
        >
          ×
        </button>
      </div>

      <div className="ot-card-content">
        {/* Cliente ID */}
        <div className="ot-card-field">
          <span className="ot-card-label">Cliente:</span>
          <span className="ot-card-value">{ot.cliente_id}</span>
        </div>

        {/* Status Badge */}
        <div className="ot-card-field">
          <span
            className="ot-card-badge ot-card-status-badge"
            style={{ backgroundColor: statusColor }}
          >
            {ot.status}
          </span>
        </div>

        {/* Project Type Badge */}
        <div className="ot-card-field">
          <span
            className="ot-card-badge ot-card-type-badge"
            style={{ backgroundColor: projectTypeColor }}
          >
            {ot.project_type}
          </span>
        </div>

        {/* Location Information */}
        <div className="ot-card-field">
          {ot.error_geo ? (
            <span className="ot-card-badge ot-card-error-badge">
              ⚠️ ERROR_GEO
            </span>
          ) : ot.lat && ot.long ? (
            <span className="ot-card-location">
              📍 {ot.lat.toFixed(4)}, {ot.long.toFixed(4)}
            </span>
          ) : (
            <span className="ot-card-badge ot-card-warning-badge">
              No Location
            </span>
          )}
        </div>

        {/* Cuadrilla Assignment */}
        {ot.cuadrilla_id ? (
          <div className="ot-card-field">
            <span className="ot-card-label">Cuadrilla ID:</span>
            <span className="ot-card-value ot-card-cuadrilla">
              {ot.cuadrilla_id}
            </span>
          </div>
        ) : (
          <div className="ot-card-field">
            <span className="ot-card-badge ot-card-unassigned-badge">
              Unassigned
            </span>
          </div>
        )}

        {/* Metadata */}
        <div className="ot-card-metadata">
          <small className="ot-card-timestamp">
            Created: {new Date(ot.created_at).toLocaleDateString()}
          </small>
        </div>
      </div>
    </div>
  )
}

const otCardStyles = `
.ot-card {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;
  user-select: none;
  touch-action: none;
}

.ot-card:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.ot-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  border-bottom: 2px solid #f0f0f0;
  padding-bottom: 8px;
}

.ot-card-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #333;
  flex: 1;
}

.ot-card-close {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #999;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ot-card-close:hover {
  color: #d32f2f;
}

.ot-card-content {
  font-size: 12px;
}

.ot-card-field {
  display: flex;
  align-items: center;
  margin-bottom: 6px;
  gap: 6px;
  flex-wrap: wrap;
}

.ot-card-label {
  font-weight: 600;
  color: #666;
  min-width: 60px;
}

.ot-card-value {
  color: #333;
  word-break: break-word;
}

.ot-card-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  color: white;
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.ot-card-status-badge {
  flex: 1;
  text-align: center;
}

.ot-card-type-badge {
  flex: 0 0 auto;
}

.ot-card-error-badge {
  background-color: #d32f2f !important;
  color: white;
  font-weight: 600;
}

.ot-card-warning-badge {
  background-color: #f57c00 !important;
  color: white;
}

.ot-card-unassigned-badge {
  background-color: #9c27b0 !important;
  color: white;
}

.ot-card-location {
  color: #0066cc;
  font-family: monospace;
  font-size: 11px;
}

.ot-card-cuadrilla {
  background-color: #e3f2fd;
  padding: 2px 6px;
  border-radius: 3px;
  color: #1565c0;
  font-weight: 600;
}

.ot-card-metadata {
  display: flex;
  justify-content: space-between;
  padding-top: 6px;
  border-top: 1px solid #f0f0f0;
  margin-top: 6px;
}

.ot-card-timestamp {
  color: #999;
  font-size: 10px;
}

@media (max-width: 768px) {
  .ot-card {
    padding: 10px;
    margin-bottom: 6px;
  }

  .ot-card-title {
    font-size: 12px;
  }

  .ot-card-content {
    font-size: 11px;
  }

  .ot-card-badge {
    font-size: 10px;
    padding: 3px 6px;
  }
}
`

export default OTCard

