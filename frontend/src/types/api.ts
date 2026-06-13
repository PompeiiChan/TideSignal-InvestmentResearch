export type SessionSource = 'client' | 'admin'
export type MessageRole = 'user' | 'assistant' | 'system'
export type TraceStatus = 'pending' | 'running' | 'success' | 'failed'
export type SubAgent = 'hotspot_agent' | 'data_agent' | 'stock_agent' | 'chit_chat' | 'clarification'
export type RiskLevel = 'low' | 'medium' | 'high'
export type QualityResult = 'PASS' | 'FAIL'
export type SourceType = 'announcement' | 'report' | 'financial' | 'market' | 'qa' | 'knowledge'
export type RichBlockType = 'ranking_table' | 'calculator' | 'sector_heatmap'

export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface Session {
  id: string
  title: string
  title_source: 'first_query' | 'system'
  is_draft: boolean
  source: SessionSource
  created_at: string
  updated_at: string
  last_message_preview: string
  last_trace_id: string | null
}

export interface SourceRef {
  type: SourceType
  label: string
  time?: string
}

export interface CalculatorField {
  key: 'buy_price' | 'target_price' | 'share_count' | 'fee_rate'
  label: string
  value: number
  unit: string
}

export interface CalculatorResult {
  key: 'return_rate' | 'profit_amount' | 'cost_amount'
  label: string
  value: string
}

export interface RankingTablePayload {
  columns: string[]
  rows: Record<string, string | number>[]
}

export interface MetricTablePayload {
  columns: string[]
  rows: Record<string, string | number>[]
}

export interface StockCardPayload {
  name: string
  code: string
  price: string
  change_pct: string
  tags: string[]
  metrics: MetricTablePayload
}

export interface TextPayload {
  paragraphs: string[]
}

export interface CalculatorPayload {
  fields: CalculatorField[]
  results: CalculatorResult[]
}

export interface SectorHeatmapTile {
  board_name: string
  board_code?: string
  pct_change: number
  turnover_amount: number
  leader?: string
  leader_change?: number | null
  up_count?: number
  down_count?: number
}

export interface SectorHeatmapPayload {
  board_kind: string
  trade_date: string
  tiles: SectorHeatmapTile[]
  size_by: 'turnover_amount'
}

export interface CitationListPayload {
  items: SourceRef[]
}

export interface RiskNoticePayload {
  level: RiskLevel
  text: string
  items: string[]
}

export type RichBlockPayload =
  | RankingTablePayload
  | MetricTablePayload
  | StockCardPayload
  | TextPayload
  | CalculatorPayload
  | SectorHeatmapPayload
  | CitationListPayload
  | RiskNoticePayload
  | Record<string, never>

export interface RichBlock {
  id: string
  type: RichBlockType
  title: string
  payload: RichBlockPayload
  sources: SourceRef[]
  risk_notice: string
}

export interface Message {
  id: string
  session_id: string
  role: MessageRole
  content: string
  rich_blocks: RichBlock[]
  trace_id: string | null
  created_at: string
  /** Optimistic / streaming UI state (client-only). */
  streaming?: boolean
  status_label?: string
  /** Set when SSE content_done arrives; flushes the last streaming line into markdown. */
  content_complete?: boolean
}

export interface SessionDetail {
  session: Session
  messages: Message[]
}

export interface DeleteSessionResponse {
  id: string
  deleted: boolean
}

export interface DetailSectionItem {
  label: string
  value: string
}

export interface TraceDetailSection {
  title: string
  items: DetailSectionItem[]
}

export interface TraceStep {
  step_id: string
  step_index: number
  name: string
  node: string
  status: TraceStatus
  latency_ms: number
  summary: string
  detail_sections: TraceDetailSection[]
  input: Record<string, unknown>
  output: Record<string, unknown>
  raw_json: Record<string, unknown>
  error: string | null
}

export interface TraceMetadata {
  total_latency_ms: number
  tool_calls_count: number
  quality_check_result: QualityResult
  model_versions?: Record<string, string>
}

export interface Trace {
  id: string
  session_id: string
  message_id: string
  user_query: string
  status: TraceStatus
  steps: TraceStep[]
  metadata: TraceMetadata
}

export interface TraceSummary {
  id: string
  status: TraceStatus
  metadata: TraceMetadata
}

export interface ChatQueryRequest {
  session_id: string
  source: SessionSource
  query: string
}

export interface ChatRegenerateRequest {
  session_id: string
  assistant_message_id: string
  source: SessionSource
}

export interface ChatQueryResponse {
  session: Session
  user_message: Message
  assistant_message: Message
  trace: TraceSummary
}

export interface LayoutPreferences {
  sidebar_width: number
  sidebar_width_range: { min: number; max: number }
  trace_panel_width: number
  trace_panel_width_range: { min: number; max: number }
  updated_at: string
}

export interface DataSourceStatus {
  mock_data: Array<{
    type: SourceType
    name: string
    path: string
    status: 'ready' | 'mocked' | 'missing'
    sample_count: number
  }>
  rag: {
    mode: 'mock' | 'semantic'
    embedding_provider: string
    rerank_provider: string
    status: 'mocked' | 'ready'
  }
}

export interface ConfigStatus {
  models: Array<{
    name: string
    fields: string[]
    status: 'mocked' | 'ready' | 'missing'
    missing_fields: string[]
  }>
  prompts: Array<{
    agent: 'master_agent' | 'hotspot_agent' | 'data_agent' | 'stock_agent' | 'quality_check'
    name: string
    status: 'default' | 'custom'
  }>
  compliance_rules: {
    blacklist_expressions: string[]
    risk_tip_required: boolean
    citation_required: boolean
  }
}

export interface RawTraceStepResponse {
  trace_id: string
  step_id: string
  raw_json: Record<string, unknown>
}
