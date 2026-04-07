import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { PaperProject, Template, BuildJob } from '../../../shared/types'
import { BuildStatus } from '../../../shared/enums'
import type { Route } from '../App'

interface Props {
  projectId: string
  navigate: (route: Route) => void
}

type ActiveTab = 'structure' | 'template' | 'assets' | 'build'

/**
 * 论文项目主工作页
 * 包含四个内部区域：结构、模板、素材、构建
 */
export default function ProjectPage({ projectId, navigate }: Props): JSX.Element {
  const [project, setProject] = useState<PaperProject | null>(null)
  const [templates, setTemplates] = useState<Template[]>([])
  const [builds, setBuilds] = useState<BuildJob[]>([])
  const [activeTab, setActiveTab] = useState<ActiveTab>('structure')
  const [loading, setLoading] = useState(true)
  const [buildError, setBuildError] = useState<string | null>(null)

  const loadProject = async (): Promise<void> => {
    const [proj, tmpls, blds] = await Promise.all([
      api.getProject(projectId),
      api.listTemplates(),
      api.listBuilds(projectId)
    ])
    setProject(proj)
    setTemplates(tmpls)
    setBuilds(blds)
    setLoading(false)
  }

  useEffect(() => { loadProject() }, [projectId])

  const handleSelectTemplate = async (templateId: string): Promise<void> => {
    await api.setTemplate(projectId, templateId)
    loadProject()
  }

  const handleTriggerBuild = async (): Promise<void> => {
    setBuildError(null)
    try {
      await api.triggerBuild({ projectId })
      loadProject()
    } catch (err) {
      setBuildError(err instanceof Error ? err.message : '构建触发失败')
    }
  }

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-gray-400 text-sm">加载中…</div>
  }

  if (!project) {
    return <div className="min-h-screen flex items-center justify-center text-red-500 text-sm">项目不存在</div>
  }

  const selectedTemplate = templates.find((t): boolean => t.id === project.template_id)

  const tabs: { key: ActiveTab; label: string }[] = [
    { key: 'structure', label: '章节结构' },
    { key: 'template', label: '模板' },
    { key: 'assets', label: '素材' },
    { key: 'build', label: '构建' }
  ]

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* 顶部导航 */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-4">
        <button
          onClick={() => navigate({ page: 'research-input' })}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          ← 首页
        </button>
        <h1 className="text-base font-semibold text-gray-900 flex-1 truncate">{project.title}</h1>
        <span className="text-xs text-gray-400">v{project.current_version}</span>
      </header>

      {/* Tab 切换 */}
      <nav className="bg-white border-b border-gray-200 px-6 flex gap-1">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`px-4 py-3 text-sm border-b-2 transition-colors ${
              activeTab === t.key
                ? 'border-blue-600 text-blue-600 font-medium'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {/* 内容区 */}
      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-6">
        {/* ── 章节结构 ── */}
        {activeTab === 'structure' && (
          <StructureSection project={project} onRefresh={loadProject} />
        )}

        {/* ── 模板选择 ── */}
        {activeTab === 'template' && (
          <TemplateSection
            templates={templates}
            selectedTemplateId={project.template_id ?? null}
            onSelect={handleSelectTemplate}
          />
        )}

        {/* ── 素材 ── */}
        {activeTab === 'assets' && (
          <div className="text-center text-gray-400 text-sm py-16">
            素材管理功能即将推出
          </div>
        )}

        {/* ── 构建 ── */}
        {activeTab === 'build' && (
          <BuildSection
            builds={builds}
            selectedTemplate={selectedTemplate ?? null}
            onTrigger={handleTriggerBuild}
            error={buildError}
          />
        )}
      </main>
    </div>
  )
}

// ── 子组件 ──────────────────────────────────────────────

interface StructureSectionProps {
  project: PaperProject
  onRefresh: () => void
}

/** 章节结构区域 */
function StructureSection({ project }: StructureSectionProps): JSX.Element {
  const sections = project.sections ?? []

  if (sections.length === 0) {
    return (
      <div className="text-center text-gray-400 text-sm py-16">
        暂无章节，请从研究卡片导入或手动添加
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {sections.map(s => (
        <div key={s.id} className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-gray-800">{s.heading}</h3>
            <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded">{s.section_key}</span>
          </div>
          <p className="text-xs text-gray-500 leading-relaxed line-clamp-3">
            {s.content || '（暂无内容）'}
          </p>
        </div>
      ))}
    </div>
  )
}

interface TemplateSectionProps {
  templates: Template[]
  selectedTemplateId: string | null
  onSelect: (id: string) => void
}

/** 模板选择区域 */
function TemplateSection({ templates, selectedTemplateId, onSelect }: TemplateSectionProps): JSX.Element {
  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-500">选择论文模板，决定 LaTeX 构建样式</p>
      {templates.map(t => (
        <button
          key={t.id}
          onClick={() => onSelect(t.id)}
          className={`w-full text-left p-4 rounded-xl border transition-colors ${
            selectedTemplateId === t.id
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-200 bg-white hover:border-blue-300'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-800">{t.display_name}</span>
            {selectedTemplateId === t.id && (
              <span className="text-xs text-blue-600 font-medium">已选择</span>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-1">v{t.template_version}</p>
        </button>
      ))}
    </div>
  )
}

interface BuildSectionProps {
  builds: BuildJob[]
  selectedTemplate: Template | null
  onTrigger: () => void
  error: string | null
}

/** 构建状态区域 */
function BuildSection({ builds, selectedTemplate, onTrigger, error }: BuildSectionProps): JSX.Element {
  const latestBuild = builds[0]

  const statusLabel: Record<string, string> = {
    queued: '队列中',
    running: '构建中',
    succeeded: '成功',
    failed: '失败'
  }

  const statusColor: Record<string, string> = {
    queued: 'text-yellow-600 bg-yellow-50',
    running: 'text-blue-600 bg-blue-50',
    succeeded: 'text-green-600 bg-green-50',
    failed: 'text-red-600 bg-red-50'
  }

  return (
    <div className="space-y-4">
      {/* 触发按钮 */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        {!selectedTemplate ? (
          <p className="text-sm text-amber-600">请先在「模板」标签选择模板后再触发构建</p>
        ) : (
          <>
            <p className="text-sm text-gray-600 mb-3">
              当前模板：<span className="font-medium text-gray-800">{selectedTemplate.display_name}</span>
            </p>
            <button
              onClick={onTrigger}
              disabled={latestBuild?.status === BuildStatus.Running || latestBuild?.status === BuildStatus.Queued}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {latestBuild?.status === BuildStatus.Running ? '构建中…' :
               latestBuild?.status === BuildStatus.Queued ? '排队中…' : '触发构建'}
            </button>
          </>
        )}
        {error && (
          <p className="text-red-600 text-sm mt-3">{error}</p>
        )}
      </div>

      {/* 构建历史 */}
      {builds.length === 0 ? (
        <div className="text-center text-gray-400 text-sm py-8">暂无构建记录</div>
      ) : (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-gray-700">构建历史</h3>
          {builds.map(b => (
            <div key={b.id} className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">v{b.project_version} · {b.requested_at.slice(0, 16).replace('T', ' ')}</span>
                <span className={`text-xs px-2 py-0.5 rounded font-medium ${statusColor[b.status]}`}>
                  {statusLabel[b.status] ?? b.status}
                </span>
              </div>
              {b.status_summary && (
                <p className="text-xs text-gray-500 mt-2">{b.status_summary}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}