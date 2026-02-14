/**
 * Custom Hook for Agent Chat with WebSocket Connection
 *
 * This hook manages the WebSocket connection to the backend agent chat endpoint
 * and integrates with the agentStore for message management. It handles connection
 * lifecycle, message sending/receiving, and automatic reconnection with exponential backoff.
 */

import { useEffect, useRef, useCallback, useState } from "react";
import { createChatWebSocket } from "../services/api";
import { useAgentStore } from "../stores/agentStore";
import { ChatMessage } from "../types";

interface UseAgentChatOptions {
  autoConnect?: boolean;
  maxReconnectAttempts?: number;
  reconnectDelayMs?: number;
}

interface UseAgentChatReturn {
  // State
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;

  // Actions
  connect: () => void;
  disconnect: () => void;
  sendMessage: (text: string) => void;
  clearChat: () => void;

  // Store access
  messages: ChatMessage[];
  isProcessing: boolean;
}

/**
 * Custom hook for managing agent chat WebSocket connection
 *
 * @param options Configuration options for the WebSocket connection
 * @returns Hook interface with connection state and methods
 *
 * @example
 * const { isConnected, sendMessage, messages } = useAgentChat({
 *   autoConnect: true,
 *   maxReconnectAttempts: 5,
 * });
 *
 * useEffect(() => {
 *   if (isConnected) {
 *     sendMessage("Plan OTs for PUBLICO projects");
 *   }
 * }, [isConnected, sendMessage]);
 */
export function useAgentChat(
  options: UseAgentChatOptions = {}
): UseAgentChatReturn {
  const {
    autoConnect = true,
    maxReconnectAttempts = 5,
    reconnectDelayMs = 1000,
  } = options;

  // Refs for WebSocket and reconnection management
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const messageQueueRef = useRef<string[]>([]);

  // Local state for connection
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Store access
  const { messages, addMessage, setProcessing, isProcessing } = useAgentStore(
    (state) => ({
      messages: state.messages,
      addMessage: state.addMessage,
      setProcessing: state.setProcessing,
      isProcessing: state.isProcessing,
    })
  );

  /**
   * Handle incoming WebSocket messages
   */
  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);

        // Handle different message types
        if (data.type === "agent_response") {
          // Agent sent a response
          addMessage("agent", data.content);
          setProcessing(false);
        } else if (data.type === "thinking") {
          // Agent is thinking
          addMessage("agent", `🤔 ${data.content}`);
        } else if (data.type === "error") {
          // Error from agent
          addMessage("agent", `❌ Error: ${data.content}`);
          setProcessing(false);
          setError(data.content);
        } else if (data.type === "status") {
          // Status update
          if (data.content === "processing") {
            setProcessing(true);
          } else if (data.content === "ready") {
            setProcessing(false);
          }
        }
      } catch (err) {
        console.error("Failed to parse message:", err);
        setError("Failed to parse message from server");
      }
    },
    [addMessage, setProcessing]
  );

  /**
   * Handle WebSocket connection open
   */
  const handleOpen = useCallback(() => {
    console.log("WebSocket connected");
    setIsConnected(true);
    setIsConnecting(false);
    setError(null);
    reconnectAttemptsRef.current = 0;

    // Send any queued messages
    if (messageQueueRef.current.length > 0) {
      messageQueueRef.current.forEach((msg) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(msg);
        }
      });
      messageQueueRef.current = [];
    }
  }, []);

  /**
   * Handle WebSocket connection close
   */
  const handleClose = useCallback(() => {
    console.log("WebSocket disconnected");
    setIsConnected(false);
    setIsConnecting(false);

    // Attempt to reconnect with exponential backoff
    if (reconnectAttemptsRef.current < maxReconnectAttempts) {
      const delayMs =
        reconnectDelayMs * Math.pow(2, reconnectAttemptsRef.current);
      console.log(
        `Attempting to reconnect in ${delayMs}ms (attempt ${reconnectAttemptsRef.current + 1})`
      );

      reconnectTimeoutRef.current = setTimeout(() => {
        reconnectAttemptsRef.current++;
        connect();
      }, delayMs);
    } else {
      setError("Failed to connect after maximum reconnection attempts");
    }
  }, [maxReconnectAttempts, reconnectDelayMs]);

  /**
   * Handle WebSocket errors
   */
  const handleError = useCallback((event: Event) => {
    console.error("WebSocket error:", event);
    setError("WebSocket connection error");
    setIsConnecting(false);
  }, []);

  /**
   * Connect to WebSocket
   */
  const connect = useCallback(() => {
    // Prevent multiple connection attempts
    if (isConnecting || isConnected) {
      return;
    }

    try {
      setIsConnecting(true);
      setError(null);

      // Create WebSocket connection
      const ws = createChatWebSocket();
      wsRef.current = ws;

      // Set up event handlers
      ws.addEventListener("open", handleOpen);
      ws.addEventListener("message", handleMessage);
      ws.addEventListener("close", handleClose);
      ws.addEventListener("error", handleError);

      // Set timeout for connection
      const connectionTimeout = setTimeout(() => {
        if (ws.readyState !== WebSocket.OPEN) {
          ws.close();
          setIsConnecting(false);
          setError("Connection timeout");
        }
      }, 10000); // 10 second timeout

      // Store timeout for cleanup
      reconnectTimeoutRef.current = connectionTimeout;
    } catch (err) {
      console.error("Failed to create WebSocket:", err);
      setIsConnecting(false);
      setError(err instanceof Error ? err.message : "Failed to connect");
    }
  }, [isConnecting, isConnected, handleOpen, handleMessage, handleClose, handleError]);

  /**
   * Disconnect from WebSocket
   */
  const disconnect = useCallback(() => {
    // Clear any pending reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Close WebSocket connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
    setIsConnecting(false);
    reconnectAttemptsRef.current = 0;
  }, []);

  /**
   * Send a message through WebSocket
   */
  const sendMessage = useCallback(
    (text: string) => {
      if (!text.trim()) {
        return;
      }

      // Add user message to store
      addMessage("user", text);
      setProcessing(true);

      // Prepare message
      const message = JSON.stringify({
        type: "user_input",
        content: text,
        timestamp: new Date().toISOString(),
      });

      // Send through WebSocket if connected, otherwise queue it
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        try {
          wsRef.current.send(message);
        } catch (err) {
          console.error("Failed to send message:", err);
          setError("Failed to send message");
          setProcessing(false);
        }
      } else {
        // Queue message if not connected
        messageQueueRef.current.push(message);
        console.log("Message queued, waiting for connection");

        // Attempt to connect if not already
        if (!isConnected && !isConnecting) {
          connect();
        }
      }
    },
    [addMessage, setProcessing, isConnected, isConnecting, connect]
  );

  /**
   * Clear chat history
   */
  const clearChat = useCallback(() => {
    // Access store directly to clear messages
    useAgentStore.setState({ messages: [], isProcessing: false });
  }, []);

  /**
   * Set up auto-connect on mount
   */
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    // Cleanup on unmount
    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  /**
   * Handle visibility changes - reconnect when tab becomes visible
   */
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden && !isConnected && !isConnecting) {
        console.log("Tab became visible, attempting reconnect");
        reconnectAttemptsRef.current = 0; // Reset reconnect counter
        connect();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [isConnected, isConnecting, connect]);

  return {
    isConnected,
    isConnecting,
    error,
    connect,
    disconnect,
    sendMessage,
    clearChat,
    messages,
    isProcessing,
  };
}

/**
 * Simplified hook for just getting connection status
 */
export function useAgentChatStatus() {
  const { isConnected, isConnecting, error } = useAgentChat({
    autoConnect: true,
  });
  return { isConnected, isConnecting, error };
}

/**
 * Simplified hook for just getting messages
 */
export function useAgentMessages() {
  const { messages, isProcessing } = useAgentChat({ autoConnect: false });
  return { messages, isProcessing };
}

export default useAgentChat;

