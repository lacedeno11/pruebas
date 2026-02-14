/**
 * Application Constants
 * 
 * Centralized constants used throughout the frontend application.
 * Includes OT statuses, project types, cuadrilla types, and UI color mappings.
 */

/**
 * OT (Orden de Trabajo) Status Constants
 * 
 * Represents the lifecycle states of a work order
 */
export const OT_STATUSES = [
  'PREPLANIFICADA',   // Initial state, waiting for assignment
  'PLANIFICADA',      // Assigned to a cuadrilla
  'ASIGNADO_TAREA',   // Task assigned and work in progress
  'DETENIDA',         // Detained/stopped for some reason
  'ANULADA',          // Cancelled/annulled
  'FINALIZADA',       // Completed
];

/**
 * Project Type Constants with Display Labels
 * 
 * Different types of projects with varying requirements
 */
export const PROJECT_TYPES = {
  PUBLICO: 'Público',
  PRIVADO: 'Privado',
  TERCERIZADO: 'Tercerizado',
};

/**
 * Cuadrilla (Work Team) Type Constants with Display Labels
 * 
 * Classification of work teams by role and capacity
 */
export const CUADRILLA_TYPES = {
  PRINCIPAL: 'Principal',
  RESERVA: 'Reserva',
};

/**
 * Status Color Mapping for UI Display
 * 
 * Maps OT statuses to Tailwind CSS color classes and hex codes
 * for consistent visual representation throughout the application
 */
export const STATUS_COLORS = {
  PREPLANIFICADA: {
    bg: 'bg-gray-100',           // Light gray background
    text: 'text-gray-800',       // Dark gray text
    border: 'border-gray-300',   // Gray border
    hex: '#f3f4f6',              // Light gray hex
    badgeBg: 'bg-gray-200',      // Badge background
    badgeText: 'text-gray-700',  // Badge text
  },
  PLANIFICADA: {
    bg: 'bg-blue-100',           // Light blue background
    text: 'text-blue-800',       // Dark blue text
    border: 'border-blue-300',   // Blue border
    hex: '#dbeafe',              // Light blue hex
    badgeBg: 'bg-blue-200',      // Badge background
    badgeText: 'text-blue-700',  // Badge text
  },
  ASIGNADO_TAREA: {
    bg: 'bg-purple-100',         // Light purple background
    text: 'text-purple-800',     // Dark purple text
    border: 'border-purple-300', // Purple border
    hex: '#f3e8ff',              // Light purple hex
    badgeBg: 'bg-purple-200',    // Badge background
    badgeText: 'text-purple-700',// Badge text
  },
  DETENIDA: {
    bg: 'bg-yellow-100',         // Light yellow background
    text: 'text-yellow-800',     // Dark yellow text
    border: 'border-yellow-300', // Yellow border
    hex: '#fef3c7',              // Light yellow hex
    badgeBg: 'bg-yellow-200',    // Badge background
    badgeText: 'text-yellow-700',// Badge text
  },
  ANULADA: {
    bg: 'bg-red-100',            // Light red background
    text: 'text-red-800',        // Dark red text
    border: 'border-red-300',    // Red border
    hex: '#fee2e2',              // Light red hex
    badgeBg: 'bg-red-200',       // Badge background
    badgeText: 'text-red-700',   // Badge text
  },
  FINALIZADA: {
    bg: 'bg-green-100',          // Light green background
    text: 'text-green-800',      // Dark green text
    border: 'border-green-300',  // Green border
    hex: '#dcfce7',              // Light green hex
    badgeBg: 'bg-green-200',     // Badge background
    badgeText: 'text-green-700', // Badge text
  },
};

/**
 * Map Status to Display Labels
 * 
 * Provides human-readable labels for OT statuses
 */
export const STATUS_LABELS = {
  PREPLANIFICADA: 'Pre-planificada',
  PLANIFICADA: 'Planificada',
  ASIGNADO_TAREA: 'Asignado Tarea',
  DETENIDA: 'Detenida',
  ANULADA: 'Anulada',
  FINALIZADA: 'Finalizada',
};

/**
 * Result Status Constants for Agent Logs
 * 
 * Indicates the outcome of agent operations
 */
export const RESULT_STATUSES = {
  SUCCESS: 'SUCCESS',
  FAILURE: 'FAILURE',
  PENDING: 'PENDING',
};

/**
 * Result Status Color Mapping
 * 
 * Maps result statuses to colors for visual feedback
 */
export const RESULT_STATUS_COLORS = {
  SUCCESS: {
    bg: 'bg-green-100',
    text: 'text-green-800',
    hex: '#dcfce7',
  },
  FAILURE: {
    bg: 'bg-red-100',
    text: 'text-red-800',
    hex: '#fee2e2',
  },
  PENDING: {
    bg: 'bg-yellow-100',
    text: 'text-yellow-800',
    hex: '#fef3c7',
  },
};

/**
 * System Mode Constants
 * 
 * Indicates whether the system is in MOCK or PRODUCTION mode
 */
export const SYSTEM_MODES = {
  MOCK: 'MOCK',
  PRODUCTION: 'PRODUCTION',
};

/**
 * Map View Defaults
 * 
 * Ecuador coordinates for map center and initial zoom
 */
export const MAP_DEFAULTS = {
  CENTER_LAT: -1.5,           // Ecuador center latitude
  CENTER_LONG: -78.5,         // Ecuador center longitude
  INITIAL_ZOOM: 7,            // Initial map zoom level
  MAX_ZOOM: 18,               // Maximum zoom level
  MIN_ZOOM: 2,                // Minimum zoom level
};

/**
 * Distance Constants
 * 
 * Geographic distance thresholds used in the application
 */
export const DISTANCE_CONSTANTS = {
  MAX_ASSIGNMENT_DISTANCE_KM: 10,  // Maximum distance for OT assignment to cuadrilla
};

/**
 * Pagination Constants
 * 
 * Default values for paginated queries
 */
export const PAGINATION = {
  DEFAULT_LIMIT: 100,
  DEFAULT_PAGE: 1,
};

/**
 * API Response Delay Constants (for mockups)
 * 
 * Expected response times for simulating network latency
 */
export const API_DELAYS = {
  MOCK_API_LATENCY_MS: 500,    // Mock API simulates 500ms latency
  TOAST_DURATION_MS: 3000,     // Toast notification duration
};

/**
 * Empty State Messages
 * 
 * Messages shown when there is no data to display
 */
export const EMPTY_STATES = {
  NO_OTS: 'No se encontraron órdenes de trabajo',
  NO_CUADRILLAS: 'No se encontraron cuadrillas',
  NO_LOGS: 'No se encontraron registros de agentes',
};

/**
 * Loading States
 * 
 * Messages shown during data loading
 */
export const LOADING_STATES = {
  LOADING_OTS: 'Cargando órdenes de trabajo...',
  LOADING_CUADRILLAS: 'Cargando cuadrillas...',
  SYNCING_OTS: 'Sincronizando órdenes de trabajo...',
  PLANNING: 'Planificando asignaciones...',
  CHECKING_GOVERNANCE: 'Verificando gobernanza...',
};

