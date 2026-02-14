/**
 * API Client Service
 * 
 * Configures axios instance with:
 * - Base URL from VITE_API_BASE_URL environment variable
 * - 10 second request timeout
 * - JSON content type headers
 * - Request/response interceptors for logging and error handling
 */

import axios from 'axios';

// Get base URL from environment variables
const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Create axios instance with default configuration
const apiClient = axios.create({
  baseURL,
  timeout: 10000, // 10 seconds
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Request Interceptor
 * Logs outgoing requests for debugging
 */
apiClient.interceptors.request.use(
  (config) => {
    // Log request details
    console.log(`📤 [API Request] ${config.method?.toUpperCase()} ${config.url}`, {
      params: config.params,
      data: config.data,
    });
    return config;
  },
  (error) => {
    console.error('❌ [API Request Error]', error);
    return Promise.reject(error);
  }
);

/**
 * Response Interceptor
 * Logs successful responses and handles errors
 */
apiClient.interceptors.response.use(
  (response) => {
    // Log successful response
    console.log(`📥 [API Response] ${response.status} ${response.config.method?.toUpperCase()} ${response.config.url}`, {
      data: response.data,
    });
    return response;
  },
  (error) => {
    // Handle different error types
    if (error.response) {
      // Server responded with error status code
      console.error(`❌ [API Error] ${error.response.status} ${error.config?.method?.toUpperCase()} ${error.config?.url}`, {
        status: error.response.status,
        data: error.response.data,
        headers: error.response.headers,
      });

      // Extract error message from response
      const errorMessage =
        error.response.data?.detail ||
        error.response.data?.message ||
        error.response.statusText ||
        'An error occurred';

      // Create custom error with detailed information
      error.message = errorMessage;
      error.statusCode = error.response.status;
    } else if (error.request) {
      // Request made but no response received
      console.error('❌ [API Error] No response from server', {
        request: error.request,
      });
      error.message = 'No response from server. Please check your connection.';
    } else {
      // Error in request setup
      console.error('❌ [API Error] Request setup error', {
        message: error.message,
      });
    }

    return Promise.reject(error);
  }
);

export default apiClient;

