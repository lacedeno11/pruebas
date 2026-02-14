/**
 * Chat Sidebar Component - Main Agent Chat Interface
 *
 * This is the main component for the real-time agent chat interface.
 * It provides a sliding sidebar with message history, input field, and
 * quick action buttons for common operations.
 */

import React, { useEffect, useRef, useState } from "react";
import { X, MessageSquare, Zap } from "lucide-react";
import toast from "react-hot-toast";
import MessageBubble from "./MessageBubble";
import ChatInput from "./ChatInput";
import { useAgentStore } from "../../stores/agentStore";
import { useUIStore } from "../../stores/uiStore";

/**
 * Quick action button type
 */
interface QuickAction {
  label: string;
  command: string;
  icon: React.ReactNode;
  description: string;
}

/**
 * Predefined quick actions for common commands
 */
const QUICK_ACTIONS: QuickAction[] = [
  {
    label: "Ingest OTs",
    command: "Download and ingest new work orders from the system",
    icon: "📥",
    description: "Fetch latest OTs from API",
  },
  {
    label: "Run Planning",
    command: "Execute the planning algorithm to assign OTs to cuadrillas",
    icon: "📋",
    description: "Assign OTs to teams",
  },
  {
    label: "Check Alerts",
    command: "Review governance alerts and detention status",
    icon: "🚨",
    description: "Check system alerts",
  },
];

/**
 * Chat Sidebar Component
 *
 * Features:
 * - Sliding sidebar from right side (400px)
 * - Message history with scrolling
 * - Real-time message updates
 * - Auto-scroll to latest message
 * - Loading indicator while processing
 * - Quick action buttons
 * - Message input with auto-resize
 * - Close button to hide sidebar
 */
export const ChatSidebar: React.FC = () => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);

  // Get state from stores
  const { isSidebarOpen, toggleSidebar } = useUIStore();
  const { messages, isProcessing, addMessage, clearMessages } =
    useAgentStore();

  /**
   * Auto-scroll to latest message
   */
  const scrollToBottom = () => {
    if (messagesEndRef.current && shouldAutoScroll) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, shouldAutoScroll]);

  /**
   * Handle scroll to detect if user is viewing latest messages
   */
  const handleScroll = () => {
    if (messagesContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } =
        messagesContainerRef.current;
      const isAtBottom = scrollHeight - scrollTop - clientHeight < 100;
      setShouldAutoScroll(isAtBottom);
    }
  };

  /**
   * Handle message submission
   */
  const handleSubmitMessage = (message: string) => {
    try {
      // Add user message to history
      addMessage({
        role: "user",
        content: message,
        timestamp: new Date().toISOString(),
      });

      // TODO: Send message to backend via WebSocket
      // For now, simulate agent response
      setTimeout(() => {
        addMessage({
          role: "agent",
          content: `Processing: ${message}`,
          timestamp: new Date().toISOString(),
        });
      }, 1000);
    } catch (error) {
      toast.error("Error sending message");
    }
  };

  /**
   * Handle quick action click
   */
  const handleQuickAction = (action: QuickAction) => {
    handleSubmitMessage(action.command);
    toast.success(`Executing: ${action.label}`);
  };

  /**
   * Handle clear chat history
   */
  const handleClearChat = () => {
    if (messages.length === 0) {
      toast.info("Chat is already empty");
      return;
    }

    const confirmed = window.confirm(
      "Are you sure you want to clear all messages?"
    );
    if (confirmed) {
      clearMessages();
      toast.success("Chat cleared");
    }
  };

  // Don't render if sidebar is closed
  if (!isSidebarOpen) {
    return null;
  }

  const hasMessages = messages.length > 0;

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black bg-opacity-30 z-30 lg:hidden"
        onClick={() => toggleSidebar()}
      />

      {/* Sidebar */}
      <div
        className={`
          fixed right-0 top-0 bottom-0 w-full sm:w-96 bg-white shadow-2xl z-40
          transform transition-transform duration-300 ease-in-out
          flex flex-col
          ${isSidebarOpen ? "translate-x-0" : "translate-x-full"}
        `}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gradient-to-r from-blue-600 to-blue-700">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-white" />
            <h2 className="text-lg font-bold text-white">
              AI Agent Assistant
            </h2>
          </div>
          <button
            onClick={() => toggleSidebar()}
            className="p-1 rounded-lg hover:bg-blue-800 transition-colors"
            title="Close chat"
          >
            <X className="w-5 h-5 text-white" />
          </button>
        </div>

        {/* Messages Container */}
        <div
          ref={messagesContainerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto p-4 space-y-3"
        >
          {!hasMessages && !isProcessing && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="text-4xl mb-3">🤖</div>
              <p className="font-semibold text-gray-900 mb-2">
                Welcome to AI Agent Assistant
              </p>
              <p className="text-sm text-gray-600 mb-4">
                Start by clicking a quick action or typing a command
              </p>

              {/* Quick Actions */}
              <div className="w-full space-y-2 mt-6">
                {QUICK_ACTIONS.map((action) => (
                  <button
                    key={action.label}
                    onClick={() => handleQuickAction(action)}
                    disabled={isProcessing}
                    className={`
                      w-full px-4 py-3 rounded-lg border-2 text-left transition-all
                      ${
                        isProcessing
                          ? "opacity-50 cursor-not-allowed border-gray-300"
                          : "border-gray-300 hover:border-blue-500 hover:bg-blue-50"
                      }
                    `}
                  >
                    <div className="text-lg mb-1">{action.icon}</div>
                    <div className="font-medium text-gray-900">
                      {action.label}
                    </div>
                    <div className="text-xs text-gray-600">
                      {action.description}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Message List */}
          {hasMessages &&
            messages.map((message, index) => (
              <MessageBubble key={index} message={message} />
            ))}

          {/* Processing Indicator */}
          {isProcessing && (
            <div className="flex items-center gap-2 p-3 bg-blue-50 rounded-lg">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce delay-100" />
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce delay-200" />
              </div>
              <span className="text-sm text-blue-700 font-medium">
                Agent is thinking...
              </span>
            </div>
          )}

          {/* Auto-scroll anchor */}
          <div ref={messagesEndRef} />
        </div>

        {/* Footer with Input and Actions */}
        <div className="border-t border-gray-200 p-4 space-y-2 bg-gray-50">
          {/* Clear Chat Button */}
          {hasMessages && (
            <button
              onClick={handleClearChat}
              disabled={isProcessing}
              className="w-full text-xs text-gray-600 hover:text-red-600 py-1 px-2 rounded transition-colors disabled:opacity-50"
            >
              Clear chat history
            </button>
          )}

          {/* Chat Input */}
          <ChatInput
            onSubmit={handleSubmitMessage}
            isProcessing={isProcessing}
            placeholder="Ask the agent... (Press Enter to send)"
          />
        </div>
      </div>
    </>
  );
};

export default ChatSidebar;

