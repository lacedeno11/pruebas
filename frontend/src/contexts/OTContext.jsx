import React, { createContext, useState, useEffect, useContext } from 'react';
import { toast } from 'react-toastify';
import * as api from '../services/api';

/**
 * OTContext - React Context for managing OT and Cuadrilla state
 * Provides centralized state management for the entire application
 */
const OTContext = createContext();

/**
 * OTProvider - Context Provider Component
 * Manages state and provides methods for OT/Cuadrilla operations
 */
export function OTProvider({ children }) {
  // State for OTs and Cuadrillas
  const [ots, setOts] = useState([]);
  const [cuadrillas, setCuadrillas] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    status: null,
    project_type: null,
  });

  /**
   * Fetch OTs from API with optional filters
   */
  const fetchOTs = async (appliedFilters = filters) => {
    try {
      setLoading(true);
      const data = await api.getOTs(appliedFilters);
      setOts(Array.isArray(data) ? data : []);
      return data;
    } catch (error) {
      console.error('Error fetching OTs:', error);
      toast.error('Failed to fetch OTs');
      return [];
    } finally {
      setLoading(false);
    }
  };

  /**
   * Fetch Cuadrillas from API
   */
  const fetchCuadrillas = async () => {
    try {
      setLoading(true);
      const data = await api.getCuadrillas({ is_active: true });
      setCuadrillas(Array.isArray(data) ? data : []);
      return data;
    } catch (error) {
      console.error('Error fetching cuadrillas:', error);
      toast.error('Failed to fetch cuadrillas');
      return [];
    } finally {
      setLoading(false);
    }
  };

  /**
   * Update OT status with optional detention reason
   * @param {number} otId - OT database ID
   * @param {string} newStatus - New status value
   * @param {string} detentionReason - Reason for detention (optional)
   */
  const updateOTStatus = async (otId, newStatus, detentionReason = null) => {
    try {
      setLoading(true);
      
      // Update on server
      const updatedOT = await api.updateOTStatus(otId, newStatus, detentionReason);
      
      // Update local state
      setOts(ots.map(ot => 
        ot.id === otId 
          ? { ...ot, status: newStatus, detention_reason: detentionReason }
          : ot
      ));
      
      toast.success(`OT status updated to ${newStatus}`);
      return updatedOT;
    } catch (error) {
      console.error('Error updating OT status:', error);
      toast.error('Failed to update OT status');
      throw error;
    } finally {
      setLoading(false);
    }
  };

  /**
   * Sync OTs from external API or mock service
   */
  const syncOTs = async () => {
    try {
      setLoading(true);
      const result = await api.syncOTs();
      
      // Refresh OTs after sync
      await fetchOTs();
      
      toast.success(`Synced ${result.synced_count} OTs successfully`);
      return result;
    } catch (error) {
      console.error('Error syncing OTs:', error);
      toast.error('Failed to sync OTs');
      throw error;
    } finally {
      setLoading(false);
    }
  };

  /**
   * Update filters and refetch OTs
   */
  const applyFilters = async (newFilters) => {
    setFilters(newFilters);
    await fetchOTs(newFilters);
  };

  /**
   * Clear all filters and refetch OTs
   */
  const clearFilters = async () => {
    const clearedFilters = {
      status: null,
      project_type: null,
    };
    setFilters(clearedFilters);
    await fetchOTs(clearedFilters);
  };

  /**
   * Get cuadrilla by ID
   */
  const getCuadrillaById = (cuadrillaId) => {
    return cuadrillas.find(c => c.id === cuadrillaId);
  };

  /**
   * Get OT by ID
   */
  const getOTById = (otId) => {
    return ots.find(ot => ot.id === otId);
  };

  /**
   * Get OTs filtered by status
   */
  const getOTsByStatus = (status) => {
    return ots.filter(ot => ot.status === status);
  };

  /**
   * Get OTs filtered by project type
   */
  const getOTsByProjectType = (projectType) => {
    return ots.filter(ot => ot.project_type === projectType);
  };

  /**
   * Get statistics about OTs
   */
  const getStatistics = () => {
    const stats = {
      totalOTs: ots.length,
      byStatus: {},
      byProjectType: {},
      geoErrorCount: ots.filter(ot => ot.geo_error).length,
    };

    // Count by status
    const statuses = ['PREPLANIFICADA', 'PLANIFICADA', 'ASIGNADO_TAREA', 'DETENIDA', 'ANULADA', 'FINALIZADA'];
    statuses.forEach(status => {
      stats.byStatus[status] = ots.filter(ot => ot.status === status).length;
    });

    // Count by project type
    const projectTypes = ['PUBLICO', 'PRIVADO', 'TERCERIZADO'];
    projectTypes.forEach(type => {
      stats.byProjectType[type] = ots.filter(ot => ot.project_type === type).length;
    });

    return stats;
  };

  /**
   * Get average detention time for DETENIDA OTs
   */
  const getAverageDetentionTime = () => {
    const detainedOTs = ots.filter(ot => ot.status === 'DETENIDA');
    if (detainedOTs.length === 0) return 0;

    const now = new Date();
    const totalDays = detainedOTs.reduce((sum, ot) => {
      const createdDate = new Date(ot.created_at);
      const days = (now - createdDate) / (1000 * 60 * 60 * 24);
      return sum + days;
    }, 0);

    return Math.round(totalDays / detainedOTs.length);
  };

  /**
   * Get cuadrilla utilization percentage
   */
  const getCuadrillaUtilization = (cuadrillaId) => {
    const cuadrilla = getCuadrillaById(cuadrillaId);
    if (!cuadrilla || cuadrilla.capacity === 0) return 0;
    return Math.round((cuadrilla.current_load / cuadrilla.capacity) * 100);
  };

  /**
   * Fetch initial data on component mount
   */
  useEffect(() => {
    const initializeData = async () => {
      try {
        setLoading(true);
        await Promise.all([
          fetchOTs(),
          fetchCuadrillas(),
        ]);
      } catch (error) {
        console.error('Error initializing data:', error);
        toast.error('Failed to load initial data');
      } finally {
        setLoading(false);
      }
    };

    initializeData();
  }, []);

  /**
   * Context value - all state and methods
   */
  const value = {
    // State
    ots,
    cuadrillas,
    loading,
    filters,

    // Fetch methods
    fetchOTs,
    fetchCuadrillas,

    // Update methods
    updateOTStatus,
    syncOTs,

    // Filter methods
    applyFilters,
    clearFilters,

    // Query methods
    getCuadrillaById,
    getOTById,
    getOTsByStatus,
    getOTsByProjectType,

    // Statistics methods
    getStatistics,
    getAverageDetentionTime,
    getCuadrillaUtilization,
  };

  return (
    <OTContext.Provider value={value}>
      {children}
    </OTContext.Provider>
  );
}

/**
 * Custom hook to use OTContext
 * @returns {Object} Context value with state and methods
 */
export function useOT() {
  const context = useContext(OTContext);
  
  if (!context) {
    throw new Error('useOT must be used within an OTProvider');
  }

  return context;
}

/**
 * Export OTContext for advanced use cases
 */
export default OTContext;

