/**
 * Agent Chat State Store using Zustand
 *
 * This store manages the state of agent chat messages and processing status.
 * It maintains conversation history and handles message updates from the
 * WebSocket connection to the backend agent API.
 */

import { create } from "zustand";
import { ChatMessage } from "../types";

/**
 * Agent Store Interface
 * Defines the shape of agent chat state and its actions
 */
export interface AgentStore {
  // State
  messages: ChatMessage[];
  isProcessing: boolean;

  // Actions
  addMessage: (role: "user" | "agent", content: string) => void;
  clearMessages: () => void;
  setProcessing: (isProcessing: boolean) => void;
  setMessages: (messages: ChatMessage[]) => void;
  removeLastMessage: () => void;
}

/**
 * Initial state
 */
const initialState = {
  messages: [],
  isProcessing: false,
};

/**
 * Create the agent store with Zustand
 * Handles all chat-related state for the agent WebSocket connection
 */
export const useAgentStore = create<AgentStore>((set) => ({
  // Initial state
  ...initialState,

  // Actions
  addMessage: (role: "user" | "agent", content: string) =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          role,
          content,
          timestamp: new Date().toISOString(),
        },
      ],
    })),

  clearMessages: () =>
    set({ messages: [], isProcessing: false }),

  setProcessing: (isProcessing: boolean) =>
    set({ isProcessing }),

  setMessages: (messages: ChatMessage[]) =>
    set({ messages }),

  removeLastMessage: () =>
    set((state) => ({
      messages: state.messages.slice(0, -1),
    })),
}));

/**
 * Selector hooks for better performance
 * These prevent unnecessary re-renders by only subscribing to specific state slices
 */

export const useMessages = () =>
  useAgentStore((state) => state.messages);

export const useIsProcessing = () =>
  useAgentStore((state) => state.isProcessing);

export const useMessageCount = () =>
  useAgentStore((state) => state.messages.length);

/**
 * Combined selectors for related state
 */

export const useMessageActions = () =>
  useAgentStore((state) => ({
    messages: state.messages,
    addMessage: state.addMessage,
    clearMessages: state.clearMessages,
    removeLastMessage: state.removeLastMessage,
  }));

export const useProcessingState = () =>
  useAgentStore((state) => ({
    isProcessing: state.isProcessing,
    setProcessing: state.setProcessing,
  }));

/**
 * Get latest agent message for determining last response
 */
export const useLastAgentMessage = () =>
  useAgentStore((state) => {
    const lastMessage = state.messages
      .slice()
      .reverse()
      .find((msg) => msg.role === "agent");
    return lastMessage || null;
  });

/**
 * Get latest user message
 */
export const useLastUserMessage = () =>
  useAgentStore((state) => {
    const lastMessage = state.messages
      .slice()
      .reverse()
      .find((msg) => msg.role === "user");
    return lastMessage || null;
  });

export default useAgentStore;

