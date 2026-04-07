import { useState } from 'react'
import { api } from '../lib/api'
import { ResearchInputType } from '../../../shared/enums'
import type { Route } from '../App'

interface Props {
  navigate: (route: Route) => void
}

/** 输入类型选项配置 */
const INPUT_TYPE_OPTIONS: { value: ResearchInputType; label: string; placeholder: string }[] = [
  { value: ResearchInputType.Keyword, label: '关键词', placeholder: '例如：transformer architecture, attention mechanism' },
  { value: ResearchInputType.DOI, label: 'DOI', placeholder: '例如：10.1145/3290605.3300702' },
  { value: ResearchInputType.ArxivId, label: 'arXiv ID', placeholder: '例如：2305.10601' },
  { value: ResearchInputType.Title, label: '论文标题', placeholder: '例如：Attention Is All You Need' },
  { value: ResearchInputType.URL, label: '论文链接', placeholder: '例如：https://arxiv.org/abs/1706.03762' }
]

/**
 * 研究输入页面
 * 用户选择输入类型并填写内容，提交后生成研究卡片
 */
export default function ResearchInputPage({ navigate }: Props): JSX.Element {
  const [inputType, setInputType] = useState<ResearchInputType>(ResearchInputType.Keyword)
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selectedOption = INPUT_TYPE_OPTIONS.find(o => o.value === inputType)!

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault()
    if (!inputValue.trim()) return

    setLoading(true)
    setError(null)

    try {
      const { cardId } = await api.submitResearch({
        inputType,
        inputValue: inputValue.trim()
      })
      navigate({ page: 'research-card', cardId })
    } catch (err) {
      setError(err instanceof Error ? err.message : '生成失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-8">
      <div className="w-full max-w-xl">
        {/* 标题区 */}
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-semibold text-gray-900">HSO 论文工作台</h1>
          <p className="mt-2 text-gray-500 text-sm">输入研究起点，生成结构化研究卡片</p>
        </div>

        {/* 输入表单 */}
        <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-5">
          {/* 输入类型选择 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">输入类型</label>
            <div className="flex flex-wrap gap-2">
              {INPUT_TYPE_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setInputType(opt.value)}
                  className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                    inputType === opt.value
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-600 border-gray-200 hover:border-blue-400'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* 输入框 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {selectedOption.label}
            </label>
            <input
              type="text"
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              placeholder={selectedOption.placeholder}
              disabled={loading}
              className="w-full px-4 py-2.5 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            />
          </div>

          {/* 错误提示 */}
          {error && (
            <div className="text-red-600 text-sm bg-red-50 px-4 py-2.5 rounded-lg border border-red-200">
              {error}
            </div>
          )}

          {/* 提交按钮 */}
          <button
            type="submit"
            disabled={loading || !inputValue.trim()}
            className="w-full py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? '正在生成研究卡片…' : '生成研究卡片'}
          </button>
        </form>
      </div>
    </div>
  )
}