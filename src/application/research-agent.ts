import { generateObject } from 'ai'
import { createAnthropic } from '@ai-sdk/anthropic'
import { z } from 'zod'
import { ResearchInputType } from '../shared/enums'

/** Zod schema — 定义 research_card 的结构化输出契约 */
const ResearchCardSchema = z.object({
  topic_label: z.string().describe('简洁的研究主题标签，5-15个字'),
  key_papers: z.array(z.object({
    title: z.string(),
    authors: z.array(z.string()),
    year: z.number(),
    doi: z.string().optional(),
    arxiv_id: z.string().optional(),
    abstract_summary: z.string().optional()
  })).describe('3-8 篇代表性论文，客观事实，不做学术判断'),
  trend_summary: z.string().describe('领域趋势概述，100-200字，客观描述，不推荐研究方向'),
  distribution_summary: z.string().describe('研究分布概述（子领域、方法、期刊分布），50-100字'),
  project_importable_sections: z.array(z.object({
    section_key: z.string().describe('规范章节类型：introduction/related_work/method/results/conclusion'),
    heading: z.string().describe('章节显示标题'),
    content: z.string().describe('基于检索结果生成的初稿内容，可直接导入论文项目')
  })).describe('可导入论文项目的结构化章节，仅包含客观事实内容'),
  reference_candidates: z.array(z.object({
    title: z.string(),
    authors: z.array(z.string()),
    year: z.number(),
    doi: z.string().optional(),
    arxiv_id: z.string().optional()
  })).describe('候选参考文献列表，从 key_papers 提取'),
  notes: z.string().describe('补充说明，不可导入项目，仅供参考')
})

/**
 * 根据研究输入类型构建 prompt
 */
function buildPrompt(inputType: ResearchInputType, inputValue: string): string {
  const typeLabel: Record<ResearchInputType, string> = {
    [ResearchInputType.Keyword]: '关键词',
    [ResearchInputType.DOI]: 'DOI',
    [ResearchInputType.ArxivId]: 'arXiv ID',
    [ResearchInputType.Title]: '论文标题',
    [ResearchInputType.URL]: '论文链接'
  }

  return `你是一个学术信息检索助手。根据用户提供的研究输入，生成一份结构化研究卡片。

输入类型：${typeLabel[inputType]}
输入值：${inputValue}

要求：
1. 内容必须客观，基于已知学术事实，不做主观学术判断
2. key_papers 只列举真实存在的论文（你知道的），如果不确定则不列举
3. project_importable_sections 提供可以直接作为论文初稿的内容
4. 如果是 DOI 或 arXiv ID，优先提取该论文自身信息作为核心参考
5. notes 可包含检索建议，但不能导入项目`
}

/**
 * 调用 AI 生成结构化研究卡片
 * 使用 Vercel AI SDK generateObject + Zod schema 确保输出结构化
 *
 * @param inputType 研究输入类型
 * @param inputValue 输入值
 * @returns 结构化研究卡片数据（不含 id、created_at，由调用方补充）
 */
export async function generateResearchCard(
  inputType: ResearchInputType,
  inputValue: string
) {
  const apiKey = process.env.ANTHROPIC_API_KEY
  if (!apiKey) {
    throw new Error('ANTHROPIC_API_KEY 未配置。请在应用设置中添加 API Key。')
  }

  const anthropic = createAnthropic({ apiKey })

  const { object } = await generateObject({
    model: anthropic('claude-haiku-4-5-20251001'),
    schema: ResearchCardSchema,
    prompt: buildPrompt(inputType, inputValue)
  })

  return object
}
