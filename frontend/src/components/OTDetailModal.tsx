import { useEffect, useRef } from 'react';
import toast from 'react-hot-toast';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import { OT, OTStatus, ProjectType } from '@/types';
import { useOT, useUpdateOTStatus, useDocumentStatus } from '@/hooks/useOTs';
import { useUIStore } from '@/stores/uiStore';

export interface OTDetailModalProps {
  otId: string;
  onClose: () => void;
}

/**
 * Modal component for displaying full OT details
 * Shows all information, document tracking, and status change options
 */
export function OTDetailModal({ otId, onClose }: OTDetailModalProps) {
  const { data: ot, isLoading } = useOT(otId);
  const { data: docStatus } = useDocumentStatus(otId);
  const updateStatus = useUpdateOTStatus();
  const { setSelectedOT } = useUIStore();
  const modalRef = useRef<HTMLDivElement>(null);
  const [selectedStatus, setSelectedStatus] = React.useState<OTStatus | ''>('');
  const [detentionReason, setDetentionReason] = React.useState('');

  // Custom Leaflet icon for OT marker
  const otIcon = L.divIcon({
    className: 'custom-marker',
    html: '<div class="w-6 h-6 bg-blue-500 rounded-full border-2 border-white shadow-lg"></div>',
    iconSize: [24, 24],
  });

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === modalRef.current) {
      handleClose();
    }
  };

  const handleClose = () => {
    setSelectedOT(undefined);
    onClose();
  };

  const handleStatusChange = async () => {
    if (!selectedStatus || !ot) return;

    // Business rule: PUBLICO to FINALIZADA requires 29 documents
    if (ot.projectType === ProjectType.PUBLICO && selectedStatus === OTStatus.FINALIZADA) {
      if (!docStatus || docStatus.documentCount < 29) {
        toast.error(
          `No se puede finalizar: ${docStatus?.documentCount || 0}/29 documentos cargados`
        );
        return;
      }
    }

    try {
      await updateStatus.mutateAsync({
        id: ot.id,
        status: selectedStatus,
        reason: selectedStatus === OTStatus.DETENIDA ? detentionReason : undefined,
      });

      toast.success(`OT ${ot.externalId} actualizada a ${selectedStatus}`);
      setSelectedStatus('');
      setDetentionReason('');
    } catch (error: any) {
      toast.error(`Error al actualizar: ${error.message}`);
    }
  };

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
        <div className="bg-white rounded-lg p-8 max-w-2xl w-full mx-4">
          <div className="flex items-center justify-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!ot) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
        <div className="bg-white rounded-lg p-8 max-w-2xl w-full mx-4">
          <p className="text-red-600">Error al cargar OT</p>
          <button
            onClick={handleClose}
            className="mt-4 px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
          >
            Cerrar
          </button>
        </div>
      </div>
    );
  }

  const statusColors: Record<OTStatus, string> = {
    [OTStatus.PREPLANIFICADA]: 'bg-blue-100 text-blue-800',
    [OTStatus.PLANIFICADA]: 'bg-yellow-100 text-yellow-800',
    [OTStatus.ASIGNADO_TAREA]: 'bg-green-100 text-green-800',
    [OTStatus.DETENIDA]: 'bg-orange-100 text-orange-800',
    [OTStatus.ANULADA]: 'bg-red-100 text-red-800',
    [OTStatus.FINALIZADA]: 'bg-gray-100 text-gray-800',
  };

  const projectTypeColors: Record<ProjectType, string> = {
    [ProjectType.PUBLICO]: 'bg-red-100 text-red-800',
    [ProjectType.PRIVADO]: 'bg-blue-100 text-blue-800',
    [ProjectType.TERCERIZADO]: 'bg-purple-100 text-purple-800',
  };

  return (
    <div
      ref={modalRef}
      onClick={handleBackdropClick}
      className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
    >
      <div className="bg-white rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-blue-600 to-blue-700 text-white p-6 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">{ot.externalId}</h2>
            <p className="text-blue-100 text-sm">ID: {ot.id}</p>
          </div>
          <button
            onClick={handleClose}
            className="text-white hover:bg-blue-800 rounded-full p-2 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Basic Information */}
          <section className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="bg-gray-50 p-4 rounded">
              <p className="text-xs text-gray-600 font-semibold uppercase">Estado</p>
              <p className={`text-sm font-bold px-2 py-1 rounded inline-block mt-1 ${statusColors[ot.status]}`}>
                {ot.status}
              </p>
            </div>

            <div className="bg-gray-50 p-4 rounded">
              <p className="text-xs text-gray-600 font-semibold uppercase">Tipo de Proyecto</p>
              <p className={`text-sm font-bold px-2 py-1 rounded inline-block mt-1 ${projectTypeColors[ot.projectType]}`}>
                {ot.projectType}
              </p>
            </div>

            {ot.clienteName && (
              <div className="bg-gray-50 p-4 rounded">
                <p className="text-xs text-gray-600 font-semibold uppercase">Cliente</p>
                <p className="text-sm font-semibold mt-1 truncate">{ot.clienteName}</p>
              </div>
            )}

            {ot.loginId && (
              <div className="bg-gray-50 p-4 rounded">
                <p className="text-xs text-gray-600 font-semibold uppercase">Login ID</p>
                <p className="text-sm font-semibold mt-1">{ot.loginId}</p>
              </div>
            )}

            <div className="bg-gray-50 p-4 rounded">
              <p className="text-xs text-gray-600 font-semibold uppercase">Creado</p>
              <p className="text-sm font-semibold mt-1">
                {new Date(ot.createdAt).toLocaleDateString('es-ES')}
              </p>
            </div>

            <div className="bg-gray-50 p-4 rounded">
              <p className="text-xs text-gray-600 font-semibold uppercase">Actualizado</p>
              <p className="text-sm font-semibold mt-1">
                {new Date(ot.updatedAt).toLocaleDateString('es-ES')}
              </p>
            </div>
          </section>

          {/* Assigned Cuadrilla */}
          {ot.cuadrilla && (
            <section className="bg-green-50 border-l-4 border-green-500 p-4 rounded">
              <h3 className="font-bold text-green-900 mb-2">Equipo Asignado</h3>
              <p className="text-sm text-green-800">
                <span className="font-semibold">{ot.cuadrilla.name}</span>
                {' '} ({ot.cuadrilla.type})
              </p>
              <p className="text-xs text-green-700 mt-1">
                Capacidad: {ot.cuadrilla.currentLoad}/{ot.cuadrilla.dailyCapacity}
              </p>
            </section>
          )}

          {/* Geo Error Alert */}
          {ot.hasGeoError && (
            <section className="bg-red-50 border-l-4 border-red-500 p-4 rounded">
              <p className="text-sm text-red-800 font-semibold">
                ⚠️ Coordenadas Inválidas
              </p>
            </section>
          )}

          {/* Coordinates */}
          {ot.lat && ot.long && (
            <>
              <section>
                <h3 className="text-lg font-bold mb-3">Ubicación</h3>
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <p className="text-xs text-gray-600">Latitud</p>
                    <p className="text-sm font-semibold">{ot.lat.toFixed(6)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-600">Longitud</p>
                    <p className="text-sm font-semibold">{ot.long.toFixed(6)}</p>
                  </div>
                </div>

                {/* Embedded Map */}
                <div className="w-full h-64 rounded border border-gray-300 overflow-hidden">
                  <MapContainer
                    center={[ot.lat, ot.long]}
                    zoom={13}
                    scrollWheelZoom={false}
                    style={{ height: '100%', width: '100%' }}
                  >
                    <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                    <Marker position={[ot.lat, ot.long]} icon={otIcon}>
                      <Popup>{ot.externalId}</Popup>
                    </Marker>
                  </MapContainer>
                </div>
              </section>
            </>
          )}

          {/* Document Checklist (PUBLICO projects only) */}
          {ot.projectType === ProjectType.PUBLICO && docStatus && (
            <section>
              <h3 className="text-lg font-bold mb-3">Documentos ({docStatus.documentCount}/{docStatus.requiredCount})</h3>

              {/* Progress Bar */}
              <div className="mb-4">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all"
                    style={{ width: `${(docStatus.documentCount / docStatus.requiredCount) * 100}%` }}
                  />
                </div>
                <p className="text-xs text-gray-600 mt-1">
                  {docStatus.documentCount} de {docStatus.requiredCount} documentos
                </p>
              </div>

              {/* Document List */}
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {docStatus.documents.map((doc, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-sm">
                    <span className={`text-lg ${doc.uploaded ? '✅' : '❌'}`}></span>
                    <span className={doc.uploaded ? 'text-gray-800' : 'text-gray-500 line-through'}>
                      {doc.name}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Status Change Section */}
          <section className="border-t pt-6">
            <h3 className="text-lg font-bold mb-4">Cambiar Estado</h3>

            <div className="space-y-4">
              {/* Status Selector */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Nuevo Estado
                </label>
                <select
                  value={selectedStatus}
                  onChange={(e) => setSelectedStatus(e.target.value as OTStatus | '')}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Seleccionar estado...</option>
                  {Object.values(OTStatus).map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </div>

              {/* Reason Input (for DETENIDA status) */}
              {selectedStatus === OTStatus.DETENIDA && (
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Razón de Detención
                  </label>
                  <textarea
                    value={detentionReason}
                    onChange={(e) => setDetentionReason(e.target.value)}
                    placeholder="Explique por qué se detiene esta OT..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    rows={3}
                  />
                </div>
              )}

              {/* Submit Button */}
              <button
                onClick={handleStatusChange}
                disabled={!selectedStatus || updateStatus.isPending}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {updateStatus.isPending ? 'Actualizando...' : 'Actualizar Estado'}
              </button>
            </div>
          </section>

          {/* Recent Agent Logs */}
          <section className="border-t pt-6">
            <h3 className="text-lg font-bold mb-4">Registro de Actividad</h3>
            <p className="text-xs text-gray-600 mb-3">
              Últimas acciones realizadas en esta OT
            </p>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              <p className="text-sm text-gray-600 italic">
                Los registros de agentes se mostrarán aquí
              </p>
            </div>
          </section>
        </div>

        {/* Footer */}
        <div className="border-t bg-gray-50 p-6 flex justify-between">
          <button
            onClick={handleClose}
            className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg font-semibold hover:bg-gray-300 transition-colors"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}

export default OTDetailModal;

