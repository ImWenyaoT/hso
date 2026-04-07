import { IPC } from '../../../shared/ipc-channels'
import type {
  ResearchCard,
  PaperProject,
  Template,
  BuildJob,
  SubmitResearchInput,
  CreateProjectFromCard,
  UpdateSectionPayload,
  TriggerBuildPayload
} from '../../../shared/types'

/**
 * 渲染进程 API 封装
 * 通过 window.api.invoke 调用主进程 IPC handler
 * 所有方法均为类型安全封装
 */
const invoke = <T>(channel: string, ...args: unknown[]): Promise<T> =>
  (window.api.invoke(channel, ...args) as Promise<T>)

export const api = {
  // ── 研究输入 ──────────────────────────────
  /** 提交研究输入，返回生成的卡片 ID */
  submitResearch: (payload: SubmitResearchInput): Promise<{ cardId: string }> =>
    invoke<{ cardId: string }>(IPC.RESEARCH_SUBMIT, payload),

  /** 读取研究卡片详情 */
  getResearchCard: (cardId: string): Promise<ResearchCard | null> =>
    invoke<ResearchCard | null>(IPC.RESEARCH_GET_CARD, cardId),

  // ── 论文项目 ──────────────────────────────
  /** 从研究卡片创建论文项目 */
  createProjectFromCard: (payload: CreateProjectFromCard): Promise<{ projectId: string }> =>
    invoke<{ projectId: string }>(IPC.PROJECT_CREATE_FROM_CARD, payload),

  /** 读取项目详情（含章节和引用来源） */
  getProject: (projectId: string): Promise<PaperProject | null> =>
    invoke<PaperProject | null>(IPC.PROJECT_GET, projectId),

  /** 列出所有项目 */
  listProjects: (): Promise<PaperProject[]> =>
    invoke<PaperProject[]>(IPC.PROJECT_LIST),

  /** 更新章节内容 */
  updateSection: (payload: UpdateSectionPayload): Promise<{ ok: boolean }> =>
    invoke<{ ok: boolean }>(IPC.PROJECT_UPDATE_SECTION, payload),

  /** 为项目选择模板 */
  setTemplate: (projectId: string, templateId: string): Promise<{ ok: boolean }> =>
    invoke<{ ok: boolean }>(IPC.PROJECT_SET_TEMPLATE, { projectId, templateId }),

  // ── 模板 ──────────────────────────────────
  /** 列出所有可用模板 */
  listTemplates: (): Promise<Template[]> =>
    invoke<Template[]>(IPC.TEMPLATE_LIST),

  // ── 构建 ──────────────────────────────────
  /** 触发构建，返回 jobId */
  triggerBuild: (payload: TriggerBuildPayload): Promise<{ jobId: string }> =>
    invoke<{ jobId: string }>(IPC.BUILD_TRIGGER, payload),

  /** 查询构建状态 */
  getBuildStatus: (jobId: string): Promise<BuildJob | null> =>
    invoke<BuildJob | null>(IPC.BUILD_GET_STATUS, jobId),

  /** 列出项目构建历史 */
  listBuilds: (projectId: string): Promise<BuildJob[]> =>
    invoke<BuildJob[]>(IPC.BUILD_LIST, projectId)
}