import React, { useState } from 'react';
import { useUIStore } from '@/stores/uiStore';
import MapView from './MapView';
import KanbanBoard from './KanbanBoard';
import AgentChat from './AgentChat';
import OTDetailModal from './OTDetailModal';
import Header from './Header';
import { MessageCircle } from 'lucide-react';

/**
 * Main Dashboard component
 * Layout: Header + Map (top 40vh) + Kanban (bottom 60vh) + Agent Chat sidebar
 */
export function Dashboard() {
  const { selectedOTId, sidebarOpen } = useUIStore();
  const [chatOpen, setChatOpen] = useState(window.innerWidth > 768);
  const [showChat, setShowChat] = useState(window.innerWidth > 768);

  // Handle window resize for responsive behavior
  React.useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth <= 768) {
        setShowChat(false); // Hide chat on mobile by default
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

