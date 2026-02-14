import React, { useState } from 'react';
import { toast } from 'react-toastify';
import {
  DndContext,
  DragOverlay,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useOT } from '../contexts/OTContext';
import OTCard from './OTCard';
import DetentionModal from './DetentionModal';

// Define Kanban columns
const COLUMNS = [
  { id: 'PREPLANIFICADA', title: 'Pre-Planificada' },
  { id: 'PLANIFICADA', title: 'Planificada' },
  { id: 'ASIGNADO_TAREA', title: 'Asignado' },
  { id: 'DETENIDA', title: 'Detenida' },
  { id: 'FINALIZADA', title: 'Finalizada' },
];

/**
 * KanbanColumn - Individual column component with drag-drop support
 */
function KanbanColumn({ column, ots, onDragStart, loadingOtId }) {
  const { setNodeRef } = useSortable({
    id: column.id,
    data: {
      type: 'Column',
      column,
    },
  });

  return (
    <div
      ref={setNodeRef}
      className="flex flex-col bg-gray-100 rounded-lg p-4 min-w-80 max-h-96 overflow-y-auto"
    >
      {/* Column Header */}
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-semibold text-gray-800">{column.title}</h3>
        <span className="bg-gray-300 text-gray-700 px-2 py-1 rounded text-sm font-medium">
          {ots.length}
        </span>
      </div>

      {/* OT Cards */}
      <SortableContext items={ots.map(ot => ot.id)} strategy={verticalListSortingStrategy}>
        <div className="space-y-2 flex-1">
          {ots.length === 0 ? (
            <div className="text-center text-gray-400 py-8">
              No OTs
            </div>
          ) : (
            ots.map(ot => (
              <OTCard
                key={ot.id}
                ot={ot}
                isLoading={loadingOtId === ot.id}
                onDragStart={onDragStart}
              />
            ))
          )}
        </div>
      </SortableContext>
    </div>
  );
}

/**
 * KanbanBoard - Main Kanban board component with drag-and-drop
 */
function KanbanBoard() {
  const { ots, updateOTStatus, loading } = useOT();

  // Local state
  const [activeId, setActiveId] = useState(null);
  const [showDetentionModal, setShowDetentionModal] = useState(false);
  const [pendingMove, setPendingMove] = useState(null);
  const [loadingOtId, setLoadingOtId] = useState(null);

  // Sensors for drag detection
  const sensors = useSensors(
    useSensor(PointerSensor, {
      distance: 8,
    })
  );

  /**
   * Handle drag start
   */
  const handleDragStart = (event) => {
    const { active } = event;
    setActiveId(active.id);
  };

  /**
   * Handle drag end - process OT status change
   */
  const handleDragEnd = async (event) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over) return;

    const otId = active.id;
    const newStatus = over.id;

    // Get the OT being moved
    const ot = ots.find(o => o.id === otId);
    if (!ot) return;

    // If OT is already in this status, do nothing
    if (ot.status === newStatus) return;

    // Check if moving to DETENIDA - need detention reason
    if (newStatus === 'DETENIDA') {
      setPendingMove({ otId, ot, newStatus });
      setShowDetentionModal(true);
      return;
    }

    // Otherwise, directly update status
    try {
      setLoadingOtId(otId);
      await updateOTStatus(otId, newStatus);
    } catch (error) {
      toast.error('Failed to update OT status');
    } finally {
      setLoadingOtId(null);
    }
  };

  /**
   * Handle detention modal confirmation
   */
  const handleDetentionConfirm = async (detentionReason) => {
    if (!pendingMove) return;

    const { otId, newStatus } = pendingMove;

    try {
      setLoadingOtId(otId);
      await updateOTStatus(otId, newStatus, detentionReason);
      setShowDetentionModal(false);
      setPendingMove(null);
    } catch (error) {
      toast.error('Failed to update OT status');
    } finally {
      setLoadingOtId(null);
    }
  };

  /**
   * Handle detention modal cancel
   */
  const handleDetentionCancel = () => {
    setShowDetentionModal(false);
    setPendingMove(null);
  };

  /**
   * Get OTs for each column
   */
  const getOTsForColumn = (columnId) => {
    return ots.filter(ot => ot.status === columnId);
  };

  /**
   * Get OT being dragged (for overlay)
   */
  const getActiveOT = () => {
    if (!activeId) return null;
    return ots.find(ot => ot.id === activeId);
  };

  const activeOT = getActiveOT();

  return (
    <>
      <div className="p-6 bg-gray-50 min-h-screen overflow-x-auto">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          {/* Kanban Columns */}
          <div className="flex gap-4 pb-4">
            {COLUMNS.map(column => (
              <KanbanColumn
                key={column.id}
                column={column}
                ots={getOTsForColumn(column.id)}
                onDragStart={handleDragStart}
                loadingOtId={loadingOtId}
              />
            ))}
          </div>

          {/* Drag Overlay */}
          <DragOverlay>
            {activeOT ? (
              <div className="opacity-90 scale-105">
                <OTCard ot={activeOT} isDragging={true} />
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </div>

      {/* Detention Modal */}
      {pendingMove && (
        <DetentionModal
          isOpen={showDetentionModal}
          onClose={handleDetentionCancel}
          ot={pendingMove.ot}
          onConfirm={handleDetentionConfirm}
        />
      )}
    </>
  );
}

export default KanbanBoard;

