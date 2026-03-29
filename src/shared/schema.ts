import { sqliteTable, text, integer, real } from 'drizzle-orm/sqlite-core'

/**
 * research_card — 研究卡片
 * 由研究输入流程生成，存储结构化研究结果
 * JSON 字段序列化存储，读取时反序列化
 */
export const researchCards = sqliteTable('research_card', {
  id: text('id').primaryKey(),
  input_type: text('input_type').notNull(),
  input_value: text('input_value').notNull(),
  topic_label: text('topic_label').notNull(),
  key_papers: text('key_papers').notNull().default('[]'),           // JSON: KeyPaper[]
  trend_summary: text('trend_summary').notNull().default(''),
  distribution_summary: text('distribution_summary').notNull().default(''),
  project_importable_sections: text('project_importable_sections').notNull().default('[]'), // JSON: ImportableSection[]
  reference_candidates: text('reference_candidates').notNull().default('[]'),               // JSON: ReferenceCandidate[]
  notes: text('notes').notNull().default(''),
  created_at: text('created_at').notNull()
})

/**
 * template — 论文模板
 * v1 固定三个模板，由 seed-templates.ts 在首次启动时写入
 */
export const templates = sqliteTable('template', {
  id: text('id').primaryKey(),
  slug: text('slug').notNull().unique(),
  display_name: text('display_name').notNull(),
  template_version: text('template_version').notNull(),
  supported_section_keys: text('supported_section_keys').notNull().default('[]'), // JSON: string[]
  mapping_rules: text('mapping_rules').notNull().default('{}')                    // JSON: Record<string, string>
})

/**
 * paper_project — 论文项目（核心对象）
 * 关联研究卡片、模板、章节、素材、构建记录
 */
export const paperProjects = sqliteTable('paper_project', {
  id: text('id').primaryKey(),
  source_research_card_id: text('source_research_card_id').references(() => researchCards.id),
  title: text('title').notNull(),
  template_id: text('template_id').references(() => templates.id),
  current_version: integer('current_version').notNull().default(1),
  created_at: text('created_at').notNull(),
  updated_at: text('updated_at').notNull()
})

/**
 * paper_section — 论文章节（有序）
 * order_index 决定章节顺序，section_key 为规范化章节类型
 */
export const paperSections = sqliteTable('paper_section', {
  id: text('id').primaryKey(),
  paper_project_id: text('paper_project_id').notNull().references(() => paperProjects.id, { onDelete: 'cascade' }),
  order_index: integer('order_index').notNull(),
  section_key: text('section_key').notNull(),
  heading: text('heading').notNull(),
  content: text('content').notNull().default(''),
  created_at: text('created_at').notNull(),
  updated_at: text('updated_at').notNull()
})

/**
 * asset — 素材（v1 仅图片）
 * visibility_mode 决定跨项目共享范围
 * selected_project_ids 序列化为 JSON 数组
 */
export const assets = sqliteTable('asset', {
  id: text('id').primaryKey(),
  owner_project_id: text('owner_project_id').notNull().references(() => paperProjects.id),
  name: text('name').notNull(),
  asset_kind: text('asset_kind').notNull().default('image'),
  storage_path: text('storage_path').notNull(),
  visibility_mode: text('visibility_mode').notNull().default('project_only'),
  selected_project_ids: text('selected_project_ids').notNull().default('[]'), // JSON: string[]
  created_at: text('created_at').notNull()
})

/**
 * reference_source — 引用来源
 * 由项目转化流程从研究卡片 reference_candidates 导入
 * authors 序列化为 JSON 数组
 */
export const referenceSources = sqliteTable('reference_source', {
  id: text('id').primaryKey(),
  paper_project_id: text('paper_project_id').notNull().references(() => paperProjects.id, { onDelete: 'cascade' }),
  source_type: text('source_type').notNull(),   // 'doi' | 'arxiv_id' | 'manual'
  source_value: text('source_value').notNull(),
  title: text('title').notNull(),
  authors: text('authors').notNull().default('[]'), // JSON: string[]
  publication_year: integer('publication_year'),
  created_at: text('created_at').notNull()
})

/**
 * build_job — 构建任务
 * status 为 v1 冻结的 4 个状态枚举（不含 canceled）
 * 绑定 project_version 快照，确保构建可追溯
 */
export const buildJobs = sqliteTable('build_job', {
  id: text('id').primaryKey(),
  paper_project_id: text('paper_project_id').notNull().references(() => paperProjects.id),
  project_version: integer('project_version').notNull(),
  status: text('status').notNull().default('queued'), // BuildStatus enum
  requested_at: text('requested_at').notNull(),
  started_at: text('started_at'),
  finished_at: text('finished_at'),
  status_summary: text('status_summary')
})

/**
 * build_artifact — 构建产物
 * 关联 build_job，记录 PDF 和日志文件路径
 */
export const buildArtifacts = sqliteTable('build_artifact', {
  id: text('id').primaryKey(),
  build_job_id: text('build_job_id').notNull().references(() => buildJobs.id, { onDelete: 'cascade' }),
  artifact_kind: text('artifact_kind').notNull(), // 'pdf' | 'log'
  storage_path: text('storage_path').notNull(),
  created_at: text('created_at').notNull()
})

/**
 * error_event — 错误事件
 * 记录各阶段（研究生成、项目创建、构建等）的结构化错误
 * 可脱离 paper_project 或 build_job 独立存在
 */
export const errorEvents = sqliteTable('error_event', {
  id: text('id').primaryKey(),
  paper_project_id: text('paper_project_id').references(() => paperProjects.id),
  build_job_id: text('build_job_id').references(() => buildJobs.id),
  stage: text('stage').notNull(),          // ErrorStage enum
  error_code: text('error_code').notNull(),
  human_summary: text('human_summary').notNull(),
  location_hint: text('location_hint'),    // LaTeX 错误行号等
  suggested_fix: text('suggested_fix'),
  created_at: text('created_at').notNull()
})
