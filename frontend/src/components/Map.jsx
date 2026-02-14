import React, { useState, useEffect } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  useMap,
} from 'react-leaflet';
import L from 'leaflet';
import { useOT } from '../contexts/OTContext';

/**
 * Status icon colors for OT markers
 */
const STATUS_ICON_COLORS = {
  PREPLANIFICADA: '#3B82F6', // blue
  PLANIFICADA: '#FBBF24',    // yellow
  ASIGNADO_TAREA: '#10B981', // green
  DETENIDA: '#EF4444',       // red
  ANULADA: '#9CA3AF',        // gray
  FINALIZADA: '#059669',     // dark green
};

/**
 * Create custom icon for OT markers
 */
const createOTIcon = (status) => {
  const color = STATUS_ICON_COLORS[status] || STATUS_ICON_COLORS.PREPLANIFICADA;
  
  return L.divIcon({
    html: `
      <div style="
        background-color: ${color};
        width: 28px;
        height: 28px;
        border-radius: 50%;
        border: 3px solid white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: 14px;
      ">
        📋
      </div>
    `,
    iconSize: [28, 28],
    className: 'ot-icon',
  });
};

/**
 * Create custom icon for Cuadrilla markers (centroid)
 */
const createCuadrillaIcon = () => {
  return L.divIcon({
    html: `
      <div style="
        background-color: #8B5CF6;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        border: 3px solid white;
        box-shadow: 0 2px 6px rgba(0,0,0,0.4);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: 16px;
      ">
        👥
      </div>
    `,
    iconSize: [32, 32],
    className: 'cuadrilla-icon',
  });
};

/**
 * MapUpdater - Child component to update map bounds when data changes
 */
function MapUpdater({ ots, cuadrillas }) {
  const map = useMap();

  useEffect(() => {
    if (!map) return;

    // Collect all valid coordinates
    const allCoords = [];

    // Add OT coordinates
    ots.forEach(ot => {
      if (ot.lat && ot.long) {
        allCoords.push([ot.lat, ot.long]);
      }
    });

    // Add Cuadrilla centroid coordinates
    cuadrillas.forEach(c => {
      if (c.last_centroid_lat && c.last_centroid_long) {
        allCoords.push([c.last_centroid_lat, c.last_centroid_long]);
      }
    });

    // Fit bounds if we have coordinates
    if (allCoords.length > 0) {
      const bounds = L.latLngBounds(allCoords);
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [ots, cuadrillas, map]);

  return null;
}

/**
 * Legend component showing icon meanings
 */
function Legend() {
  return (
    <div className="absolute bottom-4 left-4 bg-white rounded-lg shadow-lg p-4 z-10 text-sm">
      <h4 className="font-semibold text-gray-800 mb-3">Leyenda</h4>
      
      {/* OT Status Legend */}
      <div className="mb-3">
        <h5 className="font-medium text-gray-700 text-xs mb-2">Estados OT:</h5>
        <div className="space-y-1">
          {Object.entries(STATUS_ICON_COLORS).map(([status, color]) => (
            <div key={status} className="flex items-center gap-2">
              <div
                className="w-5 h-5 rounded-full border-2 border-white"
                style={{ backgroundColor: color }}
              ></div>
              <span className="text-xs text-gray-600">
                {status.replace(/_/g, ' ')}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Cuadrilla Legend */}
      <div>
        <h5 className="font-medium text-gray-700 text-xs mb-2">Cuadrillas:</h5>
        <div className="flex items-center gap-2">
          <div
            className="w-6 h-6 rounded-full border-2 border-white"
            style={{ backgroundColor: '#8B5CF6' }}
          ></div>
          <span className="text-xs text-gray-600">Centroide</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Map - Main map component with Leaflet integration
 *
 * Props:
 * - center: Default map center [lat, long] (default: Ecuador [-1.8312, -78.1834])
 * - zoom: Default zoom level (default: 7)
 */
function Map({ center = [-1.8312, -78.1834], zoom = 7 }) {
  const { ots, cuadrillas } = useOT();
  const [displayedOTs, setDisplayedOTs] = useState([]);
  const [displayedCuadrillas, setDisplayedCuadrillas] = useState([]);

  /**
   * Filter OTs with valid coordinates
   */
  useEffect(() => {
    const filtered = ots.filter(ot => ot.lat && ot.long);
    setDisplayedOTs(filtered);
  }, [ots]);

  /**
   * Filter Cuadrillas with valid centroid coordinates
   */
  useEffect(() => {
    const filtered = cuadrillas.filter(
      c => c.last_centroid_lat && c.last_centroid_long
    );
    setDisplayedCuadrillas(filtered);
  }, [cuadrillas]);

  return (
    <div className="relative w-full h-full">
      <MapContainer
        center={center}
        zoom={zoom}
        scrollWheelZoom={true}
        style={{
          height: '100%',
          width: '100%',
        }}
      >
        {/* OpenStreetMap Tile Layer */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Map Updater - Updates bounds when data changes */}
        <MapUpdater ots={displayedOTs} cuadrillas={displayedCuadrillas} />

        {/* OT Markers */}
        {displayedOTs.map(ot => (
          <Marker
            key={`ot-${ot.id}`}
            position={[ot.lat, ot.long]}
            icon={createOTIcon(ot.status)}
          >
            <Popup className="ot-popup">
              <div className="w-64 text-sm">
                <h4 className="font-bold text-gray-900 mb-2">
                  OT {ot.external_id}
                </h4>
                
                <div className="space-y-1 text-gray-700 mb-2">
                  <div className="flex justify-between">
                    <span className="font-medium">Proyecto:</span>
                    <span>{ot.project_type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-medium">Estado:</span>
                    <span className="font-semibold">{ot.status}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-medium">Cliente:</span>
                    <span className="truncate ml-2">{ot.cliente_id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-medium">Coordenadas:</span>
                    <span className="font-mono text-xs">
                      {ot.lat.toFixed(4)}, {ot.long.toFixed(4)}
                    </span>
                  </div>
                </div>

                {/* Geo Error Warning */}
                {ot.geo_error && (
                  <div className="bg-red-50 border border-red-200 rounded p-2 text-red-700 text-xs mb-2">
                    ⚠️ Error de geolocalización
                  </div>
                )}

                {/* Detention Info */}
                {ot.detention_reason && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded p-2 text-yellow-800 text-xs mb-2">
                    <strong>Motivo detención:</strong> {ot.detention_reason}
                  </div>
                )}

                {/* Cuadrilla Assignment Info */}
                {ot.asignaciones && ot.asignaciones.length > 0 && (
                  <div className="bg-green-50 border border-green-200 rounded p-2 text-green-800 text-xs">
                    <strong>Asignada a:</strong> Cuadrilla #{ot.asignaciones[0].cuadrilla_id}
                  </div>
                )}
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Cuadrilla Centroid Markers */}
        {displayedCuadrillas.map(cuadrilla => (
          <Marker
            key={`cuadrilla-${cuadrilla.id}`}
            position={[cuadrilla.last_centroid_lat, cuadrilla.last_centroid_long]}
            icon={createCuadrillaIcon()}
          >
            <Popup className="cuadrilla-popup">
              <div className="w-48 text-sm">
                <h4 className="font-bold text-gray-900 mb-2">
                  {cuadrilla.name}
                </h4>
                
                <div className="space-y-1 text-gray-700">
                  <div className="flex justify-between">
                    <span className="font-medium">Tipo:</span>
                    <span>{cuadrilla.type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-medium">Carga:</span>
                    <span>
                      {cuadrilla.current_load} / {cuadrilla.capacity}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-medium">Utilización:</span>
                    <span>
                      {Math.round((cuadrilla.current_load / cuadrilla.capacity) * 100)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-medium">Estado:</span>
                    <span className={cuadrilla.is_active ? 'text-green-600' : 'text-red-600'}>
                      {cuadrilla.is_active ? 'Activa' : 'Inactiva'}
                    </span>
                  </div>
                </div>
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Legend */}
        <Legend />
      </MapContainer>

      {/* Empty State */}
      {displayedOTs.length === 0 && displayedCuadrillas.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/10 rounded">
          <div className="bg-white rounded-lg p-6 text-center shadow-lg">
            <p className="text-gray-600">
              No hay OTs o cuadrillas con coordenadas para mostrar en el mapa
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export default Map;

