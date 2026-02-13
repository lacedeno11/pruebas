import axios from 'axios'
import { toast } from 'react-toastify'

// Create axios instance
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // You can add loading state here if needed
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    // Handle error responses
    if (error.response) {
      const status = error.response.status
      const message = error.response.data?.detail || error.response.data?.message || 'Unknown error'

      if (status === 404) {
        toast.error(`Not found: ${message}`)
      } else if (status === 400) {
        toast.error(`Invalid request: ${message}`)
      } else if (status === 401) {
        toast.error('Unauthorized - please login')
      } else if (status === 403) {
        toast.error('Forbidden')
      } else if (status >= 500) {
        toast.error(`Server error: ${message}`)
      } else {
        toast.error(message)
      }

      return Promise.reject(error.response.data)
    } else if (error.request) {
      toast.error('No response from server - check connection')
      return Promise.reject(error)
    } else {
      toast.error('Request failed: ' + error.message)
      return Promise.reject(error)
    }
  }
)

// ==================== OT Management Functions ====================

/**
 * Fetch list of OTs with optional filters
 * @param {Object} filters - Filter parameters
 * @param {string} filters.status - Filter by status (PREPLANIFICADA, PLANIFICADA, etc.)
 * @param {string} filters.projectType - Filter by project type (PUBLICO, PRIVADO, TERCERIZADO)
 * @param {number} filters.cuadrillaId - Filter by assigned crew ID
 * @param {number} filters.limit - Maximum results to return
 * @param {number} filters.offset - Pagination offset
 * @returns {Promise<Array>} Array of OT objects
 */
export async function fetchOTs(filters = {}) {
  const params = new URLSearchParams()

  if (filters.status) params.append('status', filters.status)
  if (filters.projectType) params.append('project_type', filters.projectType)
  if (filters.cuadrillaId) params.append('cuadrilla_id', filters.cuadrillaId)
  if (filters.limit) params.append('limit', filters.limit)
  if (filters.offset) params.append('offset', filters.offset)

  return api.get('/api/ots', { params })
}

/**
 * Fetch single OT by ID
 * @param {number} id - OT ID
 * @returns {Promise<Object>} OT object with details
 */
export async function fetchOT(id) {
  return api.get(`/api/ots/${id}`)
}

/**
 * Update OT status (for drag & drop)
 * @param {number} id - OT ID
 * @param {string} status - New status
 * @param {string} reason - Optional reason for status change (required for DETENIDA)
 * @returns {Promise<Object>} Updated OT object
 */
export async function updateOTStatus(id, status, reason = null) {
  return api.patch(`/api/ots/${id}/status`, {
    new_status: status,
    reason: reason,
  })
}

/**
 * Trigger OT sync from TELCOS API
 * @returns {Promise<Object>} Sync results
 */
export async function triggerSync() {
  return api.post('/api/ots/sync')
}

/**
 * Soft delete OT (set status to ANULADA)
 * @param {number} id - OT ID
 * @returns {Promise<Object>} Deleted OT object
 */
export async function deleteOT(id) {
  return api.delete(`/api/ots/${id}`)
}

// ==================== Crew (Cuadrilla) Management Functions ====================

/**
 * Fetch all crews
 * @returns {Promise<Array>} Array of crew objects
 */
export async function fetchCuadrillas() {
  return api.get('/api/cuadrillas')
}

/**
 * Fetch single crew by ID
 * @param {number} id - Crew ID
 * @returns {Promise<Object>} Crew object with details
 */
export async function fetchCuadrilla(id) {
  return api.get(`/api/cuadrillas/${id}`)
}

/**
 * Fetch all OTs assigned to a crew
 * @param {number} id - Crew ID
 * @returns {Promise<Array>} Array of assigned OTs
 */
export async function fetchCuadrillaOTs(id) {
  return api.get(`/api/cuadrillas/${id}/ots`)
}

/**
 * Fetch crew's current centroid
 * @param {number} id - Crew ID
 * @returns {Promise<Object>} Centroid coordinates {lat, long}
 */
export async function fetchCuadrillaCentroid(id) {
  return api.get(`/api/cuadrillas/${id}/centroid`)
}

/**
 * Create new crew
 * @param {Object} crew - Crew data {name, type, capacidad_diaria}
 * @returns {Promise<Object>} Created crew object
 */
export async function createCuadrilla(crew) {
  return api.post('/api/cuadrillas', crew)
}

/**
 * Update crew details
 * @param {number} id - Crew ID
 * @param {Object} updates - Fields to update
 * @returns {Promise<Object>} Updated crew object
 */
export async function updateCuadrilla(id, updates) {
  return api.patch(`/api/cuadrillas/${id}`, updates)
}

// ==================== Planning Functions ====================

/**
 * Trigger automatic planning algorithm
 * @returns {Promise<Object>} Planning results
 */
export async function triggerAutoPlanning() {
  return api.post('/api/planning/auto')
}

/**
 * Manually assign OT to crew
 * @param {number} otId - OT ID
 * @param {number} cuadrillaId - Crew ID
 * @returns {Promise<Object>} Assignment result
 */
export async function assignOTToCrew(otId, cuadrillaId) {
  return api.post('/api/planning/assign', {
    ot_id: otId,
    cuadrilla_id: cuadrillaId,
  })
}

/**
 * Trigger nightly route optimization
 * @returns {Promise<Object>} Optimization results
 */
export async function triggerOptimization() {
  return api.post('/api/planning/optimize')
}

/**
 * Fetch planning status and statistics
 * @returns {Promise<Object>} Planning statistics
 */
export async function fetchPlanningStatus() {
  return api.get('/api/planning/status')
}

// ==================== Validation Functions ====================

/**
 * Validate status transition
 * @param {number} otId - OT ID
 * @param {string} fromStatus - Current status
 * @param {string} toStatus - Desired status
 * @param {string} projectType - Project type (PUBLICO, PRIVADO, TERCERIZADO)
 * @returns {Promise<Object>} Validation result {valid, error_message, warnings}
 */
export async function validateTransition(otId, fromStatus, toStatus, projectType) {
  return api.post('/api/validate/transition', {
    ot_id: otId,
    from_status: fromStatus,
    to_status: toStatus,
    project_type: projectType,
  })
}

/**
 * Validate PÚBLICO project documents
 * @param {number} otId - OT ID
 * @returns {Promise<Object>} Document validation result
 */
export async function validateDocuments(otId) {
  return api.get(`/api/validate/documents/${otId}`)
}

/**
 * Validate crew assignment
 * @param {number} otId - OT ID
 * @param {number} cuadrillaId - Crew ID
 * @returns {Promise<Object>} Assignment validation result
 */
export async function validateAssignment(otId, cuadrillaId) {
  return api.post('/api/validate/assignment', {
    ot_id: otId,
    cuadrilla_id: cuadrillaId,
  })
}

// ==================== Chat Functions ====================

/**
 * Send message to chat agent
 * @param {string} message - User message
 * @param {string} conversationId - Optional conversation ID (UUID)
 * @returns {Promise<Object>} Chat response {response, conversation_id, suggested_actions}
 */
export async function sendChatMessage(message, conversationId = null) {
  return api.post('/api/chat', {
    message: message,
    conversation_id: conversationId,
  })
}

// ==================== System Functions ====================

/**
 * Fetch system information
 * @returns {Promise<Object>} System info {mode, version}
 */
export async function fetchSystemInfo() {
  return api.get('/api/system/info')
}

/**
 * Health check
 * @returns {Promise<Object>} Health status
 */
export async function healthCheck() {
  return api.get('/health')
}

// ==================== Helper Functions ====================

/**
 * Format relative time (e.g., "2 hours ago")
 * @param {Date|string} date - Date to format
 * @returns {string} Relative time string
 */
export function formatRelativeTime(date) {
  const now = new Date()
  const dateObj = typeof date === 'string' ? new Date(date) : date
  const diffMs = now - dateObj
  const diffSecs = Math.floor(diffMs / 1000)
  const diffMins = Math.floor(diffSecs / 60)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffSecs < 60) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`

  return dateObj.toLocaleDateString()
}

/**
 * Get color for OT status
 * @param {string} status - OT status
 * @returns {string} CSS variable name for status color
 */
export function getStatusColor(status) {
  const statusColorMap = {
    PREPLANIFICADA: '--status-preplanificada',
    PLANIFICADA: '--status-planificada',
    ASIGNADO_TAREA: '--status-asignado',
    DETENIDA: '--status-detenida',
    ANULADA: '--status-anulada',
    FINALIZADA: '--status-finalizada',
  }
  return `var(${statusColorMap[status] || '--color-text'})`
}

/**
 * Get color for project type
 * @param {string} projectType - Project type
 * @returns {string} Hex color code
 */
export function getProjectTypeColor(projectType) {
  const projectColorMap = {
    PUBLICO: '#1565c0',
    PRIVADO: '#2e7d32',
    TERCERIZADO: '#e65100',
  }
  return projectColorMap[projectType] || '#757575'
}

/**
 * Get badge background color for project type
 * @param {string} projectType - Project type
 * @returns {string} Hex background color
 */
export function getProjectTypeBgColor(projectType) {
  const projectBgMap = {
    PUBLICO: '#e3f2fd',
    PRIVADO: '#e8f5e9',
    TERCERIZADO: '#fff3e0',
  }
  return projectBgMap[projectType] || '#f5f5f5'
}

export default api

