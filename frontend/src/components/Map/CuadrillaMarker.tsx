/**
 * Cuadrilla (Team) Marker Component for Map
 *
 * This component represents a technical team (cuadrilla) on the Leaflet map.
 * It displays team location markers with 10km proximity circles and popups
 * showing capacity utilization and team details.
 */

import React from "react";
import { Marker, Popup, Circle } from "react-leaflet";
import L from "leaflet";
import { Cuadrilla, CuadrillaType } from "../../types";
import { Users, TrendingUp } from "lucide-react";

interface CuadrillaMarkerProps {
  cuadrilla: Cuadrilla;
  onDetailsClick?: (cuadrillaId: number) => void;
}

/**
 * Cuadrilla type to color mapping
 */
const cuadrillaTypeColors: Record<CuadrillaType, { icon: string; color: string; fillColor: string }> = {
  [CuadrillaType.PRINCIPAL]: {
    icon: "⭐",
    color: "#2563EB", // Blue
    fillColor: "#3B82F6",
  },
  [CuadrillaType.RESERVA]: {
    icon: "🔄",
    color: "#7C3AED", // Purple
    fillColor: "#A78BFA",
  },
};

/**
 * Proximity threshold in km
 */
const PROXIMITY_RADIUS_KM = 10;

/**
 * Create a custom marker icon for cuadrilla based on type
 */
function createCuadrillaIcon(cuadrilla: Cuadrilla): L.Icon {
  const typeConfig = cuadrillaTypeColors[cuadrilla.type as CuadrillaType];

  const svgString = `
    <svg width="40" height="50" viewBox="0 0 40 50" xmlns="http://www.w3.org/2000/svg">
      <!-- Pin shape -->
      <path
        d="M20 0C10 0 2 8 2 18c0 15 18 32 18 32s18-17 18-32c0-10-8-18-18-18z"
        fill="${typeConfig.color}"
        stroke="white"
        stroke-width="2"
      />
      <!-- Team icon inside -->
      <circle cx="20" cy="18" r="8" fill="white" />
      <text x="20" y="22" text-anchor="middle" font-size="14" fill="${typeConfig.color}" font-weight="bold">
        👥
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
 * Calculate capacity utilization percentage
 */
function getUtilizationPercentage(current: number, max: number): number {
  if (max === 0) return 0;
  return Math.min(100, Math.round((current / max) * 100));
}

/**
 * Get utilization color based on percentage
 */
function getUtilizationColor(percentage: number): string {
  if (percentage < 50) return "#10B981"; // Green
  if (percentage < 75) return "#F59E0B"; // Amber
  if (percentage < 100) return "#EF4444"; // Red
  return "#991B1B"; // Dark Red (over capacity)
}

/**
 * Get utilization status text
 */
function getUtilizationStatus(percentage: number): string {
  if (percentage < 50) return "Disponible";
  if (percentage < 75) return "Moderado";
  if (percentage < 100) return "Alto";
  return "Lleno";
}

/**
 * Cuadrilla Marker Component
 *
 * Features:
 * - Custom icon based on cuadrilla type (PRINCIPAL or RESERVA)
 * - 10km proximity circle showing coverage area
 * - Popup with team details and capacity bar
 * - Utilization status color coding
 * - Team capacity information
 * - Click handler for team details
 */
export const CuadrillaMarker: React.FC<CuadrillaMarkerProps> = ({
  cuadrilla,
  onDetailsClick,
}) => {
  // Skip rendering if no centroid coordinates
  if (
    cuadrilla.last_centroid_lat === null ||
    cuadrilla.last_centroid_long === null
  ) {
    return null;
  }

  const icon = createCuadrillaIcon(cuadrilla);
  const typeConfig = cuadrillaTypeColors[cuadrilla.type as CuadrillaType];
  const utilizationPercentage = getUtilizationPercentage(
    cuadrilla.current_load,
    cuadrilla.max_daily_capacity
  );
  const utilizationColor = getUtilizationColor(utilizationPercentage);
  const utilizationStatus = getUtilizationStatus(utilizationPercentage);

  const position: [number, number] = [
    cuadrilla.last_centroid_lat,
    cuadrilla.last_centroid_long,
  ];

  return (
    <>
      {/* Proximity Circle (10km radius) */}
      <Circle
        center={position}
        radius={PROXIMITY_RADIUS_KM * 1000} // Convert km to meters
        pathOptions={{
          color: typeConfig.fillColor,
          fillColor: typeConfig.fillColor,
          fillOpacity: 0.1,
          weight: 2,
          dashArray: "5, 5",
        }}
      />

      {/* Cuadrilla Marker */}
      <Marker position={position} icon={icon}>
        <Popup>
          <div className="w-72 p-4 space-y-3">
            {/* Header with Team Name and Type */}
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-lg">{typeConfig.icon}</span>
                <h3 className="text-lg font-bold text-gray-900">
                  {cuadrilla.name}
                </h3>
              </div>
              <div className="inline-block px-2 py-1 text-xs font-medium rounded">
                {cuadrilla.type === CuadrillaType.PRINCIPAL ? (
                  <span className="bg-blue-100 text-blue-800">Principal</span>
                ) : (
                  <span className="bg-purple-100 text-purple-800">Reserva</span>
                )}
              </div>
            </div>

            {/* Capacity Utilization Section */}
            <div className="border-t border-gray-200 pt-3">
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-semibold text-gray-600">
                  Capacidad Diaria
                </label>
                <span
                  className="text-xs font-bold px-2 py-1 rounded"
                  style={{
                    backgroundColor: utilizationColor,
                    color: "white",
                  }}
                >
                  {utilizationStatus}
                </span>
              </div>

              {/* Capacity Numbers */}
              <div className="text-sm text-gray-700 mb-2">
                <span className="font-semibold">{cuadrilla.current_load}</span>/
                <span className="text-gray-600">{cuadrilla.max_daily_capacity}</span> OTs
              </div>

              {/* Progress Bar */}
              <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden border border-gray-300">
                <div
                  className="h-full transition-all duration-300"
                  style={{
                    width: `${Math.min(utilizationPercentage, 100)}%`,
                    backgroundColor: utilizationColor,
                  }}
                />
              </div>

              {/* Percentage Text */}
              <div className="mt-2 text-xs text-gray-600 text-right">
                {utilizationPercentage}% utilizado
              </div>
            </div>

            {/* Available Capacity */}
            <div className="bg-blue-50 border border-blue-200 rounded p-2">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-blue-600 flex-shrink-0" />
                <div className="text-sm">
                  <span className="text-blue-900 font-semibold">
                    {Math.max(0, cuadrilla.max_daily_capacity - cuadrilla.current_load)}
                  </span>
                  <span className="text-blue-700"> espacio disponible</span>
                </div>
              </div>
            </div>

            {/* Centroid Coordinates */}
            <div className="text-xs text-gray-600 bg-gray-50 p-2 rounded border border-gray-200">
              <div className="font-semibold text-gray-700 mb-1">Ubicación Centroide</div>
              <div className="font-mono">
                <div>{cuadrilla.last_centroid_lat.toFixed(4)}</div>
                <div>{cuadrilla.last_centroid_long.toFixed(4)}</div>
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Rango de proximidad: {PROXIMITY_RADIUS_KM}km
              </div>
            </div>

            {/* Action Button */}
            {onDetailsClick && (
              <button
                onClick={() => onDetailsClick(cuadrilla.id)}
                className="w-full px-3 py-2 mt-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors"
              >
                Ver Detalles del Equipo
              </button>
            )}
          </div>
        </Popup>
      </Marker>
    </>
  );
};

export default CuadrillaMarker;

