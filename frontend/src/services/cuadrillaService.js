/**
 * Cuadrilla Service
 * 
 * Provides functions for Cuadrilla (Work Team) management via API.
 * Handles fetching, creating, updating, and managing cuadrilla operations.
 */

import apiClient from './apiClient';

/**
 * Fetch all cuadrillas with optional filters.
 * 
 * @param {Object} filters - Filter options
 * @param {string} filters.type - Filter by cuadrilla type (PRINCIPAL, RESERVA)
 * @param {boolean} filters.is_active - Filter by active status (true/false)
 * @returns {Promise} Promise resolving to list of cuadrilla objects
 */
export const fetchCuadrillas = (filters = {}) => {
  return apiClient.get('/api/cuadrillas', {
    params: filters,
  });
};

/**
 * Fetch a single cuadrilla by ID with assigned OTs.
 * 
 * @param {number} id - Cuadrilla ID to fetch
 * @returns {Promise} Promise resolving to cuadrilla object with complete details and assigned OTs
 */
export const fetchCuadrillaById = (id) => {
  return apiClient.get(`/api/cuadrillas/${id}`);
};

/**
 * Create a new cuadrilla.
 * 
 * @param {Object} data - Cuadrilla creation data
 * @param {string} data.name - Cuadrilla name (must be unique)
 * @param {string} data.type - Cuadrilla type (PRINCIPAL or RESERVA)
 * @param {number} data.daily_capacity - Daily capacity (number of OTs per day)
 * @returns {Promise} Promise resolving to newly created cuadrilla object
 * 
 * @example
 * // Create a new principal cuadrilla with capacity of 5 OTs per day
 * await createCuadrilla({
 *   name: 'Cuadrilla Sur',
 *   type: 'PRINCIPAL',
 *   daily_capacity: 5
 * });
 */
export const createCuadrilla = (data) => {
  return apiClient.post('/api/cuadrillas', data);
};

/**
 * Trigger cuadrilla load balancing and rebalancing.
 * 
 * Invokes the Planificación Agent to:
 * 1. Rebalance OT assignments across all cuadrillas
 * 2. Recalculate centroid positions based on current assignments
 * 3. Optimize route planning for all teams
 * 
 * This is the PHASE 2 and PHASE 3 of the planning algorithm:
 * - PHASE 2: Proximity-based assignment (distance < 10km from centroid)
 * - PHASE 3: Recalculate centroids for next day operations
 * 
 * @returns {Promise} Promise resolving to rebalancing result with statistics
 * 
 * @example
 * // Trigger rebalancing of all cuadrilla assignments
 * const result = await triggerRebalance();
 * console.log(`${result.data.ots_rebalanced} OTs rebalanced`);
 * console.log(`${result.data.cuadrillas_updated} cuadrillas updated`);
 */
export const triggerRebalance = () => {
  return apiClient.post('/api/cuadrillas/balance');
};

