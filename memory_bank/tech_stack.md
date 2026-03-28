# HSO Tech Stack List

## 1. 文档目的

这不是一份“唯一正确答案”，而是一份 HSO 的技术栈预选池。

目标是先按产品形态、工程取向和长期边界，把值得长期保留的技术预选出来。后续做具体模块时，再从这份 list 里按场景挑选，而不是每次从零开始争论。

选择标准只有三个：

1. 符合 HSO 的产品定位
2. 符合 [idea.md](/Users/edward/Documents/hso/idea.md) 中的 `thin client`、`DDD`、`smart agent, dumb tool`
3. 优先选择 `简单但稳健`，而不是功能最花哨

## 2. 使用原则

这份 list 分成三层：

1. `核心必选`
这些技术默认进入第一版主栈，除非有明确理由替换。

2. `条件引入`
这些技术是好技术，但不是第一天就必须上。只有在具体需求成立时才引入。

3. `暂缓引入`
这些技术并不是差，只是当前阶段引入它们会让系统复杂度增长快于产品价值增长。

## 2.5 当前最佳推荐

如果目标是为 HSO 选出一套 `最简单但最稳健` 的默认主栈，那么当前最佳推荐是：

- Desktop Shell：`Electron`
- UI：`React`
- Primary Language：`TypeScript`
- Auxiliary Language：`Python`
- UI Styling：`Tailwind CSS + shadcn/ui`
- Design System：`design tokens + theme contract`
- Application / Agent：`Node.js + Vercel AI SDK`
- Local Database：`SQLite + Drizzle`
- Local File Storage：`filesystem`
- Build Runtime：`local LaTeX worker process`
- LaTeX Toolchain：`latexmk + xelatex + BibTeX`
- Monitoring：`structured logging + trace id`

这是当前最适合 HSO 的默认组合，原因不是它在每个点上都“最强”，而是它在下面三个目标之间平衡最好：

1. 足够贴合产品形态
HSO 第一版的真实形态是 `.app` / `.exe` 形式启动的桌面应用，而不是网页站点。

2. 足够稳
Electron 生态成熟，桌面产品验证充分，本地文件、本地缓存、本地构建边界更自然。

3. 足够可扩展
未来仍然可以按需补充联网检索、模型调用、同步与云能力，而不需要推翻 desktop-first 基线重做。

这一推荐的底层原则是：

1. 第一版先把 `论文项目` 主流程跑通
2. 先保证 `高内聚、低耦合`
3. 技术选型优先服务产品形态，而不是沿用 Web 默认答案

### 2.6 语言基线

- `TypeScript`
- `Python`

判断：

1. HSO 的桌面壳、Renderer UI、应用编排层、IPC 契约、本地 worker 主体都建立在 `Electron + React + Node.js` 之上，主语言应统一，避免多语言扩散主干复杂度。
2. 第一版强调 schema、状态机、跨进程契约、可观测性与回归测试，`TypeScript` 更适合承载主工程的类型边界。
3. `Python` 在脚本化安装、离线分析、数据清洗、实验性处理流程上有价值，但不应成为桌面应用主干运行时。

结论：

- `TypeScript` 是 HSO 第一版的主工程语言
- `Python` 仅作为辅助语言，用于脚本、分析、数据处理或实验性工具
- Electron main、renderer、application/orchestrator、shared schema/contracts、local worker 默认统一使用 `TypeScript`
- 若引入 `Python`，必须保持 sidecar 定位，不承担主应用生命周期控制与核心桌面交互

## 3. 核心必选

### 3.1 桌面应用层

- `Electron`
- `React`

判断：

1. HSO 第一版的默认载体是桌面应用，而不是网页
2. 需要本地启动、本地文件访问、本地优先离线体验
3. 不追求极致轻量化，更看重成熟生态和市场验证

结论：

- `Electron` 是默认桌面壳方案
- `React` 是默认 UI 运行时

### 3.2 UI 工程层

- `Tailwind CSS`
- `shadcn/ui`
- design tokens

判断：

1. 第一版要快
2. 需要结构化、可复用的界面系统
3. 不值得为第一版自建复杂组件库
4. `idea.md` 已将 tokenized design system 视为中长期界面基础，第一版应从一开始预留

结论：

- `Tailwind CSS` 作为样式系统默认选项
- `shadcn/ui` 作为基础组件预选库
- 颜色、字号、spacing、radius、shadow 等应沉淀为 design tokens，而不是散落在组件里

### 3.3 应用编排层

- `Node.js`
- `Vercel AI SDK`

判断：

1. HSO 的中枢是 Agent / Application 层
2. 第一版需要稳定编排，不需要重型实验性 Agent 框架
3. `Node.js` 与 Electron / React 共享语言与生态，降低心智负担

结论：

- `Node.js` 是默认应用运行时
- `Vercel AI SDK` 是默认 AI / Agent 接入层

### 3.4 本地主数据库

- `SQLite`
- `Drizzle ORM`

判断：

1. 第一版默认是本地单用户桌面应用
2. 核心对象如论文项目、研究卡片、模板、构建记录天然适合关系型建模
3. 本地优先时，SQLite 更符合安装、迁移和离线使用成本

结论：

- `SQLite` 是第一版默认主数据库
- `Drizzle` 是默认 ORM

### 3.5 文件与本地存储

- local filesystem

判断：

1. HSO 有图表、模板、构建产物、日志等本地文件需求
2. 桌面应用天然适合使用本地文件系统
3. 第一版不应把本地资产强依赖到远程对象存储

结论：

- 本地文件系统是第一版默认文件边界
- 文件路径、项目目录和构建产物默认落地本机

### 3.6 构建执行

- local worker process
- `latexmk`
- `xelatex`
- `BibTeX`

判断：

1. LaTeX 构建是第一版核心能力
2. 桌面应用形态下，本地构建比远程构建更符合离线与项目目录模型
3. 构建执行必须与 UI 线程隔离
4. 当前模板集合应以受控方式适配统一 toolchain，而不是为了兼容任意模板扩散出多条构建路径

结论：

- LaTeX build 使用本地独立 worker 进程
- UI 不直接承担构建执行
- v1 默认并冻结主 toolchain 为 `latexmk + xelatex + BibTeX`

### 3.6.1 Toolchain 交付方式

判断：

1. v1 不应依赖用户自行预装系统级 TeX 环境
2. 又不应把完整 LaTeX 发行版粗暴塞进应用安装包，避免包体和维护成本失控
3. 桌面应用应尽量给用户提供接近“内建能力”的安装体验

结论：

- 应用在首次 build 前检测本地受控 toolchain
- 若不存在，则由应用引导用户一键安装
- 安装过程可由受控脚本完成，但对用户表现为应用内安装体验
- toolchain 安装位置位于 app data，而不是系统全局环境
- 后续构建只依赖该受控 toolchain

### 3.7 可观测性

- structured logging
- `trace id / decision id`
- `Sentry` 作为条件增强

判断：

1. [idea.md](/Users/edward/Documents/hso/idea.md) 强调决策追踪和自动优化飞轮
2. 本地桌面产品同样需要可调试的日志链路
3. 第一版先保证本地日志可读，再决定是否默认接入远程错误上报

结论：

- `structured logging + trace id` 是默认配置
- `Sentry` 在需要远程聚合错误时引入

### 3.8 测试与自动优化飞轮

- focused automated tests
- regression cases from production bugs
- local repro workflow

判断：

1. [idea.md](/Users/edward/Documents/hso/idea.md) 已将决策追踪、根因锁定、用例沉淀、回归闭环定义为关键工程实践
2. 第一版如果不从一开始规划测试与回归路径，后续补齐成本会明显升高
3. 桌面产品同样需要把线上或内测问题沉淀为本地可复现用例

结论：

- 测试规划不是后续优化项，而是第一版必做工程项
- 必须从一开始保留“日志 -> 根因 -> 用例 -> 回归验证”的闭环入口

## 4. 条件引入

### 4.1 Next.js

- `Next.js`

适合引入的条件：

1. 后续需要独立的 Web 配套入口
2. 需要云端项目页、官网或远程协作面板
3. 桌面应用之外明确新增 Web 产品线

当前判断：

- 不是第一版主栈
- 可作为未来补充能力，而不是当前默认入口

### 4.2 Postgres

- `Postgres`

适合引入的条件：

1. 需要多用户共享数据库
2. 需要跨设备同步和远程协作
3. 本地 SQLite 无法满足后续数据规模或部署要求

当前判断：

- 是良好的长期扩展方向
- 不是第一版默认主数据库

### 4.3 Redis

- `Redis`

适合引入的条件：

1. 需要跨进程或跨设备的共享队列状态
2. 引入远程任务、同步任务或云端编排
3. 本地简单任务调度开始不够用

当前判断：

- 进入预选池
- 不是第一版本地优先方案的必选项

### 4.4 S3-compatible Object Storage

- `S3-compatible Object Storage`

适合引入的条件：

1. 需要云端同步构建产物或项目附件
2. 需要多设备共享文件
3. 需要把本地资产向云端抽象迁移

当前判断：

- 适合作为后续云增强能力
- 不是第一版默认文件边界

### 4.5 远程 LLM / 检索服务

- remote retrieval service
- remote model API

适合引入的条件：

1. 需要真实检索
2. 需要在线模型总结和结构化输出
3. 接受联网能力是增强层而非本地核心依赖

当前判断：

- 这是重要能力
- 但应定义为“联网增强”，不是桌面应用启动前提

### 4.6 Sentry

- `Sentry`

适合引入的条件：

1. 需要收集内测用户错误
2. 需要远程排查桌面应用异常
3. 愿意接入外部错误聚合平台

当前判断：

- 值得保留
- 但第一版不应因为没有它而阻塞交付

### 4.7 更明确的 Multi-Agent 体系

- orchestrator agent
- domain agents

适合引入的条件：

1. 两个核心领域的边界已经稳定
2. 编排逻辑已经复杂到值得从单应用编排层中抽离
3. 需要更明确地表达 `idea.md` 中的顶层编排器 + 领域 Agent 形态

当前判断：

- 这是中长期架构方向
- 不是第一版必须先落地的物理拆分形态

## 5. 暂缓引入

### 5.1 Tauri

暂缓原因：

1. 当前不追求极致轻量化
2. Electron 生态更成熟，桌面产品验证更充分
3. 当前阶段更重视稳定和可预期，而不是缩小包体

### 5.2 微服务化拆分

暂缓原因：

1. 当前规模下收益不大
2. 会让边界从“业务边界清晰”变成“部署边界复杂”

### 5.3 纯 Web First 架构

暂缓原因：

1. 当前第一版已明确是 `desktop-first`
2. 会与离线、本地文件和本地构建目标冲突

### 5.4 NoSQL 作为主数据库

暂缓原因：

1. 核心业务对象更适合关系型建模
2. NoSQL 目前没有明确胜出场景

## 6. 当前建议的默认组合

如果今天就开始做 HSO 第一版，默认组合建议如下：

- Desktop Shell：`Electron`
- UI：`React`
- UI Styling：`Tailwind CSS + shadcn/ui`
- Design System：`design tokens + theme contract`
- Application / Agent：`Node.js + Vercel AI SDK`
- Database：`SQLite + Drizzle`
- File Storage：`local filesystem`
- Build Runtime：`local worker process`
- LaTeX Toolchain：`latexmk + xelatex + BibTeX`
- Monitoring：`structured logging + trace id`
- Quality Loop：`tests + regression cases + local repro workflow`
