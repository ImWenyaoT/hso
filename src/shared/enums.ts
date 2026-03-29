/** 构建任务状态（v1 冻结：不含 canceled） */
export enum BuildStatus {
  Queued = 'queued',
  Running = 'running',
  Succeeded = 'succeeded',
  Failed = 'failed'
}

/** 素材可见性模式 */
export enum AssetVisibility {
  ProjectOnly = 'project_only',
  SelectedProjects = 'selected_projects',
  AllProjects = 'all_projects'
}

/** 研究输入类型（v1 冻结 5 种） */
export enum ResearchInputType {
  Keyword = 'keyword',
  DOI = 'doi',
  ArxivId = 'arxiv_id',
  Title = 'title',
  URL = 'url'
}

/** 错误事件所在阶段 */
export enum ErrorStage {
  ResearchGeneration = 'research_generation',
  ProjectConversion = 'project_conversion',
  AssetUpload = 'asset_upload',
  BuildExecution = 'build_execution'
}
