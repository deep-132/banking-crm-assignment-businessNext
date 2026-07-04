export interface ScoreBreakdownEntry {
  met?: boolean
  points?: number
  [key: string]: unknown
}

export interface HvcBreakdown {
  balance_percentile: number
  income_percentile: number
  tenure_percentile: number
  product_depth_percentile: number
  active_product_count: number
}

export interface CustomerResult {
  customer_id: string
  name: string
  city: string
  segment: string
  hvc_score: number
  conversion_score: number
  composite_score: number
  recommended_product: string | null
  recommended_amount: number | null
  recommended_rate: number | null
  whatsapp_message: string | null
  hvc_breakdown: HvcBreakdown | null
  conversion_breakdown: Record<string, ScoreBreakdownEntry> | null
}

export interface ChatResponse {
  session_id: string
  reply_text: string
  action: 'full_search' | 'refine' | 'explain' | 'clarify'
  customers: CustomerResult[]
}

export interface ChatMessage {
  role: 'rm' | 'agent'
  content: string
  customers?: CustomerResult[]
  action?: ChatResponse['action']
}
