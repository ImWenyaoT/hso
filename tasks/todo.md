# Task Todo

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
