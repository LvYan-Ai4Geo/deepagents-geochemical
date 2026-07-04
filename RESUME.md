# 简历项目版本

## 版本一：地球化学数据分析助手

基于 deepagents 编排多智能体协作工作流（需求拆解→指标公式检索/数据查询双路调度→结果整合→地质解释输出），实现地球化学指标（CV/GSD/EF）的准确计算与地质学解释，端到端以 WebSocket 流式返回推理链路与工具调用过程。

设计主智能体（Orchestrator）+ 双 SubAgent 协作架构——主智能体零工具仅负责任务路由与结果整合，通过框架注入的 `task` 工具将请求分发至专业子智能体；数据库查询 SubAgent 挂载 MySQL 工具链（SHOW TABLES→预览100行→自定义SQL）与文件读取工具，并通过 `SkillsMiddleware + FilesystemBackend` 加载遵循 Agent Skills 规范的「地化数析」SKILL.md（YAML frontmatter + Markdown 公式），将 CV=S/X̄、GSD=exp(S_lnX)、EF=(Ci/Cref)样本/(Ci/Cref)背景 等行业标准公式与 UCC/PAAS 背景值标准注入子智能体 system prompt，约束 LLM 严格遵循公式计算避免幻觉；网络搜索 SubAgent 以专属地化指标查询 Prompt 引导 LLM 检索公式与背景值标准，确保计算参数不出错。

引入 MCP 协议扩展工具边界——通过 `langchain-mcp-adapters` 的 `MultiServerMCPClient` 以 stdio 启动 Tavily MCP Server，将 MCP 工具与 tavily-python SDK 工具合并注入网络搜索 SubAgent；针对 MCP 依赖 Node.js 子进程的不确定性，设计前置可用性检测（npx/env/依赖三重校验）+ try-except 容错降级，MCP 不可用时自动退回 SDK 工具保障服务不中断；因 MCP 工具需异步加载而 SubAgent 工具列表在构建时确定，设计 `asyncio.Lock` 异步双重检查锁单例工厂，避免并发请求重复构建 agent 与 MCP 进程泄漏。

基于 Python `ContextVar` 实现请求级会话隔离（session_dir / thread_id），在多会话并发执行时让深层工具函数隔空获取当前会话状态避免数据串台；FastAPI WebSocket 实时推送 agent 执行进度，针对 agent 在同循环/跨线程两种执行上下文调用工具的场景，自适应选择 `loop.create_task` 与 `asyncio.run_coroutine_threadsafe` 调度协程，解决跨事件循环推送报错问题；`resolve_path` 工具函数做虚拟路径清洗、会话目录隔离、嵌套防护与 `is_relative_to` 越权校验，防止 LLM 生成的路径遍历攻击。

---

## 版本二：精简版（适合空间有限的简历）

基于 deepagents + LangGraph 编排多智能体协作工作流（需求拆解→双路子智能体调度→结果整合→地质解释），端到端以 WebSocket 流式返回推理链路。

设计主智能体（零工具 Orchestrator）+ 双 SubAgent 架构：数据库 SubAgent 挂载 MySQL 工具链（SHOW TABLES→预览→SQL），通过 `SkillsMiddleware + FilesystemBackend` 加载遵循 Agent Skills 规范的 SKILL.md，将 CV/GSD/EF 标准公式与 UCC 背景值注入 prompt 约束 LLM 避免幻觉；网络 SubAgent 以专属地化 Prompt 引导检索指标公式确保参数准确。

通过 `langchain-mcp-adapters` 的 `MultiServerMCPClient` 以 stdio 接入 Tavily MCP Server 扩展工具能力，设计前置三重校验 + 容错降级（MCP 不可用时退回 SDK 工具）；因 MCP 异步加载，设计 `asyncio.Lock` 双重检查锁异步单例工厂避免重复构建与进程泄漏。

基于 `ContextVar` 实现多会话并发隔离，工具函数隔空获取会话状态；FastAPI WebSocket 实时推送执行进度，自适应 `create_task`/`run_coroutine_threadsafe` 解决跨事件循环协程调度；`resolve_path` 做虚拟路径清洗 + 嵌套防护 + 越权校验防路径遍历。

---

## 版本三：一句话项目标签（适合项目列表第一行）

**地球化学数据分析多智能体系统** | deepagents + LangGraph + MCP + FastAPI | 主智能体编排双 SubAgent，Agent Skills 注入领域公式约束 LLM 计算，MCP 协议扩展工具链，ContextVar 会话隔离，WebSocket 流式推送推理链路
