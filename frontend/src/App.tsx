import { useState } from "react"
import axios from "axios"
import { EstimationForm } from "@/components/EstimationForm"
import { ResultsTable } from "@/components/ResultsTable"
import { useEstimationWebSocket } from "@/hooks/useEstimationWebSocket"
import { API_BASE_URL } from "@/config"
import type { EstimationRequest, BatchResponse } from "@/types"

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [parentPageUrl, setParentPageUrl] = useState("")
  const { results, isConnected } = useEstimationWebSocket(sessionId)

  const handleSubmit = async (items: EstimationRequest[]) => {
    setIsSubmitting(true)
    try {
      const response = await axios.post<BatchResponse>(
        `${API_BASE_URL}/api/estimations/batch`,
        { items }
      )
      setSessionId(response.data.session_id)
    } catch (error) {
      console.error("Failed to submit batch:", error)
      alert("Failed to submit estimation request. Please try again.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto py-8 px-4 max-w-6xl">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Estimation Tool</h1>
          <p className="text-muted-foreground">
            Generate BA notes and PERT estimates from Confluence/Jira URLs
          </p>
        </div>

        <div className="space-y-6">
          <EstimationForm 
            onSubmit={handleSubmit} 
            isSubmitting={isSubmitting}
            parentPageUrl={parentPageUrl}
            onParentPageUrlChange={setParentPageUrl}
          />
          
          {sessionId && results.length > 0 && (
            <ResultsTable 
              results={results} 
              sessionId={sessionId}
              parentPageUrl={parentPageUrl}
            />
          )}

          {sessionId && !isConnected && results.length === 0 && (
            <div className="text-center py-4 text-muted-foreground">
              Connecting to server...
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
