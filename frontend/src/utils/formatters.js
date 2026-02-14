/**
 * Formatter Utilities
 * 
 * Collection of utility functions for formatting data display in the UI.
 * Uses date-fns for date formatting and constants for consistent styling.
 */

import { format, formatDistance } from 'date-fns';
import { es } from 'date-fns/locale';
import { STATUS_COLORS, STATUS_LABELS, PROJECT_TYPES } from './constants';

/**
 * Format a date string to a human-readable date display.
 * 
 * Converts ISO date strings to formatted date strings with Spanish locale.
 * Examples:
 *   - "2024-02-13T10:30:00" -> "13/02/2024"
 *   - "2024-02-13T10:30:00" -> "13/02/2024 10:30" (with time)
 * 
 * @param {string|Date} dateString - ISO date string or Date object to format
 * @param {boolean} includeTime - Optional: include time in output (default: false)
 * @returns {string} Formatted date string (e.g., "13/02/2024" or "13/02/2024 10:30")
 * 
 * @example
 * formatDate('2024-02-13T10:30:00');
 * // Returns: "13/02/2024"
 * 
 * @example
 * formatDate('2024-02-13T10:30:00', true);
 * // Returns: "13/02/2024 10:30"
 */
export const formatDate = (dateString, includeTime = false) => {
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) {
      return 'Invalid date';
    }
    
    if (includeTime) {
      return format(date, 'dd/MM/yyyy HH:mm', { locale: es });
    }
    
    return format(date, 'dd/MM/yyyy', { locale: es });
  } catch (error) {
    console.error('Error formatting date:', error);
    return 'Invalid date';
  }
};

/**
 * Format date to relative time format (e.g., "2 hours ago", "3 days ago").
 * 
 * Uses date-fns formatDistance with Spanish locale for natural language display.
 * 
 * @param {string|Date} dateString - ISO date string or Date object to format
 * @returns {string} Relative time string (e.g., "hace 2 horas", "hace 3 días")
 * 
 * @example
 * formatDateRelative('2024-02-13T10:30:00');
 * // Returns: "hace 2 horas" (if current time is 12:30)
 */
export const formatDateRelative = (dateString) => {
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) {
      return 'Invalid date';
    }
    
    return formatDistance(date, new Date(), {
      addSuffix: true,
      locale: es,
    });
  } catch (error) {
    console.error('Error formatting relative date:', error);
    return 'Invalid date';
  }
};

/**
 * Format geographic coordinates to a human-readable string.
 * 
 * Converts latitude and longitude to a formatted coordinate string.
 * Examples:
 *   - (-1.2345, -78.5432) -> "-1.23°, -78.54°"
 *   - (-1.2345, -78.5432) -> "-1.2345°, -78.5432°" (with 4 decimals)
 * 
 * @param {number} lat - Latitude value
 * @param {number} long - Longitude value
 * @param {number} decimals - Optional: number of decimal places (default: 2)
 * @returns {string} Formatted coordinate string
 * 
 * @example
 * formatCoordinate(-1.2345, -78.5432);
 * // Returns: "-1.23°, -78.54°"
 * 
 * @example
 * formatCoordinate(-1.2345, -78.5432, 4);
 * // Returns: "-1.2345°, -78.5432°"
 */
export const formatCoordinate = (lat, long, decimals = 2) => {
  if (lat === null || lat === undefined || long === null || long === undefined) {
    return 'N/A';
  }
  
  const latFormatted = parseFloat(lat).toFixed(decimals);
  const longFormatted = parseFloat(long).toFixed(decimals);
  
  return `${latFormatted}°, ${longFormatted}°`;
};

/**
 * Get human-readable label for an OT status.
 * 
 * Converts status code to display label using STATUS_LABELS constant.
 * Examples:
 *   - "PREPLANIFICADA" -> "Pre-planificada"
 *   - "ASIGNADO_TAREA" -> "Asignado Tarea"
 * 
 * @param {string} status - OT status code (e.g., "PREPLANIFICADA", "PLANIFICADA")
 * @returns {string} Human-readable status label
 * 
 * @example
 * getStatusLabel('PREPLANIFICADA');
 * // Returns: "Pre-planificada"
 * 
 * @example
 * getStatusLabel('FINALIZADA');
 * // Returns: "Finalizada"
 */
export const getStatusLabel = (status) => {
  if (!status) {
    return 'Unknown';
  }
  
  return STATUS_LABELS[status.toUpperCase()] || status;
};

/**
 * Get Tailwind CSS classes for an OT status.
 * 
 * Returns background and text color classes based on OT status.
 * Examples:
 *   - "PREPLANIFICADA" -> { bg: "bg-gray-100", text: "text-gray-800", ... }
 *   - "FINALIZADA" -> { bg: "bg-green-100", text: "text-green-800", ... }
 * 
 * @param {string} status - OT status code
 * @returns {Object} Object containing:
 *   - bg: background color class
 *   - text: text color class
 *   - border: border color class
 *   - hex: hex color code
 *   - badgeBg: badge background class
 *   - badgeText: badge text class
 * 
 * @example
 * const colors = getStatusColor('FINALIZADA');
 * // Returns: { 
 * //   bg: "bg-green-100", 
 * //   text: "text-green-800", 
 * //   border: "border-green-300",
 * //   hex: "#dcfce7",
 * //   badgeBg: "bg-green-200",
 * //   badgeText: "text-green-700"
 * // }
 */
export const getStatusColor = (status) => {
  if (!status) {
    return STATUS_COLORS.PREPLANIFICADA; // Default color
  }
  
  return STATUS_COLORS[status.toUpperCase()] || STATUS_COLORS.PREPLANIFICADA;
};

/**
 * Get Tailwind CSS background class for a project type badge.
 * 
 * Returns appropriate background and text color classes based on project type.
 * Examples:
 *   - "PUBLICO" -> { bg: "bg-blue-200", text: "text-blue-700", label: "Público" }
 *   - "PRIVADO" -> { bg: "bg-purple-200", text: "text-purple-700", label: "Privado" }
 *   - "TERCERIZADO" -> { bg: "bg-orange-200", text: "text-orange-700", label: "Tercerizado" }
 * 
 * @param {string} type - Project type (e.g., "PUBLICO", "PRIVADO", "TERCERIZADO")
 * @returns {Object} Object containing:
 *   - bg: badge background color class
 *   - text: badge text color class
 *   - label: human-readable project type label
 * 
 * @example
 * const badge = getProjectTypeBadgeColor('PUBLICO');
 * // Returns: {
 * //   bg: "bg-blue-200",
 * //   text: "text-blue-700",
 * //   label: "Público"
 * // }
 */
export const getProjectTypeBadgeColor = (type) => {
  if (!type) {
    return {
      bg: 'bg-gray-200',
      text: 'text-gray-700',
      label: 'Unknown',
    };
  }
  
  const typeUpper = type.toUpperCase();
  const label = PROJECT_TYPES[typeUpper] || type;
  
  // Define badge colors for each project type
  const projectTypeBadgeColors = {
    PUBLICO: {
      bg: 'bg-blue-200',
      text: 'text-blue-700',
      label,
    },
    PRIVADO: {
      bg: 'bg-purple-200',
      text: 'text-purple-700',
      label,
    },
    TERCERIZADO: {
      bg: 'bg-orange-200',
      text: 'text-orange-700',
      label,
    },
  };
  
  return projectTypeBadgeColors[typeUpper] || {
    bg: 'bg-gray-200',
    text: 'text-gray-700',
    label,
  };
};

/**
 * Format a distance in kilometers to a human-readable string.
 * 
 * Converts numeric distance to formatted string with units.
 * Examples:
 *   - 3.5 -> "3.5 km"
 *   - 0.5 -> "0.5 km"
 *   - null -> "N/A"
 * 
 * @param {number} distanceKm - Distance in kilometers
 * @param {number} decimals - Optional: number of decimal places (default: 2)
 * @returns {string} Formatted distance string
 * 
 * @example
 * formatDistance(3.456);
 * // Returns: "3.46 km"
 */
export const formatDistance = (distanceKm, decimals = 2) => {
  if (distanceKm === null || distanceKm === undefined) {
    return 'N/A';
  }
  
  const formatted = parseFloat(distanceKm).toFixed(decimals);
  return `${formatted} km`;
};

/**
 * Format a load/capacity value as a percentage.
 * 
 * Converts load and capacity values to a formatted percentage string.
 * Examples:
 *   - (3, 5) -> "3/5 (60%)"
 *   - (5, 5) -> "5/5 (100%)"
 * 
 * @param {number} current - Current load value
 * @param {number} capacity - Maximum capacity value
 * @returns {string} Formatted load string with percentage
 * 
 * @example
 * formatLoadPercentage(3, 5);
 * // Returns: "3/5 (60%)"
 */
export const formatLoadPercentage = (current, capacity) => {
  if (capacity === 0 || current === null || capacity === null) {
    return 'N/A';
  }
  
  const percentage = Math.round((current / capacity) * 100);
  return `${current}/${capacity} (${percentage}%)`;
};

export default {
  formatDate,
  formatDateRelative,
  formatCoordinate,
  getStatusLabel,
  getStatusColor,
  getProjectTypeBadgeColor,
  formatDistance,
  formatLoadPercentage,
};

