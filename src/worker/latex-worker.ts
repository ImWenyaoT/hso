/**
 * LaTeX Worker 进程
 * 独立的 Node.js 进程，由主进程通过 worker-bridge.ts 启动
 *
 * 职责（严格限定）：
 * - 接收构建输入包（job ID、项目快照、模板、产物输出路径）
 * - 检测 latexmk 工具链
 * - 执行 latexmk + xelatex + BibTeX
 * - 返回结构化构建结果（状态、产物路径、日志摘要、错误位置）
 *
 * 绝对不做：
 * - 用户编排
 * - 项目创建逻辑
 * - UI 状态管理
 * - 学术推理
 * - 任意项目变更
 */

import { execFile } from 'child_process'
import { promisify } from 'util'
import { existsSync } from 'fs'
import { join } from 'path'

const execFileAsync = promisify(execFile)

export interface BuildInput {
  jobId: string
  projectId: string
  projectVersion: number
  templateSlug: string
  /** LaTeX 主文件的绝对路径 */
  mainTexPath: string
  /** 构建产物输出目录 */
  outputDir: string
}

export interface BuildOutput {
  jobId: string
  success: boolean
  pdfPath?: string
  logPath?: string
  /** 人类可读错误摘要 */
  errorSummary?: string
  /** 错误行号提示（来自 LaTeX 日志解析） */
  locationHint?: string
  /** 修复建议 */
  suggestedFix?: string
  /** 耗时（ms） */
  durationMs: number
}

/**
 * 检测 latexmk 是否可用
 * 返回 latexmk 路径或 null
 */
export async function detectLatexmk(): Promise<string | null> {
  try {
    const { stdout } = await execFileAsync('which', ['latexmk'])
    const path = stdout.trim()
    return path || null
  } catch {
    return null
  }
}

/**
 * 执行 LaTeX 构建
 * 使用 latexmk + xelatex + BibTeX
 *
 * @param input 构建输入包
 * @returns 构建结果（含产物路径和错误信息）
 */
export async function runBuild(input: BuildInput): Promise<BuildOutput> {
  const startTime = Date.now()

  const latexmk = await detectLatexmk()
  if (!latexmk) {
    return {
      jobId: input.jobId,
      success: false,
      errorSummary: '未检测到 latexmk。请通过应用设置安装受控 LaTeX 工具链。',
      suggestedFix: '打开设置 → LaTeX 工具链 → 安装向导',
      durationMs: Date.now() - startTime
    }
  }

  if (!existsSync(input.mainTexPath)) {
    return {
      jobId: input.jobId,
      success: false,
      errorSummary: `主 LaTeX 文件不存在：${input.mainTexPath}`,
      durationMs: Date.now() - startTime
    }
  }

  try {
    const { stderr } = await execFileAsync(latexmk, [
      '-xelatex',
      '-bibtex',
      '-interaction=nonstopmode',
      `-output-directory=${input.outputDir}`,
      input.mainTexPath
    ], { timeout: 120_000 }) // 最多 2 分钟

    const pdfName = input.mainTexPath.replace(/\.tex$/, '.pdf').split('/').pop()!
    const pdfPath = join(input.outputDir, pdfName)
    const logPath = join(input.outputDir, pdfName.replace('.pdf', '.log'))

    if (existsSync(pdfPath)) {
      return {
        jobId: input.jobId,
        success: true,
        pdfPath,
        logPath: existsSync(logPath) ? logPath : undefined,
        durationMs: Date.now() - startTime
      }
    }

    // PDF 未生成，解析 stderr 找错误位置
    const { errorSummary, locationHint, suggestedFix } = parseLatexError(stderr)
    return {
      jobId: input.jobId,
      success: false,
      logPath: existsSync(logPath) ? logPath : undefined,
      errorSummary,
      locationHint,
      suggestedFix,
      durationMs: Date.now() - startTime
    }
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err)
    return {
      jobId: input.jobId,
      success: false,
      errorSummary: `构建进程异常退出：${message}`,
      durationMs: Date.now() - startTime
    }
  }
}

/**
 * 解析 LaTeX 错误日志，提取可读摘要和行号提示
 */
function parseLatexError(stderr: string): {
  errorSummary: string
  locationHint?: string
  suggestedFix?: string
} {
  const lines = stderr.split('\n')

  // 查找 ! 开头的 LaTeX 错误行
  const errorLine = lines.find(l => l.startsWith('!'))
  if (errorLine) {
    // 查找行号提示 (l.xxx)
    const lineMatch = stderr.match(/l\.(\d+)/)
    const locationHint = lineMatch ? `行 ${lineMatch[1]}` : undefined

    // 常见错误的修复建议
    let suggestedFix: string | undefined
    if (errorLine.includes('Undefined control sequence')) {
      suggestedFix = '检查拼写错误的 LaTeX 命令，或确认所需宏包已在模板中引入'
    } else if (errorLine.includes('Missing $ inserted')) {
      suggestedFix = '数学符号需要用 $ ... $ 包裹'
    } else if (errorLine.includes('File not found')) {
      suggestedFix = '检查图片或文件路径是否正确，确认文件已上传到素材库'
    }

    return {
      errorSummary: errorLine.replace(/^!\s*/, ''),
      locationHint,
      suggestedFix
    }
  }

  return {
    errorSummary: '构建失败，未找到明确错误信息。请查看完整日志。'
  }
}
