import React, { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Bell, Settings, RotateCcw } from 'lucide-react';
import { getSystemStatus } from '@/services/api';

/**
 * Header component with title, mode badge, refresh button, and controls
 */
export function Header() {
  const queryClient = useQueryClient();
  const [systemMode, setSystemMode] = useState<'MOCK' | 'PRODUCTION'>('MOCK');
  const [notificationCount, setNotificationCount] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Check system mode on mount
  React.useEffect(() => {
    const checkSystemMode = async () => {
      try {
        const status = await getSystemStatus();
        setSystemMode(status.systemMode);
      } catch (error) {
        console.error('Failed to fetch system status:', error);
      }
    };

    checkSystemMode();
  }, []);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      // Invalidate all queries to trigger refetch
      await queryClient.invalidateQueries();
    } catch (error) {
      console.error('Refresh failed:', error);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handlePlanningClick = () => {
    // Placeholder for opening planning modal
    console.log('Opening planning modal');
    // TODO: Integrate with PlanningModal component
  };

  return (
    <header className="bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-lg sticky top-0 z-50">
      <div className="px-6 py-4 flex items-center justify-between">
        {/* Left Section - Logo/Title */}
        <div className="flex items-center gap-3">
          <div className="bg-white rounded-lg p-2">
            <span className="text-blue-600 font-bold text-lg">DERCAS</span>
          </div>
          <div>
            <h1 className="text-2xl font-bold">DERCAS PEI</h1>
            <p className="text-blue-100 text-xs">Gestión Agéntica de OTs</p>
          </div>
        </div>

        {/* Center Section - System Mode Badge */}
        <div className="flex items-center gap-4">
          {systemMode === 'MOCK' && (
            <span className="bg-yellow-400 text-yellow-900 px-3 py-1 rounded-full text-sm font-semibold">
              🔧 MOCK MODE
            </span>
          )}
          {systemMode === 'PRODUCTION' && (
            <span className="bg-green-400 text-green-900 px-3 py-1 rounded-full text-sm font-semibold">
              ✓ LIVE
            </span>
          )}
        </div>

        {/* Right Section - Controls */}
        <div className="flex items-center gap-4">
          {/* Refresh Button */}
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="p-2 hover:bg-blue-600 rounded-lg transition-colors disabled:opacity-50"
            title="Refrescar datos"
          >
            <RotateCcw size={20} className={isRefreshing ? 'animate-spin' : ''} />
          </button>

          {/* Planning Trigger Button */}
          <button
            onClick={handlePlanningClick}
            className="px-3 py-2 bg-white text-blue-600 rounded-lg font-semibold hover:bg-blue-50 transition-colors"
            title="Ejecutar planificación"
          >
            📋 Planificar
          </button>

          {/* Notifications Bell */}
          <div className="relative">
            <button
              className="p-2 hover:bg-blue-600 rounded-lg transition-colors relative"
              title="Notificaciones"
            >
              <Bell size={20} />
              {notificationCount > 0 && (
                <span className="absolute top-1 right-1 bg-red-500 text-white text-xs font-bold rounded-full h-5 w-5 flex items-center justify-center">
                  {notificationCount > 9 ? '9+' : notificationCount}
                </span>
              )}
            </button>
          </div>

          {/* Settings/User Menu */}
          <div className="relative">
            <button
              className="p-2 hover:bg-blue-600 rounded-lg transition-colors"
              title="Configuración"
            >
              <Settings size={20} />
            </button>
          </div>

          {/* User Avatar Placeholder */}
          <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center text-blue-600 font-bold cursor-pointer hover:bg-blue-50 transition-colors">
            U
          </div>
        </div>
      </div>
    </header>
  );
}

export default Header;

