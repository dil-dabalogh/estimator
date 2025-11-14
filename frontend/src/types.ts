export interface EstimationRequest {
  url: string
  name: string
  ballpark?: string
}

export interface BatchRequest {
  items: EstimationRequest[]
}

export interface BatchResponse {
  session_id: string
}

export type EstimationStatus = 
  | "pending"
  | "fetching"
  | "ba_generation"
  | "pert_generation"
  | "completed"
  | "failed"

export type TShirtSize = "XS" | "S" | "M" | "L" | "XL" | "XXL"

export interface EstimationResult {
  name: string
  status: EstimationStatus
  progress?: string
  tshirt_size?: TShirtSize
  man_weeks?: number
  error?: string
  ba_notes_available: boolean
  pert_available: boolean
}

export interface WebSocketMessage {
  session_id: string
  results: EstimationResult[]
}

