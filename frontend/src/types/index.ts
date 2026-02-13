/**
 * OT Status enumeration
 * Represents the lifecycle states of an OT (Orden de Trabajo)
 */
export enum OTStatus {
  PREPLANIFICADA = 'PREPLANIFICADA',
  PLANIFICADA = 'PLANIFICADA',
  ASIGNADO_TAREA = 'ASIGNADO_TAREA',
  DETENIDA = 'DETENIDA',
  ANULADA = 'ANULADA',
  FINALIZADA = 'FINALIZADA',
}

/**
 * Project Type enumeration
 * Categorizes OTs by project type for resource allocation
 */
export enum ProjectType {
  PUBLICO = 'PUBLICO',
  PRIVADO = 'PRIVADO',
  TERCERIZADO = 'TERCERIZADO',
}

/**
 * Cuadrilla (Crew) Type enumeration
 * Distinguishes between primary and reserve crews
 */
export enum CuadrillaType {
  PRINCIPAL = 'PRINCIPAL',
  RESERVA = 'RESERVA',
}

/**
 * OT (Orden de Trabajo) interface
 * Represents a work order in the system
 */
export interface OT {
  id: string;
  externalId: string;
  status: OTStatus;
  projectType: ProjectType;
  clienteName?: string;
  loginId?: string;
  lat?: number;
  long?: number;
  assignedCuadrillaId?: string;
  hasGeoError: boolean;
  createdAt: string;
  updatedAt: string;
  cuadrilla?: Cuadrilla;
}

/**
 * Cuadrilla (Crew) interface
 * Represents a team of workers assigned to OTs
 */
export interface Cuadrilla {
  id: string;
  name: string;
  type: CuadrillaType;
  lastCentroidLat?: number;
  lastCentroidLong?: number;
  dailyCapacity: number;
  currentLoad: number;
  isActive: boolean;
  createdAt: string;
  ots?: OT[];
}

/**
 * Agent Log interface
 * Tracks all agent executions and actions
 */
export interface AgentLog {
  id: string;
  otId?: string;
  agentName: string;
  accion: string;
  resultado: string;
  rawLlmResponse?: string;
  errorMessage?: string;
  createdAt: string;
  ot?: OT;
}

/**
 * Assignment interface
 * Represents the assignment of an OT to a Cuadrilla
 */
export interface Assignment {
  id: string;
  otId: string;
  cuadrillaId: string;
  assignedByAgent: string;
  distanceFromCentroid?: number;
  createdAt: string;
  ot?: OT;
  cuadrilla?: Cuadrilla;
}

/**
 * Generic API Response wrapper
 * Provides consistent response structure across all API endpoints
 */
export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  message?: string;
  pagination?: {
    page: number;
    limit: number;
    total: number;
    pages?: number;
  };
  status?: 'success' | 'error';
  timestamp?: string;
}

/**
 * Pagination Parameters interface
 * Used for list queries with pagination support
 */
export interface PaginationParams {
  page?: number;
  limit?: number;
}

/**
 * OT Filter Parameters interface
 * Used for filtering OTs in list queries
 */
export interface OTFilterParams extends PaginationParams {
  status?: OTStatus;
  projectType?: ProjectType;
}

/**
 * Cuadrilla Filter Parameters interface
 * Used for filtering Cuadrillas in list queries
 */
export interface CuadrillaFilterParams {
  type?: CuadrillaType;
  isActive?: boolean;
}

/**
 * Agent Result interface
 * Represents the result of an agent execution
 */
export interface AgentResult {
  success: boolean;
  data?: any;
  error?: string;
  llmResponse?: string;
  nextAgent?: string;
}

/**
 * Planning Mode type
 * Determines which phases of the planning algorithm to execute
 */
export type PlanningMode = 'full' | 'phase1' | 'phase2' | 'phase3';

/**
 * Planning Request interface
 * Used to trigger planning workflow
 */
export interface PlanningRequest {
  mode: PlanningMode;
  projectType?: ProjectType;
}

/**
 * Planning Result interface
 * Contains results from planning execution
 */
export interface PlanningResult {
  phase1?: {
    assigned: number;
    phase: 1;
  };
  phase2?: {
    assigned: number;
    rejected: number;
    phase: 2;
  };
  phase3?: {
    optimized: number;
    phase: 3;
  };
}

/**
 * Document Status interface
 * Tracks document upload progress for PUBLICO projects
 */
export interface DocumentStatus {
  otId: string;
  documentCount: number;
  requiredCount: number;
  documents: Array<{
    name: string;
    uploaded: boolean;
  }>;
}

/**
 * Communication Type
 * Specifies the communication channel
 */
export type CommunicationType = 'telegram' | 'email';

/**
 * Communication Request interface
 * Used to send notifications
 */
export interface CommunicationRequest {
  type: CommunicationType;
  recipients: string[];
  subject?: string;
  message: string;
  otIds?: string[];
  alertType?: 'ERROR_GEO' | 'INACTIVIDAD_WARNING' | 'AUTO_CANCELLATION' | 'HIGH_PRIORITY';
}

/**
 * Governance Alert interface
 * Represents alerts from governance checks
 */
export interface GovernanceAlert {
  otIds: string[];
  daysDetained?: number;
  alertType: 'INACTIVIDAD_WARNING' | 'AUTO_CANCELLATION' | 'HIGH_PRIORITY';
  severity: 'warning' | 'critical';
  message: string;
}

/**
 * Chat Message interface
 * Represents a message in the agent chat
 */
export interface ChatMessage {
  role: 'user' | 'agent' | 'system';
  content: string;
  timestamp: Date;
  metadata?: {
    intent?: string;
    confidence?: number;
  };
}

/**
 * UI State interface
 * Represents the UI application state (used by Zustand store)
 */
export interface UIState {
  selectedOTId?: string;
  sidebarOpen: boolean;
  mapCenter: {
    lat: number;
    lng: number;
    zoom: number;
  };
  setSelectedOT: (otId?: string) => void;
  toggleSidebar: () => void;
  setMapCenter: (lat: number, lng: number, zoom: number) => void;
}

/**
 * Kanban Column interface
 * Represents a column in the Kanban board
 */
export interface KanbanColumn {
  status: OTStatus;
  label: string;
  color: string;
  ots: OT[];
}

/**
 * Map Marker interface
 * Represents a marker on the map
 */
export interface MapMarker {
  id: string;
  lat: number;
  lng: number;
  type: 'ot' | 'cuadrilla';
  data: OT | Cuadrilla;
  color: string;
}

/**
 * Error Response interface
 * Standard error response from API
 */
export interface ErrorResponse {
  error: string;
  details?: string;
  statusCode?: number;
  timestamp?: string;
}

/**
 * Status Color Map type
 * Maps OT statuses to their display colors
 */
export type StatusColorMap = Record<OTStatus, string>;

/**
 * Project Type Color Map type
 * Maps project types to their display colors
 */
export type ProjectTypeColorMap = Record<ProjectType, string>;

