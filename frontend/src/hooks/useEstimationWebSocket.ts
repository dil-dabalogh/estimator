import { useEffect, useRef, useState } from "react"
import type { EstimationResult, WebSocketMessage } from "@/types"
import { WS_BASE_URL } from "@/config"

export function useEstimationWebSocket(sessionId: string | null) {
  const [results, setResults] = useState<EstimationResult[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!sessionId) return

    const wsUrl = `${WS_BASE_URL}/ws/${sessionId}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
    }

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data)
        setResults(message.results)
      } catch (error) {
        console.error("Failed to parse WebSocket message:", error)
      }
    }

    ws.onerror = (error) => {
      console.error("WebSocket error:", error)
    }

    ws.onclose = () => {
      setIsConnected(false)
    }

    return () => {
      ws.close()
    }
  }, [sessionId])

  return { results, isConnected }
}

