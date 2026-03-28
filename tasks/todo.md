# Task Todo

## Current Task: Repository Guidelines

- [x] 盘点仓库结构、现有文档与可用开发上下文
- [x] 生成仓库级 `AGENTS.md` contributor guide
- [x] 校验文档字数、标题、章节结构与内容贴合度
- [x] 在本文件补充本次任务的 review 结果

## Current Task: Implementation Plan

- [x] 提炼 `PRD.md` 与 `tech_stack.md` 中的 base game 范围
- [x] 设计面向 AI 开发者的分步实施计划结构
- [x] 生成 `implementation_plan.md`
- [x] 复核每一步是否足够小、足够具体、且带验证测试

## Current Task: Refine Implementation Plan

- [x] 根据最新产品问答收敛 `implementation_plan.md` 的核心约束
- [x] 将研究卡片、paper project、template、asset、build 的边界写清楚
- [x] 修正文档中的引用路径与模糊状态定义
- [x] 复核修订后的计划是否可直接指导后续实现

## Current Task: Desktop-First Product Correction

- [x] 将 `PRD.md` 的产品形态从 Web-first 收敛为 desktop-first
- [x] 将 `tech_stack.md` 的主栈从 `Next.js + Vercel` 收敛为 `Electron + React`
- [x] 将 `implementation_plan.md` 中运行时、离线、构建与分发假设改为桌面应用语境
- [x] 复核三份文档是否对产品形态、离线能力与分发级别保持一致

## Current Task: Align Memory Bank With Idea

- [x] 将 multi-agent 明确写成中长期架构方向，而不是 v1 必做形态
- [x] 将 design token 体系补进 `PRD.md` 与 `tech_stack.md`
- [x] 将测试与自动优化飞轮写成 v1 必做工程项
- [x] 复核 `memory_bank` 文档与 `idea.md` 的一致性

## Current Task: Freeze Toolchain And Asset Scope

- [x] 将 LaTeX 主 toolchain 冻结为 `latexmk + xelatex + BibTeX`
- [x] 将素材归属模型冻结为 `project_only / selected_projects / all_projects`
- [x] 复核 `tech_stack.md` 与 `implementation_plan.md` 的一致性

## Current Task: Freeze Final Implementation Decisions

- [x] 将受控 LaTeX toolchain 安装方式写入文档
- [x] 将 `.hso` 与全局 asset store 的目录边界写入文档
- [x] 将 Windows 双平台 release gate 写入文档
- [x] 复核 `implementation_plan.md` 与 `tech_stack.md` 的一致性

## Current Task: Freeze Language Baseline

- [x] 将 `TypeScript` 明确写成项目主语言
- [x] 将 `Python` 明确写成辅助脚本与分析语言，而非主干运行时
- [x] 在 `tech_stack.md` 与 `implementation_plan.md` 中同步语言边界
- [x] 复核语言口径与 desktop-first 架构假设保持一致

## Current Task: Step 1 Base Game Contract

- [x] 读取 `memory_bank` 中与 Step 1 相关的核心文档
- [x] 新建集中式合同文档 `memory_bank/base_game_contract.md`
- [x] 冻结 base game 六步用户流程与核心对象词汇
- [x] 冻结 v1 non-goals，并与 `memory_bank/PRD.md` 第 8 节对齐
- [ ] 等待用户执行 Step 1 测试并确认结果
- [ ] 待测试通过后再补写 `memory_bank/progress.md` 与 `memory_bank/architecture.md`

## Checklist

- [x] 阅读 `idea.md`、`PRD.md`、`CLAUDE.md`、`AGENTS.md`
- [x] 检查 `tasks/lessons.md` 是否存在并回顾
- [x] 确认当前仓库状态与可用上下文
- [x] 识别 `idea.md` 与 `PRD.md` 的关键一致点与偏差
- [x] 通过问答确认产品愿景中的关键取舍
- [x] 精简并修订 `PRD.md`
- [x] 复核文档是否符合“不过度设计、表达结构与意图”的目标
- [x] 在本文件补充 review 结果
- [x] 结合产品定位推荐技术栈
- [x] 通过问答确认部署与交付边界
- [x] 输出技术栈预选清单到 `tech_stack.md`
- [x] 复核技术栈方案是否符合“simple but robust”

## Notes

- 当前目录不是 git 仓库，无法读取提交历史。
- `tasks/lessons.md` 已建立，后续用户纠正应持续沉淀为规则。

## Review

- 已将 PRD 主线从“两个独立工作台并列叙事”收紧为“以论文项目为核心对象的低门槛论文工作台”。
- 已明确 LaTeX 构建域是第一版主价值域，信息检索域是前置辅助域。
- 已补足第一版范围与非目标，避免文档滑向泛化科研助手或过重架构说明。
- 已保留 `LUI`、`thin client`、`DDD`、`smart agent, dumb tool` 等理念，但将其降级为支撑原则，避免压过产品主线。
- 已根据 `纯 Web`、`服务端优先构建`、`托管优先但可迁移` 三个约束整理技术栈预选池。
- 已将文档从单一路线推荐改成 `核心必选 / 条件引入 / 暂缓引入` 的 tech stack list，便于后续按场景选型。
- 已新增仓库级 `AGENTS.md`，标题为 `Repository Guidelines`，覆盖仓库结构、开发命令、命名约定、测试要求、提交与 PR 规范。
- 已按当前仓库事实说明“项目尚处于规划阶段、尚无脚手架与测试框架”，避免生成与现状不符的命令说明。
- 已验证 `AGENTS.md` 字数为 343，位于要求的 200-400 区间内。
- 已新增 `implementation_plan.md`，聚焦 base game，从研究输入到论文项目再到构建预览形成最小闭环。
- 已确保实施计划为无代码版本，且每个步骤都附带明确验证测试，适合 AI 开发者逐步执行。
- 已根据最新产品问答重新收敛 `implementation_plan.md`，加入冻结决策，明确 research card、paper project、template、asset/reference、build revision 与 preview 边界。
- 已将原先模糊的 `canceled if supported`、根目录文档引用、`user` 必选实体、PDF 作为核心 asset 等表述改成更适合当前 v1 的明确约束。
- 已将产品形态从 `Web-first` 正式纠偏为 `desktop-first`，并在 `PRD.md`、`tech_stack.md`、`implementation_plan.md` 中统一到 Electron、本地数据库、本地文件系统、本地 LaTeX worker 和 1-2 级分发假设。
- 已根据 `idea.md` 补回三类此前被弱化的愿景：design token 体系、测试与自动优化飞轮为 v1 必做项、以及 multi-agent 作为中长期架构方向。
- 已正式冻结 v1 LaTeX 主 toolchain 为 `latexmk + xelatex + BibTeX`，并将素材归属模型收敛为 `project_only / selected_projects / all_projects`。
- 已将最后一批实现级决策写回文档：受控 toolchain 安装方式、`.hso` 与全局 asset store 的目录边界、以及 macOS/Windows 双平台 release gate。
- 已将语言基线正式写死：`TypeScript` 为主工程语言，`Python` 仅作脚本、分析与辅助工具用途，避免继续停留在默认推断层。
- 已新增 `memory_bank/base_game_contract.md` 作为 Step 1 的唯一事实来源，集中冻结六步 base game 流程、核心对象词汇和 v1 non-goals。
- 已明确 `research card` 是前置研究材料、`paper project` 是主工作对象、`build result` 是单次 build job 的结果、`reference source` 不是通用 asset。
- 已将本轮任务状态写入 `tasks/todo.md`，并明确在你确认测试通过前，不更新 `memory_bank/progress.md`、不更新 `memory_bank/architecture.md`、不进入 Step 2。
