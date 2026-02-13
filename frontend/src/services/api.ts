import axios, { AxiosError, AxiosInstance } from 'axios';
import toast from 'react-hot-toast';
import { OT, Cuadrilla, AgentLog, OTStatus, ApiResponse } from '@/types';

// Create axios instance with base URL
const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const message = error.response?.data?.error ||
      error.response?.data?.message ||
      error.message ||
      'An error occurred';

    // Show error toast (but avoid duplicate toasts for multiple errors)
    if (error.config?.method !== 'get' || error.response?.status !== 404) {
      toast.error(String(message), {
        duration: 5000,
      });
    }

    return Promise.reject(error);
  }
);

/**
 * Get list of OTs with optional filters and pagination
 */
export async function getOTs(params?: {
  status?: OTStatus;
  projectType?: string;
  page?: number;
  limit?: number;
}): Promise<OT[]> {
  try {
    const response = await apiClient.get<ApiResponse<OT[]>>('/ots', { params });
    return response.data.data || [];
  } catch (error) {
    console.error('Failed to fetch OTs:', error);
    throw error;
  }
}

/**
 * Get a single OT by ID
 */
export async function getOTById(id: string): Promise<OT> {
  try {
    const response = await apiClient.get<OT>(`/ots/${id}`);
    return response.data;
  } catch (error) {
    console.error('Failed to fetch OT:', error);
    throw error;
  }
}

/**
 * Create a new OT
 */
export async function createOT(data: {
  externalId: string;
  projectType: string;
  status?: OTStatus;
  clienteName?: string;
  loginId?: string;
  lat?: number;
  long?: number;
}): Promise<OT> {
  try {
    const response = await apiClient.post<OT>('/ots', data);
    toast.success('OT created successfully');
    return response.data;
  } catch (error) {
    console.error('Failed to create OT:', error);
    throw error;
  }
}

/**
 * Update OT status with optional reason
 */
export async function updateOTStatus(
  id: string,
  status: OTStatus,
  reason?: string
): Promise<OT> {
  try {
    const response = await apiClient.patch<OT>(`/ots/${id}/status`, {
      status,
      reason,
    });
    toast.success('OT status updated successfully');
    return response.data;
  } catch (error) {
    console.error('Failed to update OT status:', error);
    throw error;
  }
}

/**
 * Update OT fields
 */
export async function updateOT(
  id: string,
  data: {
    clienteName?: string;
    loginId?: string;
    lat?: number;
    long?: number;
  }
): Promise<OT> {
  try {
    const response = await apiClient.patch<OT>(`/ots/${id}`, data);
    toast.success('OT updated successfully');
    return response.data;
  } catch (error) {
    console.error('Failed to update OT:', error);
    throw error;
  }
}

/**
 * Get list of cuadrillas with optional filters
 */
export async function getCuadrillas(params?: {
  type?: string;
  isActive?: boolean;
}): Promise<Cuadrilla[]> {
  try {
    const response = await apiClient.get<ApiResponse<Cuadrilla[]>>('/cuadrillas', {
      params,
    });
    return response.data.data || [];
  } catch (error) {
    console.error('Failed to fetch cuadrillas:', error);
    throw error;
  }
}

/**
 * Get a single cuadrilla by ID
 */
export async function getCuadrillaById(id: string): Promise<Cuadrilla> {
  try {
    const response = await apiClient.get<Cuadrilla>(`/cuadrillas/${id}`);
    return response.data;
  } catch (error) {
    console.error('Failed to fetch cuadrilla:', error);
    throw error;
  }
}

/**
 * Get centroid for a cuadrilla
 */
export async function getCuadrillaCentroid(id: string): Promise<{
  cuadrillaId: string;
  centroid: { lat: number; long: number } | null;
  otCount: number;
  validCoordsCount: number;
}> {
  try {
    const response = await apiClient.get(`/cuadrillas/${id}/centroid`);
    return response.data;
  } catch (error) {
    console.error('Failed to fetch cuadrilla centroid:', error);
    throw error;
  }
}

/**
 * Create a new cuadrilla
 */
export async function createCuadrilla(data: {
  name: string;
  type: string;
  dailyCapacity?: number;
}): Promise<Cuadrilla> {
  try {
    const response = await apiClient.post<Cuadrilla>('/cuadrillas', data);
    toast.success('Cuadrilla created successfully');
    return response.data;
  } catch (error) {
    console.error('Failed to create cuadrilla:', error);
    throw error;
  }
}

/**
 * Update a cuadrilla
 */
export async function updateCuadrilla(
  id: string,
  data: {
    name?: string;
    isActive?: boolean;
    dailyCapacity?: number;
  }
): Promise<Cuadrilla> {
  try {
    const response = await apiClient.patch<Cuadrilla>(`/cuadrillas/${id}`, data);
    toast.success('Cuadrilla updated successfully');
    return response.data;
  } catch (error) {
    console.error('Failed to update cuadrilla:', error);
    throw error;
  }
}

/**
 * Trigger planning workflow
 */
export async function triggerPlanning(params: {
  mode: 'full' | 'phase1' | 'phase2' | 'phase3';
  projectType?: string;
}): Promise<any> {
  try {
    const response = await apiClient.post('/agents/plan', params);
    toast.success('Planning workflow completed');
    return response.data;
  } catch (error) {
    console.error('Failed to trigger planning:', error);
    throw error;
  }
}

/**
 * Route a message to the agent router
 */
export async function routeAgentMessage(message: string, eventType?: string): Promise<any> {
  try {
    const response = await apiClient.post('/agents/route', {
      message,
      eventType,
    });
    return response.data;
  } catch (error) {
    console.error('Failed to route message:', error);
    throw error;
  }
}

/**
 * Get agent execution logs with pagination
 */
export async function getAgentLogs(params?: {
  page?: number;
  limit?: number;
  agentName?: string;
}): Promise<{ data: AgentLog[]; pagination: any }> {
  try {
    const response = await apiClient.get<ApiResponse<AgentLog[]>>('/agents/logs', {
      params,
    });
    return {
      data: response.data.data || [],
      pagination: response.data.pagination,
    };
  } catch (error) {
    console.error('Failed to fetch agent logs:', error);
    throw error;
  }
}

/**
 * Get document status for an OT (mock endpoint)
 */
export async function getDocumentStatus(otId: string): Promise<{
  otId: string;
  documentCount: number;
  requiredCount: number;
  documents: Array<{ name: string; uploaded: boolean }>;
}> {
  try {
    const response = await apiClient.get(`/telcodrive/documents/${otId}`);
    return response.data;
  } catch (error) {
    console.error('Failed to fetch document status:', error);
    throw error;
  }
}

/**
 * Get mock OTs from telcos API
 */
export async function getMockOTs(): Promise<any[]> {
  try {
    const response = await apiClient.get('/telcos/ots');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch mock OTs:', error);
    throw error;
  }
}

/**
 * Update OT status via mock telcos API
 */
export async function updateOTStatusViaTelcos(
  otId: string,
  status: string
): Promise<{ success: boolean; message: string }> {
  try {
    const response = await apiClient.post('/telcos/update_status', {
      otId,
      status,
    });
    return response.data;
  } catch (error) {
    console.error('Failed to update OT status via telcos:', error);
    throw error;
  }
}

/**
 * Get system status (health check)
 */
export async function getSystemStatus(): Promise<{
  status: string;
  timestamp: string;
  systemMode: 'MOCK' | 'PRODUCTION';
}> {
  try {
    const response = await apiClient.get('/health');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch system status:', error);
    throw error;
  }
}

export default apiClient;

