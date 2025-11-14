import { useState } from "react"
import { Plus, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { EstimationRequest } from "@/types"

interface EstimationFormProps {
  onSubmit: (items: EstimationRequest[]) => void
  isSubmitting: boolean
}

export function EstimationForm({ onSubmit, isSubmitting }: EstimationFormProps) {
  const [items, setItems] = useState<EstimationRequest[]>([
    { url: "", name: "", ballpark: "" }
  ])

  const addItem = () => {
    setItems([...items, { url: "", name: "", ballpark: "" }])
  }

  const removeItem = (index: number) => {
    if (items.length > 1) {
      setItems(items.filter((_, i) => i !== index))
    }
  }

  const updateItem = (index: number, field: keyof EstimationRequest, value: string) => {
    const newItems = [...items]
    newItems[index] = { ...newItems[index], [field]: value }
    setItems(newItems)
  }

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
                <Input
                  type="text"
                  placeholder="Unique name for this estimation"
                  value={item.name}
                  onChange={(e) => updateItem(index, "name", e.target.value)}
                  required
                />
                <Input
                  type="text"
                  placeholder="Ballpark (optional, e.g., '30 manweeks')"
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
  )
}

