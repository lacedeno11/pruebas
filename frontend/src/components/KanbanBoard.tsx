import { useState } from 'react';
import {
  DndContext,
  DragEndEvent,
  DragStartEvent,
  closestCorners,
} from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import toast from 'react-hot-toast';
import { OT, OTStatus, ProjectType } from '@/types';
import { useOTsByStatus, useUpdateOTStatus } from '@/hooks/useOTs';
import { useDocumentStatus } from '@/hooks/useOTs';

// Define status columns with labels and colors
const STATUS_COLUMNS = [
  {
    status: OTStatus.PREPLANIFICADA,
    label: 'Por Planificar',
    color: 'bg-blue-100',
    borderColor: 'border-blue-400',
  },
  {
    status: OTStatus.PLANIFICADA,
    label: 'Planificada',
    color: 'bg-yellow-100',
    borderColor: 'border-yellow-400',
  },
  {
    status: OTStatus.ASIGNADO_TAREA,
    label: 'Asignada',
    color: 'bg-green-100',
    borderColor: 'border-green-400',
  },
  {
    status: OTStatus.DETENIDA,
    label: 'Detenida',
    color: 'bg-orange-100',
    borderColor: 'border-orange-400',
  },
  {
    status: OTStatus.ANULADA,
    label: 'Anulada',
    color: 'bg-red-100',
    borderColor: 'border-red-400',
  },
  {
    status: OTStatus.FINALIZADA,
    label: 'Finalizada',
    color: 'bg-gray-100',
    borderColor: 'border-gray-400',
  },
];

export interface KanbanBoardProps {
  filters?: {
    projectType?: ProjectType;
  };
}

export function KanbanBoard({ filters }: KanbanBoardProps) {
  const { otsByStatus, isLoading } = useOTsByStatus(filters);
  const updateStatus = useUpdateOTStatus();
  const [draggingOTId, setDraggingOTId] = useState<string | null>(null);
  const [isUpdating, setIsUpdating] = useState<string | null>(null);

  const handleDragStart = (event: DragStartEvent) => {
    const otId = event.active.id as string;
    setDraggingOTId(otId);
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    setDraggingOTId(null);

    const { active, over } = event;

    // If no drop zone, do nothing
    if (!over) {
      return;
    }

    const otId = active.id as string;
    const newStatus = over.id as OTStatus;

    // Find the OT being dragged
    let draggedOT: OT | null = null;
    for (const status in otsByStatus) {
      const ot = otsByStatus[status as OTStatus].find((o) => o.id === otId);
      if (ot) {
        draggedOT = ot;
        break;
      }
    }

    if (!draggedOT) {
      return;
    }

    // Check if OT is already in target status
    if (draggedOT.status === newStatus) {
      return;
    }

    // Business rule: PUBLICO projects cannot move to FINALIZADA without 29 documents
    if (draggedOT.projectType === ProjectType.PUBLICO && newStatus === OTStatus.FINALIZADA) {
      setIsUpdating(otId);

      try {
        // Fetch document status to check if 29 documents uploaded
        const docStatus = await useDocumentStatus(otId);
        
        if (!docStatus || docStatus.documentCount < 29) {
          toast.error(
            `No se puede finalizar: ${docStatus?.documentCount || 0}/29 documentos cargados`,
            { duration: 5000 }
          );
          setIsUpdating(null);
          return;
        }
      } catch (error) {
        toast.error('Error al verificar documentos');
        setIsUpdating(null);
        return;
      }
    }

    // Show loading and update status
    setIsUpdating(otId);

    try {
      await updateStatus.mutateAsync({
        id: otId,
        status: newStatus as OTStatus,
      });

      toast.success(`OT ${draggedOT.externalId} movida a ${newStatus}`);
    } catch (error: any) {
      toast.error(`Error al actualizar OT: ${error.message}`);
      // Card will revert automatically due to mutation error
    } finally {
      setIsUpdating(null);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Cargando OTs...</p>
        </div>
      </div>
    );
  }

  return (
    <DndContext
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="grid grid-cols-6 gap-4 p-6 bg-gray-50 h-full overflow-auto">
        {STATUS_COLUMNS.map((column) => (
          <div key={column.status} className="flex flex-col">
            {/* Column Header */}
            <div className={`${column.color} rounded-t-lg p-4 border-l-4 ${column.borderColor}`}>
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-gray-800 text-sm">
                  {column.label}
                </h3>
                <span className="bg-white text-gray-800 text-xs font-bold rounded-full h-6 w-6 flex items-center justify-center">
                  {otsByStatus[column.status]?.length || 0}
                </span>
              </div>
            </div>

            {/* Column Content - Droppable Area */}
            <SortableContext
              items={otsByStatus[column.status]?.map((ot) => ot.id) || []}
              strategy={verticalListSortingStrategy}
            >
              <div
                className={`
                  flex-1 ${column.color} rounded-b-lg p-3
                  border-2 ${column.borderColor} border-dashed
                  overflow-y-auto min-h-96
                  transition-colors duration-200
                `}
                data-drop-zone={column.status}
              >
                <div className="space-y-3">
                  {otsByStatus[column.status]?.map((ot) => (
                    <KanbanOTCard
                      key={ot.id}
                      ot={ot}
                      isDragging={draggingOTId === ot.id}
                      isUpdating={isUpdating === ot.id}
                      onStatusChange={() => {}} // Handled by drag end
                    />
                  ))}

                  {/* Empty state message */}
                  {otsByStatus[column.status]?.length === 0 && (
                    <div className="text-center py-8 text-gray-500">
                      <p className="text-sm">No hay OTs</p>
                    </div>
                  )}
                </div>

                {/* Add button for future feature */}
                <button className="w-full mt-3 py-2 border-2 border-dashed border-gray-400 rounded text-gray-500 hover:border-gray-600 hover:text-gray-700 text-xs font-medium">
                  + Agregar OT
                </button>
              </div>
            </SortableContext>
          </div>
        ))}
      </div>
    </DndContext>
  );
}

/**
 * Individual OT Card component for Kanban board
 */
interface KanbanOTCardProps {
  ot: OT;
  isDragging?: boolean;
  isUpdating?: boolean;
  onStatusChange?: (newStatus: OTStatus) => void;
}

function KanbanOTCard({ ot, isDragging, isUpdating }: KanbanOTCardProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging: isSortableDragging } =
    require('@dnd-kit/sortable').useSortable({ id: ot.id });

  const projectTypeColors: Record<string, string> = {
    PUBLICO: 'bg-red-500',
    PRIVADO: 'bg-blue-500',
    TERCERIZADO: 'bg-purple-500',
  };

  const statusDotColors: Record<OTStatus, string> = {
    [OTStatus.PREPLANIFICADA]: 'bg-blue-500',
    [OTStatus.PLANIFICADA]: 'bg-yellow-500',
    [OTStatus.ASIGNADO_TAREA]: 'bg-green-500',
    [OTStatus.DETENIDA]: 'bg-orange-500',
    [OTStatus.ANULADA]: 'bg-red-500',
    [OTStatus.FINALIZADA]: 'bg-gray-500',
  };

  const style = {
    transform: transform
      ? `translate3d(${transform.x}px, ${transform.y}px, 0)`
      : undefined,
    transition,
    opacity: isDragging || isSortableDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`
        bg-white rounded-lg p-4 shadow hover:shadow-lg
        transition-all duration-200 cursor-grab active:cursor-grabbing
        border-l-4 border-transparent hover:border-gray-400
        ${isSortableDragging ? 'opacity-50' : ''}
        ${isUpdating ? 'opacity-60' : ''}
      `}
    >
      {/* Loading overlay */}
      {isUpdating && (
        <div className="absolute inset-0 bg-white bg-opacity-70 rounded-lg flex items-center justify-center">
          <div className="inline-block animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
        </div>
      )}

      {/* External ID - Large */}
      <h4 className="font-bold text-gray-800 text-sm mb-2">{ot.externalId}</h4>

      {/* Project Type Badge */}
      <div className="flex items-center gap-2 mb-2">
        <span
          className={`${projectTypeColors[ot.projectType]} text-white text-xs font-bold px-2 py-1 rounded`}
        >
          {ot.projectType}
        </span>

        {/* Status indicator dot */}
        <div className="flex items-center gap-1">
          <div className={`${statusDotColors[ot.status]} w-2 h-2 rounded-full`}></div>
        </div>
      </div>

      {/* Client Name */}
      {ot.clienteName && (
        <p className="text-xs text-gray-600 truncate mb-2">{ot.clienteName}</p>
      )}

      {/* Assigned Cuadrilla */}
      {ot.cuadrilla && (
        <p className="text-xs text-gray-600 mb-2">
          <span className="font-semibold">Equipo:</span> {ot.cuadrilla.name}
        </p>
      )}

      {/* Coordinates - Truncated */}
      {ot.lat && ot.long && (
        <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
          <span>📍</span>
          <span>
            {ot.lat.toFixed(2)}, {ot.long.toFixed(2)}
          </span>
        </div>
      )}

      {/* Geo Error Warning */}
      {ot.hasGeoError && (
        <div className="flex items-center gap-1 text-xs text-red-600 font-semibold">
          <span>⚠️</span>
          <span>Coordenadas inválidas</span>
        </div>
      )}
    </div>
  );
}

export default KanbanBoard;

