import { Download, Loader2, CheckCircle2, XCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { EstimationResult, TShirtSize } from "@/types"
import { API_BASE_URL } from "@/config"

interface ResultsTableProps {
  results: EstimationResult[]
  sessionId: string
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

export function ResultsTable({ results, sessionId }: ResultsTableProps) {
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
            </TableRow>
          </TableHeader>
          <TableBody>
            {results.map((result) => (
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
              </TableRow>
            ))}
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

