import React, { useState, useEffect } from 'react';
import { useOT } from '../contexts/OTContext';

/**
 * StatsPanel - Dashboard statistics display component
 *
 * Features:
 * - Total OTs count
 * - Breakdown by status with percentages
 * - Breakdown by project type with percentages
 * - Average detention time for DETENIDA OTs
 * - Cuadrilla utilization percentages
 * - OTs with geo errors count
 * - Trend indicators (up/down)
 * - Responsive grid layout
 */
function StatsPanel() {
  const { ots, cuadrillas, getStatistics, getAverageDetentionTime, getCuadrillaUtilization } = useOT();
  const [stats, setStats] = useState(null);
  const [detentionTime, setDetentionTime] = useState(0);
  const [cuadrillaUtilization, setCuadrillaUtilization] = useState([]);

  /**
   * Calculate all statistics when OTs or Cuadrillas change
   */
  useEffect(() => {
    const calculatedStats = getStatistics();
    setStats(calculatedStats);
    
    const avgDetention = getAverageDetentionTime();
    setDetentionTime(avgDetention);

    const utilization = cuadrillas.map(c => ({
      id: c.id,
      name: c.name,
      utilization: getCuadrillaUtilization(c.id),
    }));
    setCuadrillaUtilization(utilization);
  }, [ots, cuadrillas, getStatistics, getAverageDetentionTime, getCuadrillaUtilization]);

  if (!stats) {
    return null;
  }

  /**
   * Calculate percentage for a count
   */
  const getPercentage = (count, total) => {
    if (total === 0) return 0;
    return Math.round((count / total) * 100);
  };

  /**
   * StatCard Component - Individual statistic card
   */
  const StatCard = ({ icon, label, value, unit, trend, subText }) => {
    return (
      <div className="bg-white rounded-lg shadow p-4 hover:shadow-lg transition-shadow">
        <div className="flex items-start justify-between mb-2">
          <span className="text-3xl">{icon}</span>
          {trend && (
            <span className={`text-sm font-semibold ${trend === 'up' ? 'text-green-600' : 'text-red-600'}`}>
              {trend === 'up' ? '↑' : '↓'}
            </span>
          )}
        </div>
        <p className="text-gray-600 text-sm font-medium mb-2">{label}</p>
        <p className="text-2xl font-bold text-gray-900">
          {value}
          {unit && <span className="text-sm text-gray-500 ml-1">{unit}</span>}
        </p>
        {subText && (
          <p className="text-xs text-gray-500 mt-2">{subText}</p>
        )}
      </div>
    );
  };

  /**
   * StatusCard Component - Status breakdown card
   */
  const StatusCard = ({ status, label, count, percentage, color }) => {
    return (
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center justify-between mb-2">
          <p className="text-sm font-medium text-gray-700">{label}</p>
          <span className={`px-2 py-1 rounded text-xs font-bold ${color}`}>
            {percentage}%
          </span>
        </div>
        <p className="text-2xl font-bold text-gray-900 mb-2">{count}</p>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-300 ${color.split(' ')[0]}`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
    );
  };

  /**
   * ProjectTypeCard Component - Project type breakdown card
   */
  const ProjectTypeCard = ({ type, label, count, percentage, bgColor }) => {
    return (
      <div className={`${bgColor} rounded-lg shadow p-4`}>
        <p className="text-sm font-medium text-gray-700 mb-2">{label}</p>
        <p className="text-2xl font-bold text-gray-900 mb-2">{count}</p>
        <p className="text-xs text-gray-600">{percentage}% del total</p>
      </div>
    );
  };

  /**
   * CuadrillaUtilizationCard Component
   */
  const CuadrillaUtilizationCard = ({ name, utilization }) => {
    const getUtilizationColor = (util) => {
      if (util >= 80) return 'bg-red-500';
      if (util >= 60) return 'bg-yellow-500';
      return 'bg-green-500';
    };

    return (
      <div className="bg-white rounded-lg shadow p-4">
        <p className="text-sm font-medium text-gray-700 mb-2">{name}</p>
        <p className="text-2xl font-bold text-gray-900 mb-2">{utilization}%</p>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-300 ${getUtilizationColor(utilization)}`}
            style={{ width: `${utilization}%` }}
          />
        </div>
      </div>
    );
  };

  // Color mappings for status
  const statusColorMap = {
    PREPLANIFICADA: 'bg-blue-100 text-blue-800',
    PLANIFICADA: 'bg-yellow-100 text-yellow-800',
    ASIGNADO_TAREA: 'bg-green-100 text-green-800',
    DETENIDA: 'bg-red-100 text-red-800',
    ANULADA: 'bg-gray-100 text-gray-800',
    FINALIZADA: 'bg-green-200 text-green-900',
  };

  // Color mappings for project types
  const projectTypeColorMap = {
    PUBLICO: 'bg-blue-50 border-l-4 border-blue-500',
    PRIVADO: 'bg-purple-50 border-l-4 border-purple-500',
    TERCERIZADO: 'bg-orange-50 border-l-4 border-orange-500',
  };

  return (
    <div className="bg-gray-50 p-6 rounded-lg">
      {/* Main Statistics Grid */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">📊 Resumen General</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Total OTs */}
          <StatCard
            icon="📋"
            label="Total OTs"
            value={stats.totalOTs}
            trend={stats.totalOTs > 0 ? 'up' : null}
          />

          {/* Geo Errors */}
          <StatCard
            icon="⚠️"
            label="Errores de Geo"
            value={stats.geoErrorCount}
            trend={stats.geoErrorCount > 0 ? 'down' : 'up'}
            subText={`${getPercentage(stats.geoErrorCount, stats.totalOTs)}% del total`}
          />

          {/* Detention Time */}
          <StatCard
            icon="⏱️"
            label="Tiempo Promedio Detención"
            value={detentionTime}
            unit="días"
            trend={detentionTime > 20 ? 'down' : 'up'}
            subText="Para OTs en estado DETENIDA"
          />

          {/* Average Utilization */}
          <StatCard
            icon="⚙️"
            label="Utilización Promedio"
            value={
              cuadrillaUtilization.length > 0
                ? Math.round(
                    cuadrillaUtilization.reduce((sum, c) => sum + c.utilization, 0) /
                      cuadrillaUtilization.length
                  )
                : 0
            }
            unit="%"
            trend={
              cuadrillaUtilization.length > 0 &&
              cuadrillaUtilization.reduce((sum, c) => sum + c.utilization, 0) /
                cuadrillaUtilization.length >
                60
                ? 'up'
                : 'down'
            }
          />
        </div>
      </div>

      {/* Status Breakdown */}
      <div className="mb-8">
        <h3 className="text-lg font-bold text-gray-900 mb-4">📈 Estado de OTs</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(stats.byStatus).map(([status, count]) => {
            const percentage = getPercentage(count, stats.totalOTs);
            return (
              <StatusCard
                key={status}
                status={status}
                label={status.replace(/_/g, ' ')}
                count={count}
                percentage={percentage}
                color={statusColorMap[status] || 'bg-gray-100 text-gray-800'}
              />
            );
          })}
        </div>
      </div>

      {/* Project Type Breakdown */}
      <div className="mb-8">
        <h3 className="text-lg font-bold text-gray-900 mb-4">🏢 Tipo de Proyecto</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(stats.byProjectType).map(([type, count]) => {
            const percentage = getPercentage(count, stats.totalOTs);
            const typeLabel =
              type === 'PUBLICO'
                ? 'Público'
                : type === 'PRIVADO'
                ? 'Privado'
                : 'Tercerizado';
            return (
              <ProjectTypeCard
                key={type}
                type={type}
                label={typeLabel}
                count={count}
                percentage={percentage}
                bgColor={projectTypeColorMap[type]}
              />
            );
          })}
        </div>
      </div>

      {/* Cuadrilla Utilization */}
      {cuadrillaUtilization.length > 0 && (
        <div>
          <h3 className="text-lg font-bold text-gray-900 mb-4">👥 Utilización de Cuadrillas</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {cuadrillaUtilization.map(cuadrilla => (
              <CuadrillaUtilizationCard
                key={cuadrilla.id}
                name={cuadrilla.name}
                utilization={cuadrilla.utilization}
              />
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {stats.totalOTs === 0 && (
        <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
          <p className="text-blue-800 text-sm">
            📭 No hay OTs aún. Sincroniza desde la API para comenzar.
          </p>
        </div>
      )}
    </div>
  );
}

export default StatsPanel;

