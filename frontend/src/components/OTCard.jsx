import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

/**
 * Project type color mapping for badges
 */
const PROJECT_TYPE_COLORS = {
  PUBLICO: {
    bg: 'bg-red-100',
    text: 'text-red-800',
    border: 'border-red-300',
  },
  PRIVADO: {
    bg: 'bg-blue-100',
    text: 'text-blue-800',
    border: 'border-blue-300',
  },
  TERCERIZADO: {
    bg: 'bg-green-100',
    text: 'text-green-800',
    border: 'border-green-300',
  },
};

/**
 * OT Status color mapping for visual indication
 */
const STATUS_COLORS = {
  PREPLANIFICADA: 'border-l-4 border-l-blue-400 bg-blue-50',
  PLANIFICADA: 'border-l-4 border-l-yellow-400 bg-yellow-50',
  ASIGNADO_TAREA: 'border-l-4 border-l-green-400 bg-green-50',
  DETENIDA: 'border-l-4 border-l-red-400 bg-red-50',
  ANULADA: 'border-l-4 border-l-gray-400 bg-gray-50',
  FINALIZADA: 'border-l-4 border-l-green-600 bg-green-100',
};

/**
 * OTCard - Individual draggable work order card component
 *
 * Props:
 * - ot: OT object with id, external_id, status, project_type, lat, long, cliente_id, login_id, created_at, geo_error
 * - isDragging: Boolean indicating if card is currently being dragged
 * - isLoading: Boolean indicating if card is being updated
 */
function OTCard({ ot, isDragging = false, isLoading = false }) {
  // Use Sortable hook for drag-and-drop functionality
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging: isSortableDragging,
  } = useSortable({ id: ot.id });

  // Apply transform and transition styles
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isSortableDragging ? 0.5 : 1,
  };

  /**
   * Format the created date in relative format
   */
  const formatCreatedDate = () => {
    try {
      return formatDistanceToNow(new Date(ot.created_at), {
        addSuffix: true,
        locale: es,
      });
    } catch (error) {
      return 'Fecha desconocida';
    }
  };

  /**
   * Get project type badge styling
   */
  const getProjectTypeBadgeStyle = () => {
    return PROJECT_TYPE_COLORS[ot.project_type] || PROJECT_TYPE_COLORS.PRIVADO;
  };

  /**
   * Get status color styling
   */
  const getStatusColor = () => {
    return STATUS_COLORS[ot.status] || STATUS_COLORS.PREPLANIFICADA;
  };

  /**
   * Format coordinates display
   */
  const formatCoordinates = () => {
    if (ot.lat && ot.long) {
      return `${ot.lat.toFixed(4)}, ${ot.long.toFixed(4)}`;
    }
    return null;
  };

  const projectTypeColors = getProjectTypeBadgeStyle();
  const statusColor = getStatusColor();
  const coordinates = formatCoordinates();

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`
        p-4 rounded-lg border border-gray-200 shadow-sm hover:shadow-md 
        transition-shadow duration-200 cursor-grab active:cursor-grabbing
        ${statusColor}
        ${isDragging || isSortableDragging ? 'opacity-50 scale-95' : ''}
        ${isLoading ? 'opacity-75 pointer-events-none' : ''}
      `}
    >
      {/* Loading Spinner */}
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center rounded-lg bg-white/50 z-10">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
        </div>
      )}

      {/* Card Content */}
      <div className="space-y-2">
        {/* Header: OT ID and Project Type Badge */}
        <div className="flex items-start justify-between gap-2">
          <h4 className="font-semibold text-gray-900 text-sm flex-1 break-words">
            OT {ot.external_id}
          </h4>
          <span
            className={`
              px-2 py-1 rounded text-xs font-medium whitespace-nowrap
              ${projectTypeColors.bg} ${projectTypeColors.text} ${projectTypeColors.border} border
            `}
          >
            {ot.project_type}
          </span>
        </div>

        {/* Client and Login Info */}
        <div className="text-xs text-gray-600 space-y-1">
          <div className="flex items-center gap-1">
            <span className="font-medium">Cliente:</span>
            <span className="truncate">{ot.cliente_id}</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="font-medium">Login:</span>
            <span className="truncate">{ot.login_id}</span>
          </div>
        </div>

        {/* Geographic Coordinates */}
        <div className="text-xs">
          {coordinates ? (
            <div className="flex items-center gap-1 text-gray-600">
              <span className="font-medium">📍</span>
              <span className="font-mono text-gray-700">{coordinates}</span>
            </div>
          ) : (
            <div className="flex items-center gap-1 text-orange-600">
              <span className="font-medium">⚠️</span>
              <span>Sin coordenadas</span>
            </div>
          )}
        </div>

        {/* Geo Error Flag */}
        {ot.geo_error && (
          <div className="flex items-center gap-1 text-xs text-red-600 bg-red-50 p-1 rounded">
            <span>❌</span>
            <span>Error de geolocalización</span>
          </div>
        )}

        {/* Detention Reason (if applicable) */}
        {ot.detention_reason && (
          <div className="bg-yellow-50 border border-yellow-200 rounded p-2 text-xs">
            <div className="font-medium text-yellow-900">Motivo de detención:</div>
            <div className="text-yellow-800">{ot.detention_reason}</div>
          </div>
        )}

        {/* Footer: Created Date */}
        <div className="text-xs text-gray-500 pt-1 border-t border-gray-200">
          Creada {formatCreatedDate()}
        </div>
      </div>
    </div>
  );
}

export default OTCard;

