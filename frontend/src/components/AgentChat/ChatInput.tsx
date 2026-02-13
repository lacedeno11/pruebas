/**
 * Chat Input Component for Agent Chat
 *
 * Provides textarea input for sending messages to the agent with features like
 * auto-resize, Enter-to-send, voice input placeholder, and submit button.
 */

import React, { useRef, useEffect, useState } from "react";
import { Send, Mic } from "lucide-react";
import toast from "react-hot-toast";

interface ChatInputProps {
  onSubmit: (message: string) => void;
  isProcessing?: boolean;
  placeholder?: string;
}

/**
 * Chat Input Component
 *
 * Features:
 * - Auto-expanding textarea
 * - Enter to submit, Shift+Enter for new line
 * - Submit button with Send icon
 * - Disabled state while processing
 * - Voice input button (placeholder)
 * - Placeholder text with example
 * - Character count display
 * - Smooth focus states
 */
export const ChatInput: React.FC<ChatInputProps> = ({
  onSubmit,
  isProcessing = false,
  placeholder = "Ask the agent... (e.g., Plan OTs for DataLegal project)",
}) => {
  const [message, setMessage] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [isListening, setIsListening] = useState(false);

  /**
   * Auto-resize textarea based on content
   */
  const autoResizeTextarea = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = Math.min(scrollHeight, 200) + "px";
    }
  };

  // Auto-resize on text change
  useEffect(() => {
    autoResizeTextarea();
  }, [message]);

  /**
   * Handle message submission
   */
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const trimmedMessage = message.trim();

    if (!trimmedMessage) {
      toast.error("Por favor escribe un mensaje");
      return;
    }

    if (isProcessing) {
      toast.error("El agente está procesando...");
      return;
    }

    // Submit message
    onSubmit(trimmedMessage);

    // Clear input
    setMessage("");

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  /**
   * Handle keyboard events
   */
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter to submit (Ctrl+Enter or Cmd+Enter also works)
    if (
      (e.key === "Enter" && !e.shiftKey && !e.ctrlKey && !e.metaKey) ||
      (e.key === "Enter" && (e.ctrlKey || e.metaKey))
    ) {
      e.preventDefault();
      handleSubmit(e as any);
    }
  };

  /**
   * Handle voice input (placeholder - future Web Speech API integration)
   */
  const handleVoiceInput = () => {
    // Check if browser supports Web Speech API
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      toast.error("Tu navegador no soporta entrada de voz");
      return;
    }

    if (isListening) {
      // Stop listening
      setIsListening(false);
      return;
    }

    // Start listening
    const recognition = new SpeechRecognition();
    recognition.lang = "es-EC";
    recognition.continuous = false;
    recognition.interimResults = true;

    let transcript = "";

    recognition.onstart = () => {
      setIsListening(true);
      toast.loading("Escuchando...", { id: "listening" });
    };

    recognition.onresult = (event) => {
      transcript = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      setMessage(transcript);
    };

    recognition.onend = () => {
      setIsListening(false);
      toast.dismiss("listening");
      if (transcript) {
        toast.success("Mensaje capturado");
      }
    };

    recognition.onerror = (event) => {
      setIsListening(false);
      toast.dismiss("listening");
      toast.error(`Error de voz: ${event.error}`);
    };

    try {
      recognition.start();
    } catch (error) {
      setIsListening(false);
      toast.error("Error al iniciar entrada de voz");
    }
  };

  const messageLength = message.length;
  const maxLength = 1000;
  const isNearLimit = messageLength > maxLength - 100;

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2">
      {/* Character Count */}
      {messageLength > 0 && (
        <div className="text-xs text-gray-400 px-3">
          {messageLength} / {maxLength} caracteres
        </div>
      )}

      {/* Input Container */}
      <div
        className={`
          flex gap-2 px-3 py-2 rounded-lg border-2 transition-all
          ${
            isNearLimit
              ? "border-yellow-500 bg-yellow-50"
              : messageLength > 0
                ? "border-blue-500 bg-blue-50"
                : "border-gray-300 bg-white"
          }
          focus-within:ring-2
          focus-within:ring-blue-300
        `}
      >
        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isProcessing}
          maxLength={maxLength}
          rows={1}
          className={`
            flex-1
            bg-transparent
            outline-none
            resize-none
            text-sm
            font-sans
            placeholder-gray-500
            disabled:opacity-50
            disabled:cursor-not-allowed
            max-h-48
          `}
        />

        {/* Action Buttons */}
        <div className="flex gap-1">
          {/* Voice Input Button */}
          <button
            type="button"
            onClick={handleVoiceInput}
            disabled={isProcessing}
            className={`
              p-2 rounded-lg transition-all flex-shrink-0
              ${
                isListening
                  ? "bg-red-500 text-white animate-pulse"
                  : "bg-gray-200 hover:bg-gray-300 text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              }
            `}
            title={isListening ? "Detener grabación" : "Entrada de voz"}
          >
            <Mic className="w-4 h-4" />
          </button>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isProcessing || !message.trim()}
            className={`
              p-2 rounded-lg transition-all flex-shrink-0
              ${
                isProcessing || !message.trim()
                  ? "bg-gray-300 text-gray-600 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-700 text-white"
              }
            `}
            title={isProcessing ? "Procesando..." : "Enviar mensaje (Enter)"}
          >
            {isProcessing ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Helper Text */}
      <div className="text-xs text-gray-500 px-3">
        <span className="font-medium">Tip:</span> Presiona Enter para enviar, Shift+Enter para nueva línea
      </div>
    </form>
  );
};

export default ChatInput;

