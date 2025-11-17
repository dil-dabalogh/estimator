import { useEffect, useRef, useState } from "react"
import axios from "axios"
import type { EstimationResult, WebSocketMessage } from "@/types"
import { API_BASE_URL, WS_BASE_URL } from "@/config"

export function useEstimationWebSocket(sessionId: string | null) {
  const [results, setResults] = useState<EstimationResult[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    if (!sessionId) return

    // Use polling for AWS Lambda deployment (no WebSocket support)
    // Use WebSocket for local development
    const useWebSocket = WS_BASE_URL.startsWith('ws://localhost') || WS_BASE_URL.startsWith('ws://127.0.0.1')

    if (useWebSocket) {
      // WebSocket mode (local development)
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
    } else {
      // Polling mode (AWS Lambda deployment)
      const pollStatus = async () => {
        try {
          const response = await axios.get<{ session_id: string; results: EstimationResult[] }>(
            `${API_BASE_URL}/api/estimations/${sessionId}/status`
          )
          setResults(response.data.results)
          setIsConnected(true)

          // Stop polling if all tasks are completed or failed
          const allDone = response.data.results.every(
            (r: EstimationResult) => r.status === 'completed' || r.status === 'failed'
          )
          if (allDone && pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current)
            pollingIntervalRef.current = null
          }
        } catch (error) {
          console.error("Failed to poll status:", error)
          setIsConnected(false)
        }
      }

      // Poll immediately
      pollStatus()

      // Poll every 2 seconds
      pollingIntervalRef.current = setInterval(pollStatus, 2000)

      return () => {
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current)
          pollingIntervalRef.current = null
        }
      }
    }
  }, [sessionId])

  return { results, isConnected }
}

