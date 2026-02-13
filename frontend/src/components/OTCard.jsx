/**
 * OT Card Component
 * 
 * Draggable card component for displaying OT (Orden de Trabajo) information.
 * Used in the Kanban board for visual representation of work orders.
 */

import Spinner from './Spinner';
import { formatCoordinate, getStatusColor, getProjectTypeBadgeColor } from '../utils/formatters';
import { PROJECT_TYPES } from '../utils/constants';

/**
 * OTCard component for displaying a single OT in the Kanban board.
 * 
 * @param {Object} props - Component props
 * @param {Object} props.ot - OT object with properties: external_id, cliente_id, project_type, lat, long, cuadrilla_id, etc.
 * @param {boolean} props.isDragging - Whether the card is currently being dragged
 * @returns {JSX.Element} Draggable OT card component
 * 
 * @example
 * <OTCard 
 *   ot={{
 *     external_id: 'OT-2024001',
 *     cliente_id: 'CLIENT-1001',
 *     project_type: 'PUBLICO',
 *     lat: -0.22,
 *     long: -78.51,
 *     cuadrilla_id: 1
 *   }}
 *   isDragging={false}
 * />
 */
export default function OTCard({ ot, isDragging }) {
  // Get status color styling
  const statusColor = getStatusColor(ot.status);
  
  // Get project type badge color and label
  const projectTypeBadge = getProjectTypeBadgeColor(ot.project_type);
  
  // Format coordinates for display
  const coordinates = formatCoordinate(ot.lat, ot.long, 2);
  const hasValidCoordinates = ot.lat !== null && ot.long !== null && !ot.geo_error;

  return (
    <div
      className={`
        ot-card
        p-3 rounded-lg border-2 transition-all duration-200
        ${statusColor.bg} ${statusColor.border}
        hover:shadow-lg hover:scale-105
        cursor-move
        relative
      `}
    >
      {/* Loading spinner overlay during drag */}
      {isDragging && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/50 rounded-lg z-10">
          <Spinner size="small" />
        </div>
      )}

      {/* Header: External ID and Project Type Badge */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <h4 className={`text-sm font-bold ${statusColor.text}`}>
          {ot.external_id}
        </h4>
        <span
          className={`
            px-2 py-1 rounded text-xs font-semibold whitespace-nowrap
            ${projectTypeBadge.badgeBg} ${projectTypeBadge.badgeText}
          `}
        >
          {projectTypeBadge.label}
        </span>
      </div>

      {/* Client ID */}
      <div className="mb-2">
        <p className={`text-xs ${statusColor.text}`}>
          <span className="font-semibold">Cliente:</span> {ot.cliente_id}
        </p>
      </div>

      {/* Geographic Information */}
      <div className="mb-2">
        {hasValidCoordinates ? (
          <p className={`text-xs ${statusColor.text} flex items-center gap-1`}>
            <span className="text-lg">📍</span>
            {coordinates}
          </p>
        ) : (
          <p className="text-xs text-red-600 flex items-center gap-1">
            <span className="text-lg">⚠️</span>
            Geo error or missing coordinates
          </p>
        )}
      </div>

      {/* Assigned Cuadrilla (if present) */}
      {ot.cuadrilla_id && (
        <div className="mt-2 pt-2 border-t border-current opacity-50">
          <p className={`text-xs ${statusColor.text}`}>
            <span className="font-semibold">Cuadrilla:</span> {ot.cuadrilla_id}
          </p>
        </div>
      )}

      {/* Status indicator at bottom */}
      <div className="mt-2 pt-2 border-t border-current opacity-50">
        <p className={`text-xs font-semibold ${statusColor.text}`}>
          Status: {ot.status}
        </p>
      </div>
    </div>
  );
}

