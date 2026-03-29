/**
 * 所有 IPC channel 名称常量
 * 渲染进程与主进程通过这些字符串通信，集中维护防止拼写错误
 */
export const IPC = {
  // ── 研究输入 ────────────────────────────────────
  /** 提交研究输入 → 触发 Agent → 返回 research_card */
  RESEARCH_SUBMIT: 'research:submit-input',
  /** 读取研究卡片详情 */
  RESEARCH_GET_CARD: 'research:get-card',

  // ── 论文项目 ────────────────────────────────────
  /** 从研究卡片创建论文项目 */
  PROJECT_CREATE_FROM_CARD: 'project:create-from-card',
  /** 读取项目详情 */
  PROJECT_GET: 'project:get',
  /** 列出所有项目 */
  PROJECT_LIST: 'project:list',
  /** 更新章节内容 */
  PROJECT_UPDATE_SECTION: 'project:update-section',
  /** 为项目选择模板 */
  PROJECT_SET_TEMPLATE: 'project:set-template',

  // ── 模板 ────────────────────────────────────────
  /** 列出所有可用模板 */
  TEMPLATE_LIST: 'template:list',

  // ── 构建 ────────────────────────────────────────
  /** 触发构建 */
  BUILD_TRIGGER: 'build:trigger',
  /** 查询构建状态 */
  BUILD_GET_STATUS: 'build:get-status',
  /** 列出项目的构建历史 */
  BUILD_LIST: 'build:list'
} as const

export type IpcChannel = (typeof IPC)[keyof typeof IPC]
