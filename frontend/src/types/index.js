/**
 * @typedef {Object} OT
 * @property {number} id - Unique identifier (primary key)
 * @property {string} external_id - External ID from TELCOS system (unique)
 * @property {string} status - Current OT status (PREPLANIFICADA | PLANIFICADA | ASIGNADO_TAREA | DETENIDA | ANULADA | FINALIZADA)
 * @property {string} project_type - Type of project (PUBLICO | PRIVADO | TERCERIZADO)
 * @property {string} cliente_id - Customer ID from BSS system
 * @property {string} login_id - Login/Service point ID
 * @property {number|null} lat - Latitude coordinate (nullable)
 * @property {number|null} long - Longitude coordinate (nullable)
 * @property {boolean} error_geo - Flag indicating missing geographic data
 * @property {number|null} cuadrilla_id - Assigned team ID (nullable, foreign key)
 * @property {string} created_at - ISO 8601 creation timestamp
 * @property {string} updated_at - ISO 8601 last update timestamp
 */

/**
 * @typedef {Object} Cuadrilla
 * @property {number} id - Unique identifier (primary key)
 * @property {string} name - Team name (unique)
 * @property {string} type - Team type (Principal | Reserva)
 * @property {number|null} last_centroid_lat - Last calculated centroid latitude (nullable)
 * @property {number|null} last_centroid_long - Last calculated centroid longitude (nullable)
 * @property {number} capacity - Maximum OT capacity (default: 10)
 * @property {number} current_load - Current number of assigned OTs (default: 0)
 * @property {string} created_at - ISO 8601 creation timestamp
 */

/**
 * @enum {string}
 * OT Status enumeration for work order lifecycle
 */
const OTStatus = {
  PREPLANIFICADA: 'PREPLANIFICADA',  // Initial state, awaiting planning
  PLANIFICADA: 'PLANIFICADA',        // Assigned to a team plan
  ASIGNADO_TAREA: 'ASIGNADO_TAREA',  // Task assigned to specific team member
  DETENIDA: 'DETENIDA',              // Work halted/paused
  ANULADA: 'ANULADA',                // Cancelled/voided
  FINALIZADA: 'FINALIZADA'           // Completed
}

/**
 * @enum {string}
 * Project Type enumeration for classification
 */
const ProjectType = {
  PUBLICO: 'PUBLICO',        // Public/government projects (requires 29 documents)
  PRIVADO: 'PRIVADO',        // Private customer projects
  TERCERIZADO: 'TERCERIZADO' // Third-party/outsourced projects
}

/**
 * Status badge color mapping for UI display
 * @type {Object<string, string>}
 */
const StatusColors = {
  PREPLANIFICADA: '#FFD700',   // Yellow
  PLANIFICADA: '#1E90FF',      // Blue
  ASIGNADO_TAREA: '#9370DB',   // Purple
  DETENIDA: '#FF8C00',         // Orange
  ANULADA: '#DC143C',          // Red
  FINALIZADA: '#32CD32'        // Green
}

/**
 * Project type badge color mapping for UI display
 * @type {Object<string, string>}
 */
const ProjectTypeColors = {
  PUBLICO: '#4169E1',       // Royal Blue
  PRIVADO: '#228B22',       // Forest Green
  TERCERIZADO: '#FF6347'    // Tomato
}

export {
  OTStatus,
  ProjectType,
  StatusColors,
  ProjectTypeColors
}

