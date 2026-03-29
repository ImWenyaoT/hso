import { BuildStatus, AssetVisibility, ResearchInputType, ErrorStage } from './enums'

// ── 研究卡片 ──────────────────────────────────────────

export interface KeyPaper {
  title: string
  authors: string[]
  year: number
  doi?: string
  arxiv_id?: string
  abstract_summary?: string
}

export interface ImportableSection {
  section_key: string
  heading: string
  content: string
}

export interface ReferenceCandidate {
  title: string
  authors: string[]
  year: number
  doi?: string
  arxiv_id?: string
}

export interface ResearchCard {
  id: string
  input_type: ResearchInputType
  input_value: string
  topic_label: string
  key_papers: KeyPaper[]
  trend_summary: string
  distribution_summary: string
  project_importable_sections: ImportableSection[]
  reference_candidates: ReferenceCandidate[]
  notes: string
  created_at: string
}

// ── 论文项目 ──────────────────────────────────────────

export interface PaperSection {
  id: string
  paper_project_id: string
  order_index: number
  section_key: string
  heading: string
  content: string
  created_at: string
  updated_at: string
}

export interface ReferenceSource {
  id: string
  paper_project_id: string
  source_type: string
  source_value: string
  title: string
  authors: string[]
  publication_year?: number
  created_at: string
}

export interface PaperProject {
  id: string
  source_research_card_id?: string
  title: string
  template_id?: string
  current_version: number
  created_at: string
  updated_at: string
  sections?: PaperSection[]
  references?: ReferenceSource[]
}

// ── 模板 ────────────────────────────────────────────

export interface Template {
  id: string
  slug: string
  display_name: string
  template_version: string
  supported_section_keys: string[]
  mapping_rules: Record<string, string>
}

// ── 构建 ────────────────────────────────────────────

export interface BuildJob {
  id: string
  paper_project_id: string
  project_version: number
  status: BuildStatus
  requested_at: string
  started_at?: string
  finished_at?: string
  status_summary?: string
}

export interface BuildArtifact {
  id: string
  build_job_id: string
  artifact_kind: 'pdf' | 'log'
  storage_path: string
  created_at: string
}

// ── 错误事件 ─────────────────────────────────────────

export interface ErrorEvent {
  id: string
  paper_project_id?: string
  build_job_id?: string
  stage: ErrorStage
  error_code: string
  human_summary: string
  location_hint?: string
  suggested_fix?: string
  created_at: string
}

// ── 素材 ────────────────────────────────────────────

export interface Asset {
  id: string
  owner_project_id: string
  name: string
  asset_kind: 'image'
  storage_path: string
  visibility_mode: AssetVisibility
  selected_project_ids: string[]
  created_at: string
}

// ── IPC 请求/响应 DTO ────────────────────────────────

export interface SubmitResearchInput {
  inputType: ResearchInputType
  inputValue: string
}

export interface CreateProjectFromCard {
  cardId: string
  selectedSectionKeys: string[]
  selectedReferenceIndices: number[]
  titleOverride?: string
}

export interface UpdateSectionPayload {
  sectionId: string
  content: string
  heading?: string
}

export interface TriggerBuildPayload {
  projectId: string
}
