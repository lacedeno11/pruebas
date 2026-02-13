import React, { useState, useEffect } from 'react';
import { useOT } from '../contexts/OTContext';

/**
 * FilterPanel - Collapsible filter sidebar for advanced filtering
 *
 * Features:
 * - Status filtering with counts
 * - Project type filtering with counts
 * - Cuadrilla type filtering
 * - Date range filtering
 * - Active filter count badge
 */
function FilterPanel() {
  const { ots, filters, applyFilters, clearFilters } = useOT();
  const [isOpen, setIsOpen] = useState(false);

  // Local filter state
  const [selectedStatuses, setSelectedStatuses] = useState(
    filters.status ? [filters.status] : []
  );
  const [selectedProjectTypes, setSelectedProjectTypes] = useState(
    filters.project_type ? [filters.project_type] : []
  );
  const [selectedCuadrillaType, setSelectedCuadrillaType] = useState(null);
  const [dateRange, setDateRange] = useState({
    start: null,
    end: null,
  });

  // Status options with counts
  const statusOptions = [
    { value: 'PREPLANIFICADA', label: 'Pre-Planificada' },
    { value: 'PLANIFICADA', label: 'Planificada' },
    { value: 'ASIGNADO_TAREA', label: 'Asignado' },
    { value: 'DETENIDA', label: 'Detenida' },
    { value: 'ANULADA', label: 'Anulada' },
    { value: 'FINALIZADA', label: 'Finalizada' },
  ];

  // Project type options with counts
  const projectTypeOptions = [
    { value: 'PUBLICO', label: 'Público' },
    { value: 'PRIVADO', label: 'Privado' },
    { value: 'TERCERIZADO', label: 'Tercerizado' },
  ];

  // Cuadrilla type options
  const cuadrillaTypeOptions = [
    { value: 'Principal', label: 'Principal' },
    { value: 'Reserva', label: 'Reserva' },
  ];

  /**
   * Calculate count for each status
   */
  const getStatusCount = (status) => {
    return ots.filter(ot => ot.status === status).length;
  };

  /**
   * Calculate count for each project type
   */
  const getProjectTypeCount = (projectType) => {
    return ots.filter(ot => ot.project_type === projectType).length;
  };

  /**
   * Calculate total active filters
   */
  const activeFilterCount = selectedStatuses.length + selectedProjectTypes.length + (selectedCuadrillaType ? 1 : 0) + (dateRange.start || dateRange.end ? 1 : 0);

  /**
   * Handle status checkbox change
   */
  const handleStatusChange = (status) => {
    setSelectedStatuses(prev =>
      prev.includes(status)
        ? prev.filter(s => s !== status)
        : [...prev, status]
    );
  };

  /**
   * Handle project type checkbox change
   */
  const handleProjectTypeChange = (projectType) => {
    setSelectedProjectTypes(prev =>
      prev.includes(projectType)
        ? prev.filter(p => p !== projectType)
        : [...prev, projectType]
    );
  };

  /**
   * Handle cuadrilla type radio change
   */
  const handleCuadrillaTypeChange = (type) => {
    setSelectedCuadrillaType(selectedCuadrillaType === type ? null : type);
  };

  /**
   * Handle date range change
   */
  const handleDateChange = (type, value) => {
    setDateRange(prev => ({
      ...prev,
      [type]: value,
    }));
  };

  /**
   * Apply selected filters to context
   */
  const handleApplyFilters = () => {
    const newFilters = {
      status: selectedStatuses.length > 0 ? selectedStatuses[0] : null,
      project_type: selectedProjectTypes.length > 0 ? selectedProjectTypes[0] : null,
      cuadrilla_type: selectedCuadrillaType,
      date_range: dateRange.start || dateRange.end ? dateRange : null,
    };
    applyFilters(newFilters);
  };

  /**
   * Clear all filters
   */
  const handleClearFilters = () => {
    setSelectedStatuses([]);
    setSelectedProjectTypes([]);
    setSelectedCuadrillaType(null);
    setDateRange({ start: null, end: null });
    clearFilters();
  };

  return (
    <>
      {/* Toggle Button */}
      <div className="fixed left-0 top-20 z-30">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="bg-blue-600 text-white p-3 rounded-r-lg hover:bg-blue-700 transition-colors shadow-lg flex items-center gap-2 relative"
          aria-label="Toggle filters"
          title="Abrir filtros"
        >
          🔍 Filtros
          {activeFilterCount > 0 && (
            <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold">
              {activeFilterCount}
            </span>
          )}
        </button>
      </div>

      {/* Filter Panel */}
      <div
        className={`
          fixed left-0 top-16 h-screen w-64 bg-white shadow-xl overflow-y-auto
          transform transition-transform duration-300 z-20
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <div className="p-4 space-y-4">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-gray-200 pb-3">
            <h2 className="font-bold text-gray-900">Filtros</h2>
            <button
              onClick={() => setIsOpen(false)}
              className="text-gray-600 hover:text-gray-900 text-xl"
            >
              ✕
            </button>
          </div>

          {/* Status Filters */}
          <div>
            <h3 className="font-semibold text-sm text-gray-800 mb-2">Estado</h3>
            <div className="space-y-2">
              {statusOptions.map(option => (
                <label
                  key={option.value}
                  className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={selectedStatuses.includes(option.value)}
                    onChange={() => handleStatusChange(option.value)}
                    className="rounded"
                  />
                  <span className="text-sm text-gray-700 flex-1">
                    {option.label}
                  </span>
                  <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                    {getStatusCount(option.value)}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Project Type Filters */}
          <div className="border-t border-gray-200 pt-4">
            <h3 className="font-semibold text-sm text-gray-800 mb-2">Tipo de Proyecto</h3>
            <div className="space-y-2">
              {projectTypeOptions.map(option => (
                <label
                  key={option.value}
                  className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={selectedProjectTypes.includes(option.value)}
                    onChange={() => handleProjectTypeChange(option.value)}
                    className="rounded"
                  />
                  <span className="text-sm text-gray-700 flex-1">
                    {option.label}
                  </span>
                  <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                    {getProjectTypeCount(option.value)}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Cuadrilla Type Filters */}
          <div className="border-t border-gray-200 pt-4">
            <h3 className="font-semibold text-sm text-gray-800 mb-2">Tipo de Cuadrilla</h3>
            <div className="space-y-2">
              {cuadrillaTypeOptions.map(option => (
                <label
                  key={option.value}
                  className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded transition-colors"
                >
                  <input
                    type="radio"
                    name="cuadrilla_type"
                    checked={selectedCuadrillaType === option.value}
                    onChange={() => handleCuadrillaTypeChange(option.value)}
                    className="rounded"
                  />
                  <span className="text-sm text-gray-700">
                    {option.label}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Date Range Filters */}
          <div className="border-t border-gray-200 pt-4">
            <h3 className="font-semibold text-sm text-gray-800 mb-2">Rango de Fechas</h3>
            <div className="space-y-2">
              <div>
                <label className="text-xs text-gray-600 block mb-1">Desde:</label>
                <input
                  type="date"
                  value={dateRange.start || ''}
                  onChange={(e) => handleDateChange('start', e.target.value)}
                  className="w-full px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="text-xs text-gray-600 block mb-1">Hasta:</label>
                <input
                  type="date"
                  value={dateRange.end || ''}
                  onChange={(e) => handleDateChange('end', e.target.value)}
                  className="w-full px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="border-t border-gray-200 pt-4 flex gap-2">
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

          {/* Active Filters Display */}
          {activeFilterCount > 0 && (
            <div className="border-t border-gray-200 pt-4 bg-blue-50 p-3 rounded">
              <p className="text-xs text-gray-600 mb-2">
                <strong>{activeFilterCount}</strong> filtro(s) activo(s)
              </p>
              <ul className="text-xs text-gray-700 space-y-1">
                {selectedStatuses.map(status => (
                  <li key={status}>• {status}</li>
                ))}
                {selectedProjectTypes.map(type => (
                  <li key={type}>• {type}</li>
                ))}
                {selectedCuadrillaType && (
                  <li>• Cuadrilla: {selectedCuadrillaType}</li>
                )}
                {(dateRange.start || dateRange.end) && (
                  <li>• Fechas: {dateRange.start} a {dateRange.end}</li>
                )}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Overlay (when panel is open) */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-10"
          onClick={() => setIsOpen(false)}
          aria-hidden="true"
        />
      )}
    </>
  );
}

export default FilterPanel;

