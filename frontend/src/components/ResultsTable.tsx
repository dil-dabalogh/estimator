import { Download, Loader2, CheckCircle2, XCircle, Upload, ExternalLink } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { EstimationResult, TShirtSize, ConfluenceExportRequest, ConfluenceExportResponse } from "@/types"
import { API_BASE_URL } from "@/config"
import { useState, useEffect } from "react"
import axios from "axios"

interface ResultsTableProps {
  results: EstimationResult[]
  sessionId: string
  parentPageUrl: string
}

const tshirtColors: Record<TShirtSize, string> = {
  XS: "bg-green-500",
  S: "bg-blue-500",
  M: "bg-yellow-500",
  L: "bg-orange-500",
  XL: "bg-red-500",
  XXL: "bg-purple-500"
}

const downloadFile = async (sessionId: string, name: string, type: "ba-notes" | "pert") => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/estimations/${sessionId}/${name}/${type}`)
    if (!response.ok) throw new Error("Download failed")
    
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${name}_${type === "ba-notes" ? "BA_Notes" : "PERT"}.md`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  } catch (error) {
    console.error("Download error:", error)
  }
}

interface ExportState {
  [key: string]: {
    loading: boolean
    success: boolean
    pageUrl?: string
    error?: string
  }
}

export function ResultsTable({ results, sessionId, parentPageUrl }: ResultsTableProps) {
  const [exportState, setExportState] = useState<ExportState>({})

  // Reset export state when session changes (new estimations generated)
  useEffect(() => {
    setExportState({})
  }, [sessionId])

  const exportToConfluence = async (name: string) => {
    if (!parentPageUrl) {
      setExportState(prev => ({
        ...prev,
        [name]: { loading: false, success: false, error: "Please enter a Confluence parent page URL" }
      }))
      return
    }

    setExportState(prev => ({
      ...prev,
      [name]: { loading: true, success: false }
    }))

    try {
      const request: ConfluenceExportRequest = { parent_page_url: parentPageUrl }
      const response = await axios.post<ConfluenceExportResponse>(
        `${API_BASE_URL}/api/estimations/${sessionId}/${name}/export-confluence`,
        request
      )

      if (response.data.success) {
        setExportState(prev => ({
          ...prev,
          [name]: { 
            loading: false, 
            success: true, 
            pageUrl: response.data.page_url 
          }
        }))
      } else {
        setExportState(prev => ({
          ...prev,
          [name]: { 
            loading: false, 
            success: false, 
            error: response.data.error || "Export failed" 
          }
        }))
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || "Export failed"
      setExportState(prev => ({
        ...prev,
        [name]: { loading: false, success: false, error: errorMessage }
      }))
    }
  }

  if (results.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle>Estimation Results</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>T-shirt Size</TableHead>
              <TableHead>Man-weeks</TableHead>
              <TableHead>BA Notes</TableHead>
              <TableHead>PERT</TableHead>
              <TableHead>Export to Confluence</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {results.map((result) => {
              const exportStatus = exportState[result.name]
              return (
              <TableRow key={result.name}>
                <TableCell className="font-medium">{result.name}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    {result.status === "completed" && (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    )}
                    {result.status === "failed" && (
                      <XCircle className="h-4 w-4 text-red-500" />
                    )}
                    {!["completed", "failed"].includes(result.status) && (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    )}
                    <span className="text-sm">{result.progress || result.status}</span>
                  </div>
                </TableCell>
                <TableCell>
                  {result.tshirt_size && (
                    <Badge className={tshirtColors[result.tshirt_size]}>
                      {result.tshirt_size}
                    </Badge>
                  )}
                </TableCell>
                <TableCell>
                  {result.man_weeks != null && result.man_weeks.toFixed(1)}
                </TableCell>
                <TableCell>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={!result.ba_notes_available}
                    onClick={() => downloadFile(sessionId, result.name, "ba-notes")}
                  >
                    <Download className="h-3 w-3 mr-1" />
                    Download
                  </Button>
                </TableCell>
                <TableCell>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={!result.pert_available}
                    onClick={() => downloadFile(sessionId, result.name, "pert")}
                  >
                    <Download className="h-3 w-3 mr-1" />
                    Download
                  </Button>
                </TableCell>
                  <TableCell>
                    <div className="flex flex-col gap-2">
                      {exportStatus?.success ? (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => exportStatus.pageUrl && window.open(exportStatus.pageUrl, "_blank")}
                          className="text-green-600"
                        >
                          <ExternalLink className="h-3 w-3 mr-1" />
                          View Page
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={result.status !== "completed" || exportStatus?.loading || !parentPageUrl}
                          onClick={() => exportToConfluence(result.name)}
                        >
                          {exportStatus?.loading ? (
                            <>
                              <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                              Exporting...
                            </>
                          ) : (
                            <>
                              <Upload className="h-3 w-3 mr-1" />
                              Export
                            </>
                          )}
                        </Button>
                      )}
                      {exportStatus?.error && (
                        <span className="text-xs text-red-600">{exportStatus.error}</span>
                      )}
                    </div>
                  </TableCell>
              </TableRow>
              )
            })}
          </TableBody>
        </Table>
        {results.some(r => r.error) && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-800">
            {results.filter(r => r.error).map(r => (
              <div key={r.name}>
                <strong>{r.name}:</strong> {r.error}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

