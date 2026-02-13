import React, { useState, useRef, useEffect } from 'react';
import { toast } from 'react-toastify';
import { sendAgentCommand } from '../services/api';

/**
 * Suggested commands for quick access
 */
const SUGGESTED_COMMANDS = [
  {
    label: 'Sincronizar OTs',
    command: 'Sincronizar nuevas órdenes de trabajo del sistema externo',
  },
  {
    label: 'Planificar todas las OTs',
    command: 'Planificar y asignar todas las órdenes de trabajo a las cuadrillas disponibles',
  },
  {
    label: 'Revisar gobernanza',
    command: 'Revisar reglas de gobernanza y alertas de detención',
  },
];

/**
 * AgentChat - Chat interface sidebar for agent interaction
 *
 * State:
 * - messages: Array of message objects {role, content, timestamp}
 * - inputValue: Current textarea input value
 * - isLoading: Whether waiting for agent response
 * - isOpen: Whether sidebar is visible
 */
function AgentChat() {
  // State
  const [messages, setMessages] = useState([
    {
      role: 'agent',
      content: '¡Hola! Soy el asistente PEI. Puedo ayudarte a sincronizar órdenes de trabajo, planificar asignaciones, revisar alertas y más. ¿Qué necesitas?',
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  // Refs
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);

  /**
   * Auto-scroll to bottom when new messages arrive
   */
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  /**
   * Send message to agent
   */
  const sendMessage = async (messageContent = inputValue) => {
    // Validate input
    if (!messageContent || messageContent.trim().length === 0) {
      toast.error('Por favor, escribe un mensaje');
      return;
    }

    try {
      setIsLoading(true);

      // Add user message to chat
      const userMessage = {
        role: 'user',
        content: messageContent,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, userMessage]);
      setInputValue('');

      // Send to agent API
      const response = await sendAgentCommand(messageContent);

      // Add agent response to chat
      const agentMessage = {
        role: 'agent',
        content: response.message || response.data?.message || 'Comando procesado',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, agentMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      
      const errorMessage = {
        role: 'agent',
        content: `Error: ${error.message || 'No se pudo procesar el comando'}`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
      
      toast.error('Error al procesar el comando del agente');
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Handle suggested command click
   */
  const handleSuggestedCommand = (command) => {
    sendMessage(command);
  };

  /**
   * Handle textarea enter key
   */
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  /**
   * Toggle sidebar visibility
   */
  const toggleSidebar = () => {
    setIsOpen(!isOpen);
  };

  return (
    <>
      {/* Chat Sidebar */}
      <div
        className={`
          fixed right-0 top-0 h-full w-80 bg-white shadow-2xl z-30
          transform transition-transform duration-300 flex flex-col
          ${isOpen ? 'translate-x-0' : 'translate-x-full'}
        `}
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4 flex items-center justify-between shadow-md">
          <h2 className="font-bold text-lg">PEI Assistant</h2>
          <button
            onClick={toggleSidebar}
            className="text-white hover:bg-blue-500 rounded p-1 transition-colors"
            aria-label="Close chat"
          >
            ✕
          </button>
        </div>

        {/* Messages Container */}
        <div
          ref={messagesContainerRef}
          className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50"
        >
          {messages.length === 0 ? (
            <div className="text-center text-gray-400 py-8">
              <p className="text-sm">No hay mensajes aún</p>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                <div
                  className={`
                    max-w-xs px-4 py-3 rounded-lg text-sm
                    ${
                      message.role === 'user'
                        ? 'bg-blue-600 text-white rounded-br-none'
                        : 'bg-gray-300 text-gray-900 rounded-bl-none'
                    }
                  `}
                >
                  <p className="break-words">{message.content}</p>
                  <span className="text-xs opacity-70 mt-1 block">
                    {message.timestamp.toLocaleTimeString('es-ES', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>
              </div>
            ))
          )}

          {/* Loading Indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-300 text-gray-900 px-4 py-3 rounded-lg rounded-bl-none">
                <div className="flex gap-1 items-center">
                  <span className="animate-bounce" style={{ animationDelay: '0s' }}>
                    ●
                  </span>
                  <span className="animate-bounce" style={{ animationDelay: '0.2s' }}>
                    ●
                  </span>
                  <span className="animate-bounce" style={{ animationDelay: '0.4s' }}>
                    ●
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Auto-scroll anchor */}
          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Commands */}
        {messages.length === 1 && !isLoading && (
          <div className="px-4 py-3 bg-white border-t border-gray-200">
            <p className="text-xs font-medium text-gray-600 mb-2">Comandos sugeridos:</p>
            <div className="space-y-2">
              {SUGGESTED_COMMANDS.map((cmd, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestedCommand(cmd.command)}
                  disabled={isLoading}
                  className={`
                    w-full text-left px-3 py-2 rounded text-sm border border-gray-300
                    bg-white text-gray-700 hover:bg-blue-50 hover:border-blue-300
                    transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                  `}
                >
                  {cmd.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="border-t border-gray-200 bg-white p-4 flex flex-col gap-3">
          <div className="flex gap-2">
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Escribe tu comando aquí..."
              disabled={isLoading}
              className={`
                flex-1 px-3 py-2 border border-gray-300 rounded-lg
                focus:outline-none focus:ring-2 focus:ring-blue-500
                resize-none text-sm disabled:opacity-50 disabled:cursor-not-allowed
              `}
              rows="3"
            />
          </div>

          {/* Send Button */}
          <button
            onClick={() => sendMessage()}
            disabled={isLoading || !inputValue.trim()}
            className={`
              w-full px-4 py-2 rounded-lg font-medium transition-colors
              flex items-center justify-center gap-2
              ${
                isLoading || !inputValue.trim()
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800'
              }
            `}
          >
            {isLoading ? (
              <>
                <span className="animate-spin">⏳</span>
                <span>Procesando...</span>
              </>
            ) : (
              <>
                <span>📤</span>
                <span>Enviar</span>
              </>
            )}
          </button>

          {/* Keyboard Hint */}
          <p className="text-xs text-gray-500 text-center">
            Shift + Enter para nueva línea
          </p>
        </div>
      </div>

      {/* Toggle Button */}
      <button
        onClick={toggleSidebar}
        className={`
          fixed right-0 top-1/2 transform -translate-y-1/2 -translate-x-full
          bg-blue-600 text-white p-3 rounded-l-lg hover:bg-blue-700
          transition-colors z-30 shadow-lg
          ${isOpen ? 'hidden' : 'block'}
        `}
        aria-label="Open chat"
        title="Abrir asistente PEI"
      >
        💬
      </button>

      {/* Overlay (when sidebar open) */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-20"
          onClick={() => setIsOpen(false)}
          aria-hidden="true"
        />
      )}
    </>
  );
}

export default AgentChat;

