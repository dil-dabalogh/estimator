import { useState, useEffect, useRef } from "react"
import { Plus, X, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { EstimationRequest, FetchTitleResponse } from "@/types"
import { API_BASE_URL } from "@/config"
import axios from "axios"

interface EstimationFormProps {
  onSubmit: (items: EstimationRequest[]) => void
  isSubmitting: boolean
  parentPageUrl: string
  onParentPageUrlChange: (url: string) => void
}

export function EstimationForm({ onSubmit, isSubmitting, parentPageUrl, onParentPageUrlChange }: EstimationFormProps) {
  const [items, setItems] = useState<EstimationRequest[]>([
    { url: "", name: "", ballpark: "" }
  ])
  const [fetchingTitle, setFetchingTitle] = useState<{ [key: number]: boolean }>({})
  const debounceTimers = useRef<{ [key: number]: NodeJS.Timeout }>({})

  const addItem = () => {
    setItems([...items, { url: "", name: "", ballpark: "" }])
  }

  const removeItem = (index: number) => {
    if (items.length > 1) {
      setItems(items.filter((_, i) => i !== index))
    }
  }

  const fetchTitle = async (url: string, index: number) => {
    if (!url || url.length < 10) return
    
    setFetchingTitle(prev => ({ ...prev, [index]: true }))
    
    try {
      const response = await axios.get<FetchTitleResponse>(
        `${API_BASE_URL}/api/fetch-title`,
        { params: { url } }
      )
      
      if (response.data.title && !response.data.error) {
        // Use functional update to get the current state
        setItems(currentItems => {
          const newItems = [...currentItems]
          // Only update if the name field is empty or wasn't manually edited
          if (!newItems[index].name) {
            // Append " ROM Estimation" to the fetched title
            const nameWithSuffix = `${response.data.title} ROM Estimation`
            newItems[index] = { ...newItems[index], name: nameWithSuffix }
          }
          return newItems
        })
      }
    } catch (error) {
      console.error("Failed to fetch title:", error)
    } finally {
      setFetchingTitle(prev => ({ ...prev, [index]: false }))
    }
  }

  const updateItem = (index: number, field: keyof EstimationRequest, value: string) => {
    const newItems = [...items]
    newItems[index] = { ...newItems[index], [field]: value }
    setItems(newItems)
    
    // Auto-fetch title when URL changes
    if (field === "url" && value) {
      // Clear existing timer for this index
      if (debounceTimers.current[index]) {
        clearTimeout(debounceTimers.current[index])
      }
      
      // Set new timer to fetch after 500ms of no typing
      debounceTimers.current[index] = setTimeout(() => {
        fetchTitle(value, index)
      }, 500)
    }
  }
  
  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      Object.values(debounceTimers.current).forEach(timer => clearTimeout(timer))
    }
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const validItems = items.filter(item => item.url && item.name)
    if (validItems.length > 0) {
      onSubmit(validItems.map(item => ({
        url: item.url,
        name: item.name,
        ballpark: item.ballpark || undefined
      })))
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Confluence Estimation Location (optional)</CardTitle>
        </CardHeader>
        <CardContent>
                <Input
                  type="url"
                  placeholder="https://your-domain.atlassian.net/wiki/spaces/SPACE/pages/12345/Page-Title"
                  value={parentPageUrl}
                  onChange={(e) => onParentPageUrlChange(e.target.value)}
                  disabled={isSubmitting}
                />
                <p className="text-sm text-muted-foreground mt-2">
                  Enter the Confluence parent page URL where estimations will be exported.
                </p>
        </CardContent>
      </Card>

    <Card>
      <CardHeader>
        <CardTitle>Create Estimations</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {items.map((item, index) => (
            <div key={index} className="flex gap-2 items-start">
              <div className="flex-1 space-y-2">
                <Input
                  type="url"
                  placeholder="Confluence or Jira URL"
                  value={item.url}
                  onChange={(e) => updateItem(index, "url", e.target.value)}
                  required
                />
                <div className="relative">
                <Input
                  type="text"
                  placeholder="Unique name for this estimation"
                  value={item.name}
                  onChange={(e) => updateItem(index, "name", e.target.value)}
                  required
                    disabled={fetchingTitle[index]}
                />
                  {fetchingTitle[index] && (
                    <Loader2 className="h-4 w-4 animate-spin absolute right-3 top-3 text-muted-foreground" />
                  )}
                </div>
                <Input
                  type="text"
                  placeholder="Ballpark (optional, e.g., '30 weeks' or '6 months')"
                  value={item.ballpark}
                  onChange={(e) => updateItem(index, "ballpark", e.target.value)}
                />
              </div>
              {items.length > 1 && (
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={() => removeItem(index)}
                  className="mt-0"
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
          ))}
          
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={addItem}
              disabled={isSubmitting}
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Another URL
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Processing..." : "Generate Estimations"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
    </div>
  )
}

