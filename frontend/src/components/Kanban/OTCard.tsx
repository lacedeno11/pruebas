/**
 * OT Card Component for Kanban Board
 *
 * This component represents a single work order (OT) card that can be
 * dragged between columns. It displays OT information with visual indicators
 * for status, project type, and validation state.
 */

import React, { useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { OT, OTStatus, ProjectType } from "../../types";
import { AlertCircle, Loader, MapPin } from "lucide-react";

interface OTCardProps {
  ot: OT;
  isValidating?: boolean;
}

/**
 * Project type to color mapping
 */
const projectTypeColors: Record<ProjectType, { bg: string; badge: string; text: string }> = {
  [ProjectType.PUBLICO]: {
    bg: "bg-blue-50",
    badge: "bg-blue-100 text-blue-800",
    text: "text-blue-700",
  },
  [ProjectType.PRIVADO]: {
    bg: "bg-green-50",
    badge: "bg-green-100 text-green-800",
    text: "text-green-700",
  },
  [ProjectType.TERCERIZADO]: {
    bg: "bg-orange-50",
    badge: "bg-orange-100 text-orange-800",
    text: "text-orange-700",
  },
};

/**
 * Status to icon/color mapping
 */
const statusStyles: Record<OTStatus, { dot: string; text: string }> = {
  [OTStatus.PREPLANIFICADA]: { dot: "bg-yellow-400", text: "text-yellow-700" },
  [OTStatus.PLANIFICADA]: { dot: "bg-blue-400", text: "text-blue-700" },
  [OTStatus.ASIGNADO_TAREA]: { dot: "bg-purple-400", text: "text-purple-700" },
  [OTStatus.DETENIDA]: { dot: "bg-red-400", text: "text-red-700" },
  [OTStatus.ANULADA]: { dot: "bg-gray-400", text: "text-gray-700" },
  [OTStatus.FINALIZADA]: { dot: "bg-green-400", text: "text-green-700" },
};

/**
 * Format coordinates for display
 */
function formatCoordinates(lat: number | null, long: number | null): string {
  if (lat === null || long === null) {
    return "No coordinates";
  }
  return `${lat.toFixed(2)}, ${long.toFixed(2)}`;
}

/**
 * OT Card Component
 *
 * Displays a single OT with:
 * - External ID (main identifier)
 * - Project type badge (PUBLICO/PRIVADO/TERCERIZADO)
 * - Cuadrilla assignment (if assigned)
 * - Geographic coordinates
 * - Status indicator dot
 * - GEO_ERROR badge (if applicable)
 * - Drag & drop support
 * - Validation spinner overlay
 */
export const OTCard: React.FC<OTCardProps> = ({ ot, isValidating = false }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Drag & drop setup
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: ot.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const projectType = ot.project_type as ProjectType;
  const status = ot.status as OTStatus;
  const colors = projectTypeColors[projectType];
  const statusStyle = statusStyles[status];

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`
        relative
        p-3
        rounded-lg
        border-2
        border-transparent
        cursor-grab
        active:cursor-grabbing
        transition-all
        duration-200
        hover:shadow-md
        ${colors.bg}
        ${isDragging ? "opacity-50 shadow-lg" : ""}
      `}
    >
      {/* Validation Spinner Overlay */}
      {isValidating && (
        <div className="absolute inset-0 bg-white/50 rounded-lg flex items-center justify-center">
          <Loader className="w-5 h-5 animate-spin text-blue-500" />
        </div>
      )}

      {/* Header: External ID + Status Dot */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {/* Status Indicator Dot */}
          <div
            className={`w-2 h-2 rounded-full flex-shrink-0 ${statusStyle.dot}`}
            title={status}
          />

          {/* External ID */}
          <span className="font-semibold text-sm text-gray-900 truncate">
            {ot.external_id}
          </span>
        </div>

        {/* GEO_ERROR Badge */}
        {ot.is_geo_error && (
          <div className="flex-shrink-0 ml-2">
            <AlertCircle className="w-4 h-4 text-red-500" title="Geographic Error" />
          </div>
        )}
      </div>

      {/* Project Type Badge */}
      <div className="mb-2">
        <span className={`inline-block px-2 py-1 text-xs font-medium rounded ${colors.badge}`}>
          {projectType}
        </span>
      </div>

      {/* Main Content */}
      <div className="space-y-1 text-xs text-gray-700">
        {/* Cuadrilla Assignment */}
        {ot.cuadrilla_name ? (
          <div className="flex items-start gap-1">
            <span className="text-gray-600 flex-shrink-0">Equipo:</span>
            <span className="font-medium text-gray-900 truncate">{ot.cuadrilla_name}</span>
          </div>
        ) : (
          <div className="text-yellow-700 font-medium">No asignado</div>
        )}

        {/* Geographic Coordinates */}
        {ot.is_geo_error ? (
          <div className="flex items-center gap-1 text-red-700">
            <MapPin className="w-3 h-3 flex-shrink-0" />
            <span>Coordenadas inválidas</span>
          </div>
        ) : (
          <div className="flex items-start gap-1 text-gray-600">
            <MapPin className="w-3 h-3 mt-0.5 flex-shrink-0" />
            <span className="font-mono text-xs">
              {formatCoordinates(ot.lat, ot.long)}
            </span>
          </div>
        )}
      </div>

      {/* Footer: Cliente ID (collapsed) */}
      {!isExpanded && (
        <div className="mt-2 pt-2 border-t border-gray-200">
          <div className="text-xs text-gray-600 truncate">
            Cliente: {ot.cliente_id}
          </div>
        </div>
      )}

      {/* Expanded Details */}
      {isExpanded && (
        <div className="mt-2 pt-2 border-t border-gray-200 space-y-1">
          <div className="text-xs">
            <span className="text-gray-600">Cliente: </span>
            <span className="font-mono text-gray-900">{ot.cliente_id}</span>
          </div>
          <div className="text-xs">
            <span className="text-gray-600">Login: </span>
            <span className="font-mono text-gray-900">{ot.login_id}</span>
          </div>
          {ot.assigned_at && (
            <div className="text-xs">
              <span className="text-gray-600">Asignado: </span>
              <span className="text-gray-900">
                {new Date(ot.assigned_at).toLocaleDateString("es-EC")}
              </span>
            </div>
          )}
          {ot.detention_reason && (
            <div className="text-xs bg-red-50 p-1 rounded border border-red-200">
              <span className="text-red-700 font-medium">Razón detención: </span>
              <span className="text-red-900">{ot.detention_reason}</span>
            </div>
          )}
        </div>
      )}

      {/* Expand/Collapse Button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="mt-2 text-xs text-gray-600 hover:text-gray-900 hover:underline w-full text-center"
      >
        {isExpanded ? "Mostrar menos" : "Mostrar más"}
      </button>

      {/* Drag Handle Indicator */}
      <div className="absolute top-1 right-1 opacity-0 hover:opacity-100 transition-opacity">
        <div className="w-1 h-1 bg-gray-400 rounded-full"></div>
        <div className="w-1 h-1 bg-gray-400 rounded-full mt-0.5"></div>
        <div className="w-1 h-1 bg-gray-400 rounded-full mt-0.5"></div>
      </div>
    </div>
  );
};

export default OTCard;

