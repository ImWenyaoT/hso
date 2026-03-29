# HSO 编码实施进度

> **当前阶段：编码实施**。规格阶段已完成并归档至 `architecture.md` 和 `progress.md`。本文件追踪编码任务。

---

## 决策冻结（不得重新讨论）

1. 研究卡片生成使用 **Vercel AI SDK `generateObject`**，模型 `claude-haiku-4-5-20251001`
2. 支持的研究输入类型：**关键词、DOI、arXiv ID、论文标题、论文 URL**（共 5 种）
3. 研究卡片可导入项目的内容：`project_importable_sections`、标题候选、`reference_candidates`，其余不导入
4. 论文项目使用**有序章节模型**，不是自由格式编辑器
5. 模板为**预定义包**（generic-article, ieee, elsevier），不允许用户上传自定义模板
6. 构建状态：`queued / running / succeeded / failed`（v1 不支持取消）
7. 构建工具链：`latexmk + xelatex + BibTeX`
8. 资产可见性：`project_only / selected_projects / all_projects`
9. 本地存储：项目元数据在 `.hso/`，全局 DB/资产/工具链在 `app.getPath('userData')`
10. **TypeScript** 为主语言；**Python** 仅辅助脚本

---

## 编码进度

### 阶段 1：脚手架 ✅

**文件：** `package.json`, `electron.vite.config.ts`, `tsconfig*.json`, `tailwind.config.js`, `postcss.config.js`

- [x] electron-vite 项目结构（main + preload + renderer）
- [x] React 18 + TypeScript + Tailwind CSS
- [x] 目录结构对齐：`src/main/`, `src/renderer/`, `src/application/`, `src/worker/`, `src/shared/`
- [x] `npm run dev` 可启动，`npm run build` 无报错

---

### 阶段 2：数据库 Schema ✅

**文件：** `src/shared/schema.ts`, `src/main/db.ts`, `src/main/seed-templates.ts`

- [x] Drizzle SQLite 表定义（9 个实体）
- [x] `initDb()` 幂等建表（`CREATE TABLE IF NOT EXISTS`）
- [x] WAL 模式 + foreign keys pragma
- [x] 3 个模板 fixture 幂等写入（首次启动时执行）

---

### 阶段 3：IPC 契约 ✅

**文件：** `src/shared/enums.ts`, `src/shared/ipc-channels.ts`, `src/shared/types.ts`, `src/preload/index.ts`, `src/main/ipc-handlers.ts`, `src/renderer/src/lib/api.ts`

- [x] `BuildStatus`, `AssetVisibility`, `ResearchInputType`, `ErrorStage` 枚举
- [x] 11 个 IPC channel 常量
- [x] 所有 TypeScript 接口（9 个实体 + DTO 类型）
- [x] preload 桥接（`window.api.invoke`）
- [x] `registerIpcHandlers()` 注册所有 handler
- [x] 渲染层 `api.ts` 类型封装

---

### 阶段 4：UI 骨架 ✅

**文件：** `src/renderer/src/App.tsx`, `src/renderer/src/pages/ResearchInputPage.tsx`, `src/renderer/src/pages/ResearchCardPage.tsx`, `src/renderer/src/pages/ProjectPage.tsx`

- [x] 状态路由（`{ page, params }` 对象，无 React Router）
- [x] ResearchInputPage：5 种输入类型选择 + 输入框 + 提交
- [x] ResearchCardPage：展示研究卡片 + section/reference 勾选 + 转化按钮
- [x] ProjectPage：4 个 Tab（StructureSection, TemplateSection, AssetsSection, BuildSection）

---

### 阶段 5：研究输入流程 ✅

**文件：** `src/application/research-agent.ts`, `src/application/id.ts`

- [x] `generateResearchCard(inputType, inputValue)` — `generateObject` + Zod schema
- [x] ResearchCardSchema（对齐 architecture.md §4）
- [x] IPC handler `research:submit-input` → 调用 Agent → INSERT research_card → 返回 card id

---

### 阶段 6：项目转化流程 ✅

**文件：** `src/application/project-converter.ts`

- [x] `convertCardToProject(cardId, selectedSectionIds, selectedReferenceIds)` — Drizzle 事务
- [x] 仅导入 `project_importable_sections`（用户选中）、标题候选、选中引用
- [x] 失败时全部回滚，源卡片保留

---

### 阶段 7：LaTeX Worker ⬜

**文件：** `src/worker/latex-worker.ts`, `src/main/worker-bridge.ts`

- [ ] `latex-worker.ts`：独立 Node 子进程，接收构建包 → 调用 `latexmk` → 返回结果
  - 检测 `latexmk` 是否可用，不可用时返回安装引导错误
  - 执行：`latexmk -xelatex -interaction=nonstopmode -output-directory=<outDir> main.tex`
  - 捕获 stdout/stderr，提取错误位置（文件名 + 行号）
  - 返回：`{ status, pdfPath, logSummary, errorLocation, durationMs }`
- [ ] `worker-bridge.ts`：主进程启动/管理 worker 子进程，转发 IPC
  - `triggerBuild(buildJobId, payload)` → 发消息给 worker → 更新 build_job status
  - 写 `build_artifact`（成功时）或 `error_event`（失败时）
- [ ] IPC handler `build:trigger` 完整实现（当前为 stub）
- [ ] IPC handler `build:get-status` 读取 build_job + build_artifact

**验收：**
- 触发构建 → UI 显示 `running` → 完成后显示 `succeeded` 或 `failed`
- `succeeded` 时有 PDF 路径，可用系统查看器打开
- `failed` 时 UI 显示错误位置 + 可读摘要

---

### 阶段 8：端到端验收 ⬜

- [ ] 完整用户旅程手动测试：关键词输入 → 研究卡片 → 转化项目 → 选模板 → 触发构建 → 查看 PDF
- [ ] 失败路径测试：构建失败时显示错误位置 + 可读摘要 + 可重试
- [ ] macOS 和 Windows 均通过

---

## AI 开发者工作规范

1. 规格已够清楚时，直接写代码，不再写规划文档
2. 每个任务完成后立即更新本文件的 checkbox 状态
3. 不引入任何基础产品范围外的功能
4. 找到 bug 时先写可复现测试，再修复
5. 发现上面 checkbox 有未完成项时，直接开始写代码

---

## 完整闭环验收标准

1. 输入关键词 → 看到研究卡片（有真实内容）
2. 转化为论文项目 → 项目页面有章节和引用占位
3. 选择模板 → 模板绑定到项目
4. 触发构建 → UI 显示进度 → 构建完成
5. 打开 PDF 预览
6. 构建失败时 → 显示错误位置 + 可读摘要 + 可重试
