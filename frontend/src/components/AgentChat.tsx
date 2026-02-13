import React, { useState, useEffect, useRef } from 'react';
import toast from 'react-hot-toast';
import { Send, X, MessageCircle, Copy, CheckCircle } from 'lucide-react';
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

// Quick action commands
const QUICK_ACTIONS = [
  { label: '📋 Planifica OTs', command: 'Planifica los OTs que están en estado PREPLANIFICADA' },
  { label: '⚖️ Gobernanza', command: 'Revisa las reglas de gobernanza y alertas' },
  { label: '👥 Cuadrillas', command: 'Muéstrame el estado actual de todas las cuadrillas' },
  { label: '⏸️ Detenidas', command: 'Cuáles son los OTs que están en estado DETENIDA' },
];

/**
 * Agent Chat sidebar component for user-agent interaction with enhancements
 * Features: Quick actions, typing indicator, markdown rendering, copy button
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
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Render markdown content with bold, lists, headers, and code blocks
  const renderMarkdown = (content: string): React.ReactNode => {
    let html = content;

    // Handle code blocks
    html = html.replace(/```([\s\S]*?)```/g, '<CODE_BLOCK>$1</CODE_BLOCK>');

    // Handle bold text
    html = html.replace(/\*\*(.*?)\*\*/g, '<BOLD>$1</BOLD>');

    // Handle headers
    html = html.replace(/^### (.*?)$/gm, '<H3>$1</H3>');
    html = html.replace(/^## (.*?)$/gm, '<H2>$1</H2>');
    html = html.replace(/^# (.*?)$/gm, '<H1>$1</H1>');

    // Handle lists
    html = html.replace(/^\* (.*?)$/gm, '<LI>$1</LI>');

    return (
      <div className="whitespace-pre-wrap text-sm">
        {html.split('\n').map((line, idx) => {
          if (line.startsWith('<H1>')) {
            return (
              <div key={idx} className="text-lg font-bold mt-2">
                {line.replace(/<H1>(.*?)<\/H1>/, '$1')}
              </div>
            );
          }
          if (line.startsWith('<H2>')) {
            return (
              <div key={idx} className="text-base font-bold mt-1">
                {line.replace(/<H2>(.*?)<\/H2>/, '$1')}
              </div>
            );
          }
          if (line.startsWith('<H3>')) {
            return (
              <div key={idx} className="font-bold text-sm">
                {line.replace(/<H3>(.*?)<\/H3>/, '$1')}
              </div>
            );
          }
          if (line.includes('<CODE_BLOCK>')) {
            const codeContent = line.replace(/<CODE_BLOCK>(.*?)<\/CODE_BLOCK>/, '$1');
            return (
              <div key={idx} className="bg-gray-800 text-gray-100 p-2 rounded font-mono text-xs my-1 overflow-x-auto">
                {codeContent}
              </div>
            );
          }
          if (line.startsWith('<LI>')) {
            const listItem = line.replace(/<LI>(.*?)<\/LI>/, '$1');
            return (
              <div key={idx} className="ml-4 flex gap-2">
                <span>•</span>
                <span>{listItem}</span>
              </div>
            );
          }

          const hasBold = line.includes('<BOLD>');
          const displayLine = line.replace(/<BOLD>(.*?)<\/BOLD>/g, '$1');

          return (
            <div key={idx} className={hasBold ? 'font-bold' : ''}>
              {displayLine}
            </div>
          );
        })}
      </div>
    );
  };

  // Copy message to clipboard
  const copyToClipboard = (content: string, messageIdx: number) => {
    navigator.clipboard.writeText(content);
    setCopiedIdx(messageIdx);
    toast.success('Mensaje copiado al portapapeles');
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  // Handle quick action click
  const handleQuickAction = (command: string) => {
    setInputValue(command);
  };

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

    setMessages([...messages, userMessage]);

    const userInputValue = inputValue;
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await routeAgentMessage(userInputValue);

      const agentMessage: ChatMessage = {
        role: 'agent',
        content: response.message || response.classification?.reasoning || 'Sin respuesta',
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, agentMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      const errorMessage: ChatMessage = {
        role: 'system',
        content: 'Error al procesar el mensaje. Intenta de nuevo.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed right-0 top-0 h-full w-96 bg-white shadow-2xl z-40 flex flex-col border-l border-gray-200">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageCircle size={20} />
          <h2 className="font-bold text-lg">Asistente DERCAS</h2>
        </div>
        {onToggle && (
          <button
            onClick={onToggle}
            className="text-white hover:bg-blue-800 rounded-full p-1 transition-colors"
          >
            <X size={20} />
          </button>
        )}
      </div>

      {/* Quick Actions */}
      <div className="bg-blue-50 border-b border-blue-200 p-3 grid grid-cols-2 gap-2">
        {QUICK_ACTIONS.map((action, idx) => (
          <button
            key={idx}
            onClick={() => handleQuickAction(action.command)}
            className="text-xs px-2 py-1 bg-white border border-blue-300 rounded text-blue-700 hover:bg-blue-100 transition-colors truncate font-medium"
            title={action.label}
          >
            {action.label}
          </button>
        ))}
      </div>

      {/* Messages Area */}
      <div
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50"
      >
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className="relative max-w-xs group">
              <div
                className={`px-4 py-2 rounded-lg ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white rounded-br-none'
                    : msg.role === 'agent'
                      ? 'bg-gray-300 text-gray-800 rounded-bl-none'
                      : 'bg-yellow-50 text-yellow-900 italic text-center text-xs border border-yellow-200'
                }`}
              >
                {msg.role === 'agent' || msg.role === 'user' ? (
                  <div className="text-sm">{renderMarkdown(msg.content)}</div>
                ) : (
                  <p className="text-sm">{msg.content}</p>
                )}
                <p
                  className={`text-xs mt-1 ${
                    msg.role === 'user'
                      ? 'text-blue-200'
                      : msg.role === 'agent'
                        ? 'text-gray-500'
                        : 'text-yellow-700'
                  }`}
                >
                  {msg.timestamp.toLocaleTimeString()}
                </p>
              </div>

              {/* Copy button for agent messages */}
              {msg.role === 'agent' && (
                <button
                  onClick={() => copyToClipboard(msg.content, idx)}
                  className="absolute -right-8 top-0 text-gray-400 hover:text-blue-600 opacity-0 group-hover:opacity-100 transition-all"
                  title="Copiar mensaje"
                >
                  {copiedIdx === idx ? (
                    <CheckCircle size={16} className="text-green-600" />
                  ) : (
                    <Copy size={16} />
                  )}
                </button>
              )}
            </div>
          </div>
        ))}

        {/* Typing Indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-300 text-gray-800 rounded-lg rounded-bl-none px-4 py-2">
              <div className="flex gap-1 items-center">
                <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce"></div>
                <div
                  className="w-2 h-2 bg-gray-600 rounded-full animate-bounce"
                  style={{ animationDelay: '0.2s' }}
                ></div>
                <div
                  className="w-2 h-2 bg-gray-600 rounded-full animate-bounce"
                  style={{ animationDelay: '0.4s' }}
                ></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 p-4 bg-white">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Escribe tu mensaje..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !inputValue.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}

export default AgentChat;

