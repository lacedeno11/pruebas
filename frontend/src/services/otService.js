/**
 * OT Service
 * 
 * Provides functions for OT (Orden de Trabajo) management via API.
 * Handles fetching, syncing, updating, and managing OT operations.
 */

import apiClient from './apiClient';

/**
 * Fetch all OTs with optional filters.
 * 
 * @param {Object} filters - Filter options
 * @param {string} filters.status - Filter by status (PREPLANIFICADA, PLANIFICADA, etc.)
 * @param {string} filters.project_type - Filter by project type (PUBLICO, PRIVADO, TERCERIZADO)
 * @param {number} filters.cuadrilla_id - Filter by assigned cuadrilla
 * @param {boolean} filters.geo_error - Filter by geo error flag
 * @returns {Promise} Promise resolving to list of OT objects
 */
export const fetchOTs = (filters = {}) => {
  return apiClient.get('/api/ots', {
    params: filters,
  });
};

/**
 * Fetch a single OT by ID.
 * 
 * @param {number} id - OT ID to fetch
 * @returns {Promise} Promise resolving to OT object with details
 */
export const fetchOTById = (id) => {
  return apiClient.get(`/api/ots/${id}`);
};

/**
 * Sync OTs from TELCOS API.
 * Triggers the OTSAgent to download and register new OTs from external TELCOS system.
 * 
 * @returns {Promise} Promise resolving to sync result with statistics
 */
export const syncOTs = () => {
  return apiClient.post('/api/ots/sync');
};

/**
 * Update OT status with business rule validation.
 * 
 * Triggers validation via GobernanzaAgent and potentially PlanificacionAgent
 * depending on the target status.
 * 
 * @param {number} id - OT ID to update
 * @param {string} status - New status (PREPLANIFICADA, PLANIFICADA, ASIGNADO_TAREA, DETENIDA, ANULADA, FINALIZADA)
 * @returns {Promise} Promise resolving to updated OT object
 * 
 * @example
 * // Update OT to PLANIFICADA status
 * await updateOTStatus(1, 'PLANIFICADA');
 * 
 * @example
 * // Move OT to FINALIZADA (triggers document validation for PUBLICO projects)
 * await updateOTStatus(1, 'FINALIZADA');
 */
export const updateOTStatus = (id, status) => {
  return apiClient.patch(`/api/ots/${id}/status`, {
    status,
  });
};

/**
 * Set OT to DETENIDA (detained) status with reason.
 * 
 * Used when an OT needs to be paused/detained for some reason.
 * Triggers governance rules for alerts and auto-cancellation tracking.
 * 
 * @param {number} id - OT ID to detain
 * @param {string} motivo - Reason for detention (e.g., "Cliente no disponible", "Falta de materiales")
 * @returns {Promise} Promise resolving to updated OT object with detention status
 * 
 * @example
 * // Detain OT due to client unavailability
 * await setOTDetention(1, 'Client unavailable for site access');
 */
export const setOTDetention = (id, motivo) => {
  return apiClient.post(`/api/ots/${id}/detention`, {
    motivo,
  });
};

