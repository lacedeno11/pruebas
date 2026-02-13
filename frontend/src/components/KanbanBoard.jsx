import React, { useState, useEffect, useRef } from 'react'
import {
  DndContext,
  DragOverlay,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import { useDraggable, useDroppable } from '@dnd-kit/core'
import OTCard from './OTCard'
import { fetchOTs, updateOTStatus, validateTransition, validateDocuments } from '../services/api'
import { toast } from 'react-toastify'
import './KanbanBoard.css'

// Status columns configuration
const STATUS_COLUMNS = [
  { status: 'PREPLANIFICADA', label: 'Por Planificar', color: '#9e9e9e' },
  { status: 'PLANIFICADA', label: 'Planificada', color: '#2196f3' },
  { status: 'ASIGNADO_TAREA', label: 'Asignada', color: '#4caf50' },
  { status: 'DETENIDA', label: 'Detenida', color: '#ff9800' },
  { status: 'FINALIZADA', label: 'Finalizada', color: '#66bb6a' },
  { status: 'ANULADA', label: 'Anulada', color: '#f44336' },
]

/**
 * Column Component - Represents a Kanban column
 */
function KanbanColumn({ column, ots, isDragOver, isLoading }) {
  const { setNodeRef } = useDroppable({
    id: column.status,
  })

  return (
    <div
      ref={setNodeRef}
      className="kanban-column"
      style={{ borderTopColor: column.color }}
    >
      <div className="kanban-column-header">
        <h3>{column.label}</h3>
        <span className="kanban-column-count" style={{ backgroundColor: column.color }}>
          {ots.length}
        </span>
      </div>

      <div
        className={`kanban-column-dropzone ${isDragOver ? 'drag-over' : ''}`}
        style={isDragOver ? { borderColor: column.color } : {}}
      >
        {ots.length === 0 && !isLoading && (
          <div className="kanban-empty-state">
            <p>No hay OTs en esta columna</p>
          </div>
        )}

        {isLoading && (
          <div className="kanban-loading-state">
            <div className="spinner"></div>
          </div>
        )}

        {ots.map((ot) => (
          <OTCard key={ot.id} ot={ot} />
        ))}
      </div>
    </div>
  )
}

/**
 * Main KanbanBoard Component
 */
export default function KanbanBoard() {
  // State management
  const [ots, setOts] = useState([])
  const [loading, setLoading] = useState(true)
  const [draggingId, setDraggingId] = useState(null)
  const [dragOverColumn, setDragOverColumn] = useState(null)
  const [filterProjectType, setFilterProjectType] = useState('ALL')
  const [searchOtId, setSearchOtId] = useState('')
  const [showReasonModal, setShowReasonModal] = useState(false)
  const [reasonText, setReasonText] = useState('')
  const [pendingTransition, setPendingTransition] = useState(null)

  // Refs for modal management
  const reasonModalRef = useRef(null)

  // Setup sensors for drag detection
  const sensors = useSensors(
    useSensor(PointerSensor, {
      distance: 8,
    })
  )

  /**
   * Fetch OTs from API
   */
  const loadOTs = async () => {
    try {
      setLoading(true)
      const filters = {
        limit: 100,
        offset: 0,
      }

      if (filterProjectType !== 'ALL') {
        filters.projectType = filterProjectType
      }

      const data = await fetchOTs(filters)
      setOts(Array.isArray(data) ? data : [])
    } catch (error) {
      console.error('Failed to load OTs:', error)
      toast.error('Failed to load OTs')
      setOts([])
    } finally {
      setLoading(false)
    }
  }

  /**
   * Load OTs on mount and when filters change
   */
  useEffect(() => {
    loadOTs()
  }, [filterProjectType])

  /**
   * Group OTs by status
   */
  const otsByStatus = STATUS_COLUMNS.reduce((acc, column) => {
    const columnOts = ots.filter((ot) => ot.status === column.status)

    // Apply search filter
    if (searchOtId) {
      const filtered = columnOts.filter((ot) =>
        ot.external_id.toLowerCase().includes(searchOtId.toLowerCase())
      )
      acc[column.status] = filtered
    } else {
      acc[column.status] = columnOts
    }

    return acc
  }, {})

  /**
   * Handle drag start
   */
  const handleDragStart = (event) => {
    setDraggingId(event.active.id)
  }

  /**
   * Handle drag over (column highlighting)
   */
  const handleDragOver = (event) => {
    const { over } = event
    setDragOverColumn(over?.id || null)
  }

  /**
   * Handle drag end - perform status update
   */
  const handleDragEnd = async (event) => {
    const { active, over } = event
    setDraggingId(null)
    setDragOverColumn(null)

    if (!over || active.id === over.id) {
      return
    }

    const ot = ots.find((o) => o.id === active.id)
    if (!ot) {
      return
    }

    const toStatus = over.id
    const fromStatus = ot.status

    // If target is DETENIDA, show modal to collect reason
    if (toStatus === 'DETENIDA') {
      setPendingTransition({ ot, fromStatus, toStatus })
      setShowReasonModal(true)
      return
    }

    // If source is PUBLICO and target is FINALIZADA, validate documents
    if (ot.project_type === 'PUBLICO' && toStatus === 'FINALIZADA') {
      try {
        const docValidation = await validateDocuments(ot.id)
        if (!docValidation.is_valid) {
          toast.error(
            `Cannot finalize: ${docValidation.error_message || 'Document requirements not met'}`
          )
          return
        }
      } catch (error) {
        toast.error('Failed to validate documents')
        return
      }
    }

    // Validate transition
    try {
      const validation = await validateTransition(
        ot.id,
        fromStatus,
        toStatus,
        ot.project_type
      )

      if (!validation.valid) {
        toast.error(`Cannot change status: ${validation.error_message}`)
        return
      }

      // Show warnings
      if (validation.warnings && validation.warnings.length > 0) {
        validation.warnings.forEach((warning) => {
          toast.warn(warning)
        })
      }

      // Perform update
      await performStatusUpdate(ot, toStatus, null)
    } catch (error) {
      toast.error('Validation failed: ' + error.message)
    }
  }

  /**
   * Perform the actual status update
   */
  const performStatusUpdate = async (ot, toStatus, reason) => {
    try {
      // Show loading on card
      setDraggingId(ot.id)

      // Update status via API
      const updated = await updateOTStatus(ot.id, toStatus, reason)

      // Update local state
      setOts((prevOts) =>
        prevOts.map((o) => (o.id === ot.id ? { ...o, status: toStatus } : o))
      )

      toast.success(`OT ${ot.external_id} moved to ${toStatus}`)
    } catch (error) {
      // Revert on error
      toast.error(`Failed to update OT: ${error.message || error}`)
    } finally {
      setDraggingId(null)
    }
  }

  /**
   * Handle reason modal submit
   */
  const handleReasonSubmit = async () => {
    if (!reasonText.trim()) {
      toast.warn('Please provide a reason for stopping')
      return
    }

    if (!pendingTransition) {
      return
    }

    const { ot, toStatus } = pendingTransition

    try {
      // Validate transition first
      const validation = await validateTransition(
        ot.id,
        ot.status,
        toStatus,
        ot.project_type
      )

      if (!validation.valid) {
        toast.error(`Cannot change status: ${validation.error_message}`)
        return
      }

      // Perform update with reason
      await performStatusUpdate(ot, toStatus, reasonText)

      // Close modal
      setShowReasonModal(false)
      setReasonText('')
      setPendingTransition(null)
    } catch (error) {
      toast.error('Failed to update OT: ' + error.message)
    }
  }

  /**
   * Handle reason modal cancel
   */
  const handleReasonCancel = () => {
    setShowReasonModal(false)
    setReasonText('')
    setPendingTransition(null)
  }

  /**
   * Handle refresh button
   */
  const handleRefresh = () => {
    loadOTs()
    toast.info('OTs refreshed')
  }

  return (
    <div className="kanban-container">
      {/* Controls */}
      <div className="kanban-controls">
        <div className="controls-left">
          <input
            type="text"
            placeholder="Search OT ID..."
            value={searchOtId}
            onChange={(e) => setSearchOtId(e.target.value)}
            className="search-input"
          />

          <select
            value={filterProjectType}
            onChange={(e) => setFilterProjectType(e.target.value)}
            className="filter-select"
          >
            <option value="ALL">All Projects</option>
            <option value="PUBLICO">PÚBLICO</option>
            <option value="PRIVADO">PRIVADO</option>
            <option value="TERCERIZADO">TERCERIZADO</option>
          </select>
        </div>

        <button onClick={handleRefresh} className="btn btn-primary">
          🔄 Refresh
        </button>
      </div>

      {/* Kanban Board */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
      >
        <div className="kanban-board">
          {STATUS_COLUMNS.map((column) => (
            <KanbanColumn
              key={column.status}
              column={column}
              ots={otsByStatus[column.status] || []}
              isDragOver={dragOverColumn === column.status}
              isLoading={loading && draggingId === null}
            />
          ))}
        </div>

        <DragOverlay>
          {draggingId ? (
            <div className="ot-card-dragging">
              <div className="spinner"></div>
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>

      {/* Reason Modal for DETENIDA */}
      {showReasonModal && (
        <div className="modal-backdrop" onClick={handleReasonCancel}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Why is the OT being stopped?</h2>
              <button className="modal-close" onClick={handleReasonCancel}>
                ✕
              </button>
            </div>

            <div className="modal-body">
              <p>Please provide a reason for stopping OT {pendingTransition?.ot?.external_id}:</p>
              <textarea
                value={reasonText}
                onChange={(e) => setReasonText(e.target.value)}
                placeholder="Enter reason (e.g., waiting for materials, client request, etc.)"
                className="reason-textarea"
                autoFocus
              />
            </div>

            <div className="modal-footer">
              <button onClick={handleReasonCancel} className="btn btn-secondary">
                Cancel
              </button>
              <button onClick={handleReasonSubmit} className="btn btn-warning">
                Stop OT
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

