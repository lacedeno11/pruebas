import React, { useState, useEffect, useRef } from 'react';
import toast from 'react-hot-toast';
import { Send, X, MessageCircle } from 'lucide-react';
import { routeAgentMessage } from '@/services/api';

export interface ChatMessage {
  role: 'user' | 'agent' | 'system';
  content: string;
  timestamp: Date;
}

export interface AgentChatProps {
  isOpen?: boolean;
  onToggle?: () => void;
}

/**
 * Agent Chat sidebar component for user-agent interaction
 */
export function AgentChat({ isOpen = true, onToggle }: AgentChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'system',
      content: 'Bienvenido al asistente de DERCAS PEI. Puedo ayudarte con la planificación de OTs, gobernanza y más.',
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!inputValue.trim()) {
      return;
    }

    // Add user message immediately
    const userMessage: ChatMessage = {
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      // Call agent routing endpoint
      const response = await routeAgentMessage(inputValue);

      // Extract agent response
      const agentContent = response.message || response.classification?.reasoning || 'Sin respuesta';

      // Add agent response
      const agentMessage: ChatMessage = {
        role: 'agent',
        content: agentContent,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, agentMessage]);
    } catch (error: any) {
      // Add error message
      const errorMessage: ChatMessage = {
        role: 'system',
        content: `Error: ${error.message || 'Failed to process request'}`,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, errorMessage]);
      toast.error('Error al procesar el mensaje');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleQuickAction = (action: string) => {
    setInputValue(action);
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed right-0 top-0 h-screen w-96 bg-white shadow-2xl z-40 flex flex-col border-l border-gray-200">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <MessageCircle size={20} />
          <h2 className="font-bold text-lg">Asistente DERCAS</h2>
        </div>
        {onToggle && (
          <button
            onClick={onToggle}
            className="hover:bg-blue-800 rounded-full p-1 transition-colors"
            title="Cerrar chat"
          >
            <X size={20} />
          </button>
        )}
      </div>

      {/* Quick Actions */}
      <div className="px-4 py-3 bg-blue-50 border-b border-gray-200 shrink-0">
        <p className="text-xs font-semibold text-gray-700 mb-2">Acciones Rápidas:</p>
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => handleQuickAction('Planifica OTs pendientes')}
            className="text-xs bg-white border border-blue-300 text-blue-700 rounded px-2 py-1 hover:bg-blue-50 transition-colors"
          >
            📋 Planificar
          </button>
          <button
            onClick={() => handleQuickAction('Revisa gobernanza')}
            className="text-xs bg-white border border-blue-300 text-blue-700 rounded px-2 py-1 hover:bg-blue-50 transition-colors"
          >
            ⚖️ Gobernanza
          </button>
          <button
            onClick={() => handleQuickAction('Estado de cuadrillas')}
            className="text-xs bg-white border border-blue-300 text-blue-700 rounded px-2 py-1 hover:bg-blue-50 transition-colors"
          >
            👥 Cuadrillas
          </button>
          <button
            onClick={() => handleQuickAction('OTs detenidas')}
            className="text-xs bg-white border border-blue-300 text-blue-700 rounded px-2 py-1 hover:bg-blue-50 transition-colors"
          >
            ⏸️ Detenidas
          </button>
        </div>
      </div>

      {/* Messages List */}
      <div
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50"
      >
        {messages.map((message, idx) => (
          <div
            key={idx}
            className={`flex ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            } animate-fadeIn`}
          >
            <div
              className={`max-w-xs lg:max-w-md xl:max-w-lg px-4 py-2 rounded-lg ${
                message.role === 'user'
                  ? 'bg-blue-600 text-white rounded-br-none'
                  : message.role === 'agent'
                    ? 'bg-gray-300 text-gray-800 rounded-bl-none'
                    : 'bg-yellow-50 text-yellow-800 italic text-center text-xs border border-yellow-200'
              }`}
            >
              {/* Render markdown content */}
              <div className="text-sm whitespace-pre-wrap break-words">
                {renderMarkdown(message.content)}
              </div>

              {/* Timestamp and copy button */}
              {message.role !== 'system' && (
                <div className="flex items-center justify-between mt-1 text-xs opacity-70">
                  <span>
                    {message.timestamp.toLocaleTimeString('es-ES', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                  {message.role === 'agent' && (
                    <button
                      onClick={() => copyToClipboard(message.content)}
                      className="hover:opacity-100 ml-2"
                      title="Copiar mensaje"
                    >
                      📋
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-300 text-gray-800 px-4 py-2 rounded-lg rounded-bl-none">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce"></div>
                <div
                  className="w-2 h-2 bg-gray-600 rounded-full animate-bounce"
                  style={{ animationDelay: '0.1s' }}
                ></div>
                <div
                  className="w-2 h-2 bg-gray-600 rounded-full animate-bounce"
                  style={{ animationDelay: '0.2s' }}
                ></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 p-4 bg-white shrink-0">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Escribe tu mensaje..."
            disabled={isLoading}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !inputValue.trim()}
            className="bg-blue-600 text-white p-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Enviar mensaje"
          >
            <Send size={20} />
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          💡 Presiona Enter para enviar, Shift+Enter para nueva línea
        </p>
      </div>
    </div>
  );
}

/**
 * Simple markdown rendering for agent responses
 */
function renderMarkdown(content: string): React.ReactNode {
  // Split by lines for processing
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];

  let inCodeBlock = false;
  let codeContent = '';

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Code block detection (triple backticks)
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        // End code block
        elements.push(
          <div key={`code-${i}`} className="bg-gray-800 text-gray-100 p-2 rounded text-xs overflow-x-auto">
            <pre>{codeContent}</pre>
          </div>
        );
        codeContent = '';
        inCodeBlock = false;
      } else {
        // Start code block
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeContent += line + '\n';
      continue;
    }

    // Bold text (**text**)
    const boldRegex = /\*\*(.*?)\*\*/g;
    // Lists (* item)
    const isListItem = line.trim().startsWith('* ');
    // Headers (# Title)
    const isHeader = line.trim().startsWith('# ');

    if (isHeader) {
      elements.push(
        <div key={i} className="font-bold text-sm mt-2">
          {line.replace(/^#+\s/, '')}
        </div>
      );
    } else if (isListItem) {
      elements.push(
        <div key={i} className="ml-2">
          • {line.trim().substring(2)}
        </div>
      );
    } else if (line.trim()) {
      // Regular text with bold support
      const parts = line.split(boldRegex);
      elements.push(
        <div key={i}>
          {parts.map((part, idx) =>
            idx % 2 === 1 ? (
              <span key={idx} className="font-bold">
                {part}
              </span>
            ) : (
              <span key={idx}>{part}</span>
            )
          )}
        </div>
      );
    } else {
      // Empty line for spacing
      elements.push(<div key={i} className="h-1" />);
    }
  }

  return elements.length > 0 ? elements : content;
}

/**
 * Copy message to clipboard
 */
function copyToClipboard(content: string) {
  navigator.clipboard.writeText(content);
  toast.success('Mensaje copiado al portapapeles');
}

export default AgentChat;

