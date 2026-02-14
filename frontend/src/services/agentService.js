/**
 * Agent Service
 * 
 * Provides functions for agent communication and management via API.
 * Handles chat messaging, log retrieval, and manual agent triggering.
 */

import apiClient from './apiClient';

/**
 * Send chat message to RouterAgent for intelligent routing and processing.
 * 
 * Accepts user input and routes to appropriate agent based on intent classification.
 * The RouterAgent analyzes the input and determines which specialized agent
 * (OTSAgent, PlanificacionAgent, GobernanzaAgent, ComunicacionAgent) should handle it.
 * 
 * @param {string} message - User input message
 * @param {string} eventType - Optional event type (defaults to 'user_input')
 * @returns {Promise} Promise resolving to agent response containing:
 *   - response: Agent's response message
 *   - action_result: Result status (SUCCESS, FAILURE, PENDING)
 *   - next_agent: Name of agent that processed the request
 *   - logs: Related log entries
 * 
 * @example
 * // Ask to download new OTs
 * const response = await sendChatMessage('Download new OTs from TELCOS');
 * console.log(response.data.response);
 * 
 * @example
 * // Request OT planning/assignment
 * const response = await sendChatMessage('Plan assignments for all unassigned OTs');
 * 
 * @example
 * // Check for governance issues
 * const response = await sendChatMessage('Check for inactive or detained OTs');
 */
export const sendChatMessage = (message, eventType = 'user_input') => {
  return apiClient.post('/api/agents/chat', {
    message,
    event_type: eventType,
  });
};

/**
 * Fetch agent execution logs with optional filtering.
 * 
 * Retrieves historical logs of agent actions for debugging and monitoring.
 * Supports filtering by agent name, OT, result status, and date range.
 * 
 * @param {Object} filters - Filter options
 * @param {string} filters.agente_name - Filter by agent name (e.g., 'RouterAgent', 'OTSAgent')
 * @param {number} filters.ot_id - Filter by associated OT ID
 * @param {string} filters.resultado - Filter by result status (SUCCESS, FAILURE, PENDING)
 * @param {string} filters.start_date - Filter from date (YYYY-MM-DD format)
 * @param {string} filters.end_date - Filter until date (YYYY-MM-DD format)
 * @param {number} filters.limit - Maximum logs to return (default: 100, max: 1000)
 * @returns {Promise} Promise resolving to list of log entries containing:
 *   - id: Log entry ID
 *   - ot_id: Associated OT ID
 *   - agente_name: Agent name
 *   - accion: Action description
 *   - resultado: Result status
 *   - raw_llm_response: Raw LLM response if applicable
 *   - metadata: Additional metadata
 *   - created_at: Timestamp in ISO format
 * 
 * @example
 * // Get all OTSAgent logs
 * const logs = await fetchAgentLogs({
 *   agente_name: 'OTSAgent'
 * });
 * 
 * @example
 * // Get failed operations from last 7 days
 * const logs = await fetchAgentLogs({
 *   resultado: 'FAILURE',
 *   start_date: '2024-02-06',
 *   end_date: '2024-02-13'
 * });
 * 
 * @example
 * // Get logs for specific OT
 * const logs = await fetchAgentLogs({
 *   ot_id: 1,
 *   limit: 50
 * });
 */
export const fetchAgentLogs = (filters = {}) => {
  return apiClient.get('/api/agents/logs', {
    params: filters,
  });
};

/**
 * Manually trigger Planificación Agent to execute 3-phase planning algorithm.
 * 
 * Invokes the planning agent to assign OTs to cuadrillas using:
 * - PHASE 1: Balance assignments (1 OT per cuadrilla)
 * - PHASE 2: Proximity-based assignment (<10km from cuadrilla centroid)
 * - PHASE 3: Recalculate centroid positions from new assignments
 * 
 * @param {Array} otIds - Optional array of specific OT IDs to plan
 *                        If omitted, plans all unassigned OTs
 * @param {boolean} forceReplan - Optional boolean to force replan even assigned OTs
 * @returns {Promise} Promise resolving to planning result containing:
 *   - status: Operation status
 *   - message: Description of planning operation
 *   - ots_planned: Number of OTs planned/assigned
 *   - assignments: List of assignment details
 *   - cuadrillas_updated: Number of cuadrillas with updated centroids
 * 
 * @example
 * // Plan all unassigned OTs
 * const result = await triggerManualPlan();
 * console.log(`Planned ${result.data.ots_planned} OTs`);
 * 
 * @example
 * // Plan specific OTs
 * const result = await triggerManualPlan([1, 2, 3]);
 * 
 * @example
 * // Force replan all OTs (including already assigned)
 * const result = await triggerManualPlan([], true);
 */
export const triggerManualPlan = (otIds = [], forceReplan = false) => {
  return apiClient.post('/api/agents/plan', {
    ot_ids: otIds,
    force_replan: forceReplan,
  });
};

/**
 * Manually trigger Gobernanza Agent to perform governance checks.
 * 
 * Invokes the governance agent to:
 * 1. Check for inactive OTs (PREPLANIFICADA > 48 hours) and send alerts
 * 2. Check for OTs in detention (DETENIDA status) and send reminders on days 20, 25, 29
 * 3. Auto-cancel OTs that have been detained for >= 30 days
 * 4. Validate PUBLICO project document completion (must have 29 docs)
 * 5. Generate and send notifications to relevant parties
 * 
 * @returns {Promise} Promise resolving to governance check result containing:
 *   - status: Operation status
 *   - message: Description of governance check
 *   - inactivity_alerts: Count of inactivity alerts sent
 *   - detention_alerts: Count of detention reminder alerts sent
 *   - auto_cancellations: Count of OTs auto-cancelled
 *   - document_warnings: Count of incomplete document warnings
 * 
 * @example
 * // Run governance check
 * const result = await triggerGovernanceCheck();
 * console.log(`Sent ${result.data.inactivity_alerts} inactivity alerts`);
 * console.log(`Auto-cancelled ${result.data.auto_cancellations} OTs`);
 */
export const triggerGovernanceCheck = () => {
  return apiClient.post('/api/agents/govern');
};

