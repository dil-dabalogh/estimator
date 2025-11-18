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
  | "requirements_generation"
  | "ba_generation"
  | "pert_generation"
  | "completed"
  | "failed"

export type TShirtSize = "XS" | "S" | "M" | "L" | "XL" | "XXL"

export type MaturityState = "ready_for_dev" | "in_discovery" | "early_draft"

export interface EstimationResult {
  name: string
  status: EstimationStatus
  progress?: string
  tshirt_size?: TShirtSize
  man_weeks?: number
  maturity_state?: MaturityState
  error?: string
  requirements_available: boolean
  ba_notes_available: boolean
  pert_available: boolean
}

export interface WebSocketMessage {
  session_id: string
  results: EstimationResult[]
}

export interface ConfluenceExportRequest {
  parent_page_url: string
  overwrite?: boolean
}

export interface ConfluenceExportResponse {
  success: boolean
  page_url?: string
  error?: string
}

export interface FetchTitleResponse {
  title: string
  error?: string
}

