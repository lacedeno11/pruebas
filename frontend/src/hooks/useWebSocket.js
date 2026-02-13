import { useState, useEffect, useRef } from 'react'

export function useWebSocket(url = 'ws://localhost:8000/ws') {
  const [isConnected, setIsConnected] = useState(false)
  const [latestMessage, setLatestMessage] = useState(null)
  const [connectionError, setConnectionError] = useState(null)
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const reconnectAttemptsRef = useRef(0)
  const maxReconnectAttempts = 5
  const reconnectDelay = 3000 // 3 seconds

  useEffect(() => {
    const connectWebSocket = () => {
      try {
        // Create WebSocket connection
        const ws = new WebSocket(url)

        ws.onopen = () => {
          console.log('[WebSocket] Connected to', url)
          setIsConnected(true)
          setConnectionError(null)
          reconnectAttemptsRef.current = 0
        }

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            console.log('[WebSocket] Message received:', data)
            setLatestMessage(data)
          } catch (e) {
            console.error('[WebSocket] Failed to parse message:', event.data)
          }
        }

        ws.onerror = (error) => {
          console.error('[WebSocket] Error:', error)
          setConnectionError('WebSocket connection error')
          setIsConnected(false)
        }

        ws.onclose = () => {
          console.log('[WebSocket] Connection closed')
          setIsConnected(false)

          // Attempt to reconnect with exponential backoff
          if (reconnectAttemptsRef.current < maxReconnectAttempts) {
            reconnectAttemptsRef.current += 1
            const delay = reconnectDelay * reconnectAttemptsRef.current
            console.log(
              `[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`
            )
            reconnectTimeoutRef.current = setTimeout(() => {
              connectWebSocket()
            }, delay)
          } else {
            setConnectionError(
              'WebSocket connection failed after maximum reconnection attempts'
            )
          }
        }

        wsRef.current = ws
      } catch (error) {
        console.error('[WebSocket] Connection error:', error)
        setConnectionError(error.message)
        setIsConnected(false)
      }
    }

    connectWebSocket()

    // Cleanup function
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close()
      }
    }
  }, [url])

  const sendMessage = (message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify(message))
        console.log('[WebSocket] Message sent:', message)
      } catch (error) {
        console.error('[WebSocket] Failed to send message:', error)
      }
    } else {
      console.warn('[WebSocket] Cannot send message - connection not ready')
    }
  }

  return {
    isConnected,
    latestMessage,
    connectionError,
    sendMessage
  }
}

export default useWebSocket

