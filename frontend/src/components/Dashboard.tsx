import React, { useState, useEffect } from 'react';
import { Menu } from 'lucide-react';
import Header from './Header';
import MapView from './MapView';
import KanbanBoard from './KanbanBoard';
import AgentChat from './AgentChat';

/**
 * Main Dashboard component - DERCAS PEI
 * Layout: 
 *   - Header bar at top with DERCAS PEI title, mode badge, controls
 *   - Map section (40vh on desktop) - Geographic visualization
 *   - Kanban section (60vh on desktop) - OT status management
 *   - AgentChat sidebar (toggleable, overlays on right) - AI assistant
 * Mobile: Responsive layout with floating chat button
 */
export function Dashboard() {
  const [chatOpen, setChatOpen] = useState(window.innerWidth > 768);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  // Handle window resize for responsive behavior
  useEffect(() => {
    const handleResize = () => {
      const newIsMobile = window.innerWidth < 768;
      setIsMobile(newIsMobile);
      if (newIsMobile) {
        setChatOpen(false); // Hide chat on mobile by default
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div className="h-screen w-screen flex flex-col bg-gray-50 overflow-hidden">
      {/* Header - Top navigation bar */}
      <Header />

      {/* Main content area with map and kanban */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Content wrapper - Map and Kanban sections */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Map section - 40vh on desktop, flexible on mobile */}
          <div
            className={`${
              isMobile && !chatOpen ? 'flex-1' : 'h-[40vh]'
            } overflow-hidden border-b border-gray-200 bg-white`}
          >
            <MapView />
          </div>

          {/* Kanban section - 60vh on desktop, flexible on mobile */}
          <div
            className={`${isMobile && !chatOpen ? 'flex-1' : 'h-[60vh]'} overflow-hidden`}
          >
            <KanbanBoard />
          </div>
        </div>

        {/* Agent Chat sidebar - overlays on right side, toggleable */}
        {chatOpen && (
          <AgentChat isOpen={chatOpen} onToggle={() => setChatOpen(false)} />
        )}

        {/* Floating chat button on mobile when chat is closed */}
        {isMobile && !chatOpen && (
          <button
            onClick={() => setChatOpen(true)}
            className="fixed bottom-6 right-6 w-14 h-14 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 transition-all z-30 flex items-center justify-center"
            title="Abrir asistente"
            aria-label="Open chat"
          >
            <Menu size={24} />
          </button>
        )}
      </div>
    </div>
  );
}

export default Dashboard;tOpen(false); // Hide chat on mobile by default
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const toggleChat = () => {
    setShowChat(!showChat);
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-gray-50 overflow-hidden">
      {/* Header */}
      <Header />

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Content (Map + Kanban) */}
        <div className="flex-1 flex flex-col overflow-hidden md:w-full lg:w-full xl:w-full">
          {/* Map View - Top 40vh on desktop, full width on mobile */}
          <div className="h-2/5 md:h-2/5 lg:h-2/5 xl:h-2/5 w-full overflow-hidden border-b border-gray-200">
            <MapView />
          </div>

          {/* Kanban Board - Bottom 60vh on desktop, full width on mobile */}
          <div className="h-3/5 md:h-3/5 lg:h-3/5 xl:h-3/5 w-full overflow-hidden">
            <KanbanBoard />
          </div>
        </div>

        {/* Agent Chat Sidebar - Right side, toggleable on mobile */}
        <div className="hidden md:block md:w-96 lg:w-96 xl:w-96">
          {showChat && <AgentChat isOpen={true} onToggle={toggleChat} />}
        </div>

        {/* Mobile Chat Toggle Button */}
        {!showChat && (
          <button
            onClick={toggleChat}
            className="fixed bottom-4 right-4 md:hidden bg-blue-600 text-white rounded-full p-4 shadow-lg hover:bg-blue-700 transition-colors z-30"
            title="Abrir chat"
          >
            <MessageCircle size={24} />
          </button>
        )}
      </div>

      {/* OT Detail Modal */}
      {selectedOTId && (
        <OTDetailModal
          otId={selectedOTId}
          onClose={() => {
            // Close is handled by useUIStore
          }}
        />
      )}

      {/* Mobile Chat Overlay */}
      {showChat && (
        <div className="md:hidden absolute inset-0 z-40">
          <AgentChat isOpen={true} onToggle={toggleChat} />
        </div>
      )}
    </div>
  );
}

export default Dashboard;






