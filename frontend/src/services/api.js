import axios from 'axios';
import { toast } from 'react-toastify';

// Get API base URL from environment variable or use default
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance with default configuration
const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Track loading state for global use
let isLoading = false;

/**
 * Request interceptor to handle loading state
 * Adds loading indicator before each request
 */
axiosInstance.interceptors.request.use(
  (config) => {
    isLoading = true;
    // Could dispatch loading state to a global state manager here
    return config;
  },
  (error) => {
    isLoading = false;
    return Promise.reject(error);
  }
);

/**
 * Response interceptor to handle errors globally
 * Shows error toast notifications for failed requests
 */
axiosInstance.interceptors.response.use(
  (response) => {
    isLoading = false;
    return response;
  },
  (error) => {
    isLoading = false;
    
    // Handle different error types
    if (error.response) {
      // Server responded with error status
      const status = error.response.status;
      const data = error.response.data;
      
      let errorMessage = data?.detail || data?.message || 'An error occurred';
      
      if (status === 401) {
        errorMessage = 'Unauthorized. Please log in.';
      } else if (status === 403) {
        errorMessage = 'Forbidden. You do not have permission.';
      } else if (status === 404) {
        errorMessage = 'Resource not found.';
      } else if (status === 500) {
        errorMessage = 'Server error. Please try again later.';
      }
      
      toast.error(errorMessage);
    } else if (error.request) {
      // Request made but no response received
      toast.error('No response from server. Check your connection.');
    } else {
      // Error in request setup
      toast.error(error.message || 'An error occurred');
    }
    
    return Promise.reject(error);
  }
);

/**
 * API Methods for OT Management
 */

/**
 * Sync OTs from external API or mock service
 * @returns {Promise<Object>} Sync result with counts and status
 */
export const syncOTs = async () => {
  try {
    const response = await axiosInstance.post('/api/ots/sync');
    toast.success(`Synced ${response.data.synced_count} OTs successfully`);
    return response.data;
  } catch (error) {
    console.error('Error syncing OTs:', error);
    throw error;
  }
};

/**
 * Get list of OTs with optional filters
 * @param {Object} filters - Filter criteria (status, project_type, etc.)
 * @returns {Promise<Array>} Array of OT objects
 */
export const getOTs = async (filters = {}) => {
  try {
    const params = new URLSearchParams();
    
    // Add query parameters from filters
    if (filters.status) {
      params.append('status', filters.status);
    }
    if (filters.project_type) {
      params.append('project_type', filters.project_type);
    }
    
    const queryString = params.toString();
    const url = queryString ? `/api/ots/?${queryString}` : '/api/ots/';
    
    const response = await axiosInstance.get(url);
    return response.data;
  } catch (error) {
    console.error('Error fetching OTs:', error);
    throw error;
  }
};

/**
 * Get a single OT by ID
 * @param {number} otId - OT database ID
 * @returns {Promise<Object>} OT object
 */
export const getOTById = async (otId) => {
  try {
    const response = await axiosInstance.get(`/api/ots/${otId}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching OT ${otId}:`, error);
    throw error;
  }
};

/**
 * Update OT status with optional detention reason
 * @param {number} otId - OT database ID
 * @param {string} newStatus - New status value
 * @param {string} detentionReason - Reason for detention (if status is DETENIDA)
 * @returns {Promise<Object>} Updated OT object
 */
export const updateOTStatus = async (otId, newStatus, detentionReason = null) => {
  try {
    const response = await axiosInstance.put(
      `/api/ots/${otId}/status?new_status=${newStatus}`,
      detentionReason ? { detention_reason: detentionReason } : {}
    );
    toast.success(`OT status updated to ${newStatus}`);
    return response.data;
  } catch (error) {
    console.error(`Error updating OT ${otId} status:`, error);
    throw error;
  }
};

/**
 * Update OT fields
 * @param {number} otId - OT database ID
 * @param {Object} updates - Fields to update
 * @returns {Promise<Object>} Updated OT object
 */
export const updateOT = async (otId, updates) => {
  try {
    const response = await axiosInstance.put(`/api/ots/${otId}`, updates);
    toast.success('OT updated successfully');
    return response.data;
  } catch (error) {
    console.error(`Error updating OT ${otId}:`, error);
    throw error;
  }
};

/**
 * Delete OT (soft delete - sets status to ANULADA)
 * @param {number} otId - OT database ID
 * @returns {Promise<Object>} Deletion result
 */
export const deleteOT = async (otId) => {
  try {
    const response = await axiosInstance.delete(`/api/ots/${otId}`);
    toast.success('OT marked as ANULADA');
    return response.data;
  } catch (error) {
    console.error(`Error deleting OT ${otId}:`, error);
    throw error;
  }
};

/**
 * API Methods for Cuadrilla Management
 */

/**
 * Get list of all cuadrillas
 * @param {Object} filters - Filter criteria (type, is_active, etc.)
 * @returns {Promise<Array>} Array of Cuadrilla objects
 */
export const getCuadrillas = async (filters = {}) => {
  try {
    const params = new URLSearchParams();
    
    if (filters.type) {
      params.append('type', filters.type);
    }
    if (filters.is_active !== undefined) {
      params.append('is_active', filters.is_active);
    }
    
    const queryString = params.toString();
    const url = queryString ? `/api/cuadrillas/?${queryString}` : '/api/cuadrillas/';
    
    const response = await axiosInstance.get(url);
    return response.data;
  } catch (error) {
    console.error('Error fetching cuadrillas:', error);
    throw error;
  }
};

/**
 * Get a single cuadrilla by ID
 * @param {number} cuadrillaId - Cuadrilla database ID
 * @returns {Promise<Object>} Cuadrilla object
 */
export const getCuadrillaById = async (cuadrillaId) => {
  try {
    const response = await axiosInstance.get(`/api/cuadrillas/${cuadrillaId}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching cuadrilla ${cuadrillaId}:`, error);
    throw error;
  }
};

/**
 * Create a new cuadrilla
 * @param {Object} cuadrillData - Cuadrilla data (name, type, capacity, is_active)
 * @returns {Promise<Object>} Created Cuadrilla object
 */
export const createCuadrilla = async (cuadrillaData) => {
  try {
    const response = await axiosInstance.post('/api/cuadrillas/', cuadrillaData);
    toast.success(`Cuadrilla "${cuadrillaData.name}" created successfully`);
    return response.data;
  } catch (error) {
    console.error('Error creating cuadrilla:', error);
    throw error;
  }
};

/**
 * Update cuadrilla
 * @param {number} cuadrillaId - Cuadrilla database ID
 * @param {Object} updates - Fields to update
 * @returns {Promise<Object>} Updated Cuadrilla object
 */
export const updateCuadrilla = async (cuadrillaId, updates) => {
  try {
    const response = await axiosInstance.put(`/api/cuadrillas/${cuadrillaId}`, updates);
    toast.success('Cuadrilla updated successfully');
    return response.data;
  } catch (error) {
    console.error(`Error updating cuadrilla ${cuadrillaId}:`, error);
    throw error;
  }
};

/**
 * Get assignments for a specific cuadrilla
 * @param {number} cuadrillaId - Cuadrilla database ID
 * @returns {Promise<Object>} Cuadrilla with assignments
 */
export const getCuadrillaAssignments = async (cuadrillaId) => {
  try {
    const response = await axiosInstance.get(`/api/cuadrillas/${cuadrillaId}/assignments`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching assignments for cuadrilla ${cuadrillaId}:`, error);
    throw error;
  }
};

/**
 * Recalculate centroid for a cuadrilla
 * @param {number} cuadrillaId - Cuadrilla database ID
 * @returns {Promise<Object>} Updated centroid coordinates
 */
export const recalculateCuadrillaCentroid = async (cuadrillaId) => {
  try {
    const response = await axiosInstance.put(`/api/cuadrillas/${cuadrillaId}/centroid`);
    toast.success('Centroid recalculated');
    return response.data;
  } catch (error) {
    console.error(`Error recalculating centroid for cuadrilla ${cuadrillaId}:`, error);
    throw error;
  }
};

/**
 * API Methods for Agent Interaction
 */

/**
 * Send natural language command to router agent
 * @param {string} command - Natural language command
 * @returns {Promise<Object>} Agent response with action and results
 */
export const sendAgentCommand = async (command) => {
  try {
    const response = await axiosInstance.post('/api/agents/chat', {
      action: command,
      parameters: {},
    });
    return response.data;
  } catch (error) {
    console.error('Error sending agent command:', error);
    throw error;
  }
};

/**
 * Trigger planning algorithm for OT assignment
 * @param {Array<number>} otIds - Array of OT IDs to plan
 * @param {boolean} forceBalance - Force balance phase
 * @returns {Promise<Object>} Planning results with assignments
 */
export const triggerPlanning = async (otIds, forceBalance = false) => {
  try {
    const response = await axiosInstance.post('/api/agents/plan', {
      ot_ids: otIds,
      force_balance: forceBalance,
    });
    toast.success(`Assigned ${response.data.assigned_count} OTs`);
    return response.data;
  } catch (error) {
    console.error('Error triggering planning:', error);
    throw error;
  }
};

/**
 * Manually trigger governance checks
 * @returns {Promise<Object>} Governance check results
 */
export const triggerGovernanceCheck = async () => {
  try {
    const response = await axiosInstance.post('/api/agents/govern');
    return response.data;
  } catch (error) {
    console.error('Error triggering governance check:', error);
    throw error;
  }
};

/**
 * Get agent logs with optional filters
 * @param {Object} filters - Filter criteria (agent_name, ot_id, days, etc.)
 * @returns {Promise<Object>} Agent logs array
 */
export const getAgentLogs = async (filters = {}) => {
  try {
    const params = new URLSearchParams();
    
    if (filters.agent_name) {
      params.append('agent_name', filters.agent_name);
    }
    if (filters.ot_id) {
      params.append('ot_id', filters.ot_id);
    }
    if (filters.days) {
      params.append('days', filters.days);
    }
    
    const queryString = params.toString();
    const url = queryString ? `/api/agents/logs?${queryString}` : '/api/agents/logs';
    
    const response = await axiosInstance.get(url);
    return response.data;
  } catch (error) {
    console.error('Error fetching agent logs:', error);
    throw error;
  }
};

/**
 * Health check endpoint
 * @returns {Promise<Object>} Health status
 */
export const healthCheck = async () => {
  try {
    const response = await axiosInstance.get('/health');
    return response.data;
  } catch (error) {
    console.error('Health check failed:', error);
    throw error;
  }
};

/**
 * Get loading state
 * @returns {boolean} Whether a request is currently in progress
 */
export const getIsLoading = () => isLoading;

/**
 * Export axios instance for custom requests if needed
 */
export default axiosInstance;

