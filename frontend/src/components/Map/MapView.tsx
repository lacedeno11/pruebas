/**
 * Map View Component - Main Geographic Visualization
 *
 * This is the main map component that displays work orders (OTs) and
 * technical teams (cuadrillas) on an interactive Leaflet map with controls.
 */

import React, { useEffect, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  ZoomControl,
  ScaleControl,
  LayerGroup,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import { AlertCircle, Loader } from "lucide-react";
import { fetchMapData } from "../../services/api";
import { useUIStore } from "../../stores/uiStore";
import OTMarker from "./OTMarker";
import CuadrillaMarker from "./CuadrillaMarker";

/**
 * Ecuador map center coordinates
 */
const ECUADOR_CENTER: [number, number] = [-1.8312, -78.1834];
const DEFAULT_ZOOM = 7;

/**
 * Status colors for legend
 */
const statusLegend = [
  { color: "#EAB308", status: "Por Planificar" },
  { color: "#3B82F6", status: "Planificada" },
  { color: "#A855F7", status: "Tareas Asignadas" },
  { color: "#EF4444", status: "Detenida" },
  { color: "#10B981", status: "Finalizada" },
  { color: "#6B7280", status: "Anulada" },
];

/**
 * Fit bounds to all markers
 */
function FitBoundsController({
  otCount,
  cuadrillaCount,
}: {
  otCount: number;
  cuadrillaCount: number;
}): null {
  const map = useMap();

  useEffect(() => {
    if (otCount === 0 && cuadrillaCount === 0) {
      return;
    }

    // Get all marker positions
    const bounds = L.latLngBounds([]);

    // Add OT coordinates
    map.eachLayer((layer: any) => {
      if (layer instanceof L.Marker && layer.getLatLng) {
        bounds.extend(layer.getLatLng());
      }
    });

    // Fit to bounds with padding
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [otCount, cuadrillaCount, map]);

  return null;
}

/**
 * Map Legend Component
 */
function MapLegend(): JSX.Element {
  return (
    <div className="leaflet-control leaflet-bar bg-white rounded-lg shadow-lg p-4 max-w-xs">
      <div className="mb-3">
        <h3 className="font-bold text-sm text-gray-900 mb-2">
          Estados de OT
        </h3>
        <div className="space-y-1">
          {statusLegend.map((item) => (
            <div key={item.status} className="flex items-center gap-2 text-xs">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: item.color }}
              />
              <span className="text-gray-700">{item.status}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="border-t border-gray-200 pt-3">
        <h3 className="font-bold text-sm text-gray-900 mb-2">
          Tipos de Proyecto
        </h3>
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs">
            <span className="text-lg">🏛️</span>
            <span className="text-gray-700">Público</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-lg">🏢</span>
            <span className="text-gray-700">Privado</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-lg">🏭</span>
            <span className="text-gray-700">Tercerizado</span>
          </div>
        </div>
      </div>

      <div className="border-t border-gray-200 pt-3">
        <h3 className="font-bold text-sm text-gray-900 mb-2">
          Equipos (Cuadrillas)
        </h3>
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs">
            <span className="text-lg">⭐</span>
            <span className="text-gray-700">Principal</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-lg">🔄</span>
            <span className="text-gray-700">Reserva</span>
          </div>
        </div>
      </div>

      <div className="border-t border-gray-200 pt-3">
        <div className="flex items-center gap-2 text-xs">
          <AlertCircle className="w-4 h-4 text-red-600" />
          <span className="text-gray-700">Error Geográfico</span>
        </div>
        <div className="text-xs text-gray-500 mt-1">
          Círculos discontinuos = radio de 10km
        </div>
      </div>
    </div>
  );
}

/**
 * Map View Component
 *
 * Features:
 * - Leaflet map centered on Ecuador
 * - OpenStreetMap tiles
 * - OT markers with custom icons
 * - Cuadrilla markers with 10km radius circles
 * - Interactive legend
 * - Zoom and scale controls
 * - Auto-fit bounds to all markers
 * - Layer controls for toggling visibility
 * - Error and loading states
 */
export const MapView: React.FC = () => {
  const [mapData, setMapData] = React.useState<any>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [showOTs, setShowOTs] = React.useState(true);
  const [showCuadrillas, setShowCuadrillas] = React.useState(true);
  const legendRef = useRef<HTMLDivElement>(null);

  // Fetch map data
  React.useEffect(() => {
    const loadMapData = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const data = await fetchMapData();
        setMapData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error loading map data");
      } finally {
        setIsLoading(false);
      }
    };

    loadMapData();

    // Refetch every 60 seconds
    const interval = setInterval(loadMapData, 60000);
    return () => clearInterval(interval);
  }, []);

  // Error state
  if (error) {
    return (
      <div className="w-full h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-600 font-semibold mb-4">Error cargando mapa</p>
          <p className="text-gray-600">{error}</p>
        </div>
      </div>
    );
  }

  // Loading state
  if (isLoading || !mapData) {
    return (
      <div className="w-full h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <Loader className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Cargando mapa...</p>
        </div>
      </div>
    );
  }

  const ots = mapData.ots || [];
  const cuadrillas = mapData.cuadrillas || [];
  const bounds = mapData.bounds || {
    north: 2,
    south: -5,
    east: -75,
    west: -81,
  };

  return (
    <div className="relative w-full h-screen">
      <MapContainer
        center={ECUADOR_CENTER}
        zoom={DEFAULT_ZOOM}
        style={{ height: "100%", width: "100%" }}
        zoomControl={false}
      >
        {/* Base layer */}
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />

        {/* Controls */}
        <ZoomControl position="topright" />
        <ScaleControl position="bottomright" />

        {/* Fit bounds controller */}
        <FitBoundsController otCount={ots.length} cuadrillaCount={cuadrillas.length} />

        {/* OTs Layer */}
        {showOTs && (
          <LayerGroup>
            {ots.map((ot) => (
              <OTMarker key={ot.id} ot={ot} />
            ))}
          </LayerGroup>
        )}

        {/* Cuadrillas Layer */}
        {showCuadrillas && (
          <LayerGroup>
            {cuadrillas.map((cuadrilla) => (
              <CuadrillaMarker key={cuadrilla.id} cuadrilla={cuadrilla} />
            ))}
          </LayerGroup>
        )}
      </MapContainer>

      {/* Legend - Floating Control */}
      <div
        ref={legendRef}
        className="absolute top-4 left-4 z-40 leaflet-control-container"
      >
        <MapLegend />
      </div>

      {/* Toggle Controls - Floating Buttons */}
      <div className="absolute bottom-4 right-4 z-40 flex flex-col gap-2">
        {/* OTs Toggle */}
        <button
          onClick={() => setShowOTs(!showOTs)}
          className={`
            px-4 py-2 rounded-lg font-medium transition-all
            ${
              showOTs
                ? "bg-blue-600 text-white shadow-lg"
                : "bg-white text-gray-700 shadow border border-gray-300"
            }
          `}
          title={showOTs ? "Ocultar OTs" : "Mostrar OTs"}
        >
          📍 OTs {ots.length}
        </button>

        {/* Cuadrillas Toggle */}
        <button
          onClick={() => setShowCuadrillas(!showCuadrillas)}
          className={`
            px-4 py-2 rounded-lg font-medium transition-all
            ${
              showCuadrillas
                ? "bg-blue-600 text-white shadow-lg"
                : "bg-white text-gray-700 shadow border border-gray-300"
            }
          `}
          title={showCuadrillas ? "Ocultar Equipos" : "Mostrar Equipos"}
        >
          👥 Equipos {cuadrillas.length}
        </button>
      </div>

      {/* Info Panel - Top Right */}
      <div className="absolute top-4 right-4 z-40 bg-white rounded-lg shadow-lg p-4 max-w-xs">
        <div className="text-sm">
          <div className="font-bold text-gray-900 mb-2">
            Información del Mapa
          </div>
          <div className="space-y-1 text-gray-700 text-xs">
            <div>
              <span className="font-semibold">OTs Visibles:</span> {showOTs ? ots.length : 0}
            </div>
            <div>
              <span className="font-semibold">Equipos Visibles:</span>{" "}
              {showCuadrillas ? cuadrillas.length : 0}
            </div>
            <div className="text-gray-500 text-xs mt-2">
              Última actualización: {new Date(mapData.timestamp).toLocaleTimeString("es-EC")}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MapView;

