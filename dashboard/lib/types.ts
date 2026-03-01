export interface ProjectListItem {
  id: string
  name: string
  interview_count: number
  cluster_count: number
  updated_at: string // ISO 8601
}

export interface ProjectResponse {
  id: string
  name: string
  research_goal: string
  prompt_context: string | null
  extraction_source: 'summary' | 'transcript'
  extraction_source_locked: boolean
  model_interviewer: string
  model_extraction: string
  model_clustering: string
  model_summary: string
  interview_count: number
  cluster_count: number
  fact_count: number
  created_at: string
  updated_at: string
}

export interface ClusterResponse {
  id: string
  name: string
  summary: string | null
  fact_count: number
  interview_count: number
  created_at: string
  updated_at: string
}

export interface CreateProjectRequest {
  name: string
  research_goal: string
  prompt_context?: string
  extraction_source?: 'summary' | 'transcript'
}

// --- Cluster Detail Types (Slice 5) ---

export interface FactResponse {
  id: string
  content: string
  quote: string | null
  confidence: number | null
  interview_id: string
  interview_date: string | null  // ISO 8601 datetime string (aus mvp_interviews.created_at)
  cluster_id: string | null      // UUID (NULLABLE — unassigned moeglich)
}

export interface QuoteResponse {
  fact_id: string
  content: string        // Originalzitat (fact.quote)
  interview_id: string
  interview_number: number  // 1-basierte Positionsnummer im Projekt (ROW_NUMBER vom Backend)
}

export interface ClusterDetailResponse {
  id: string
  name: string
  summary: string | null
  fact_count: number
  interview_count: number
  facts: FactResponse[]
  quotes: QuoteResponse[]  // Top-Level-Feld: Facts mit quote != null, mit interview_number
}

// --- Taxonomy-Editing Types (Slice 6) ---

export interface RenameRequest {
  name: string
}

export interface MergeRequest {
  source_cluster_id: string
  target_cluster_id: string
}

export interface MergeResponse {
  merged_cluster: ClusterResponse
  undo_id: string
  undo_expires_at: string  // ISO 8601
}

export interface UndoMergeRequest {
  undo_id: string
}

export interface SplitPreviewSubcluster {
  name: string
  fact_count: number
  facts: FactResponse[]
}

export interface SplitPreviewResponse {
  subclusters: SplitPreviewSubcluster[]
}

export interface SplitSubclusterInput {
  name: string
  fact_ids: string[]
}

export interface SplitConfirmRequest {
  subclusters: SplitSubclusterInput[]
}

export interface MoveFactRequest {
  cluster_id: string | null
}

export interface BulkMoveRequest {
  fact_ids: string[]
  target_cluster_id: string | null
}

export interface SuggestionResponse {
  id: string
  type: 'merge' | 'split'
  source_cluster_id: string
  source_cluster_name: string
  target_cluster_id: string | null
  target_cluster_name: string | null
  similarity_score: number | null
  proposed_data: Record<string, unknown> | null
  status: 'pending'
  created_at: string
}

export interface ReclusterStarted {
  status: string
  message: string
}

// --- Interview Assignment Types (Slice 8) ---

export interface InterviewAssignment {
  interview_id: string
  date: string // ISO 8601
  summary_preview: string | null
  fact_count: number
  extraction_status: string
  clustering_status: string
}

export interface AvailableInterview {
  session_id: string
  created_at: string // ISO 8601
  summary_preview: string | null
}
