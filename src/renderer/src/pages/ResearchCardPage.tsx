import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { ResearchCard } from '../../../shared/types'
import type { Route } from '../App'

interface Props {
  cardId: string
  navigate: (route: Route) => void
}

/**
 * 研究卡片结果页面
 * 展示结构化研究卡片，允许用户选择章节和引用，转化为论文项目
 */
export default function ResearchCardPage({ cardId, navigate }: Props): JSX.Element {
  const [card, setCard] = useState<ResearchCard | null>(null)
  const [loading, setLoading] = useState(true)
  const [converting, setConverting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 选择状态
  const [selectedSections, setSelectedSections] = useState<Set<string>>(new Set())
  const [selectedRefs, setSelectedRefs] = useState<Set<number>>(new Set())

  useEffect(() => {
    api.getResearchCard(cardId).then(c => {
      if (c) {
        setCard(c)
        // 默认全选章节和引用
        setSelectedSections(new Set(c.project_importable_sections.map(s => s.section_key)))
        setSelectedRefs(new Set(c.reference_candidates.map((_, i) => i)))
      }
      setLoading(false)
    })
  }, [cardId])

  const toggleSection = (key: string): void => {
    setSelectedSections(prev => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  const toggleRef = (idx: number): void => {
    setSelectedRefs(prev => {
      const next = new Set(prev)
      next.has(idx) ? next.delete(idx) : next.add(idx)
      return next
    })
  }

  const handleConvert = async (): Promise<void> => {
    if (!card) return
    setConverting(true)
    setError(null)

    try {
      const { projectId } = await api.createProjectFromCard({
        cardId: card.id,
        selectedSectionKeys: Array.from(selectedSections),
        selectedReferenceIndices: Array.from(selectedRefs)
      })
      navigate({ page: 'project', projectId })
    } catch (err) {
      setError(err instanceof Error ? err.message : '转化失败，请重试')
      setConverting(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-400 text-sm">
        加载中…
      </div>
    )
  }

  if (!card) {
    return (
      <div className="min-h-screen flex items-center justify-center text-red-500 text-sm">
        研究卡片不存在
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航 */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-4">
        <button
          onClick={() => navigate({ page: 'research-input' })}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          ← 返回
        </button>
        <h1 className="text-base font-semibold text-gray-900">{card.topic_label}</h1>
      </header>

      <div className="max-w-3xl mx-auto px-6 py-8 space-y-6">
        {/* 趋势摘要 */}
        <section className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-2">领域概览</h2>
          <p className="text-sm text-gray-600 leading-relaxed">{card.trend_summary}</p>
          {card.distribution_summary && (
            <p className="text-xs text-gray-400 mt-2">{card.distribution_summary}</p>
          )}
        </section>

        {/* 代表性论文 */}
        {card.key_papers.length > 0 && (
          <section className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">代表性论文</h2>
            <ul className="space-y-2">
              {card.key_papers.map((p, i) => (
                <li key={i} className="text-sm">
                  <span className="text-gray-800 font-medium">{p.title}</span>
                  <span className="text-gray-400 ml-2">
                    {p.authors.slice(0, 2).join(', ')}{p.authors.length > 2 ? ' 等' : ''} ({p.year})
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* 可导入章节（可选择） */}
        {card.project_importable_sections.length > 0 && (
          <section className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-1">导入章节</h2>
            <p className="text-xs text-gray-400 mb-3">选择要导入论文项目的章节</p>
            <div className="space-y-2">
              {card.project_importable_sections.map(s => (
                <label key={s.section_key} className="flex items-start gap-3 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={selectedSections.has(s.section_key)}
                    onChange={() => toggleSection(s.section_key)}
                    className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600"
                  />
                  <div>
                    <div className="text-sm font-medium text-gray-800">{s.heading}</div>
                    <div className="text-xs text-gray-400 mt-0.5 line-clamp-2">{s.content}</div>
                  </div>
                </label>
              ))}
            </div>
          </section>
        )}

        {/* 候选引用（可选择） */}
        {card.reference_candidates.length > 0 && (
          <section className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-1">候选引用</h2>
            <p className="text-xs text-gray-400 mb-3">选择要导入的参考文献</p>
            <div className="space-y-2">
              {card.reference_candidates.map((ref, i) => (
                <label key={i} className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedRefs.has(i)}
                    onChange={() => toggleRef(i)}
                    className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600"
                  />
                  <div className="text-sm">
                    <span className="text-gray-800">{ref.title}</span>
                    <span className="text-gray-400 ml-2">({ref.year})</span>
                  </div>
                </label>
              ))}
            </div>
          </section>
        )}

        {/* 错误提示 */}
        {error && (
          <div className="text-red-600 text-sm bg-red-50 px-4 py-3 rounded-lg border border-red-200">
            {error}
          </div>
        )}

        {/* 转化按钮 */}
        <button
          onClick={handleConvert}
          disabled={converting || selectedSections.size === 0}
          className="w-full py-3 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {converting ? '正在创建论文项目…' : '转化为论文项目 →'}
        </button>
      </div>
    </div>
  )
}