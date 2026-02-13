import React, { useState, useEffect, useRef } from 'react'
import { toast } from 'react-toastify'
import { sendChatMessage } from '../services/api'

export function ChatSidebar() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Auto-scroll to latest message
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  // Focus input when sidebar opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [isOpen])

  // Load initial greeting
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([
        {
          id: 'greeting-1',
          type: 'agent',
          text: 'Welcome to PEI Platform AI Assistant! 👋',
          timestamp: new Date()
        },
        {
          id: 'greeting-2',
          type: 'agent',
          text: 'I can help you with OT management, team planning, and system operations. How can I assist you today?',
          timestamp: new Date()
        }
      ])
    }
  }, [])

  const handleSendMessage = async (e) => {
    e.preventDefault()

    const trimmedInput = inputValue.trim()
    if (!trimmedInput) {
      toast.warning('Please enter a message')
      return
    }

    // Add user message to chat
    const userMessage = {
      id: `user-${Date.now()}`,
      type: 'user',
      text: trimmedInput,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    try {
      // Send message to backend
      const response = await sendChatMessage(trimmedInput)

      // Add agent response to chat
      const agentMessage = {
        id: `agent-${Date.now()}`,
        type: 'agent',
        text: response.message || response.response || 'No response received',
        timestamp: new Date(),
        metadata: response.metadata || {}
      }

      setMessages(prev => [...prev, agentMessage])
    } catch (error) {
      console.error('Error sending message:', error)
      toast.error(`Failed to send message: ${error.message}`)

      // Add error message to chat
      const errorMessage = {
        id: `error-${Date.now()}`,
        type: 'error',
        text: `Error: ${error.message}. Please try again.`,
        timestamp: new Date()
      }

      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleClearChat = () => {
    setMessages([
      {
        id: 'greeting-1',
        type: 'agent',
        text: 'Welcome to PEI Platform AI Assistant! 👋',
        timestamp: new Date()
      },
      {
        id: 'greeting-2',
        type: 'agent',
        text: 'I can help you with OT management, team planning, and system operations. How can I assist you today?',
        timestamp: new Date()
      }
    ])
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage(e)
    }
  }

  return (
    <>
      {/* Chat Toggle Button */}
      <button
        className="chat-toggle-btn"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Toggle chat sidebar"
        title={isOpen ? 'Close chat' : 'Open chat'}
      >
        <span className="chat-toggle-icon">
          {isOpen ? '✕' : '💬'}
        </span>
      </button>

      {/* Chat Overlay (for closing sidebar when clicking outside) */}
      {isOpen && (
        <div
          className="chat-overlay"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Chat Sidebar */}
      <div className={`chat-sidebar ${isOpen ? 'open' : ''}`}>
        {/* Header */}
        <div className="chat-header">
          <h3 className="chat-title">AI Assistant</h3>
          <div className="chat-header-controls">
            <button
              className="chat-clear-btn"
              onClick={handleClearChat}
              title="Clear chat history"
              aria-label="Clear chat"
            >
              🗑️
            </button>
            <button
              className="chat-close-btn"
              onClick={() => setIsOpen(false)}
              aria-label="Close chat sidebar"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Messages Container */}
        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="chat-empty-state">
              <p>No messages yet</p>
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`chat-message chat-message-${message.type}`}
              >
                <div className="chat-message-avatar">
                  {message.type === 'user' ? '👤' : message.type === 'error' ? '⚠️' : '🤖'}
                </div>
                <div className="chat-message-content">
                  <p className="chat-message-text">{message.text}</p>
                  <span className="chat-message-time">
                    {message.timestamp.toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </span>
                </div>
              </div>
            ))
          )}
          {isLoading && (
            <div className="chat-message chat-message-loading">
              <div className="chat-message-avatar">🤖</div>
              <div className="chat-message-content">
                <div className="chat-typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Form */}
        <form onSubmit={handleSendMessage} className="chat-form">
          <div className="chat-input-wrapper">
            <textarea
              ref={inputRef}
              className="chat-input"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask me anything... (Shift+Enter for new line)"
              disabled={isLoading}
              rows="1"
            />
            <button
              type="submit"
              className="chat-send-btn"
              disabled={isLoading || !inputValue.trim()}
              aria-label="Send message"
              title="Send message (or press Enter)"
            >
              {isLoading ? '⟳' : '➤'}
            </button>
          </div>
          <p className="chat-help-text">
            Shift+Enter for new line, Enter to send
          </p>
        </form>
      </div>
    </>
  )
}

// Chat Sidebar Styles
const chatSidebarStyles = `
/* Chat Toggle Button */
.chat-toggle-btn {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, #2196F3, #1976D2);
  border: none;
  color: white;
  font-size: 24px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(33, 150, 243, 0.3);
  z-index: 999;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chat-toggle-btn:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 16px rgba(33, 150, 243, 0.4);
}

.chat-toggle-btn:active {
  transform: scale(0.95);
}

.chat-toggle-icon {
  display: block;
  line-height: 1;
}

/* Chat Overlay */
.chat-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.3);
  z-index: 998;
  animation: fadeIn 0.2s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

/* Chat Sidebar */
.chat-sidebar {
  position: fixed;
  right: -400px;
  top: 0;
  bottom: 0;
  width: 400px;
  background-color: white;
  box-shadow: -4px 0 16px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  transition: right 0.3s ease;
  border-radius: 8px 0 0 8px;
  overflow: hidden;
}

.chat-sidebar.open {
  right: 0;
}

/* Chat Header */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: linear-gradient(135deg, #2196F3, #1976D2);
  color: white;
  border-bottom: 1px solid #e0e0e0;
  flex-shrink: 0;
}

.chat-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.chat-header-controls {
  display: flex;
  gap: 8px;
}

.chat-clear-btn,
.chat-close-btn {
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  border-radius: 4px;
  cursor: pointer;
  padding: 4px 8px;
  font-size: 14px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
}

.chat-clear-btn:hover,
.chat-close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
}

.chat-clear-btn:active,
.chat-close-btn:active {
  transform: scale(0.95);
}

/* Messages Container */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background-color: #f9f9f9;
}

.chat-empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: #999;
  text-align: center;
}

.chat-empty-state p {
  margin: 0;
  font-size: 14px;
}

/* Message Styling */
.chat-message {
  display: flex;
  gap: 8px;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.chat-message-user {
  justify-content: flex-end;
}

.chat-message-user .chat-message-avatar {
  order: 2;
}

.chat-message-user .chat-message-content {
  background-color: #2196F3;
  color: white;
}

.chat-message-agent {
  justify-content: flex-start;
}

.chat-message-agent .chat-message-content {
  background-color: #e0e0e0;
  color: #333;
}

.chat-message-error {
  justify-content: flex-start;
}

.chat-message-error .chat-message-content {
  background-color: #ffebee;
  color: #d32f2f;
  border: 1px solid #ef5350;
}

.chat-message-loading {
  justify-content: flex-start;
}

.chat-message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
  background-color: #f0f0f0;
}

.chat-message-user .chat-message-avatar {
  background-color: #e3f2fd;
}

.chat-message-content {
  flex: 1;
  padding: 10px 12px;
  border-radius: 8px;
  word-wrap: break-word;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.chat-message-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
}

.chat-message-time {
  font-size: 11px;
  opacity: 0.7;
  margin-top: 4px;
}

.chat-message-user .chat-message-time {
  text-align: right;
}

/* Typing Indicator */
.chat-typing-indicator {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}

.chat-typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #999;
  animation: typing 1.4s infinite;
}

.chat-typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.chat-typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    opacity: 0.5;
    transform: translateY(0);
  }
  30% {
    opacity: 1;
    transform: translateY(-8px);
  }
}

/* Chat Form */
.chat-form {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  background-color: white;
  border-top: 1px solid #e0e0e0;
  flex-shrink: 0;
}

.chat-input-wrapper {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.chat-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: inherit;
  font-size: 13px;
  resize: none;
  max-height: 100px;
  line-height: 1.5;
  transition: all 0.2s ease;
}

.chat-input:focus {
  outline: none;
  border-color: #2196F3;
  box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.1);
}

.chat-input:disabled {
  background-color: #f5f5f5;
  color: #999;
  cursor: not-allowed;
}

.chat-send-btn {
  padding: 8px 12px;
  background-color: #2196F3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  flex-shrink: 0;
}

.chat-send-btn:hover:not(:disabled) {
  background-color: #1976D2;
  transform: translateY(-2px);
}

.chat-send-btn:active:not(:disabled) {
  transform: translateY(0);
}

.chat-send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chat-help-text {
  margin: 0;
  font-size: 11px;
  color: #999;
  text-align: center;
}

/* Scrollbar Styling */
.chat-messages::-webkit-scrollbar {
  width: 6px;
}

.chat-messages::-webkit-scrollbar-track {
  background: #f0f0f0;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: #999;
}

/* Responsive Design */
@media (max-width: 768px) {
  .chat-sidebar {
    width: 100%;
    right: -100%;
  }

  .chat-sidebar.open {
    right: 0;
  }

  .chat-toggle-btn {
    bottom: 16px;
    right: 16px;
    width: 48px;
    height: 48px;
    font-size: 20px;
  }

  .chat-message-text {
    font-size: 12px;
  }

  .chat-input {
    font-size: 14px; /* Prevents zoom on iOS */
  }
}

@media (max-width: 480px) {
  .chat-sidebar {
    border-radius: 0;
  }

  .chat-header {
    padding: 12px;
  }

  .chat-title {
    font-size: 14px;
  }

  .chat-messages {
    padding: 12px;
    gap: 8px;
  }

  .chat-message-avatar {
    width: 28px;
    height: 28px;
    font-size: 14px;
  }

  .chat-message-content {
    padding: 8px 10px;
  }

  .chat-form {
    padding: 10px;
    gap: 4px;
  }

  .chat-input-wrapper {
    gap: 6px;
  }

  .chat-send-btn {
    width: 36px;
    height: 36px;
    font-size: 12px;
  }

  .chat-clear-btn,
  .chat-close-btn {
    width: 28px;
    height: 28px;
    font-size: 12px;
  }
}
`

export default ChatSidebar

