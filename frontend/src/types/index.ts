/**
 * Frontend Type Definitions for PEI Agent Platform
 *
 * This module exports all TypeScript interfaces and enums used throughout
 * the frontend application. Types are synchronized with the backend API
 * responses and database models.
 */

/**
 * OT Status Enumeration
 * Represents the lifecycle states of a work order (OT)
 */
export enum OTStatus {
  PREPLANIFICADA = "PREPLANIFICADA",      // Awaiting planning assignment
  PLANIFICADA = "PLANIFICADA",            // Assigned to cuadrilla
  ASIGNADO_TAREA = "ASIGNADO_TAREA",      // Tasks assigned to technicians
  DETENIDA = "DETENIDA",                  // Paused/detained
  ANULADA = "ANULADA",                    // Cancelled
  FINALIZADA = "FINALIZADA",              // Completed
}

/**
 * Project Type Enumeration
 * Different business classifications with varying governance rules
 */
export enum ProjectType {
  PUBLICO = "PUBLICO",           // Public/government projects (requires 29 docs)
  PRIVADO = "PRIVADO",           // Private customer projects
  TERCERIZADO = "TERCERIZADO",   // Outsourced/third-party projects
}

/**
 * Cuadrilla Type Enumeration
 * Classification of technical teams
 */
export enum CuadrillaType {
  PRINCIPAL = "PRINCIPAL",    // Base/primary teams
  RESERVA = "RESERVA",        // Backup/overflow teams
}

/**
 * Work Order (OT) Interface
 * Represents a single work order in the system
 */
export interface OT {
  id: number;
  external_id: string;                    // Unique ID from Telcos system
  status: OTStatus;
  project_type: ProjectType;
  lat: number | null;                     // Geographic latitude (nullable for GEO_ERROR)
  long: number | null;                    // Geographic longitude (nullable for GEO_ERROR)
  cliente_id: string;                     // Customer identifier
  login_id: string;                       // Login identifier
  is_geo_error: boolean;                  // Flag for geographic coordinate errors
  cuadrilla_id: number | null;            // Assigned cuadrilla ID
  cuadrilla_name?: string;                // Cuadrilla name (from populated relationship)
  assigned_at: string | null;             // Assignment timestamp (ISO format)
  detention_reason?: string;              // Reason for detention (if status=DETENIDA)
  created_at: string;                     // Creation timestamp (ISO format)
  updated_at: string;                     // Last update timestamp (ISO format)
}

/**
 * Cuadrilla (Technical Team) Interface
 * Represents a team that can be assigned OTs
 */
export interface Cuadrilla {
  id: number;
  name: string;
  type: CuadrillaType;
  current_load: number;                           // OTs currently assigned
  max_daily_capacity: number;                     // Maximum OTs per day
  last_centroid_lat: number | null;               // Last calculated center latitude
  last_centroid_long: number | null;              // Last calculated center longitude
  ots?: OT[];                                     // Assigned OTs (if populated)
  created_at: string;                             // Creation timestamp
  updated_at: string;                             // Last update timestamp
}

/**
 * Agent Log Interface
 * Tracks all agent actions for audit trail
 */
export interface AgentLog {
  id: number;
  ot_id: number | null;                   // Associated OT (nullable)
  agent_name: string;                     // Agent that performed action
  accion: string;                         // Action description
  resultado: "SUCCESS" | "FAILURE" | "WARNING";  // Action result
  raw_llm_response?: Record<string, any>; // Raw LLM response if used
  metadata?: Record<string, any>;         // Additional context
  timestamp: string;                      // Action timestamp (ISO format)
}

/**
 * Kanban Column Interface
 * Represents a status column in the Kanban board
 */
export interface KanbanColumn {
  status: OTStatus;
  title: string;
  ots: OT[];
  count: number;
}

/**
 * Dashboard Metrics Interface
 * Aggregated metrics for dashboard display
 */
export interface DashboardMetrics {
  total_ots: number;
  by_status: Record<OTStatus, number>;
  by_project_type: Record<ProjectType, number>;
  geo_error_count: number;
  cuadrilla_utilization_percent: number;
  cuadrillas_at_capacity: number;
  total_cuadrillas: number;
  avg_planning_time_hours: number;
  recent_activity: {
    new_ots_24h: number;
    completed_24h: number;
    failed_24h: number;
  };
}

/**
 * Kanban Data Interface
 * Data structure for Kanban board
 */
export interface KanbanData {
  columns: Record<OTStatus, KanbanColumn>;
  total_count: number;
  timestamp: string;
}

/**
 * Map Data Interface
 * Geographic data for map visualization
 */
export interface MapData {
  ots: Array<OT & { cuadrilla_name?: string }>;
  cuadrillas: Cuadrilla[];
  bounds: {
    north: number;
    south: number;
    east: number;
    west: number;
  };
  center: {
    latitude: number;
    longitude: number;
  };
  proximity_radius_km: number;
  timestamp: string;
}

/**
 * Alert Interface
 * Represents a governance alert
 */
export interface Alert {
  alert_type:
    | "DETENTION_CRITICAL"
    | "DETENTION_WARNING"
    | "PREPLANIFICADA_TIMEOUT"
    | "MISSING_DOCUMENTS";
  severity: "CRITICAL" | "WARNING" | "INFO";
  ot_id: number;
  external_id: string;
  message: string;
  days_detained?: number;
  days_until_cancellation?: number;
  hours_waiting?: number;
}

/**
 * Dashboard Alerts Interface
 * Aggregated alerts for dashboard
 */
export interface DashboardAlerts {
  detention_warnings: Alert[];
  preplanificada_timeouts: Alert[];
  document_warnings: Alert[];
  total_alerts: number;
  severity_breakdown: {
    CRITICAL: number;
    WARNING: number;
    INFO: number;
  };
  timestamp: string;
}

/**
 * API Response Interface
 * Standard API response wrapper
 */
export interface ApiResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
  error?: string;
  errors?: Record<string, string[]>;
}

/**
 * Paginated Response Interface
 * Wrapper for paginated list responses
 */
export interface PaginatedResponse<T> {
  total: number;
  skip: number;
  limit: number;
  count: number;
  data: T[];
}

/**
 * Agent State Interface
 * Represents the state of an agent execution
 */
export interface AgentState {
  input: string;
  agent_messages: Array<{
    agent: string;
    content: string;
    timestamp: string;
  }>;
  current_ot_id: number | null;
  ots_to_process: OT[];
  action_result: {
    success: boolean;
    message: string;
    data?: Record<string, any>;
  };
  error: string | null;
  metadata: Record<string, any>;
}

/**
 * Chat Message Interface
 * Represents a message in the agent chat
 */
export interface ChatMessage {
  role: "user" | "agent";
  content: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

/**
 * Drag and Drop Payload Interface
 * Data passed during drag & drop operations
 */
export interface DragPayload {
  ot_id: number;
  current_status: OTStatus;
  new_status: OTStatus;
}

/**
 * Transition Validation Result Interface
 * Result of validating an OT status transition
 */
export interface TransitionValidation {
  valid: boolean;
  message: string;
  error?: string;
  requires_detention_reason?: boolean;
}

/**
 * Form Submission Interface
 * Standard form submission with data
 */
export interface FormSubmission<T> {
  data: T;
  timestamp: string;
  errors?: Record<string, string>;
}

/**
 * UI State Interface
 * Manages UI-specific state
 */
export interface UIState {
  isDragging: boolean;
  selectedOTId: number | null;
  isSidebarOpen: boolean;
  activeView: "kanban" | "map" | "list";
  isLoading: boolean;
  error: string | null;
}

/**
 * Configuration Interface
 * Frontend configuration from backend
 */
export interface FrontendConfig {
  system_mode: "MOCK" | "PROD";
  is_mock_mode: boolean;
  map: {
    center: {
      latitude: number;
      longitude: number;
    };
    zoom: number;
    bounds: {
      north: number;
      south: number;
      east: number;
      west: number;
    };
  };
  project_types: ProjectType[];
  ot_statuses: OTStatus[];
  cuadrilla_types: CuadrillaType[];
  features: {
    kanban_view: boolean;
    map_view: boolean;
    agent_chat: boolean;
    drag_drop_planning: boolean;
    governance_alerts: boolean;
  };
  api_version: string;
}

/**
 * Filter Options Interface
 * Options for filtering OTs
 */
export interface OTFilters {
  status?: OTStatus;
  project_type?: ProjectType;
  cuadrilla_id?: number;
  is_geo_error?: boolean;
  skip?: number;
  limit?: number;
}

/**
 * Sort Options Interface
 * Options for sorting lists
 */
export interface SortOptions {
  field: keyof OT | keyof AgentLog;
  direction: "asc" | "desc";
}

/**
 * Query Options Interface
 * Options for API queries with React Query
 */
export interface QueryOptions<T> {
  enabled?: boolean;
  staleTime?: number;
  cacheTime?: number;
  retry?: number | boolean;
  retryDelay?: number;
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
}

export default {
  OTStatus,
  ProjectType,
  CuadrillaType,
};

