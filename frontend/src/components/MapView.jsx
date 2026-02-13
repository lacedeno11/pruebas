import React, { useMemo } from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import { useQuery } from '@tanstack/react-query'
import { fetchOTs, fetchCuadrillas } from '../services/api'
import { StatusColors, ProjectTypeColors } from '../types/index'

// Ecuador map center coordinates
const ECUADOR_CENTER = {
  lat: -1.831239,
  lng: -78.183406
}

// Default zoom level
const DEFAULT_ZOOM = 7

/**
 * Create a custom marker icon with a specific color
 * @param {string} color - Hex color for the marker
 * @param {string} label - Single letter to display in marker
 * @returns {L.Icon} Leaflet icon
 */
function createColoredIcon(color, label = '') {
  return L.divIcon({
    html: `
      <div style="
        background-color: ${color};
        color: white;
        border-radius: 50%;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 14px;
        border: 3px solid white;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        cursor: pointer;
      ">
        ${label}
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -16],
    className: 'custom-marker'
  })
}

export function MapView() {
  // Fetch OTs
  const {
    data: otsList = [],
    isLoading: otsLoading,
    error: otsError
  } = useQuery({
    queryKey: ['ots'],
    queryFn: () => fetchOTs({}),
    refetchInterval: 30000,
    staleTime: 30000
  })

  // Fetch Cuadrillas
  const {
    data: cuadrillasList = [],
    isLoading: cuadrillasLoading,
    error: cuadrillasError
  } = useQuery({
    queryKey: ['cuadrillas'],
    queryFn: () => fetchCuadrillas(),
    refetchInterval: 30000,
    staleTime: 30000
  })

  // Filter OTs with valid coordinates
  const validOTs = useMemo(() => {
    return otsList.filter(ot => 
      ot.lat !== null && 
      ot.long !== null && 
      !ot.error_geo &&
      typeof ot.lat === 'number' &&
      typeof ot.long === 'number'
    )
  }, [otsList])

  // Filter cuadrillas with centroid coordinates
  const validCuadrillas = useMemo(() => {
    return cuadrillasList.filter(cuadrilla =>
      cuadrilla.last_centroid_lat !== null &&
      cuadrilla.last_centroid_long !== null &&
      typeof cuadrilla.last_centroid_lat === 'number' &&
      typeof cuadrilla.last_centroid_long === 'number'
    )
  }, [cuadrillasList])

  // Group OTs by status for statistics
  const otsByStatus = useMemo(() => {
    const grouped = {}
    validOTs.forEach(ot => {
      grouped[ot.status] = (grouped[ot.status] || 0) + 1
    })
    return grouped
  }, [validOTs])

  if (otsError || cuadrillasError) {
    return (
      <div className="map-view-error">
        <p>Error loading map data</p>
        {otsError && <p>{otsError.message}</p>}
        {cuadrillasError && <p>{cuadrillasError.message}</p>}
      </div>
    )
  }

  return (
    <div className="map-view-container">
      <div className="map-header">
        <h2>Geographic View</h2>
        <div className="map-stats">
          <div className="map-stat">
            <span className="map-stat-label">Total OTs:</span>
            <span className="map-stat-value">{validOTs.length}</span>
          </div>
          <div className="map-stat">
            <span className="map-stat-label">Teams:</span>
            <span className="map-stat-value">{validCuadrillas.length}</span>
          </div>
        </div>
      </div>

      <div className="map-legend">
        <div className="legend-section">
          <h4>OT Status</h4>
          <div className="legend-items">
            {Object.entries(StatusColors).map(([status, color]) => (
              <div key={status} className="legend-item">
                <div
                  className="legend-color"
                  style={{ backgroundColor: color }}
                />
                <span className="legend-label">
                  {status} {otsByStatus[status] ? `(${otsByStatus[status]})` : '(0)'}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {otsLoading || cuadrillasLoading ? (
        <div className="map-loading">
          <div className="spinner"></div>
          <p>Loading map data...</p>
        </div>
      ) : (
        <MapContainer
          center={[ECUADOR_CENTER.lat, ECUADOR_CENTER.lng]}
          zoom={DEFAULT_ZOOM}
          scrollWheelZoom={true}
          className="map-container"
        >
          {/* OpenStreetMap Tile Layer */}
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {/* Render OT Markers */}
          {validOTs.map(ot => (
            <Marker
              key={`ot-${ot.id}`}
              position={[ot.lat, ot.long]}
              icon={createColoredIcon(
                StatusColors[ot.status] || '#888888',
                ot.project_type === 'PUBLICO' ? 'P' : ot.project_type === 'PRIVADO' ? 'R' : 'T'
              )}
            >
              <Popup className="ot-popup">
                <div className="popup-content">
                  <h4 className="popup-title">{ot.external_id}</h4>
                  <div className="popup-field">
                    <span className="popup-label">Client:</span>
                    <span className="popup-value">{ot.cliente_id}</span>
                  </div>
                  <div className="popup-field">
                    <span className="popup-label">Status:</span>
                    <span
                      className="popup-badge"
                      style={{ backgroundColor: StatusColors[ot.status] }}
                    >
                      {ot.status}
                    </span>
                  </div>
                  <div className="popup-field">
                    <span className="popup-label">Type:</span>
                    <span
                      className="popup-badge"
                      style={{ backgroundColor: ProjectTypeColors[ot.project_type] }}
                    >
                      {ot.project_type}
                    </span>
                  </div>
                  <div className="popup-field">
                    <span className="popup-label">Location:</span>
                    <span className="popup-coords">
                      {ot.lat.toFixed(4)}, {ot.long.toFixed(4)}
                    </span>
                  </div>
                  {ot.cuadrilla_id && (
                    <div className="popup-field">
                      <span className="popup-label">Assigned to:</span>
                      <span className="popup-value">Cuadrilla #{ot.cuadrilla_id}</span>
                    </div>
                  )}
                  <div className="popup-field">
                    <span className="popup-label">Created:</span>
                    <span className="popup-value">
                      {new Date(ot.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}

          {/* Render Cuadrilla Centroid Markers */}
          {validCuadrillas.map(cuadrilla => (
            <Marker
              key={`cuadrilla-${cuadrilla.id}`}
              position={[cuadrilla.last_centroid_lat, cuadrilla.last_centroid_long]}
              icon={createColoredIcon('#2196F3', 'T')}
            >
              <Popup className="cuadrilla-popup">
                <div className="popup-content">
                  <h4 className="popup-title">Team: {cuadrilla.name}</h4>
                  <div className="popup-field">
                    <span className="popup-label">Type:</span>
                    <span className="popup-value">{cuadrilla.type}</span>
                  </div>
                  <div className="popup-field">
                    <span className="popup-label">Current Load:</span>
                    <span className="popup-value">
                      {cuadrilla.current_load} / {cuadrilla.capacity}
                    </span>
                  </div>
                  <div className="popup-field">
                    <span className="popup-label">Load %:</span>
                    <span className="popup-value">
                      {Math.round((cuadrilla.current_load / cuadrilla.capacity) * 100)}%
                    </span>
                  </div>
                  <div className="popup-field">
                    <span className="popup-label">Centroid:</span>
                    <span className="popup-coords">
                      {cuadrilla.last_centroid_lat.toFixed(4)}, {cuadrilla.last_centroid_long.toFixed(4)}
                    </span>
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      )}

      {/* Info Box for OTs without coordinates */}
      {otsList.length > validOTs.length && (
        <div className="map-info-box">
          <p>
            ⚠️ {otsList.length - validOTs.length} OT(s) have missing or invalid location data
          </p>
        </div>
      )}
    </div>
  )
}

// Map View Styles
const mapViewStyles = `
.map-view-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #f5f5f5;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.map-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background-color: white;
  border-bottom: 1px solid #e0e0e0;
}

.map-header h2 {
  margin: 0;
  font-size: 18px;
  color: #333;
  font-weight: 600;
}

.map-stats {
  display: flex;
  gap: 24px;
}

.map-stat {
  display: flex;
  align-items: center;
  gap: 8px;
}

.map-stat-label {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.map-stat-value {
  font-size: 16px;
  color: #2196F3;
  font-weight: 600;
}

.map-legend {
  padding: 12px 16px;
  background-color: white;
  border-bottom: 1px solid #e0e0e0;
  max-height: 120px;
  overflow-y: auto;
}

.legend-section h4 {
  margin: 0 0 8px 0;
  font-size: 12px;
  color: #333;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.legend-items {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 8px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #666;
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 2px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  flex-shrink: 0;
}

.legend-label {
  font-weight: 500;
}

.map-container {
  flex: 1;
  width: 100%;
  height: 100%;
  background-color: #e0e0e0;
  border-radius: 0 0 8px 8px;
}

.map-loading {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 400px;
  gap: 16px;
  background-color: #f5f5f5;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #2196F3;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.map-view-error {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 400px;
  gap: 16px;
  color: #d32f2f;
  background-color: #f5f5f5;
}

.map-view-error p {
  margin: 0;
  font-size: 14px;
}

.map-info-box {
  padding: 12px 16px;
  background-color: #fff3cd;
  border-top: 1px solid #e0e0e0;
  color: #856404;
  font-size: 12px;
  border-radius: 0 0 8px 8px;
}

.map-info-box p {
  margin: 0;
}

/* Leaflet Popup Styling */
.popup-content {
  font-size: 12px;
  color: #333;
  min-width: 250px;
}

.popup-title {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 600;
  color: #333;
  border-bottom: 2px solid #e0e0e0;
  padding-bottom: 6px;
}

.popup-field {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  line-height: 1.4;
}

.popup-label {
  font-weight: 600;
  color: #666;
  min-width: 70px;
}

.popup-value {
  color: #333;
  word-break: break-word;
}

.popup-badge {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 3px;
  color: white;
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.popup-coords {
  font-family: monospace;
  font-size: 11px;
  color: #0066cc;
}

.ot-popup .popup-content {
  background-color: #f9f9f9;
  padding: 8px;
  border-radius: 4px;
}

.cuadrilla-popup .popup-content {
  background-color: #e3f2fd;
  padding: 8px;
  border-radius: 4px;
}

.leaflet-popup-content-wrapper {
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.leaflet-popup-tip {
  background-color: white;
}

/* Custom marker styling */
.custom-marker {
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
  transition: filter 0.2s ease;
}

.custom-marker:hover {
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.3));
}

/* Responsive Design */
@media (max-width: 768px) {
  .map-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .map-stats {
    width: 100%;
    justify-content: space-between;
  }

  .legend-items {
    grid-template-columns: repeat(2, 1fr);
  }

  .popup-content {
    min-width: 200px;
  }

  .map-legend {
    max-height: 100px;
  }
}

@media (max-width: 480px) {
  .map-header h2 {
    font-size: 16px;
  }

  .map-stats {
    font-size: 11px;
  }

  .legend-items {
    grid-template-columns: 1fr;
  }

  .popup-content {
    min-width: 180px;
    font-size: 11px;
  }

  .popup-label {
    min-width: 60px;
    font-size: 10px;
  }
}
`

export default MapView

