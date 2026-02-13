import React, { useState, useEffect, useRef } from 'react'
import { sendChatMessage } from '../services/api'
import { toast } from 'react-toastify'
import './AgentChat.css'

/**
 * Typing Indicator Component
 */
function TypingIndicator() {
  return (
    <div className="typing-indicator">
      <span></span>
      <span></span>
      <span></span>
    </div>
  )
}

/**
 * Message Component
 */
function Message({ message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`message ${isUser ? 'user' : 'assistant'}`}>
      <div className="message-content">
        {message.content}
      </div>
      <span className="message-time" title={message.timestamp}>
        {new Date(message.timestamp).toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
        })}
      </span>
    </div>
  )
}

/**
 * Suggested Actions Component
 */
function SuggestedActions({ actions, onActionClick }) {
  if (!actions || actions.length === 0) {
    return null
  }

  return (
    <div className="suggested-actions">
      {actions.map((action, index) => (
        <button
          key={index}
          className="suggested-action-btn"
          onClick={() => onActionClick(action)}
          title={action}
        >
          {action}
        </button>
      ))}
    </div>
  )
}

/**
 * Main AgentChat Component
 */
export default function AgentChat() {
  // State management
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        '¡Hola! Soy tu asistente de gestión de órdenes de trabajo. Puedo ayudarte con:\n\n📊 Ver el estado de las OTs\n👥 Verificar la utilización de las cuadrillas\n⚙️ Iniciar la planificación automática\n🔍 Consultar detalles de OTs específicas\n\n¿En qué puedo ayudarte hoy?',
      timestamp: new Date().toISOString(),
      suggestedActions: [
        'Planifica las OTs del proyecto DataLegal',
        'Muéstrame el estado de las cuadrillas',
        '¿Cuántas OTs están detenidas?',
      ],
    },
  ])
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [conversationId, setConversationId] = useState(null)
  const [lastSuggestedActions, setLastSuggestedActions] = useState([])
  const messagesEndRef = useRef(null)

  /**
   * Auto-scroll to bottom when messages change
   */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  /**
   * Handle message submission
   */
  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!inputValue.trim()) {
      return
    }

    const userMessage = {
      role: 'user',
      content: inputValue,
      timestamp: new Date().toISOString(),
    }

    // Add user message to history
    setMessages((prev) => [...prev, userMessage])
    setInputValue('')
    setLoading(true)

    try {
      // Send message to agent
      const response = await sendChatMessage(inputValue, conversationId)

      // Update conversation ID
      if (response.conversation_id && !conversationId) {
        setConversationId(response.conversation_id)
      }

      // Add assistant response
      const assistantMessage = {
        role: 'assistant',
        content: response.response,
        timestamp: new Date().toISOString(),
        suggestedActions: response.suggested_actions,
      }

      setMessages((prev) => [...prev, assistantMessage])
      setLastSuggestedActions(response.suggested_actions || [])
    } catch (error) {
      console.error('Chat error:', error)
      toast.error('Failed to send message')
    } finally {
      setLoading(false)
    }
  }

  /**
   * Handle suggested action click
   */
  const handleActionClick = (action) => {
    setInputValue(action)
    // Focus input and submit
    setTimeout(() => {
      const form = document.querySelector('.chat-input-form')
      if (form) {
        form.dispatchEvent(new Event('submit', { bubbles: true }))
      }
    }, 100)
  }

  /**
   * Handle clear conversation
   */
  const handleClearConversation = () => {
    if (window.confirm('Clear conversation history? This action cannot be undone.')) {
      setMessages([
        {
          role: 'assistant',
          content:
            '¡Hola! Soy tu asistente de gestión de órdenes de trabajo. Puedo ayudarte con:\n\n📊 Ver el estado de las OTs\n👥 Verificar la utilización de las cuadrillas\n⚙️ Iniciar la planificación automática\n🔍 Consultar detalles de OTs específicas\n\n¿En qué puedo ayudarte hoy?',
          timestamp: new Date().toISOString(),
          suggestedActions: [
            'Planifica las OTs del proyecto DataLegal',
            'Muéstrame el estado de las cuadrillas',
            '¿Cuántas OTs están detenidas?',
          ],
        },
      ])
      setConversationId(null)
      setLastSuggestedActions([])
      toast.info('Conversation cleared')
    }
  }

  /**
   * Handle voice input (optional, using Web Speech API)
   */
  const handleVoiceInput = () => {
    // Check browser support
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      toast.warn('Voice input not supported in your browser')
      return
    }

    const recognition = new SpeechRecognition()
    recognition.lang = 'es-ES' // Spanish by default
    recognition.continuous = false
    recognition.interimResults = false

    recognition.onstart = () => {
      toast.info('Listening...')
    }

    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((result) => result[0].transcript)
        .join('')

      setInputValue(transcript)
      toast.success('Voice input received')
    }

    recognition.onerror = (event) => {
      toast.error(`Voice error: ${event.error}`)
    }

    recognition.start()
  }

  return (
    <div className="chat-container">
      {/* Header */}
      <div className="chat-header">
        <h2>💬 Agent Chat</h2>
        <button onClick={handleClearConversation} className="btn btn-secondary btn-sm">
          🗑️ Clear
        </button>
      </div>

      {/* Messages Area */}
      <div className="chat-messages">
        {messages.map((message, index) => (
          <div key={index}>
            <Message message={message} />

            {/* Show suggested actions for last assistant message */}
            {message.role === 'assistant' &&
              message === messages[messages.length - 1] &&
              message.suggestedActions &&
              message.suggestedActions.length > 0 && (
                <SuggestedActions
                  actions={message.suggestedActions}
                  onActionClick={handleActionClick}
                />
              )}
          </div>
        ))}

        {/* Typing indicator while loading */}
        {loading && (
          <div className="message assistant">
            <TypingIndicator />
          </div>
        )}

        {/* Auto-scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <form className="chat-input-form" onSubmit={handleSubmit}>
        <textarea
          className="chat-input"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Ask me anything about work orders, crews, planning..."
          disabled={loading}
          rows="3"
          onKeyDown={(e) => {
            // Submit on Ctrl+Enter
            if (e.ctrlKey && e.key === 'Enter') {
              handleSubmit(e)
            }
          }}
        />

        <div className="chat-actions">
          <button
            type="button"
            onClick={handleVoiceInput}
            className="btn btn-secondary"
            title="Voice input (Spanish)"
            disabled={loading}
          >
            🎤
          </button>
          <button type="submit" className="btn btn-primary" disabled={loading || !inputValue.trim()}>
            {loading ? <span className="spinner"></span> : '📤'}
          </button>
        </div>
      </form>

      {/* Help Text */}
      <div className="chat-help">
        <p>💡 Tip: Use Ctrl+Enter to send message quickly</p>
      </div>
    </div>
  )
}

