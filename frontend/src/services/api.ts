/**
 * API Service Module for PEI Frontend
 *
 * This module provides an axios HTTP client and functions for all API interactions
 * with the backend PEI Agent Platform. It includes request/response interceptors,
 * error handling, and React Query integration.
 */

import axios, { AxiosError, AxiosInstance, AxiosResponse } from "axios";
import {
  OT,
  Cuadrilla,
  AgentLog,
  KanbanData,
  MapData,
  DashboardMetrics,
  DashboardAlerts,
  OTFilters,
  ApiResponse,
  PaginatedResponse,
} from "../types";

/**
 * Create axios instance with default configuration
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * Response interceptor for error handling
 */
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Handle specific error codes
    if (error.response?.status === 401) {
      // Unauthorized - could redirect to login
      console.error("Unauthorized - session may have expired");
    } else if (error.response?.status === 403) {
      // Forbidden
      console.error("Access denied");
    } else if (error.response?.status === 404) {
      // Not found
      console.error("Resource not found");
    } else if (error.response?.status === 500) {
      // Server error
      console.error("Server error - please try again later");
    }

    return Promise.reject(error);
  }
);

/**
 * Request interceptor for adding auth headers if needed
 */
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token from localStorage if available
    const token = localStorage.getItem("auth_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ============================================================================
// OT ENDPOINTS
// ============================================================================

/**
 * Fetch OTs with optional filtering and pagination
 */
export async function fetchOTs(
  filters?: OTFilters
): Promise<PaginatedResponse<OT>> {
  const params = new URLSearchParams();

  if (filters) {
    if (filters.status) params.append("status", filters.status);
    if (filters.project_type) params.append("project_type", filters.project_type);
    if (filters.cuadrilla_id) params.append("cuadrilla_id", filters.cuadrilla_id.toString());
    if (filters.is_geo_error !== undefined) params.append("is_geo_error", filters.is_geo_error.toString());
    if (filters.skip) params.append("skip", filters.skip.toString());
    if (filters.limit) params.append("limit", filters.limit.toString());
  }

  const response = await apiClient.get<PaginatedResponse<OT>>("/api/ots", {
    params: Object.fromEntries(params),
  });
  return response.data;
}

/**
 * Fetch a single OT by ID
 */
export async function fetchOTById(id: number): Promise<OT> {
  const response = await apiClient.get<OT>(`/api/ots/${id}`);
  return response.data;
}

/**
 * Update OT status with optional detention reason
 */
export async function updateOTStatus(
  id: number,
  newStatus: string,
  reason?: string
): Promise<OT> {
  const params = new URLSearchParams();
  params.append("new_status", newStatus);
  if (reason) params.append("reason", reason);

  const response = await apiClient.patch<OT>(`/api/ots/${id}/status`, null, {
    params: Object.fromEntries(params),
  });
  return response.data;
}

/**
 * Fetch OTs with geographic errors
 */
export async function fetchGeoErrorOTs(
  skip?: number,
  limit?: number
): Promise<PaginatedResponse<OT>> {
  const params = new URLSearchParams();
  if (skip) params.append("skip", skip.toString());
  if (limit) params.append("limit", limit.toString());

  const response = await apiClient.get<PaginatedResponse<OT>>(
    "/api/ots/geo-errors",
    { params: Object.fromEntries(params) }
  );
  return response.data;
}

/**
 * Trigger OT ingestion from external API
 */
export async function triggerOTIngestion(): Promise<ApiResponse> {
  const response = await apiClient.post<ApiResponse>("/api/ots/ingest");
  return response.data;
}

// ============================================================================
// CUADRILLA ENDPOINTS
// ============================================================================

/**
 * Fetch all cuadrillas with optional filtering
 */
export async function fetchCuadrillas(
  type?: string,
  skip?: number,
  limit?: number
): Promise<PaginatedResponse<Cuadrilla>> {
  const params = new URLSearchParams();
  if (type) params.append("cuadrilla_type", type);
  if (skip) params.append("skip", skip.toString());
  if (limit) params.append("limit", limit.toString());

  const response = await apiClient.get<PaginatedResponse<Cuadrilla>>(
    "/api/cuadrillas",
    { params: Object.fromEntries(params) }
  );
  return response.data;
}

/**
 * Fetch a single cuadrilla by ID with assigned OTs
 */
export async function fetchCuadrillaById(id: number): Promise<Cuadrilla> {
  const response = await apiClient.get<Cuadrilla>(`/api/cuadrillas/${id}`);
  return response.data;
}

/**
 * Fetch cuadrilla centroid coordinates
 */
export async function fetchCuadrillaCentroid(
  id: number
): Promise<{
  centroid_lat: number | null;
  centroid_long: number | null;
  has_centroid: boolean;
  ot_count: number;
}> {
  const response = await apiClient.get(`/api/cuadrillas/${id}/centroid`);
  return response.data;
}

/**
 * Create a new cuadrilla
 */
export async function createCuadrilla(
  name: string,
  type: string,
  maxDailyCapacity?: number
): Promise<Cuadrilla> {
  const response = await apiClient.post<Cuadrilla>("/api/cuadrillas", null, {
    params: {
      name,
      cuadrilla_type: type,
      max_daily_capacity: maxDailyCapacity || 10,
    },
  });
  return response.data;
}

/**
 * Update a cuadrilla
 */
export async function updateCuadrilla(
  id: number,
  name?: string,
  maxDailyCapacity?: number
): Promise<Cuadrilla> {
  const params = new URLSearchParams();
  if (name) params.append("name", name);
  if (maxDailyCapacity) params.append("max_daily_capacity", maxDailyCapacity.toString());

  const response = await apiClient.patch<Cuadrilla>(
    `/api/cuadrillas/${id}`,
    null,
    { params: Object.fromEntries(params) }
  );
  return response.data;
}

/**
 * Fetch cuadrilla capacity statistics
 */
export async function fetchCuadrillaStats(): Promise<ApiResponse> {
  const response = await apiClient.get<ApiResponse>("/api/cuadrillas/stats");
  return response.data;
}

// ============================================================================
// AGENT ENDPOINTS
// ============================================================================

/**
 * Execute agent workflow with user input
 */
export async function executeAgent(input: string): Promise<ApiResponse> {
  const response = await apiClient.post<ApiResponse>("/api/agents/execute", {
    input,
  });
  return response.data;
}

/**
 * Trigger planning agent for OT assignment
 */
export async function triggerPlanning(
  otIds?: number[]
): Promise<ApiResponse> {
  const response = await apiClient.post<ApiResponse>("/api/agents/plan", {
    ot_ids: otIds,
  });
  return response.data;
}

/**
 * Validate OT status transition
 */
export async function validateTransition(
  otId: number,
  newStatus: string,
  reason?: string
): Promise<{
  valid: boolean;
  message: string;
  error?: string;
  requires_detention_reason?: boolean;
}> {
  const response = await apiClient.post(
    "/api/agents/validate-transition",
    {
      ot_id: otId,
      new_status: newStatus,
      reason,
    }
  );
  return response.data;
}

/**
 * Fetch agent execution logs with filtering
 */
export async function fetchAgentLogs(
  agentName?: string,
  resultado?: string,
  dateFrom?: string,
  dateTo?: string,
  skip?: number,
  limit?: number
): Promise<PaginatedResponse<AgentLog>> {
  const params = new URLSearchParams();
  if (agentName) params.append("agent_name", agentName);
  if (resultado) params.append("resultado", resultado);
  if (dateFrom) params.append("date_from", dateFrom);
  if (dateTo) params.append("date_to", dateTo);
  if (skip) params.append("skip", skip.toString());
  if (limit) params.append("limit", limit.toString());

  const response = await apiClient.get<PaginatedResponse<AgentLog>>(
    "/api/agents/logs",
    { params: Object.fromEntries(params) }
  );
  return response.data;
}

// ============================================================================
// DASHBOARD ENDPOINTS
// ============================================================================

/**
 * Fetch dashboard metrics
 */
export async function fetchDashboardMetrics(): Promise<DashboardMetrics> {
  const response = await apiClient.get<DashboardMetrics>(
    "/api/dashboard/metrics"
  );
  return response.data;
}

/**
 * Fetch Kanban board data
 */
export async function fetchKanbanData(): Promise<KanbanData> {
  const response = await apiClient.get<KanbanData>("/api/dashboard/kanban");
  return response.data;
}

/**
 * Fetch map visualization data
 */
export async function fetchMapData(): Promise<MapData> {
  const response = await apiClient.get<MapData>("/api/dashboard/map");
  return response.data;
}

/**
 * Fetch governance alerts
 */
export async function fetchDashboardAlerts(): Promise<DashboardAlerts> {
  const response = await apiClient.get<DashboardAlerts>(
    "/api/dashboard/alerts"
  );
  return response.data;
}

// ============================================================================
// CONFIGURATION & HEALTH
// ============================================================================

/**
 * Fetch frontend configuration from backend
 */
export async function fetchFrontendConfig(): Promise<ApiResponse> {
  const response = await apiClient.get<ApiResponse>("/api/config");
  return response.data;
}

/**
 * Check backend health
 */
export async function checkHealth(): Promise<{ status: string; mode: string }> {
  const response = await apiClient.get("/health");
  return response.data;
}

// ============================================================================
// QUICK ACTION ENDPOINTS
// ============================================================================

/**
 * Quick ingest OTs shortcut
 */
export async function quickIngest(): Promise<ApiResponse> {
  const response = await apiClient.post<ApiResponse>(
    "/api/agents/quick-actions/ingest"
  );
  return response.data;
}

/**
 * Quick run planning shortcut
 */
export async function quickPlan(): Promise<ApiResponse> {
  const response = await apiClient.post<ApiResponse>(
    "/api/agents/quick-actions/plan"
  );
  return response.data;
}

/**
 * Quick check alerts shortcut
 */
export async function quickCheckAlerts(): Promise<ApiResponse> {
  const response = await apiClient.post<ApiResponse>(
    "/api/agents/quick-actions/check-alerts"
  );
  return response.data;
}

// ============================================================================
// WEBSOCKET CONNECTION
// ============================================================================

/**
 * Create WebSocket connection for agent chat
 * Returns WebSocket instance that can be used for real-time communication
 */
export function createChatWebSocket(): WebSocket {
  const protocol = import.meta.env.VITE_API_URL?.startsWith("https")
    ? "wss"
    : "ws";
  const baseURL = (import.meta.env.VITE_API_URL || "http://localhost:8000")
    .replace("https://", "")
    .replace("http://", "");

  return new WebSocket(`${protocol}://${baseURL}/api/agents/ws/chat`);
}

// ============================================================================
// ERROR HANDLING UTILITIES
// ============================================================================

/**
 * Handle API errors and extract error message
 */
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (error.response?.data?.message) {
      return error.response.data.message;
    }
    if (error.response?.data?.detail) {
      return error.response.data.detail;
    }
    if (error.response?.status === 404) {
      return "Resource not found";
    }
    if (error.response?.status === 500) {
      return "Server error - please try again later";
    }
    return error.message || "An error occurred";
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "An unknown error occurred";
}

/**
 * Retry failed requests with exponential backoff
 */
export async function retryRequest<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  delay: number = 1000
): Promise<T> {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (attempt === maxRetries - 1) {
        throw error;
      }
      await new Promise((resolve) => setTimeout(resolve, delay * Math.pow(2, attempt)));
    }
  }
  throw new Error("Max retries exceeded");
}

// ============================================================================
// EXPORT DEFAULTS
// ============================================================================

export default apiClient;

