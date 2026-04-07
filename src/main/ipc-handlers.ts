import { ipcMain } from 'electron'
import { eq, desc } from 'drizzle-orm'
import { getDb } from './db'
import {
  researchCards, paperProjects, paperSections,
  referenceSources, buildJobs, buildArtifacts, templates
} from '../shared/schema'
import { IPC } from '../shared/ipc-channels'
import { generateResearchCard } from '../application/research-agent'
import { convertCardToProject } from '../application/project-converter'
import { newId, now } from '../application/id'
import type {
  SubmitResearchInput,
  CreateProjectFromCard,
  UpdateSectionPayload,
  TriggerBuildPayload
} from '../shared/types'

/**
 * 注册所有 IPC handlers
 * 在 app.whenReady() 后、创建窗口前调用
 */
export function registerIpcHandlers(): void {
  // ── 研究输入 ────────────────────────────────────

  /**
   * research:submit-input
   * 接受输入类型和值，调用 AI Agent 生成研究卡片，写入 DB
   */
  ipcMain.handle(IPC.RESEARCH_SUBMIT, async (_event, payload: SubmitResearchInput) => {
    const db = getDb()
    const cardData = await generateResearchCard(payload.inputType, payload.inputValue)

    const cardId = newId()
    await db.insert(researchCards).values({
      id: cardId,
      input_type: payload.inputType,
      input_value: payload.inputValue,
      topic_label: cardData.topic_label,
      key_papers: JSON.stringify(cardData.key_papers),
      trend_summary: cardData.trend_summary,
      distribution_summary: cardData.distribution_summary,
      project_importable_sections: JSON.stringify(cardData.project_importable_sections),
      reference_candidates: JSON.stringify(cardData.reference_candidates),
      notes: cardData.notes,
      created_at: now()
    })

    return { cardId }
  })

  /**
   * research:get-card
   * 读取研究卡片，JSON 字段反序列化后返回
   */
  ipcMain.handle(IPC.RESEARCH_GET_CARD, async (_event, cardId: string) => {
    const db = getDb()
    const card = await db.query.researchCards.findFirst({
      where: (t, { eq }) => eq(t.id, cardId)
    })
    if (!card) return null

    return {
      ...card,
      key_papers: JSON.parse(card.key_papers),
      project_importable_sections: JSON.parse(card.project_importable_sections),
      reference_candidates: JSON.parse(card.reference_candidates)
    }
  })

  // ── 论文项目 ────────────────────────────────────

  /**
   * project:create-from-card
   * 调用 project-converter 创建论文项目
   */
  ipcMain.handle(IPC.PROJECT_CREATE_FROM_CARD, async (_event, payload: CreateProjectFromCard) => {
    return convertCardToProject(payload)
  })

  /**
   * project:get
   * 读取项目完整详情（含章节和引用来源）
   */
  ipcMain.handle(IPC.PROJECT_GET, async (_event, projectId: string) => {
    const db = getDb()

    const project = await db.query.paperProjects.findFirst({
      where: (t, { eq }) => eq(t.id, projectId)
    })
    if (!project) return null

    const sections = await db.select()
      .from(paperSections)
      .where(eq(paperSections.paper_project_id, projectId))
      .orderBy(paperSections.order_index)

    const refs = await db.select()
      .from(referenceSources)
      .where(eq(referenceSources.paper_project_id, projectId))

    return {
      ...project,
      sections: sections.map(s => ({ ...s })),
      references: refs.map(r => ({
        ...r,
        authors: JSON.parse(r.authors)
      }))
    }
  })

  /**
   * project:list
   * 返回所有项目列表（按创建时间倒序）
   */
  ipcMain.handle(IPC.PROJECT_LIST, async () => {
    const db = getDb()
    return db.select().from(paperProjects).orderBy(desc(paperProjects.created_at))
  })

  /**
   * project:update-section
   * 更新章节内容，同时递增项目版本号
   */
  ipcMain.handle(IPC.PROJECT_UPDATE_SECTION, async (_event, payload: UpdateSectionPayload) => {
    const db = getDb()
    const timestamp = now()

    // 更新章节内容
    await db.update(paperSections)
      .set({
        content: payload.content,
        heading: payload.heading ?? undefined,
        updated_at: timestamp
      })
      .where(eq(paperSections.id, payload.sectionId))

    // 读取章节关联的项目 ID，递增版本号
    const section = await db.query.paperSections.findFirst({
      where: (t, { eq }) => eq(t.id, payload.sectionId)
    })

    if (section) {
      await db.update(paperProjects)
        .set({ updated_at: timestamp })
        .where(eq(paperProjects.id, section.paper_project_id))
    }

    return { ok: true }
  })

  /**
   * project:set-template
   * 为项目选择模板
   */
  ipcMain.handle(IPC.PROJECT_SET_TEMPLATE, async (_event, { projectId, templateId }: { projectId: string; templateId: string }) => {
    const db = getDb()
    await db.update(paperProjects)
      .set({ template_id: templateId, updated_at: now() })
      .where(eq(paperProjects.id, projectId))
    return { ok: true }
  })

  // ── 模板 ────────────────────────────────────────

  /**
   * template:list
   * 返回所有可用模板
   */
  ipcMain.handle(IPC.TEMPLATE_LIST, async () => {
    const db = getDb()
    const rows = await db.select().from(templates)
    return rows.map(t => ({
      ...t,
      supported_section_keys: JSON.parse(t.supported_section_keys),
      mapping_rules: JSON.parse(t.mapping_rules)
    }))
  })

  // ── 构建 ────────────────────────────────────────

  /**
   * build:trigger
   * 创建构建任务记录（status: queued），触发 Worker
   */
  ipcMain.handle(IPC.BUILD_TRIGGER, async (_event, payload: TriggerBuildPayload) => {
    const db = getDb()

    const project = await db.query.paperProjects.findFirst({
      where: (t, { eq }) => eq(t.id, payload.projectId)
    })
    if (!project) throw new Error(`项目不存在：${payload.projectId}`)
    if (!project.template_id) throw new Error('请先选择模板后再触发构建')

    const jobId = newId()
    await db.insert(buildJobs).values({
      id: jobId,
      paper_project_id: payload.projectId,
      project_version: project.current_version,
      status: 'queued',
      requested_at: now()
    })

    // TODO（阶段7）：通过 worker-bridge 通知 LaTeX Worker 开始构建
    // workerBridge.triggerBuild(jobId, payload.projectId)

    return { jobId }
  })

  /**
   * build:get-status
   * 查询单个构建任务状态
   */
  ipcMain.handle(IPC.BUILD_GET_STATUS, async (_event, jobId: string) => {
    const db = getDb()

    const job = await db.query.buildJobs.findFirst({
      where: (t, { eq }) => eq(t.id, jobId)
    })
    if (!job) return null

    const artifacts = await db.select()
      .from(buildArtifacts)
      .where(eq(buildArtifacts.build_job_id, jobId))

    return { ...job, artifacts }
  })

  /**
   * build:list
   * 列出项目的构建历史（最新在前）
   */
  ipcMain.handle(IPC.BUILD_LIST, async (_event, projectId: string) => {
    const db = getDb()
    return db.select()
      .from(buildJobs)
      .where(eq(buildJobs.paper_project_id, projectId))
      .orderBy(desc(buildJobs.requested_at))
  })
}