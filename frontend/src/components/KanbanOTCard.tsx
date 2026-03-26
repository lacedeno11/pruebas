import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { OT, OTStatus, ProjectType } from '@/types';
import { useUIStore } from '@/stores/uiStore';

export interface KanbanOTCardProps {
  ot: OT;
}

/**
 * Individual draggable OT card component for Kanban board
 */
export function KanbanOTCard({ ot }: KanbanOTCardProps) {
  const { setSelectedOT } = useUIStore();
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: ot.id });

  // Status color mapping
  const statusColors: Record<OTStatus, string> = {
    [OTStatus.PREPLANIFICADA]: 'bg-blue-500',
    [OTStatus.PLANIFICADA]: 'bg-yellow-500',
    [OTStatus.ASIGNADO_TAREA]: 'bg-green-500',
    [OTStatus.DETENIDA]: 'bg-orange-500',
    [OTStatus.ANULADA]: 'bg-red-500',
    [OTStatus.FINALIZADA]: 'bg-gray-500',
  };

  // Project type color mapping
  const projectTypeColors: Record<ProjectType, string> = {
    [ProjectType.PUBLICO]: 'bg-red-600',
    [ProjectType.PRIVADO]: 'bg-blue-600',
    [ProjectType.TERCERIZADO]: 'bg-purple-600',
  };

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const handleClick = () => {
    setSelectedOT(ot.id);
    // In a real app, this would open a modal or detail view
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={handleClick}
      className={`
        bg-white rounded-lg p-3 shadow-sm hover:shadow-md
        transition-all duration-200 cursor-grab active:cursor-grabbing
        border-l-4 ${statusColors[ot.status]}
        ${isDragging ? 'opacity-50 ring-2 ring-blue-400' : 'hover:border-opacity-80'}
      `}
    >
      {/* External ID - Large and bold */}
      <h4 className="font-bold text-gray-800 text-sm mb-2 truncate">
        {ot.externalId}
      </h4>

      {/* Project Type Badge */}
      <div className="flex items-center gap-2 mb-2">
        <span
          className={`
            ${projectTypeColors[ot.projectType]}
            text-white text-xs font-bold px-2 py-1 rounded
          `}
        >
          {ot.projectType}
        </span>

        {/* Status Indicator Dot */}
        <div
          className={`
            ${statusColors[ot.status]}
            w-2.5 h-2.5 rounded-full
          `}
          title={ot.status}
        />
      </div>

      {/* Client Name - Truncated */}
      {ot.clienteName && (
        <p className="text-xs text-gray-600 truncate mb-1">
          <span className="font-semibold">Cliente:</span> {ot.clienteName}
        </p>
      )}

      {/* Assigned Cuadrilla - If any */}
      {ot.cuadrilla && (
        <p className="text-xs text-gray-600 truncate mb-1">
          <span className="font-semibold">Equipo:</span> {ot.cuadrilla.name}
        </p>
      )}

      {/* Coordinates with Map Icon - Truncated */}
      {ot.lat && ot.long && (
        <div className="flex items-center gap-1 text-xs text-gray-500 mb-1">
          <span>📍</span>
          <span className="truncate">
            {ot.lat.toFixed(2)}, {ot.long.toFixed(2)}
          </span>
        </div>
      )}

      {/* Geo Error Warning - If any */}
      {ot.hasGeoError && (
        <div className="flex items-center gap-1 text-xs text-red-600 font-semibold mt-2">
          <span>⚠️</span>
          <span>Coordenadas inválidas</span>
        </div>
      )}

      {/* Footer - Created date */}
      <div className="text-xs text-gray-400 mt-2 pt-2 border-t border-gray-200">
        {new Date(ot.createdAt).toLocaleDateString('es-ES')}
      </div>
    </div>
  );
}

export default KanbanOTCard;

