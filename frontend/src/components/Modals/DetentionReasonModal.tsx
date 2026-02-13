/**
 * Detention Reason Modal Component
 *
 * This modal captures the reason for transitioning an OT to DETENIDA status.
 * It's required per UC-PEI-13 for drag & drop validation, ensuring proper
 * documentation of why work orders are detained.
 */

import React, { useState, useEffect } from "react";
import toast from "react-hot-toast";
import { X, AlertCircle } from "lucide-react";

interface DetentionReasonModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (reason: string) => void;
}

const MIN_REASON_LENGTH = 10;
const MAX_REASON_LENGTH = 500;

/**
 * Detention Reason Modal Component
 *
 * Features:
 * - Modal dialog with overlay
 * - Textarea for detention reason input
 * - Character count validation (min 10, max 500)
 * - Visual feedback for validation state
 * - Submit and Cancel buttons
 * - Keyboard support (Escape to close)
 * - Auto-focus on textarea
 * - Detailed instructions
 */
export const DetentionReasonModal: React.FC<DetentionReasonModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
}) => {
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setReason("");
      setError(null);
    }
  }, [isOpen]);

  // Handle keyboard events
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  /**
   * Validate reason input
   */
  const validateReason = (text: string): string | null => {
    if (!text.trim()) {
      return "La razón de detención es requerida";
    }
    if (text.length < MIN_REASON_LENGTH) {
      return `Mínimo ${MIN_REASON_LENGTH} caracteres (tienes ${text.length})`;
    }
    if (text.length > MAX_REASON_LENGTH) {
      return `Máximo ${MAX_REASON_LENGTH} caracteres (tienes ${text.length})`;
    }
    return null;
  };

  /**
   * Handle form submission
   */
  const handleSubmit = async () => {
    const validationError = validateReason(reason);

    if (validationError) {
      setError(validationError);
      toast.error(validationError);
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);

      // Call parent's onSubmit
      onSubmit(reason.trim());

      // Show success toast
      toast.success("Razón de detención registrada");

      // Reset and close
      setReason("");
      onClose();
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Error desconocido";
      setError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setIsSubmitting(false);
    }
  };

  /**
   * Handle Cancel button
   */
  const handleCancel = () => {
    setReason("");
    setError(null);
    onClose();
  };

  // Don't render if not open
  if (!isOpen) return null;

  const reasonLength = reason.length;
  const isValid = validateReason(reason) === null;
  const isNearLimit = reasonLength > MAX_REASON_LENGTH - 50;

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40 transition-opacity"
        onClick={handleCancel}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          className="bg-white rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto animate-in fade-in zoom-in-95 duration-200"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Modal Header */}
          <div className="sticky top-0 flex items-center justify-between p-6 border-b border-gray-200 bg-white">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                <AlertCircle className="w-6 h-6 text-red-600" />
              </div>
              <h2 className="text-xl font-bold text-gray-900">
                Razón de Detención
              </h2>
            </div>
            <button
              onClick={handleCancel}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              aria-label="Cerrar"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Modal Body */}
          <div className="p-6 space-y-4">
            {/* Instructions */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-900">
                Por favor, indique la razón por la cual esta OT está siendo
                detenida. Esta información es importante para el seguimiento y
                auditoría del sistema.
              </p>
            </div>

            {/* Reason Textarea */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Razón de Detención*
              </label>
              <textarea
                value={reason}
                onChange={(e) => {
                  setReason(e.target.value);
                  setError(null);
                }}
                placeholder="Ej: Falta de materiales, espera de permiso municipal, problema de acceso..."
                className={`
                  w-full
                  px-4
                  py-3
                  border-2
                  rounded-lg
                  font-sans
                  resize-none
                  focus:outline-none
                  transition-colors
                  ${
                    error
                      ? "border-red-500 bg-red-50"
                      : isValid
                        ? "border-green-500 focus:border-green-600 focus:ring-2 focus:ring-green-200"
                        : "border-yellow-500 focus:border-yellow-600 focus:ring-2 focus:ring-yellow-200"
                  }
                `}
                rows={5}
                minLength={MIN_REASON_LENGTH}
                maxLength={MAX_REASON_LENGTH}
                autoFocus
                disabled={isSubmitting}
              />

              {/* Character Count and Validation Feedback */}
              <div className="mt-2 flex items-center justify-between">
                <div
                  className={`text-sm font-medium ${
                    error
                      ? "text-red-600"
                      : isValid
                        ? "text-green-600"
                        : "text-yellow-600"
                  }`}
                >
                  {reasonLength} / {MAX_REASON_LENGTH} caracteres
                </div>
                {reasonLength > 0 && (
                  <div
                    className={`text-xs font-medium px-2 py-1 rounded ${
                      isValid
                        ? "bg-green-100 text-green-700"
                        : isNearLimit
                          ? "bg-yellow-100 text-yellow-700"
                          : "bg-gray-100 text-gray-700"
                    }`}
                  >
                    {isValid ? "✓ Válido" : "Incompleto"}
                  </div>
                )}
              </div>

              {/* Error Message */}
              {error && (
                <div className="mt-2 flex items-center gap-2 text-red-600 text-sm">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {/* Helper Text */}
              {!error && reasonLength > 0 && reasonLength < MIN_REASON_LENGTH && (
                <div className="mt-2 text-xs text-gray-600">
                  Escribe al menos {MIN_REASON_LENGTH - reasonLength} caracteres más
                </div>
              )}
            </div>

            {/* Tips */}
            <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
              <p className="text-xs font-semibold text-gray-700 mb-2">
                Ejemplos de razones válidas:
              </p>
              <ul className="text-xs text-gray-600 space-y-1">
                <li>• Falta de materiales para completar la instalación</li>
                <li>• Espera de permisos municipales de construcción</li>
                <li>• Problema de acceso a la propiedad del cliente</li>
                <li>• Equipo técnico dañado requiere reparación</li>
              </ul>
            </div>
          </div>

          {/* Modal Footer */}
          <div className="sticky bottom-0 flex gap-3 p-6 border-t border-gray-200 bg-gray-50">
            <button
              onClick={handleCancel}
              disabled={isSubmitting}
              className={`
                flex-1
                px-4
                py-2
                rounded-lg
                font-medium
                transition-colors
                ${
                  isSubmitting
                    ? "bg-gray-200 text-gray-600 cursor-not-allowed"
                    : "bg-gray-200 text-gray-800 hover:bg-gray-300"
                }
              `}
            >
              Cancelar
            </button>
            <button
              onClick={handleSubmit}
              disabled={!isValid || isSubmitting}
              className={`
                flex-1
                px-4
                py-2
                rounded-lg
                font-medium
                text-white
                transition-all
                ${
                  isValid && !isSubmitting
                    ? "bg-red-600 hover:bg-red-700 cursor-pointer"
                    : "bg-gray-300 text-gray-600 cursor-not-allowed"
                }
              `}
            >
              {isSubmitting ? (
                <span className="flex items-center justify-center gap-2">
                  <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                  Guardando...
                </span>
              ) : (
                "Confirmar Detención"
              )}
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default DetentionReasonModal;

