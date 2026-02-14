/**
 * OT Marker Component for Map
 *
 * This component represents a single work order (OT) on the Leaflet map.
 * It displays markers with custom icons based on OT status and project type,
 * and provides popups with OT details.
 */

import React from "react";
import { Marker, Popup } from "react-leaflet";
import L from "leaflet";
import { OT, OTStatus, ProjectType } from "../../types";
import { AlertCircle, MapPin } from "lucide-react";

interface OTMarkerProps {
  ot: OT;
  onDetailsClick?: (otId: number) => void;
}

/**
 * Status to color mapping for icons
 */
const statusColors: Record<OTStatus, string> = {
  [OTStatus.PREPLANIFICADA]: "#EAB308", // Yellow
  [OTStatus.PLANIFICADA]: "#3B82F6", // Blue
  [OTStatus.ASIGNADO_TAREA]: "#A855F7", // Purple
  [OTStatus.DETENIDA]: "#EF4444", // Red
  [OTStatus.ANULADA]: "#6B7280", // Gray
  [OTStatus.FINALIZADA]: "#10B981", // Green
};

/**
 * Project type to icon shape/style mapping
 */
const projectTypeStyles: Record<ProjectType, { prefix: string; color: string }> = {
  [ProjectType.PUBLICO]: { prefix: "🏛️", color: "#0066CC" },
  [ProjectType.PRIVADO]: { prefix: "🏢", color: "#00AA00" },
  [ProjectType.TERCERIZADO]: { prefix: "🏭", color: "#FF9900" },
};

/**
 * Create a custom marker icon based on status and project type
 */
function createOTIcon(ot: OT): L.Icon {
  const statusColor = statusColors[ot.status as OTStatus];
  const projectType = ot.project_type as ProjectType;
  const projectStyle = projectTypeStyles[projectType];

  // Create SVG icon with status color circle and project type indicator
  const svgString = `
    <svg width="40" height="50" viewBox="0 0 40 50" xmlns="http://www.w3.org/2000/svg">
      <!-- Pin shape -->
      <path
        d="M20 0C10 0 2 8 2 18c0 15 18 32 18 32s18-17 18-32c0-10-8-18-18-18z"
        fill="${statusColor}"
        stroke="white"
        stroke-width="2"
      />
      <!-- Status indicator dot at bottom -->
      <circle cx="20" cy="35" r="6" fill="white" stroke="${statusColor}" stroke-width="2" />
      <!-- Project type emoji/icon -->
      <text x="20" y="38" text-anchor="middle" font-size="20" alignment-baseline="middle">
        ${projectStyle.prefix}
      </text>
    </svg>
  `;

  const iconUrl = `data:image/svg+xml;base64,${btoa(svgString)}`;

  return new L.Icon({
    iconUrl,
    iconSize: [40, 50],
    iconAnchor: [20, 50], // Bottom center
    popupAnchor: [0, -50], // Top center
    shadowUrl:
      "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
    shadowSize: [41, 41],
    shadowAnchor: [13, 41],
  });
}

/**
 * Create a GEO_ERROR marker icon
 */
function createGeoErrorIcon(): L.Icon {
  const svgString = `
    <svg width="40" height="50" viewBox="0 0 40 50" xmlns="http://www.w3.org/2000/svg">
      <!-- Pin shape in red -->
      <path
        d="M20 0C10 0 2 8 2 18c0 15 18 32 18 32s18-17 18-32c0-10-8-18-18-18z"
        fill="#EF4444"
        stroke="white"
        stroke-width="2"
      />
      <!-- Error icon X -->
      <text x="20" y="20" text-anchor="middle" font-size="24" fill="white" font-weight="bold">
        ✕
      </text>
    </svg>
  `;

  const iconUrl = `data:image/svg+xml;base64,${btoa(svgString)}`;

  return new L.Icon({
    iconUrl,
    iconSize: [40, 50],
    iconAnchor: [20, 50],
    popupAnchor: [0, -50],
    shadowUrl:
      "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
    shadowSize: [41, 41],
    shadowAnchor: [13, 41],
  });
}

/**
 * Status display names
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
 * OT Marker Component
 *
 * Features:
 * - Custom icon based on status (color) and project type (emoji)
 * - Special error icon for GEO_ERROR OTs
 * - Popup with OT details
 * - Link to open OT details
 * - Geolocation validation
 * - Click handler for details view
 */
export const OTMarker: React.FC<OTMarkerProps> = ({ ot, onDetailsClick }) => {
  // Skip rendering if coordinates are invalid
  if (ot.lat === null || ot.long === null) {
    return null;
  }

  // Use appropriate icon
  const icon = ot.is_geo_error ? createGeoErrorIcon() : createOTIcon(ot);
  const status = ot.status as OTStatus;
  const projectType = ot.project_type as ProjectType;

  return (
    <Marker position={[ot.lat, ot.long]} icon={icon}>
      <Popup>
        <div className="w-64 p-4 space-y-3">
          {/* GEO_ERROR Badge */}
          {ot.is_geo_error && (
            <div className="flex items-center gap-2 p-2 bg-red-50 border border-red-200 rounded">
              <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
              <span className="text-xs font-semibold text-red-700">
                Error Geográfico
              </span>
            </div>
          )}

          {/* External ID */}
          <div>
            <label className="text-xs font-semibold text-gray-600">OT ID</label>
            <p className="text-sm font-bold text-gray-900 break-words">
              {ot.external_id}
            </p>
          </div>

          {/* Status and Project Type */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs font-semibold text-gray-600">Estado</label>
              <div className="inline-block px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded">
                {statusDisplayNames[status]}
              </div>
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-600">Tipo</label>
              <div className="inline-block px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded">
                {projectType}
              </div>
            </div>
          </div>

          {/* Cuadrilla Assignment */}
          {ot.cuadrilla_name ? (
            <div>
              <label className="text-xs font-semibold text-gray-600">
                Equipo Asignado
              </label>
              <p className="text-sm text-gray-900">{ot.cuadrilla_name}</p>
            </div>
          ) : (
            <div className="text-sm text-yellow-700 font-medium">
              ⚠️ No asignado a equipo
            </div>
          )}

          {/* Coordinates */}
          <div className="flex items-start gap-2 p-2 bg-gray-50 rounded border border-gray-200">
            <MapPin className="w-4 h-4 mt-0.5 text-gray-600 flex-shrink-0" />
            <div className="text-xs font-mono text-gray-700">
              <div>{ot.lat.toFixed(4)}</div>
              <div>{ot.long.toFixed(4)}</div>
            </div>
          </div>

          {/* Client Info */}
          <div className="text-xs text-gray-600">
            <span className="font-semibold">Cliente:</span> {ot.cliente_id}
          </div>

          {/* Assigned Date */}
          {ot.assigned_at && (
            <div className="text-xs text-gray-600">
              <span className="font-semibold">Asignado:</span>{" "}
              {new Date(ot.assigned_at).toLocaleDateString("es-EC")}
            </div>
          )}

          {/* Action Button */}
          {onDetailsClick && (
            <button
              onClick={() => onDetailsClick(ot.id)}
              className="w-full px-3 py-2 mt-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors"
            >
              Ver Detalles
            </button>
          )}
        </div>
      </Popup>
    </Marker>
  );
};

export default OTMarker;

