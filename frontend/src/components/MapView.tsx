import { useMemo } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Circle,
  useMap,
} from 'react-leaflet';
import L from 'leaflet';
import { OT, Cuadrilla, OTStatus, CuadrillaType } from '@/types';
import { useOTs } from '@/hooks/useOTs';
import { useCuadrillas } from '@/hooks/useCuadrillas';
import { useUIStore } from '@/stores/uiStore';
import MapLegend from './MapLegend';

// Ecuador center coordinates
const ECUADOR_CENTER: [number, number] = [-1.831239, -78.183406];
const DEFAULT_ZOOM = 7;

// Status color mapping for markers
const statusMarkerColors: Record<OTStatus, string> = {
  [OTStatus.PREPLANIFICADA]: '#3b82f6', // blue
  [OTStatus.PLANIFICADA]: '#eab308', // yellow
  [OTStatus.ASIGNADO_TAREA]: '#22c55e', // green
  [OTStatus.DETENIDA]: '#f97316', // orange
  [OTStatus.ANULADA]: '#ef4444', // red
  [OTStatus.FINALIZADA]: '#6b7280', // gray
};

// Cuadrilla circle colors
const cuadrillaColors: Record<CuadrillaType, string> = {
  [CuadrillaType.PRINCIPAL]: '#3b82f6', // blue
  [CuadrillaType.RESERVA]: '#a78bfa', // purple
};

/**
 * Custom Leaflet icon for OT markers
 */
function createOTMarkerIcon(status: OTStatus) {
  const color = statusMarkerColors[status];
  return L.divIcon({
    className: 'custom-ot-marker',
    html: `
      <div style="
        width: 24px;
        height: 24px;
        background-color: ${color};
        border: 3px solid white;
        border-radius: 50%;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
      "></div>
    `,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -12],
  });
}

/**
 * Map View component displaying OTs and Cuadrilla zones
 */
export function MapView() {
  const { data: ots = [], isLoading: otsLoading } = useOTs();
  const { data: cuadrillas = [], isLoading: cuadrillasLoading } = useCuadrillas();
  const { setSelectedOT, mapCenter, setMapCenter } = useUIStore();

  // Filter OTs with valid coordinates
  const otsWithCoordinates = useMemo(
    () => ots.filter((ot) => ot.lat && ot.long),
    [ots]
  );

  // Filter Cuadrillas with centroid
  const cuadrillasWithCentroid = useMemo(
    () =>
      cuadrillas.filter(
        (c) => c.lastCentroidLat && c.lastCentroidLong && c.isActive
      ),
    [cuadrillas]
  );

  // Handle marker click
  const handleOTMarkerClick = (ot: OT) => {
    setSelectedOT(ot.id);
  };

  if (otsLoading || cuadrillasLoading) {
    return (
      <div className="w-full min-h-96 bg-gray-100 rounded-lg flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-gray-600">Cargando mapa...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full min-h-96 rounded-lg overflow-hidden shadow-lg relative">
      <MapContainer
        center={[mapCenter.lat, mapCenter.lng]}
        zoom={mapCenter.zoom}
        scrollWheelZoom={true}
        style={{ height: '100%', width: '100%', minHeight: '500px' }}
      >
        {/* Tile Layer */}
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          maxZoom={19}
        />

        {/* Cuadrilla Service Zones (10km circles) */}
        {cuadrillasWithCentroid.map((cuadrilla) => (
          <Circle
            key={`cuadrilla-${cuadrilla.id}`}
            center={[cuadrilla.lastCentroidLat!, cuadrilla.lastCentroidLong!]}
            radius={10000} // 10km in meters
            pathOptions={{
              color: cuadrillaColors[cuadrilla.type],
              weight: 2,
              opacity: 0.7,
              fill: true,
              fillColor: cuadrillaColors[cuadrilla.type],
              fillOpacity: 0.1,
            }}
          >
            <Popup>
              <div className="text-sm">
                <p className="font-bold">{cuadrilla.name}</p>
                <p className="text-xs text-gray-600">{cuadrilla.type}</p>
                <p className="text-xs">
                  Carga: {cuadrilla.currentLoad}/{cuadrilla.dailyCapacity}
                </p>
              </div>
            </Popup>
          </Circle>
        ))}

        {/* OT Markers */}
        {otsWithCoordinates.map((ot) => (
          <Marker
            key={ot.id}
            position={[ot.lat!, ot.long!]}
            icon={createOTMarkerIcon(ot.status)}
            eventHandlers={{
              click: () => handleOTMarkerClick(ot),
            }}
          >
            <Popup className="ot-popup">
              <div className="text-sm">
                <p className="font-bold text-gray-800">{ot.externalId}</p>

                {/* Project Type Badge */}
                <div className="mt-1">
                  <span
                    className={`inline-block px-2 py-1 rounded text-xs font-semibold text-white
                      ${
                        ot.projectType === 'PUBLICO'
                          ? 'bg-red-600'
                          : ot.projectType === 'PRIVADO'
                            ? 'bg-blue-600'
                            : 'bg-purple-600'
                      }
                    `}
                  >
                    {ot.projectType}
                  </span>
                </div>

                {/* Status */}
                <p className="text-xs text-gray-700 mt-1">
                  <span className="font-semibold">Estado:</span> {ot.status}
                </p>

                {/* Client */}
                {ot.clienteName && (
                  <p className="text-xs text-gray-700">
                    <span className="font-semibold">Cliente:</span>{' '}
                    {ot.clienteName}
                  </p>
                )}

                {/* Coordinates */}
                <p className="text-xs text-gray-600 mt-1">
                  📍 {ot.lat!.toFixed(4)}, {ot.long!.toFixed(4)}
                </p>

                {/* Assigned Crew */}
                {ot.cuadrilla && (
                  <p className="text-xs text-green-700 mt-1">
                    <span className="font-semibold">Equipo:</span>{' '}
                    {ot.cuadrilla.name}
                  </p>
                )}

                {/* Geo Error Warning */}
                {ot.hasGeoError && (
                  <p className="text-xs text-red-600 mt-1 font-semibold">
                    ⚠️ Coordenadas inválidas
                  </p>
                )}

                {/* Click to view detail hint */}
                <p className="text-xs text-blue-600 mt-2 italic cursor-pointer hover:underline">
                  Haz clic para ver detalles
                </p>
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Map Event Handlers */}
        <MapEventHandler setMapCenter={setMapCenter} />

        {/* Legend */}
        <MapLegend />
      </MapContainer>

      {/* Data Summary */}
      <div className="absolute bottom-4 left-4 bg-white rounded-lg shadow-md p-3 text-xs text-gray-700">
        <p>
          <span className="font-semibold">OTs:</span> {otsWithCoordinates.length}/
          {ots.length}
        </p>
        <p>
          <span className="font-semibold">Cuadrillas:</span>{' '}
          {cuadrillasWithCentroid.length}/{cuadrillas.length}
        </p>
      </div>
    </div>
  );
}

/**
 * Sub-component to handle map events
 */
interface MapEventHandlerProps {
  setMapCenter: (lat: number, lng: number, zoom: number) => void;
}

function MapEventHandler({ setMapCenter }: MapEventHandlerProps) {
  const map = useMap();

  React.useEffect(() => {
    const handleMove = () => {
      const center = map.getCenter();
      const zoom = map.getZoom();
      setMapCenter(center.lat, center.lng, zoom);
    };

    map.on('moveend', handleMove);
    map.on('zoomend', handleMove);

    return () => {
      map.off('moveend', handleMove);
      map.off('zoomend', handleMove);
    };
  }, [map, setMapCenter]);

  return null;
}

export default MapView;

