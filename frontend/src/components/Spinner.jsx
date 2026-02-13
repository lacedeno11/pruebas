/**
 * Spinner Component
 * 
 * A reusable loading spinner component with configurable sizes.
 * Used throughout the application for loading states.
 */

import './Spinner.css';

/**
 * Spinner component for displaying loading states.
 * 
 * @param {Object} props - Component props
 * @param {string} props.size - Size of spinner: 'small', 'medium', or 'large' (default: 'medium')
 * @returns {JSX.Element} Spinner element
 * 
 * @example
 * // Small spinner
 * <Spinner size="small" />
 * 
 * @example
 * // Large spinner with overlay
 * <Spinner size="large" />
 */
export default function Spinner({ size = 'medium' }) {
  const sizeClass = `spinner-${size}`;

  return (
    <div className={`spinner ${sizeClass}`}>
      <div className="spinner-ring"></div>
    </div>
  );
}

