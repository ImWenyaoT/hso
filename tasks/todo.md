# Task Todo

## 当前任务：过去 24 小时提交巡检与自修复

- [x] 读取 automation memory、架构文档、产品契约与 lessons
- [x] 检查过去 24 小时 git 提交与默认分支状态
- [x] 安装依赖并运行 lint / test / build，定位确定性回归
- [x] 修复确认的问题并补充必要验证
- [x] 记录 review 结论、验证结果与剩余风险

### Review

- 过去 24 小时仅发现 1 个提交：`32f2b4a feat: scaffold Electron app and consolidate docs`
- 确定性回归 1：`package.json` 已声明 `npm run lint`，但仓库缺少 ESLint 配置，命令不可用
- 确定性回归 2：`package.json` 已声明 `npm run test`，但仓库没有任何测试文件，命令稳定失败
- 已修复：新增 `.eslintrc.cjs`，补齐最小 Vitest 基线 `tests/id.test.ts`
- 已修复：按 ESLint 规则补齐显式返回类型，并删除未使用导入/变量
- 验证通过：`npm run lint`、`npm run test`、`npm run build`

## 当前任务：文档优化

- [x] 更新 CLAUDE.md（移除 Next.js/规划阶段描述，改为 Electron/编码阶段）
- [x] 更新 AGENTS.md（移除"文档优先"描述，添加实际开发命令）
- [x] 更新 implementation_plan.md（任务 1-14 全是规划任务，改为编码进度追踪）
- [x] 清理 tasks/todo.md（移除旧的已完成文档任务）
- [ ] 更新 tasks/lessons.md（添加"用文档替代代码"的教训）

## 下一个编码任务：LaTeX Worker（阶段 7）

待实现文件：
- [ ] `src/worker/latex-worker.ts` — 独立子进程，调用 latexmk，返回构建结果
- [ ] `src/main/worker-bridge.ts` — 主进程启动/管理 worker，转发 IPC，写 build_job/build_artifact

详见 `memory_bank/implementation_plan.md` 阶段 7。

## Notes

- 规格文档已整合：6 个 memory_bank 文件合并为 architecture.md + progress.md
- 所有规格阶段（Steps 1-6）已完成，已进入编码实施阶段
- 已完成的编码工作：脚手架、DB schema、IPC、UI 骨架、研究 Agent、项目转化