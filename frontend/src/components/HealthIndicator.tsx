import { useEffect, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { API_BASE_URL } from "@/config"

interface ModelInfo {
  provider: string
  model: string
  agentAlias: string | null
}

export function HealthIndicator() {
  const [status, setStatus] = useState<"checking" | "healthy" | "unhealthy">("checking")
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null)

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/health`, {
          method: "GET",
          signal: AbortSignal.timeout(5000), // 5 second timeout
        })
        
        if (response.ok) {
          const data = await response.json()
          setStatus("healthy")
          
          // Extract model/agent info if available
          if (data.provider && data.model) {
            setModelInfo({
              provider: data.provider,
              model: data.model,
              agentAlias: data.agent_alias || null
            })
          }
        } else {
          setStatus("unhealthy")
          setModelInfo(null)
        }
      } catch (error) {
        setStatus("unhealthy")
        setModelInfo(null)
      }
    }

    // Check immediately
    checkHealth()

    // Check every 30 seconds
    const interval = setInterval(checkHealth, 30000)

    return () => clearInterval(interval)
  }, [])

  const getStatusConfig = () => {
    switch (status) {
      case "healthy":
        let label = "Backend Online"
        if (modelInfo) {
          const { provider, model, agentAlias } = modelInfo
          if (provider === "bedrock") {
            label = agentAlias ? `Bedrock | ${agentAlias}` : `Bedrock | ${model}`
          } else if (provider === "openai") {
            label = `OpenAI | ${model}`
          }
        }
        return {
          label,
          className: "bg-green-500 text-white",
          dotColor: "bg-green-400",
        }
      case "unhealthy":
        return {
          label: "Backend Offline",
          className: "bg-red-500 text-white",
          dotColor: "bg-red-400",
        }
      case "checking":
        return {
          label: "Checking...",
          className: "bg-gray-500 text-white",
          dotColor: "bg-gray-400",
        }
    }
  }

  const config = getStatusConfig()

  return (
    <Badge variant="outline" className={config.className}>
      <span className={`inline-block w-2 h-2 rounded-full ${config.dotColor} mr-2 ${status === "checking" ? "animate-pulse" : ""}`} />
      {config.label}
    </Badge>
  )
}

