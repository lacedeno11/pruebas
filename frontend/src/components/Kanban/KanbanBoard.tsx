/**
 * Kanban Board Component - Main Drag & Drop Board
 *
 * This is the main Kanban board component that orchestrates drag & drop
 * operations between status columns. It handles validation before allowing
 * status transitions and provides visual feedback during drag operations.
 */

import React, { useState, useCallback } from "react";
import {
  DndContext,
  DragEndEvent,
  DragStartEvent,
  DragOverlay,
  closestCorners,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import toast from "react-hot-toast";
import { OT, OTStatus } from "../../types";
import { useKanban } from "../../hooks/useKanban";
import { useValidateTransition, useUpdateOTStatus } from "../../hooks/useOTs";
import KanbanColumn from "./KanbanColumn";
import OTCard from "./OTCard";
import DetentionReasonModal from "../Modals/DetentionReasonModal";

/**
 * All OT statuses for the board columns
 */
const ALL_STATUSES: OTStatus[] = [
  OTStatus.PREPLANIFICADA,
  OTStatus.PLANIFICADA,
  OTStatus.ASIGNADO_TAREA,
  OTStatus.DETENIDA,
  OTStatus.FINALIZADA,
];

/**
 * Kanban Board Component
 *
 * Features:
 * - Drag & drop OT cards between status columns
 * - Real-time validation before status transitions
 * - Optimistic updates for better UX
 * - Detention reason modal for DETENIDA transitions
 * - Visual feedback during drag operations
 * - Toast notifications for user feedback
 * - Auto-refetch to keep board in sync
 */
export const KanbanBoard: React.FC = () => {
  // State management
  const [validatingOTId, setValidatingOTId] = useState<number | null>(null);
  const [draggedOT, setDraggedOT] = useState<OT | null>(null);
  const [detentionModalOpen, setDetentionModalOpen] = useState(false);
  const [pendingTransition, setPendingTransition] = useState<{
    otId: number;
    newStatus: OTStatus;
  } | null>(null);

  // Hooks
  const { data: kanbanData, isLoading, error, refetch } = useKanban();
  const { mutate: validateTransition } = useValidateTransition();
  const { mutate: updateStatus } = useUpdateOTStatus();

  // Drag & drop sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      distance: 8, // 8px movement required to start drag
    })
  );

  /**
   * Handle drag start
   * Stores the dragged OT for preview during drag
   */
  const handleDragStart = useCallback((event: DragStartEvent) => {
    const { active } = event;
    const otId = active.id as number;

    // Find the OT being dragged
    if (kanbanData?.columns) {
      for (const column of Object.values(kanbanData.columns)) {
        const ot = column.ots.find((o) => o.id === otId);
        if (ot) {
          setDraggedOT(ot);
          break;
        }
      }
    }
  }, [kanbanData]);

  /**
   * Handle drag end
   * Validates transition and updates OT status if valid
   */
  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      setDraggedOT(null);

      // No drop target
      if (!over) {
        return;
      }

      const otId = active.id as number;
      const newStatus = over.id as OTStatus;

      // Find the OT
      const ot = draggedOT || (kanbanData?.columns[draggedOT?.status as OTStatus]?.ots || []).find(
        (o) => o.id === otId
      );

      if (!ot) {
        toast.error("OT not found");
        return;
      }

      // Same status - no transition needed
      if (ot.status === newStatus) {
        return;
      }

      // Show validating toast
      const toastId = toast.loading("Validando transición...", {
        icon: "⏳",
      });

      setValidatingOTId(otId);

      // Validate transition
      validateTransition(
        {
          otId,
          newStatus,
        },
        {
          onSuccess: (result) => {
            toast.dismiss(toastId);

            if (result.valid) {
              // Transition is valid
              toast.success("Transición válida", { icon: "✓" });

              // Check if detention reason is required
              if (result.requires_detention_reason) {
                // Store pending transition for modal
                setPendingTransition({ otId, newStatus });
                setDetentionModalOpen(true);
              } else {
                // Proceed with update
                performStatusUpdate(otId, newStatus, undefined);
              }
            } else {
              // Transition is invalid
              toast.error(`Transición inválida: ${result.error || result.message}`, {
                icon: "❌",
              });
              setValidatingOTId(null);
              refetch(); // Refetch to revert position
            }
          },
          onError: (error) => {
            toast.dismiss(toastId);
            toast.error(`Error validando: ${error.message}`, { icon: "⚠️" });
            setValidatingOTId(null);
            refetch(); // Refetch to revert position
          },
        }
      );
    },
    [draggedOT, kanbanData, validateTransition, refetch]
  );

  /**
   * Perform the actual status update
   */
  const performStatusUpdate = useCallback(
    (otId: number, newStatus: string, reason?: string) => {
      const toastId = toast.loading("Actualizando OT...", {
        icon: "⏳",
      });

      updateStatus(
        {
          id: otId,
          newStatus,
          reason,
        },
        {
          onSuccess: (updatedOT) => {
            toast.dismiss(toastId);
            toast.success(
              `OT ${updatedOT.external_id} movido a ${newStatus}`,
              { icon: "✓" }
            );
            setValidatingOTId(null);
            setPendingTransition(null);
            setDetentionModalOpen(false);

            // Refetch to ensure sync
            refetch();
          },
          onError: (error) => {
            toast.dismiss(toastId);
            toast.error(`Error actualizando OT: ${error.message}`, {
              icon: "❌",
            });
            setValidatingOTId(null);
            refetch(); // Refetch to revert position
          },
        }
      );
    },
    [updateStatus, refetch]
  );

  /**
   * Handle detention reason submission
   */
  const handleDetentionReasonSubmit = useCallback(
    (reason: string) => {
      if (pendingTransition) {
        performStatusUpdate(pendingTransition.otId, pendingTransition.newStatus, reason);
      }
    },
    [pendingTransition, performStatusUpdate]
  );

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Cargando tablero Kanban...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center">
          <p className="text-red-600 font-semibold mb-4">Error cargando tablero</p>
          <p className="text-gray-600 mb-4">{error.message}</p>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  // No data
  if (!kanbanData) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <p className="text-gray-600">No hay datos disponibles</p>
      </div>
    );
  }

  // Render Kanban board with all columns
  return (
    <>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        {/* Main Kanban Board */}
        <div className="flex gap-4 p-6 bg-gray-50 overflow-x-auto h-screen">
          {ALL_STATUSES.map((status) => {
            const column = kanbanData.columns[status];
            const ots = column?.ots || [];

            return (
              <SortableContext
                key={status}
                items={ots.map((ot) => ot.id)}
                strategy={verticalListSortingStrategy}
              >
                <KanbanColumn
                  status={status}
                  ots={ots}
                  title={getStatusTitle(status)}
                  isValidatingId={validatingOTId}
                />
              </SortableContext>
            );
          })}
        </div>

        {/* Drag Preview - Shows OT being dragged */}
        <DragOverlay>
          {draggedOT ? (
            <div className="opacity-75">
              <OTCard ot={draggedOT} isValidating={false} />
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>

      {/* Detention Reason Modal */}
      <DetentionReasonModal
        isOpen={detentionModalOpen}
        onClose={() => {
          setDetentionModalOpen(false);
          setPendingTransition(null);
          setValidatingOTId(null);
        }}
        onSubmit={handleDetentionReasonSubmit}
      />
    </>
  );
};

/**
 * Get friendly status title for column header
 */
function getStatusTitle(status: OTStatus): string {
  const titles: Record<OTStatus, string> = {
    [OTStatus.PREPLANIFICADA]: "Por Planificar",
    [OTStatus.PLANIFICADA]: "Planificada",
    [OTStatus.ASIGNADO_TAREA]: "Tareas Asignadas",
    [OTStatus.DETENIDA]: "Detenida",
    [OTStatus.ANULADA]: "Anulada",
    [OTStatus.FINALIZADA]: "Finalizada",
  };
  return titles[status];
}

export default KanbanBoard;

