/**
 * Kanban Column Component
 *
 * This component represents a single status column in the Kanban board.
 * It's a droppable zone that displays OT cards and provides visual feedback
 * when dragging cards over the column.
 */

import React from "react";
import { useDroppable } from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { OT, OTStatus } from "../../types";
import OTCard from "./OTCard";

interface KanbanColumnProps {
  status: OTStatus;
  ots: OT[];
  title: string;
  isValidatingId?: number | null;
}

/**
 * Status color mapping for column headers
 */
const statusColors: Record<OTStatus, { header: string; border: string; badge: string }> = {
  [OTStatus.PREPLANIFICADA]: {
    header: "bg-yellow-100 border-yellow-300",
    border: "border-yellow-200",
    badge: "bg-yellow-200 text-yellow-800",
  },
  [OTStatus.PLANIFICADA]: {
    header: "bg-blue-100 border-blue-300",
    border: "border-blue-200",
    badge: "bg-blue-200 text-blue-800",
  },
  [OTStatus.ASIGNADO_TAREA]: {
    header: "bg-purple-100 border-purple-300",
    border: "border-purple-200",
    badge: "bg-purple-200 text-purple-800",
  },
  [OTStatus.DETENIDA]: {
    header: "bg-red-100 border-red-300",
    border: "border-red-200",
    badge: "bg-red-200 text-red-800",
  },
  [OTStatus.ANULADA]: {
    header: "bg-gray-100 border-gray-300",
    border: "border-gray-200",
    badge: "bg-gray-200 text-gray-800",
  },
  [OTStatus.FINALIZADA]: {
    header: "bg-green-100 border-green-300",
    border: "border-green-200",
    badge: "bg-green-200 text-green-800",
  },
};

/**
 * Status-friendly display names
 */
const statusDisplayNames: Record<OTStatus, string> = {
  [OTStatus.PREPLANIFICADA]: "Por Planificar",
  [OTStatus.PLANIFICADA]: "Planificada",
  [OTStatus.ASIGNADO_TAREA]: "Tareas Asignadas",
  [OTStatus.DETENIDA]: "Detenida",
  [OTStatus.ANULADA]: "Anulada",
  [OTStatus.FINALIZADA]: "Finalizada",
};

/**
 * Kanban Column Component
 *
 * Features:
 * - Droppable zone for drag & drop
 * - Status-specific styling
 * - OT count badge
 * - Sortable context for OT ordering
 * - Visual feedback on drag over
 * - Empty state message
 * - Validation spinner support
 */
export const KanbanColumn: React.FC<KanbanColumnProps> = ({
  status,
  ots,
  title,
  isValidatingId,
}) => {
  const { setNodeRef, isOver, active } = useDroppable({
    id: status,
  });

  const colors = statusColors[status];
  const displayName = statusDisplayNames[status];

  // Determine if this is the target column during drag
  const isDragOver = isOver && active?.data.current?.sortable?.containerId === status;

  // OT IDs for sortable context
  const otIds = ots.map((ot) => ot.id);

  return (
    <div
      ref={setNodeRef}
      className={`
        flex
        flex-col
        w-full
        min-w-[320px]
        max-w-[400px]
        rounded-lg
        border-2
        transition-all
        duration-200
        ${colors.border}
        ${isDragOver ? "ring-2 ring-offset-2 ring-blue-400 shadow-lg" : ""}
        bg-white
      `}
    >
      {/* Column Header */}
      <div
        className={`
          flex
          items-center
          justify-between
          p-4
          rounded-t-md
          border-b-2
          ${colors.header}
          ${colors.border}
        `}
      >
        <div className="flex items-center gap-3 flex-1">
          {/* Status Title */}
          <h3 className="font-bold text-gray-800">
            {title || displayName}
          </h3>

          {/* OT Count Badge */}
          <span className={`
            px-3
            py-1
            text-sm
            font-semibold
            rounded-full
            ${colors.badge}
          `}>
            {ots.length}
          </span>
        </div>
      </div>

      {/* Droppable OT Cards Area */}
      <div
        className={`
          flex-1
          p-3
          overflow-y-auto
          min-h-[300px]
          max-h-[calc(100vh-300px)]
          transition-all
          duration-200
          ${isDragOver ? "bg-blue-50" : "bg-gray-50"}
        `}
      >
        <SortableContext
          items={otIds}
          strategy={verticalListSortingStrategy}
        >
          {ots.length > 0 ? (
            <div className="space-y-2">
              {ots.map((ot) => (
                <OTCard
                  key={ot.id}
                  ot={ot}
                  isValidating={isValidatingId === ot.id}
                />
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full min-h-[200px] text-center">
              <div className="text-gray-400 mb-2">
                {/* Empty State Icon */}
                <svg
                  className="w-12 h-12 mx-auto opacity-40"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
              </div>
              <p className="text-gray-600 font-medium">
                No hay OTs en esta etapa
              </p>
              <p className="text-gray-500 text-sm mt-1">
                Arrastra OTs aquí o crea nuevas
              </p>
            </div>
          )}
        </SortableContext>

        {/* Drag Over Indicator */}
        {isDragOver && (
          <div className="absolute inset-0 pointer-events-none border-2 border-dashed border-blue-400 rounded-lg" />
        )}
      </div>

      {/* Column Footer with Statistics */}
      {ots.length > 0 && (
        <div className="px-4 py-2 border-t border-gray-200 bg-gray-50 rounded-b-md text-xs text-gray-600">
          <div className="flex justify-between">
            <span>{ots.length} OT{ots.length !== 1 ? "s" : ""}</span>
            <span>
              {ots.filter((ot) => ot.is_geo_error).length} con errores geo
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default KanbanColumn;

