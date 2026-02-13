import React, { useState } from 'react';
import toast from 'react-hot-toast';
import { Download, X } from 'lucide-react';
import { triggerPlanning } from '@/services/api';
import { ProjectType } from '@/types';

export interface PlanningModalProps {
  open: boolean;
  onClose: () => void;
}

/**
 * Planning Modal component for executing planning workflows
 */
export function PlanningModal({ open, onClose }: PlanningModalProps) {
  const [mode, setMode] = useState<'full' | 'phase1' | 'phase2' | 'phase3'>('full');
  const [projectType, setProjectType] = useState<ProjectType | ''>('');
  const [isExecuting, setIsExecuting] = useState(false);
  const [results, setResults] = useState<any | null>(null);

  const handleExecute = async () => {
    setIsExecuting(true);
    setResults(null);

    try {
      const response = await triggerPlanning({
        mode,
        projectType: projectType || undefined,
      });

      setResults(response);
      toast.success('Planning completed successfully');
    } catch (error: any) {
      toast.error(`Planning failed: ${error.message}`);
    } finally {
      setIsExecuting(false);
    }
  };

  const handleDownloadLog = () => {
    if (!results) return;

    const jsonString = JSON.stringify(results, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `planning-log-${new Date().getTime()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Log downloaded');
  };

  if (!open) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-blue-600 to-blue-700 text-white p-6 flex items-center justify-between">
          <h2 className="text-2xl font-bold">Planificación de OTs</h2>
          <button
            onClick={onClose}
            className="text-white hover:bg-blue-800 rounded-full p-2 transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {!results ? (
            <>
              {/* Mode Selection */}
              <div>
                <h3 className="font-bold text-lg mb-3">Modo de Planificación</h3>
                <div className="space-y-2">
                  {(['full', 'phase1', 'phase2', 'phase3'] as const).map((m) => (
                    <label key={m} className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="radio"
                        name="mode"
                        value={m}
                        checked={mode === m}
                        onChange={(e) => setMode(e.target.value as typeof m)}
                        className="w-4 h-4"
                      />
                      <span className="text-gray-800">
                        {m === 'full' && 'Completo (3 fases)'}
                        {m === 'phase1' && 'Fase 1: Balance Inicial'}
                        {m === 'phase2' && 'Fase 2: Asignación por Proximidad'}
                        {m === 'phase3' && 'Fase 3: Optimización Nocturna'}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Project Type Filter */}
              <div>
                <h3 className="font-bold text-lg mb-3">Filtro de Tipo de Proyecto (Opcional)</h3>
                <select
                  value={projectType}
                  onChange={(e) => setProjectType(e.target.value as ProjectType | '')}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Todos los tipos</option>
                  <option value="PUBLICO">PUBLICO</option>
                  <option value="PRIVADO">PRIVADO</option>
                  <option value="TERCERIZADO">TERCERIZADO</option>
                </select>
              </div>

              {/* Description */}
              <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
                <p className="text-sm text-blue-900">
                  <strong>Fase 1:</strong> Distribuye 1 OT por cuadrilla para equidad.
                  <br />
                  <strong>Fase 2:</strong> Asigna OTs según proximidad geográfica (&lt;10km).
                  <br />
                  <strong>Fase 3:</strong> Optimiza rutas recalculando centroides.
                </p>
              </div>

              {/* Execute Button */}
              <button
                onClick={handleExecute}
                disabled={isExecuting}
                className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isExecuting ? 'Ejecutando...' : 'Ejecutar Planificación'}
              </button>
            </>
          ) : (
            <>
              {/* Results Section */}
              <div>
                <h3 className="font-bold text-lg mb-3">Resultados de la Planificación</h3>

                {/* Summary */}
                <div className="bg-green-50 border-l-4 border-green-500 p-4 rounded mb-4">
                  <p className="text-sm text-green-900">
                    {results.summary || 'Planificación completada exitosamente'}
                  </p>
                </div>

                {/* Phase Results */}
                {results.results && (
                  <div className="space-y-3">
                    {results.results.phase1 && (
                      <div className="bg-gray-50 p-3 rounded border border-gray-200">
                        <p className="font-semibold text-blue-700">Fase 1: Balance Inicial</p>
                        <p className="text-sm text-gray-700">
                          OTs Asignados: <strong>{results.results.phase1.assigned}</strong>
                        </p>
                      </div>
                    )}

                    {results.results.phase2 && (
                      <div className="bg-gray-50 p-3 rounded border border-gray-200">
                        <p className="font-semibold text-blue-700">Fase 2: Asignación por Proximidad</p>
                        <p className="text-sm text-gray-700">
                          OTs Asignados: <strong>{results.results.phase2.assigned}</strong>
                          <br />
                          OTs Rechazados: <strong>{results.results.phase2.rejected}</strong>
                        </p>
                      </div>
                    )}

                    {results.results.phase3 && (
                      <div className="bg-gray-50 p-3 rounded border border-gray-200">
                        <p className="font-semibold text-blue-700">Fase 3: Optimización</p>
                        <p className="text-sm text-gray-700">
                          OTs Optimizados: <strong>{results.results.phase3.optimized}</strong>
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Agent Logs Preview */}
                {results.executionLogs && results.executionLogs.length > 0 && (
                  <div className="mt-4">
                    <p className="font-semibold text-gray-800 mb-2">Registro de Agentes</p>
                    <div className="bg-gray-50 p-3 rounded max-h-48 overflow-y-auto text-xs text-gray-700 font-mono">
                      {results.executionLogs.slice(0, 10).map((log: any, idx: number) => (
                        <div key={idx} className="py-1">
                          {log.agent}: {log.success ? '✓' : '✗'}
                        </div>
                      ))}
                      {results.executionLogs.length > 10 && (
                        <div className="py-1 text-gray-500">
                          ...y {results.executionLogs.length - 10} más
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3">
                <button
                  onClick={handleDownloadLog}
                  className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center justify-center gap-2"
                >
                  <Download size={18} />
                  Descargar Log
                </button>
                <button
                  onClick={() => {
                    setResults(null);
                    setMode('full');
                    setProjectType('');
                  }}
                  className="flex-1 px-4 py-2 bg-gray-300 text-gray-800 rounded-lg hover:bg-gray-400 transition-colors"
                >
                  Nueva Planificación
                </button>
              </div>

              {/* Close Button */}
              <button
                onClick={onClose}
                className="w-full px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition-colors"
              >
                Cerrar
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default PlanningModal;

