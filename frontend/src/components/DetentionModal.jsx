import React, { useState } from 'react';
import { toast } from 'react-toastify';

/**
 * Predefined detention reasons for quick selection
 */
const PREDEFINED_REASONS = [
  'Falta de materiales',
  'Cliente no disponible',
  'Condiciones climáticas',
  'Permiso municipal pendiente',
];

/**
 * DetentionModal - Modal dialog for capturing detention reason
 *
 * Props:
 * - isOpen: Boolean indicating if modal is visible
 * - onClose: Function to call when closing modal (without confirming)
 * - ot: OT object with id, external_id, status, etc.
 * - onConfirm: Function to call when confirming with detention reason
 */
function DetentionModal({ isOpen, onClose, ot, onConfirm }) {
  // Local state
  const [detentionReason, setDetentionReason] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  /**
   * Handle predefined reason selection
   */
  const handleSelectReason = (reason) => {
    setDetentionReason(reason);
  };

  /**
   * Handle modal cancel/close
   */
  const handleCancel = () => {
    setDetentionReason('');
    onClose();
  };

  /**
   * Handle modal confirm with validation
   */
  const handleConfirm = async () => {
    // Validate reason length (minimum 10 characters)
    if (!detentionReason || detentionReason.trim().length < 10) {
      toast.error('Motivo de detención debe tener al menos 10 caracteres');
      return;
    }

    try {
      setIsLoading(true);
      
      // Call onConfirm callback with detention reason
      await onConfirm(detentionReason);
      
      // Reset form on success
      setDetentionReason('');
    } catch (error) {
      console.error('Error confirming detention:', error);
      toast.error('Error al confirmar motivo de detención');
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Calculate remaining character count
   */
  const remainingChars = 10 - detentionReason.trim().length;
  const isValid = detentionReason.trim().length >= 10;

  // Don't render if modal is not open
  if (!isOpen || !ot) {
    return null;
  }

  return (
    <>
      {/* Modal Backdrop */}
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-40">
        {/* Modal Dialog */}
        <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 shadow-xl z-50">
          {/* Modal Header */}
          <h2 className="text-lg font-bold text-gray-900 mb-4">
            Motivo de Detención para OT #{ot.external_id}
          </h2>

          {/* Modal Body */}
          <div className="space-y-4">
            {/* OT Info */}
            <div className="bg-gray-50 p-3 rounded border border-gray-200">
              <div className="text-sm text-gray-600">
                <div className="flex justify-between">
                  <span className="font-medium">Proyecto:</span>
                  <span>{ot.project_type}</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-medium">Cliente:</span>
                  <span className="truncate ml-2">{ot.cliente_id}</span>
                </div>
              </div>
            </div>

            {/* Predefined Reasons */}
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-2">
                Selecciona un motivo rápido (opcional):
              </label>
              <div className="space-y-2">
                {PREDEFINED_REASONS.map((reason) => (
                  <button
                    key={reason}
                    onClick={() => handleSelectReason(reason)}
                    className={`
                      w-full text-left px-3 py-2 rounded border-2 transition-colors
                      ${
                        detentionReason === reason
                          ? 'border-blue-500 bg-blue-50 text-blue-900 font-medium'
                          : 'border-gray-200 bg-white text-gray-700 hover:border-blue-300'
                      }
                      disabled:opacity-50 disabled:cursor-not-allowed
                    `}
                    disabled={isLoading}
                  >
                    {reason}
                  </button>
                ))}
              </div>
            </div>

            {/* Textarea for custom reason */}
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-2">
                O escribe un motivo personalizado (mínimo 10 caracteres):
              </label>
              <textarea
                value={detentionReason}
                onChange={(e) => setDetentionReason(e.target.value)}
                placeholder="Describe el motivo de la detención..."
                disabled={isLoading}
                className={`
                  w-full px-3 py-2 border-2 rounded resize-none focus:outline-none focus:ring-2 focus:ring-blue-500
                  ${
                    detentionReason.trim().length > 0 && !isValid
                      ? 'border-orange-300 focus:ring-orange-500'
                      : isValid
                      ? 'border-green-300 focus:ring-green-500'
                      : 'border-gray-300'
                  }
                  disabled:opacity-50 disabled:cursor-not-allowed
                `}
                rows="4"
              />
              
              {/* Character counter */}
              <div className="mt-2 text-xs text-gray-600 flex items-center justify-between">
                <span>
                  {detentionReason.length} caracteres ingresados
                </span>
                {remainingChars > 0 ? (
                  <span className="text-orange-600 font-medium">
                    {remainingChars} caracteres más necesarios
                  </span>
                ) : (
                  <span className="text-green-600 font-medium">✓ Válido</span>
                )}
              </div>
            </div>

            {/* Validation message */}
            {detentionReason.trim().length > 0 && !isValid && (
              <div className="bg-orange-50 border border-orange-200 rounded p-3 text-sm text-orange-800">
                ⚠️ El motivo debe tener al menos 10 caracteres para ser válido
              </div>
            )}

            {isValid && (
              <div className="bg-green-50 border border-green-200 rounded p-3 text-sm text-green-800">
                ✓ Motivo válido y listo para confirmar
              </div>
            )}
          </div>

          {/* Modal Footer - Action Buttons */}
          <div className="mt-6 flex gap-3 justify-end">
            {/* Cancel Button */}
            <button
              onClick={handleCancel}
              disabled={isLoading}
              className={`
                px-4 py-2 rounded font-medium transition-colors
                border border-gray-300 bg-white text-gray-700 hover:bg-gray-50
                disabled:opacity-50 disabled:cursor-not-allowed
              `}
            >
              Cancelar
            </button>

            {/* Confirm Button */}
            <button
              onClick={handleConfirm}
              disabled={!isValid || isLoading}
              className={`
                px-4 py-2 rounded font-medium transition-colors
                flex items-center gap-2
                ${
                  isValid && !isLoading
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                }
              `}
            >
              {isLoading ? (
                <>
                  <span className="inline-block animate-spin">⏳</span>
                  <span>Confirmando...</span>
                </>
              ) : (
                <>
                  <span>✓</span>
                  <span>Confirmar</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

export default DetentionModal;

