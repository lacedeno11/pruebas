import React, { useState, useEffect, useRef } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Circle } from 'react-leaflet'
import L from 'leaflet'
import { fetchOTs, fetchCuadrillas } from '../services/api'
import { toast } from 'react-toastify'
import './MapView.css'

// Fix leaflet default marker icon issue
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
import markerIconRetina from 'leaflet/dist/images/marker-icon-2x.png'

let DefaultIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIconRetina,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})

L.Marker.prototype.setIcon(DefaultIcon)

// Custom marker icons
const otStatusIcons = {
  PREPLANIFICADA: L.divIcon({
    className: 'ot-marker',
    html: `<div style="background-color: #9e9e9e;" class="status-circle">📍</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  }),
  PLANIFICADA: L.divIcon({
    className: 'ot-marker',
    html: `<div style="background-color: #2196f3;" class="status-circle">📍</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  }),
  ASIGNADO_TAREA: L.divIcon({
    className: 'ot-marker',
    html: `<div style="background-color: #4caf50;" class="status-circle">✓</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  }),
  DETENIDA: L.divIcon({
    className: 'ot-marker',
    html: `<div style="background-color: #ff9800;" class="status-circle">⏸</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  }),
  FINALIZADA: L.divIcon({
    className: 'ot-marker',
    html: `<div style="background-color: #66bb6a;" class="status-circle">✅</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  }),
  ANULADA: L.divIcon({
    className: 'ot-marker',
    html: `<div style="background-color: #f44336;" class="status-circle">✕</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  }),
}

const crewIcon = L.divIcon({
  className: 'crew-marker',
  html: `<div class="crew-circle">👥</div>`,
  iconSize: [35, 35],
  iconAnchor: [17, 17],
})

/**
 * Legend Component
 */
function MapLegend() {
  const statusColors = [
    { status: 'PREPLANIFICADA', color: '#9e9e9e' },
    { status: 'PLANIFICADA', color: '#2196f3' },
    { status: 'ASIGNADO_TAREA', color: '#4caf50' },
    { status: 'DETENIDA', color: '#ff9800' },
    { status: 'FINALIZADA', color: '#66bb6a' },
    { status: 'ANULADA', color: '#f44336' },
  ]

  return (
    <div className="map-legend">
      <h4 style={{ margin: '0 0 8px 0', fontSize: '14px', fontWeight: '600' }}>Legend</h4>
      {statusColors.map((item) => (
        <div key={item.status} className="legend-item">
          <div className="legend-color" style={{ backgroundColor: item.color }}></div>
          <span style={{ fontSize: '12px' }}>{item.status}</span>
        </div>
      ))}
      <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #e0e0e0' }}>
        <div className="legend-item">
          <div className="legend-color" style={{ fontSize: '16px', lineHeight: '20px' }}>👥</div>
          <span style={{ fontSize: '12px' }}>Crew Location</span>
        </div>
      </div>
    </div>
  )
}

/**
 * Sidebar Component - Shows selected marker details
 */
function MapSidebar({ selectedMarker, onClose }) {
  if (!selectedMarker) {
    return (
      <div className="map-sidebar">
        <div style={{ textAlign: 'center', color: '#999' }}>
          <p>Click on a marker to see details</p>
        </div>
      </div>
    )
  }

  const isOT = selectedMarker.type === 'ot'
  const isCrew = selectedMarker.type === 'crew'

  return (
    <div className="map-sidebar">
      <button
        onClick={onClose}
        style={{
          background: 'none',
          border: 'none',
          fontSize: '20px',
          cursor: 'pointer',
          float: 'right',
          color: '#999',
        }}
      >
        ✕
      </button>

      <div style={{ clear: 'both' }}>
        {isOT && (
          <div>
            <h3 style={{ marginTop: 0 }}>Work Order</h3>
            <div style={{ fontSize: '13px', lineHeight: '1.6', color: '#666' }}>
              <p>
                <strong>ID:</strong> {selectedMarker.data.external_id}
              </p>
              <p>
                <strong>Status:</strong> {selectedMarker.data.status}
              </p>
              <p>
                <strong>Project:</strong> {selectedMarker.data.project_type}
              </p>
              <p>
                <strong>Client:</strong> {selectedMarker.data.cliente_id || 'N/A'}
              </p>
              <p>
                <strong>Location:</strong> {selectedMarker.data.lat?.toFixed(4)}, {selectedMarker.data.long?.toFixed(4)}
              </p>
              {selectedMarker.data.cuadrilla && (
                <p>
                  <strong>Assigned Crew:</strong> {selectedMarker.data.cuadrilla.name}
                </p>
              )}
            </div>
          </div>
        )}

        {isCrew && (
          <div>
            <h3 style={{ marginTop: 0 }}>Crew</h3>
            <div style={{ fontSize: '13px', lineHeight: '1.6', color: '#666' }}>
              <p>
                <strong>Name:</strong> {selectedMarker.data.name}
              </p>
              <p>
                <strong>Type:</strong> {selectedMarker.data.type}
              </p>
              <p>
                <strong>Assigned OTs:</strong> {selectedMarker.data.ots_asignadas_count}/
                {selectedMarker.data.capacidad_diaria}
              </p>
              <p>
                <strong>Utilization:</strong>{' '}
                {(
                  (selectedMarker.data.ots_asignadas_count / selectedMarker.data.capacidad_diaria) *
                  100
                ).toFixed(1)}
                %
              </p>
              {selectedMarker.data.last_centroid_lat && (
                <p>
                  <strong>Centroid:</strong> {selectedMarker.data.last_centroid_lat?.toFixed(4)}, {selectedMarker.data.last_centroid_long?.toFixed(4)}
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Main MapView Component
 */
export default function MapView() {
  const [ots, setOts] = useState([])
  const [cuadrillas, setCuadrillas] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedMarker, setSelectedMarker] = useState(null)
  const [showOTMarkers, setShowOTMarkers] = useState(true)
  const [showCrewMarkers, setShowCrewMarkers] = useState(true)
  const [showDistanceCircles, setShowDistanceCircles] = useState(true)

  /**
   * Load OTs and Cuadrillas on mount
   */
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true)
        const [otsData, cuadrillasData] = await Promise.all([
          fetchOTs({ limit: 100 }),
          fetchCuadrillas(),
        ])

        setOts(Array.isArray(otsData) ? otsData : [])
        setCuadrillas(Array.isArray(cuadrillasData) ? cuadrillasData : [])
      } catch (error) {
        console.error('Failed to load map data:', error)
        toast.error('Failed to load map data')
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [])

  return (
    <div className="map-container">
      <MapContainer center={[-1.5, -78.5]} zoom={7} className="leaflet-container">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* OT Markers */}
        {showOTMarkers &&
          ots.map((ot) => (
            <Marker
              key={`ot-${ot.id}`}
              position={[ot.lat, ot.long]}
              icon={otStatusIcons[ot.status] || DefaultIcon}
              eventHandlers={{
                click: () => {
                  setSelectedMarker({
                    type: 'ot',
                    data: ot,
                  })
                },
              }}
            >
              <Popup>
                <div style={{ fontSize: '12px' }}>
                  <strong>{ot.external_id}</strong>
                  <br />
                  Status: {ot.status}
                  <br />
                  Project: {ot.project_type}
                </div>
              </Popup>
            </Marker>
          ))}

        {/* Crew Markers */}
        {showCrewMarkers &&
          cuadrillas.map((crew) => {
            // Only show marker if crew has a centroid
            if (!crew.last_centroid_lat || !crew.last_centroid_long) {
              return null
            }

            return (
              <Marker
                key={`crew-${crew.id}`}
                position={[crew.last_centroid_lat, crew.last_centroid_long]}
                icon={crewIcon}
                eventHandlers={{
                  click: () => {
                    setSelectedMarker({
                      type: 'crew',
                      data: crew,
                    })
                  },
                }}
              >
                <Popup>
                  <div style={{ fontSize: '12px' }}>
                    <strong>{crew.name}</strong>
                    <br />
                    Assigned: {crew.ots_asignadas_count}/{crew.capacidad_diaria}
                    <br />
                    Utilization: {((crew.ots_asignadas_count / crew.capacidad_diaria) * 100).toFixed(1)}%
                  </div>
                </Popup>
              </Marker>
            )
          })}

        {/* Distance Circles (10km radius) */}
        {showDistanceCircles &&
          cuadrillas.map((crew) => {
            if (!crew.last_centroid_lat || !crew.last_centroid_long) {
              return null
            }

            return (
              <Circle
                key={`circle-${crew.id}`}
                center={[crew.last_centroid_lat, crew.last_centroid_long]}
                radius={10000} // 10km in meters
                pathOptions={{
                  color: '#2196f3',
                  weight: 2,
                  opacity: 0.3,
                  fill: true,
                  fillColor: '#2196f3',
                  fillOpacity: 0.05,
                }}
              />
            )
          })}
      </MapContainer>

      {/* Legend */}
      <MapLegend />

      {/* Sidebar */}
      <MapSidebar
        selectedMarker={selectedMarker}
        onClose={() => setSelectedMarker(null)}
      />

      {/* Layer Controls */}
      <div className="map-layer-controls">
        <label>
          <input
            type="checkbox"
            checked={showOTMarkers}
            onChange={(e) => setShowOTMarkers(e.target.checked)}
          />
          OT Markers ({ots.length})
        </label>
        <label>
          <input
            type="checkbox"
            checked={showCrewMarkers}
            onChange={(e) => setShowCrewMarkers(e.target.checked)}
          />
          Crew Markers ({cuadrillas.length})
        </label>
        <label>
          <input
            type="checkbox"
            checked={showDistanceCircles}
            onChange={(e) => setShowDistanceCircles(e.target.checked)}
          />
          Distance Circles (10km)
        </label>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="map-loading">
          <div className="spinner"></div>
          <p>Loading map data...</p>
        </div>
      )}
    </div>
  )
}

