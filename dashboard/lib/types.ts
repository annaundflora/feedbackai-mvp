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
