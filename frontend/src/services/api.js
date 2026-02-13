import axios from 'axios'
import { toast } from 'react-toastify'

const client = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add request interceptor for error handling
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'An error occurred'
    toast.error(message)
    return Promise.reject(error)
  }
)

// OT endpoints
export async function fetchOTs(filters = {}) {
  try {
    const params = new URLSearchParams()
    if (filters.status) params.append('status', filters.status)
    if (filters.project_type) params.append('project_type', filters.project_type)
    if (filters.cuadrilla_id) params.append('cuadrilla_id', filters.cuadrilla_id)

    const response = await client.get(`/ots?${params}`)
    return response.data
  } catch (error) {
    throw error
  }
}

export async function fetchOTById(id) {
  try {
    const response = await client.get(`/ots/${id}`)
    return response.data
  } catch (error) {
    throw error
  }
}

export async function createOT(otData) {
  try {
    const response = await client.post('/ots', otData)
    toast.success('OT created successfully')
    return response.data
  } catch (error) {
    throw error
  }
}

export async function updateOT(id, otData) {
  try {
    const response = await client.put(`/ots/${id}`, otData)
    toast.success('OT updated successfully')
    return response.data
  } catch (error) {
    throw error
  }
}

export async function updateOTStatus(id, newStatus, metadata = {}) {
  try {
    const response = await client.put(`/ots/${id}/status`, {
      status: newStatus,
      ...metadata
    })
    toast.success(`OT status updated to ${newStatus}`)
    return response.data
  } catch (error) {
    throw error
  }
}

// Cuadrilla endpoints
export async function fetchCuadrillas() {
  try {
    const response = await client.get('/cuadrillas')
    return response.data
  } catch (error) {
    throw error
  }
}

export async function fetchCuadrillaById(id) {
  try {
    const response = await client.get(`/cuadrillas/${id}`)
    return response.data
  } catch (error) {
    throw error
  }
}

export async function fetchCuadrillaOTs(cuadrillaId) {
  try {
    const response = await client.get(`/cuadrillas/${cuadrillaId}/ots`)
    return response.data
  } catch (error) {
    throw error
  }
}

export async function createCuadrilla(cuadrillaData) {
  try {
    const response = await client.post('/cuadrillas', cuadrillaData)
    toast.success('Cuadrilla created successfully')
    return response.data
  } catch (error) {
    throw error
  }
}

// Agent endpoints
export async function triggerPlanning() {
  try {
    const response = await client.post('/agents/plan')
    toast.success('Planning triggered successfully')
    return response.data
  } catch (error) {
    throw error
  }
}

export async function sendChatMessage(message) {
  try {
    const response = await client.post('/agents/chat', {
      message: message
    })
    return response.data
  } catch (error) {
    throw error
  }
}

export async function fetchAgentLogs(filters = {}) {
  try {
    const params = new URLSearchParams()
    if (filters.agente_name) params.append('agente_name', filters.agente_name)
    if (filters.ot_id) params.append('ot_id', filters.ot_id)
    if (filters.limit) params.append('limit', filters.limit)

    const response = await client.get(`/agents/logs?${params}`)
    return response.data
  } catch (error) {
    throw error
  }
}

// Mock endpoints (SYSTEM_MODE=MOCK only)
export async function getMockOTs() {
  try {
    const response = await client.get('/mock/telcos/ots')
    return response.data
  } catch (error) {
    throw error
  }
}

export async function updateMockOTStatus(otId, newStatus) {
  try {
    const response = await client.post('/mock/telcos/update_status', {
      ot_id: otId,
      new_status: newStatus
    })
    return response.data
  } catch (error) {
    throw error
  }
}

export async function getMockDocuments(otId) {
  try {
    const response = await client.get(`/mock/telcodrive/documents?ot_id=${otId}`)
    return response.data
  } catch (error) {
    throw error
  }
}

// Health check
export async function healthCheck() {
  try {
    const response = await client.get('/')
    return response.data
  } catch (error) {
    throw error
  }
}

export default client

