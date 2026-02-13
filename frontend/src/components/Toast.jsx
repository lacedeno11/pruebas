/**
 * Toast Notification Wrapper
 * 
 * Wrapper around react-toastify for centralized toast notification management.
 * Provides simple functions for displaying success, error, and info toasts.
 */

import { toast } from 'react-toastify';

/**
 * Show a success toast notification.
 * 
 * @param {string} message - Success message to display
 * @param {Object} options - Optional additional toast options
 * @returns {void}
 * 
 * @example
 * showSuccessToast('OT updated successfully');
 * showSuccessToast('Data synced', { autoClose: 5000 });
 */
export const showSuccessToast = (message, options = {}) => {
  toast.success(message, {
    position: 'top-right',
    autoClose: 3000,
    hideProgressBar: false,
    closeOnClick: true,
    pauseOnHover: true,
    draggable: true,
    ...options,
  });
};

/**
 * Show an error toast notification.
 * 
 * @param {string} message - Error message to display
 * @param {Object} options - Optional additional toast options
 * @returns {void}
 * 
 * @example
 * showErrorToast('Failed to update OT');
 * showErrorToast('Network error', { autoClose: 5000 });
 */
export const showErrorToast = (message, options = {}) => {
  toast.error(message, {
    position: 'top-right',
    autoClose: 3000,
    hideProgressBar: false,
    closeOnClick: true,
    pauseOnHover: true,
    draggable: true,
    ...options,
  });
};

/**
 * Show an info toast notification.
 * 
 * @param {string} message - Info message to display
 * @param {Object} options - Optional additional toast options
 * @returns {void}
 * 
 * @example
 * showInfoToast('Processing your request...');
 * showInfoToast('Check back later', { autoClose: 5000 });
 */
export const showInfoToast = (message, options = {}) => {
  toast.info(message, {
    position: 'top-right',
    autoClose: 3000,
    hideProgressBar: false,
    closeOnClick: true,
    pauseOnHover: true,
    draggable: true,
    ...options,
  });
};

/**
 * Show a warning toast notification.
 * 
 * @param {string} message - Warning message to display
 * @param {Object} options - Optional additional toast options
 * @returns {void}
 * 
 * @example
 * showWarningToast('This action cannot be undone');
 */
export const showWarningToast = (message, options = {}) => {
  toast.warning(message, {
    position: 'top-right',
    autoClose: 3000,
    hideProgressBar: false,
    closeOnClick: true,
    pauseOnHover: true,
    draggable: true,
    ...options,
  });
};

export default {
  showSuccessToast,
  showErrorToast,
  showInfoToast,
  showWarningToast,
};

