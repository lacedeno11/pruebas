import { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { OTStatus, CuadrillaType } from '@/types';

/**
 * Map legend overlay component showing color coding for OTs, project types, and cuadrillas
 */
export function MapLegend() {
  const [isVisible, setIsVisible] = useState(true);

  // Status colors matching map markers
  const statusColors: Record<OTStatus, string> = {
    [OTStatus.PREPLANIFICADA]: '#3b82f6', // blue
    [OTStatus.PLANIFICADA]: '#eab308', // yellow
    [OTStatus.ASIGNADO_TAREA]: '#22c55e', // green
    [OTStatus.DETENIDA]: '#f97316', // orange
    [OTStatus.ANULADA]: '#ef4444', // red
    [OTStatus.FINALIZADA]: '#6b7280', // gray
  };

  // Project type colors
  const projectTypeColors: Record<string, string> = {
    PUBLICO: '#dc2626', // red-600
    PRIVADO: '#2563eb', // blue-600
    TERCERIZADO: '#9333ea', // purple-600
  };

  // Cuadrilla colors
  const cuadrillaColors: Record<CuadrillaType, string> = {
    [CuadrillaType.PRINCIPAL]: '#3b82f6', // blue
    [CuadrillaType.RESERVA]: '#a78bfa', // purple
  };

  return (
    <div className="absolute top-4 right-4 z-40">
      {/* Toggle Button */}
      <button
        onClick={() => setIsVisible(!isVisible)}
        className="
          bg-white rounded-lg shadow-md p-2 mb-2
          hover:shadow-lg transition-shadow
          text-gray-700 hover:text-gray-900
        "
        title={isVisible ? 'Ocultar leyenda' : 'Mostrar leyenda'}
      >
        {isVisible ? <Eye size={20} /> : <EyeOff size={20} />}
      </button>

      {/* Legend Content */}
      {isVisible && (
        <div className="bg-white rounded-lg shadow-lg p-4 max-w-64 max-h-96 overflow-y-auto">
          <h3 className="font-bold text-gray-800 mb-3 text-sm">Leyenda del Mapa</h3>

          {/* OT Statuses */}
          <div className="mb-4">
            <h4 className="font-semibold text-gray-700 text-xs uppercase mb-2">
              Estados OT
            </h4>
            <div className="space-y-2">
              {Object.entries(statusColors).map(([status, color]) => (
                <div key={status} className="flex items-center gap-2 text-xs">
                  {/* Colored circle */}
                  <div
                    className="w-3 h-3 rounded-full border-2 border-white"
                    style={{
                      backgroundColor: color,
                      boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
                    }}
                  />
                  <span className="text-gray-700">{status}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Project Types */}
          <div className="mb-4">
            <h4 className="font-semibold text-gray-700 text-xs uppercase mb-2">
              Tipo de Proyecto
            </h4>
            <div className="space-y-2">
              {Object.entries(projectTypeColors).map(([type, color]) => (
                <div key={type} className="flex items-center gap-2 text-xs">
                  {/* Colored square */}
                  <div
                    className="w-4 h-4 rounded"
                    style={{ backgroundColor: color }}
                  />
                  <span className="text-gray-700">{type}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Cuadrilla Types */}
          <div className="mb-4">
            <h4 className="font-semibold text-gray-700 text-xs uppercase mb-2">
              Tipo de Cuadrilla
            </h4>
            <div className="space-y-2">
              {Object.entries(cuadrillaColors).map(([type, color]) => (
                <div key={type} className="flex items-center gap-2 text-xs">
                  {/* Colored circle (for crew zones) */}
                  <div
                    className="w-4 h-4 rounded-full border-2"
                    style={{
                      borderColor: color,
                      backgroundColor: `${color}20`, // Semi-transparent
                    }}
                  />
                  <span className="text-gray-700">{type}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Distance Indicator */}
          <div className="border-t pt-3">
            <h4 className="font-semibold text-gray-700 text-xs uppercase mb-2">
              Zonas de Servicio
            </h4>
            <div className="flex items-center gap-2 text-xs text-gray-700">
              <div className="w-8 h-8 rounded-full border-2 border-blue-400 border-opacity-70" />
              <span>10 km de radio</span>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Área de asignación automática para cuadrillas
            </p>
          </div>

          {/* Info Footer */}
          <div className="border-t mt-3 pt-2">
            <p className="text-xs text-gray-500 italic">
              Haz clic en marcadores para ver detalles
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export default MapLegend;

