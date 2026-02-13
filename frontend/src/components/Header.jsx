import React, { useState } from 'react';
import { useOT } from '../contexts/OTContext';

/**
 * Header - Application header with navigation and controls
 *
 * Props:
 * - viewMode: Current view mode ('kanban' or 'map')
 * - onViewModeChange: Callback to change view mode
 * - onSync: Callback to trigger OT sync
 * - isSyncing: Boolean flag indicating sync in progress
 */
function Header({ viewMode, onViewModeChange, onSync, isSyncing }) {
  const { filters, applyFilters, clearFilters } = useOT();
  const [showFiltersDropdown, setShowFiltersDropdown] = useState(false);
  const [showAgentLogs, setShowAgentLogs] = useState(false);
  const [selectedStatusFilters, setSelectedStatusFilters] = useState(
    filters.status ? [filters.status] : []
  );
  const [selectedProjectTypeFilters, setSelectedProjectTypeFilters] = useState(
    filters.project_type ? [filters.project_type] : []
  );

  /**
   * Handle status filter checkbox change
   */
  const handleStatusFilterChange = (status) => {
    setSelectedStatusFilters(prev =>
      prev.includes(status)
        ? prev.filter(s => s !== status)
        : [...prev, status]
    );
  };

  /**
   * Handle project type filter checkbox change
   */
  const handleProjectTypeFilterChange = (projectType) => {
    setSelectedProjectTypeFilters(prev =>
      prev.includes(projectType)
        ? prev.filter(p => p !== projectType)
        : [...prev, projectType]
    );
  };

  /**
   * Apply selected filters
   */
  const handleApplyFilters = () => {
    const newFilters = {
      status: selectedStatusFilters.length > 0 ? selectedStatusFilters[0] : null,
      project_type: selectedProjectTypeFilters.length > 0 ? selectedProjectTypeFilters[0] : null,
    };
    applyFilters(newFilters);
    setShowFiltersDropdown(false);
  };

  /**
   * Clear all filters
   */
  const handleClearFilters = () => {
    setSelectedStatusFilters([]);
    setSelectedProjectTypeFilters([]);
    clearFilters();
    setShowFiltersDropdown(false);
  };

  /**
   * Calculate active filter count
   */
  const activeFilterCount = selectedStatusFilters.length + selectedProjectTypeFilters.length;

  /**
   * OT Status options
   */
  const statusOptions = [
    { value: 'PREPLANIFICADA', label: 'Pre-Planificada' },
    { value: 'PLANIFICADA', label: 'Planificada' },
    { value: 'ASIGNADO_TAREA', label: 'Asignado' },
    { value: 'DETENIDA', label: 'Detenida' },
    { value: 'ANULADA', label: 'Anulada' },
    { value: 'FINALIZADA', label: 'Finalizada' },
  ];

  /**
   * Project type options
   */
  const projectTypeOptions = [
    { value: 'PUBLICO', label: 'Público' },
    { value: 'PRIVADO', label: 'Privado' },
    { value: 'TERCERIZADO', label: 'Tercerizado' },
  ];

  return (
    <header className="bg-gradient-to-r from-blue-600 to-blue-700 text-white px-6 py-4 shadow-lg flex items-center justify-between">
      {/* Left Section - Logo and Title */}
      <div className="flex items-center gap-3">
        <span className="text-3xl font-bold">🏗️</span>
        <div>
          <h1 className="text-xl font-bold leading-tight">
            PEI
          </h1>
          <p className="text-xs text-blue-100">
            Plataforma de Ejecución de Instalaciones
          </p>
        </div>
      </div>

      {/* Center Section - View Toggle Buttons */}
      <div className="flex items-center gap-4">
        <div className="flex gap-2 bg-blue-500/30 rounded-lg p-1">
          <button
            onClick={() => onViewModeChange('kanban')}
            className={`
              px-4 py-2 rounded font-medium transition-colors
              ${
                viewMode === 'kanban'
                  ? 'bg-white text-blue-600'
                  : 'text-white hover:bg-blue-600'
              }
            `}
          >
            📋 Kanban
          </button>
          <button
            onClick={() => onViewModeChange('map')}
            className={`
              px-4 py-2 rounded font-medium transition-colors
              ${
                viewMode === 'map'
                  ? 'bg-white text-blue-600'
                  : 'text-white hover:bg-blue-600'
              }
            `}
          >
            🗺️ Mapa
          </button>
        </div>

        {/* Sync Button */}
        <button
          onClick={onSync}
          disabled={isSyncing}
          className={`
            px-4 py-2 rounded font-medium transition-colors flex items-center gap-2
            ${
              isSyncing
                ? 'bg-blue-400 text-white cursor-not-allowed opacity-75'
                : 'bg-white text-blue-600 hover:bg-gray-100'
            }
          `}
        >
          {isSyncing ? (
            <>
              <span className="animate-spin">⏳</span>
              <span>Sincronizando...</span>
            </>
          ) : (
            <>
              <span>🔄</span>
              <span>Sincronizar</span>
            </>
          )}
        </button>

        {/* Filters Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowFiltersDropdown(!showFiltersDropdown)}
            className="px-4 py-2 rounded font-medium transition-colors bg-white text-blue-600 hover:bg-gray-100 flex items-center gap-2 relative"
          >
            🔍 Filtros
            {activeFilterCount > 0 && (
              <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold">
                {activeFilterCount}
              </span>
            )}
          </button>

          {/* Filters Dropdown Menu */}
          {showFiltersDropdown && (
            <div className="absolute right-0 mt-2 w-80 bg-white text-gray-900 rounded-lg shadow-xl z-50 p-4">
              <h3 className="font-bold text-sm mb-3">Filtrar por:</h3>

              {/* Status Filters */}
              <div className="mb-4">
                <label className="text-xs font-semibold text-gray-700 block mb-2">
                  Estado:
                </label>
                <div className="space-y-2">
                  {statusOptions.map(option => (
                    <label
                      key={option.value}
                      className="flex items-center gap-2 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedStatusFilters.includes(option.value)}
                        onChange={() => handleStatusFilterChange(option.value)}
                        className="rounded"
                      />
                      <span className="text-sm">{option.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Project Type Filters */}
              <div className="mb-4">
                <label className="text-xs font-semibold text-gray-700 block mb-2">
                  Tipo de Proyecto:
                </label>
                <div className="space-y-2">
                  {projectTypeOptions.map(option => (
                    <label
                      key={option.value}
                      className="flex items-center gap-2 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedProjectTypeFilters.includes(option.value)}
                        onChange={() => handleProjectTypeFilterChange(option.value)}
                        className="rounded"
                      />
                      <span className="text-sm">{option.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2 pt-2 border-t border-gray-200">
                <button
                  onClick={handleApplyFilters}
                  className="flex-1 px-3 py-2 bg-blue-600 text-white rounded font-medium text-sm hover:bg-blue-700 transition-colors"
                >
                  Aplicar
                </button>
                <button
                  onClick={handleClearFilters}
                  className="flex-1 px-3 py-2 bg-gray-300 text-gray-800 rounded font-medium text-sm hover:bg-gray-400 transition-colors"
                >
                  Limpiar
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Agent Logs Button */}
        <button
          onClick={() => setShowAgentLogs(!showAgentLogs)}
          className="px-4 py-2 rounded font-medium transition-colors bg-white text-blue-600 hover:bg-gray-100 flex items-center gap-2"
        >
          📋 Logs
        </button>
      </div>

      {/* Right Section - User Profile */}
      <div className="flex items-center gap-3">
        <div className="text-right hidden sm:block">
          <p className="text-sm font-medium">Usuario</p>
          <p className="text-xs text-blue-100">PEI System</p>
        </div>
        <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center text-lg">
          👤
        </div>
      </div>

      {/* Agent Logs Modal (Placeholder) */}
      {showAgentLogs && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900">Logs de Agentes</h2>
              <button
                onClick={() => setShowAgentLogs(false)}
                className="text-gray-600 hover:text-gray-900"
              >
                ✕
              </button>
            </div>
            <div className="bg-gray-50 p-4 rounded h-96 overflow-y-auto">
              <p className="text-sm text-gray-600">
                Los logs de agentes aparecerán aquí cuando se ejecuten comandos.
              </p>
            </div>
            <div className="mt-4 flex justify-end">
              <button
                onClick={() => setShowAgentLogs(false)}
                className="px-4 py-2 bg-blue-600 text-white rounded font-medium hover:bg-blue-700 transition-colors"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}

export default Header;

