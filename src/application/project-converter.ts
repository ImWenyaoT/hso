import { getDb } from '../main/db'
import { paperProjects, paperSections, referenceSources } from '../shared/schema'
import { newId, now } from './id'
import type { CreateProjectFromCard } from '../shared/types'

/**
 * 从研究卡片创建论文项目
 *
 * 转化规则（来自 project_conversion_flow.md）：
 * - 只导入 project_importable_sections 中用户选择的章节
 * - 只导入用户选择的 reference_candidates
 * - 不导入 notes、trend_summary、distribution_summary、检索轨迹
 * - 初始状态：template_id=null, current_version=1
 *
 * @throws 创建失败时抛出错误，调用方负责记录 error_event
 */
export async function convertCardToProject(payload: CreateProjectFromCard) {
  const db = getDb()

  // 读取研究卡片
  const card = await db.query.researchCards.findFirst({
    where: (t, { eq }) => eq(t.id, payload.cardId)
  })
  if (!card) throw new Error(`研究卡片不存在：${payload.cardId}`)

  const importableSections: Array<{ section_key: string; heading: string; content: string }> =
    JSON.parse(card.project_importable_sections)
  const referenceCandidates: Array<{
    title: string; authors: string[]; year: number; doi?: string; arxiv_id?: string
  }> = JSON.parse(card.reference_candidates)

  // 确定项目标题：优先用户覆盖，其次用第一个可导入章节的主题
  const title = payload.titleOverride?.trim() ||
    `${card.topic_label} — 论文草稿`

  const projectId = newId()
  const timestamp = now()

  // 在事务中创建项目 + 章节 + 引用来源
  await db.transaction(async (tx) => {
    // 1. 插入论文项目
    await tx.insert(paperProjects).values({
      id: projectId,
      source_research_card_id: card.id,
      title,
      template_id: null,
      current_version: 1,
      created_at: timestamp,
      updated_at: timestamp
    })

    // 2. 插入选定章节（保持顺序）
    const selectedSections = importableSections.filter(s =>
      payload.selectedSectionKeys.includes(s.section_key)
    )

    for (let i = 0; i < selectedSections.length; i++) {
      const s = selectedSections[i]
      await tx.insert(paperSections).values({
        id: newId(),
        paper_project_id: projectId,
        order_index: i,
        section_key: s.section_key,
        heading: s.heading,
        content: s.content,
        created_at: timestamp,
        updated_at: timestamp
      })
    }

    // 3. 插入选定引用来源
    const selectedRefs = payload.selectedReferenceIndices
      .map(idx => referenceCandidates[idx])
      .filter(Boolean)

    for (const ref of selectedRefs) {
      await tx.insert(referenceSources).values({
        id: newId(),
        paper_project_id: projectId,
        source_type: ref.doi ? 'doi' : ref.arxiv_id ? 'arxiv_id' : 'manual',
        source_value: ref.doi || ref.arxiv_id || ref.title,
        title: ref.title,
        authors: JSON.stringify(ref.authors),
        publication_year: ref.year,
        created_at: timestamp
      })
    }
  })

  return { projectId }
}
