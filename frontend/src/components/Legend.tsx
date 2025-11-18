import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { TShirtSize, MaturityState } from "@/types"

const tshirtSizeRanges: Record<TShirtSize, string> = {
  XS: "< 2 man-weeks",
  S: "2-16 man-weeks",
  M: "16-25 man-weeks",
  L: "25-40 man-weeks",
  XL: "40-60 man-weeks",
  XXL: "60+ man-weeks"
}

const tshirtColors: Record<TShirtSize, string> = {
  XS: "bg-green-500",
  S: "bg-blue-500",
  M: "bg-yellow-500",
  L: "bg-orange-500",
  XL: "bg-red-500",
  XXL: "bg-purple-500"
}

const maturityStateDescriptions: Record<MaturityState, { label: string; description: string; color: string }> = {
  ready_for_dev: {
    label: "Ready for Development",
    description: "Low uncertainty, development team can take over the initiative for starting development, man-week estimation is confident",
    color: "bg-green-600"
  },
  in_discovery: {
    label: "In Discovery",
    description: "Significant Product Manager work needed before development can start, T-shirt size is confident",
    color: "bg-yellow-600"
  },
  early_draft: {
    label: "Early Draft",
    description: "Sigma is very high, it is hard to decide even the T-shirt size",
    color: "bg-orange-600"
  }
}

export function Legend() {
  return (
    <div className="mt-6 grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">T-shirt Size Legend</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {(Object.keys(tshirtSizeRanges) as TShirtSize[]).map((size) => (
              <div key={size} className="flex items-center justify-between">
                <Badge className={tshirtColors[size]}>{size}</Badge>
                <span className="text-sm text-muted-foreground">{tshirtSizeRanges[size]}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Maturity State Legend</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {(Object.keys(maturityStateDescriptions) as MaturityState[]).map((state) => {
              const config = maturityStateDescriptions[state]
              return (
                <div key={state} className="space-y-1">
                  <Badge className={config.color}>{config.label}</Badge>
                  <p className="text-sm text-muted-foreground ml-1">{config.description}</p>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

