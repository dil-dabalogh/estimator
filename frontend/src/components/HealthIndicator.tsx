import { useEffect, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { API_BASE_URL } from "@/config"

export function HealthIndicator() {
  const [status, setStatus] = useState<"checking" | "healthy" | "unhealthy">("checking")

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/health`, {
          method: "GET",
          signal: AbortSignal.timeout(5000), // 5 second timeout
        })
        
        if (response.ok) {
          setStatus("healthy")
        } else {
          setStatus("unhealthy")
        }
      } catch (error) {
        setStatus("unhealthy")
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
        return {
          label: "Backend Online",
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

