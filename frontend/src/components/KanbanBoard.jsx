import React, { useState, useEffect, useMemo } from 'react'
import {
  DndContext,
  DragOverlay,
  closestCorners,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable
} from '@dnd-kit/core'
import {
  SortableContext,
  verticalListSortingStrategy,
  arrayMove
} from '@dnd-kit/sortable'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'react-toastify'
import OTCard from './OTCard'
import { useDragDrop } from '../hooks'
import { fetchOTs, updateOTStatus } from '../services/api'
import { OTStatus, StatusColors } from '../types/index'

const STATUSES = [
  OTStatus.PREPLANIFICADA,
  OTStatus.PLANIFICADA,
  OTStatus.ASIGNADO_TAREA,
  OTStatus.DETENIDA,
  OTStatus.ANULADA,
  OTStatus.FINALIZADA
]

export function KanbanBoard() {
  const [otsData, setOtsData] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [showDetencionModal, setShowDetencionModal] = useState(false)
  const [selectedOTForDetention, setSelectedOTForDetention] = useState(null)

  // Fetch OTs using React Query
  const {
    data: fetchedOTs = [],
    isLoading,
    error,
    refetch
  } = useQuery({
    queryKey: ['ots'],
    queryFn: () => fetchOTs({}),
    refetchInterval: 30000,
    staleTime: 30000
  })

  // Update local state when data is fetched
  useEffect(() => {
    if (fetchedOTs && Array.isArray(fetchedOTs)) {
      setOtsData(fetchedOTs)
    }
  }, [fetchedOTs])

  // Setup drag and drop sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      distance: 8
    })
  )

  // Group OTs by status
  const groupedOTs = useMemo(() => {
    const grouped = {}
    STATUSES.forEach(status => {
      grouped[status] = otsData.filter(ot => ot.status === status)
    })
    return grouped
  }, [otsData])

  // Handle drag start
  const handleDragStart = (event) => {
    setActiveId(event.active.id)
  }

  // Handle drag over
  const handleDragOver = (event) => {
    const { active, over } = event
    if (!over) return

    const activeStatus = active.data.current?.status
    const overStatus = over.data.current?.status || over.id

    if (activeStatus === overStatus && activeStatus === STATUSES[4]) {
      // DETENIDA status - show modal for reason
      setSelectedOTForDetention(active.data.current)
      setShowDetencionModal(true)
    }
  }

  // Handle drag end
  const handleDragEnd = async (event) => {
    setActiveId(null)
    const { active, over } = event

    if (!over) return

    const activeOT = active.data.current
    const overStatus = over.data.current?.status || over.id

    // Check if we're moving to DETENIDA status
    if (overStatus === OTStatus.DETENIDA && activeOT.status !== OTStatus.DETENIDA) {
      setSelectedOTForDetention(activeOT)
      setShowDetencionModal(true)
      return
    }

    // Update OT status
    if (activeOT.status !== overStatus) {
      try {
        // Optimistic update
        const updatedOTs = otsData.map(ot =>
          ot.id === activeOT.id ? { ...ot, status: overStatus } : ot
        )
        setOtsData(updatedOTs)

        // Call API to persist changes
        await updateOTStatus(activeOT.id, overStatus)
        toast.success(`OT ${activeOT.external_id} moved to ${overStatus}`)
        refetch()
      } catch (err) {
        // Rollback on error
        setOtsData(otsData)
        toast.error(`Failed to update OT: ${err.message}`)
      }
    }
  }

  // Handle detention modal submission
  const handleDetencionSubmit = async (reason) => {
    if (!selectedOTForDetention) return

    try {
      const metadata = { reason, timestamp: new Date().toISOString() }
      await updateOTStatus(selectedOTForDetention.id, OTStatus.DETENIDA, metadata)

      // Update local state
      const updatedOTs = otsData.map(ot =>
        ot.id === selectedOTForDetention.id
          ? { ...ot, status: OTStatus.DETENIDA }
          : ot
      )
      setOtsData(updatedOTs)

      toast.success(`OT ${selectedOTForDetention.external_id} marked as DETENIDA`)
      setShowDetencionModal(false)
      setSelectedOTForDetention(null)
      refetch()
    } catch (err) {
      toast.error(`Failed to mark OT as detained: ${err.message}`)
    }
  }

  if (error) {
    return (
      <div className="kanban-error">
        <p>Error loading OTs: {error.message}</p>
        <button onClick={() => refetch()}>Retry</button>
      </div>
    )
  }

  return (
    <div className="kanban-board-container">
      <div className="kanban-header">
        <h2>Work Order Board (Kanban)</h2>
        <div className="kanban-controls">
          <button
            className="kanban-refresh-btn"
            onClick={() => refetch()}
            disabled={isLoading}
          >
            {isLoading ? '⟳ Loading...' : '⟳ Refresh'}
          </button>
          <span className="kanban-total">
            Total OTs: {otsData.length}
          </span>
        </div>
      </div>

      {isLoading && otsData.length === 0 ? (
        <div className="kanban-loading">
          <div className="spinner"></div>
          <p>Loading work orders...</p>
        </div>
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
        >
          <div className="kanban-columns">
            {STATUSES.map(status => (
              <KanbanColumn
                key={status}
                status={status}
                ots={groupedOTs[status] || []}
                activeId={activeId}
                showDetencionModal={showDetencionModal}
                selectedOT={selectedOTForDetention}
                onDetencionSubmit={handleDetencionSubmit}
                onDetencionClose={() => {
                  setShowDetencionModal(false)
                  setSelectedOTForDetention(null)
                }}
              />
            ))}
          </div>
          <DragOverlay>
            {activeId && otsData.find(ot => ot.id === activeId) && (
              <OTCard ot={otsData.find(ot => ot.id === activeId)} />
            )}
          </DragOverlay>
        </DndContext>
      )}
    </div>
  )
}

// KanbanColumn component
function KanbanColumn({
  status,
  ots,
  activeId,
  showDetencionModal,
  selectedOT,
  onDetencionSubmit,
  onDetencionClose
}) {
  const { setNodeRef } = useDroppable({
    id: status,
    data: { status }
  })

  const statusColor = StatusColors[status] || '#888888'

  return (
    <div
      className="kanban-column"
      ref={setNodeRef}
      data-status={status}
    >
      <div className="kanban-column-header">
        <div
          className="kanban-column-title"
          style={{ borderColor: statusColor }}
        >
          <span className="kanban-column-status">{status}</span>
          <span className="kanban-column-count">{ots.length}</span>
        </div>
      </div>

      <SortableContext
        items={ots.map(ot => ot.id)}
        strategy={verticalListSortingStrategy}
      >
        <div className="kanban-column-content">
          {ots.length === 0 ? (
            <div className="kanban-empty-state">
              <p>No work orders</p>
            </div>
          ) : (
            ots.map(ot => (
              <div
                key={ot.id}
                className={`kanban-card-wrapper ${activeId === ot.id ? 'dragging' : ''}`}
              >
                <OTCard ot={ot} />
              </div>
            ))
          )}
        </div>
      </SortableContext>

      {/* DetencionModal for DETENIDA column */}
      {status === OTStatus.DETENIDA && showDetencionModal && selectedOT && (
        <DetencionModal
          isOpen={true}
          otId={selectedOT.id}
          externalId={selectedOT.external_id}
          onClose={onDetencionClose}
          onSubmit={onDetencionSubmit}
        />
      )}
    </div>
  )
}

// DetencionModal component (embedded in KanbanBoard for simplicity)
function DetencionModal({ isOpen, otId, externalId, onClose, onSubmit }) {
  const [reason, setReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!reason.trim()) {
      toast.error('Please provide a reason for detention')
      return
    }

    setIsSubmitting(true)
    try {
      await onSubmit(reason)
    } finally {
      setIsSubmitting(false)
      setReason('')
    }
  }

  if (!isOpen) return null

  return (
    <div className="detention-modal-overlay" onClick={onClose}>
      <div
        className="detention-modal-content"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="detention-modal-header">
          <h3>Mark as Detained</h3>
          <button
            className="detention-modal-close"
            onClick={onClose}
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="detention-modal-body">
          <p className="detention-ot-id">
            OT: <strong>{externalId}</strong>
          </p>
          <label htmlFor="detention-reason">Reason for detention:</label>
          <textarea
            id="detention-reason"
            className="detention-textarea"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Enter the reason for marking this OT as detained..."
            rows="5"
          />
        </div>

        <div className="detention-modal-footer">
          <button
            className="detention-btn detention-btn-cancel"
            onClick={onClose}
            disabled={isSubmitting}
          >
            Cancel
          </button>
          <button
            className="detention-btn detention-btn-submit"
            onClick={handleSubmit}
            disabled={isSubmitting || !reason.trim()}
          >
            {isSubmitting ? 'Submitting...' : 'Mark as Detained'}
          </button>
        </div>
      </div>
    </div>
  )
}

// Kanban Board Styles
const kanbanStyles = `
.kanban-board-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #f5f5f5;
  border-radius: 8px;
  overflow: hidden;
}

.kanban-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background-color: white;
  border-bottom: 2px solid #e0e0e0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.kanban-header h2 {
  margin: 0;
  font-size: 20px;
  color: #333;
}

.kanban-controls {
  display: flex;
  gap: 12px;
  align-items: center;
}

.kanban-refresh-btn {
  padding: 8px 16px;
  background-color: #2196F3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  transition: background-color 0.2s;
}

.kanban-refresh-btn:hover:not(:disabled) {
  background-color: #1976D2;
}

.kanban-refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.kanban-total {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.kanban-loading {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 400px;
  gap: 16px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #2196F3;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.kanban-columns {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
  padding: 16px;
  overflow-x: auto;
  flex: 1;
}

.kanban-column {
  display: flex;
  flex-direction: column;
  background-color: #fafafa;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  overflow: hidden;
  height: fit-content;
  min-height: 400px;
}

.kanban-column-header {
  padding: 12px;
  background-color: white;
  border-bottom: 2px solid #e0e0e0;
}

.kanban-column-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 8px;
  border-left: 4px solid #888;
}

.kanban-column-status {
  font-weight: 600;
  font-size: 13px;
  text-transform: uppercase;
  color: #333;
  flex: 1;
}

.kanban-column-count {
  background-color: #f0f0f0;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  color: #666;
  font-weight: 600;
}

.kanban-column-content {
  flex: 1;
  padding: 8px;
  overflow-y: auto;
  background-color: #fafafa;
}

.kanban-empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 300px;
  color: #999;
  text-align: center;
}

.kanban-empty-state p {
  margin: 0;
  font-size: 14px;
}

.kanban-card-wrapper {
  margin-bottom: 8px;
  transition: all 0.2s ease;
}

.kanban-card-wrapper.dragging {
  opacity: 0.5;
}

.kanban-error {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 400px;
  gap: 16px;
  color: #d32f2f;
}

.kanban-error p {
  margin: 0;
}

.kanban-error button {
  padding: 8px 16px;
  background-color: #d32f2f;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
}

.kanban-error button:hover {
  background-color: #b71c1c;
}

/* Detention Modal Styles */
.detention-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.detention-modal-content {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
}

.detention-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #e0e0e0;
}

.detention-modal-header h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

.detention-modal-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
  padding: 0;
  width: 32px;
  height: 32px;
}

.detention-modal-close:hover {
  color: #d32f2f;
}

.detention-modal-body {
  padding: 16px;
}

.detention-ot-id {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #666;
}

.detention-ot-id strong {
  color: #333;
  font-weight: 600;
}

.detention-modal-body label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #333;
}

.detention-textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: inherit;
  font-size: 13px;
  resize: vertical;
  box-sizing: border-box;
}

.detention-textarea:focus {
  outline: none;
  border-color: #2196F3;
  box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.1);
}

.detention-modal-footer {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  padding: 16px;
  border-top: 1px solid #e0e0e0;
}

.detention-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  transition: all 0.2s;
}

.detention-btn-cancel {
  background-color: #f5f5f5;
  color: #333;
}

.detention-btn-cancel:hover:not(:disabled) {
  background-color: #e0e0e0;
}

.detention-btn-submit {
  background-color: #d32f2f;
  color: white;
}

.detention-btn-submit:hover:not(:disabled) {
  background-color: #b71c1c;
}

.detention-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 1200px) {
  .kanban-columns {
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  }
}

@media (max-width: 768px) {
  .kanban-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .kanban-controls {
    width: 100%;
  }

  .kanban-columns {
    grid-template-columns: 1fr;
    gap: 12px;
    padding: 12px;
  }

  .kanban-column {
    min-height: 300px;
  }
}
`

export default KanbanBoard


