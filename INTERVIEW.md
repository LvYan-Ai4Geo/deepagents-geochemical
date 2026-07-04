# 地球化学数据分析助手 — 简历项目要点 & 面试深挖

---

## 一、简历写法（可直接粘贴）

### 项目名称
**基于 deepagents 的地球化学数据分析多智能体系统**

### 项目描述（精简版，3-4 行）
基于 **deepagents + LangChain/LangGraph** 构建的多智能体协作系统，专注地质样品元素含量数据的查询、统计指标计算与地球化学解释。主智能体（Orchestrator）协调两个专业子智能体（数据库查询 + 网络搜索），通过 **Agent Skills 规范**注入领域专家知识确保指标计算准确，集成 **MCP 协议**实现可扩展工具接入，采用 **FastAPI + WebSocket** 实现流式实时交互。

### 技术栈
`Python 3.12` `deepagents` `LangChain` `LangGraph` `FastAPI` `WebSocket` `MySQL` `MCP协议` `Vue3` `ContextVar`

### 核心职责与亮点（STAR 法则，挑 5-6 条）
- **多智能体编排**：基于 deepagents `create_deep_agent` 构建主智能体（Orchestrator）+ 两个 SubAgent 的协作架构，主智能体通过 `task` 工具路由任务，实现"需求拆解 → 子智能体并行调度 → 结果整合"的工作流。
- **Agent Skills 规范落地**：遵循 Agent Skills Specification（SKILL.md + YAML frontmatter），将地球化学专家知识（CV/GSD/EF 公式、UCC 背景值、异常圈定方法）封装为可复用 Skill，通过 `SkillsMiddleware + FilesystemBackend` 动态注入 SubAgent，使 LLM 严格遵循行业标准公式计算，避免幻觉。
- **MCP 协议集成**：通过 `langchain-mcp-adapters` 的 `MultiServerMCPClient` 以 stdio 方式接入 Tavily MCP Server，实现工具层解耦与可扩展；设计**容错降级机制**（MCP 不可用时自动退回 SDK 工具），保障服务可用性。
- **异步单例 + 懒加载**：因 MCP 工具需异步加载，设计 `get_main_agent()` 异步双重检查锁单例工厂，避免重复构建 agent 与 MCP 进程泄漏。
- **会话隔离与并发安全**：基于 Python `ContextVar` 实现请求级上下文隔离（session_dir / thread_id），在多会话并发执行时确保工具函数正确获取当前会话状态，避免数据串台。
- **流式实时通信**：通过 FastAPI WebSocket 实时推送 agent 执行进度（工具调用、子智能体调度、最终结果），处理了跨事件循环协程调度问题（`create_task` vs `run_coroutine_threadsafe` 自适应）。

---

## 二、面试深挖题库（按模块分组）

### 模块 A：Agent 架构与 deepagents 框架

#### Q1: 为什么选 deepagents 而不是直接用 LangChain AgentExecutor 或 LangGraph？
**答**：
deepagents 在 LangGraph 之上封装了**多智能体编排中间件**（SubAgentMiddleware），原生支持：
1. **SubAgent 字典声明式定义**：只需提供 name/description/system_prompt/tools，框架自动构建子 agent 并注入到主 agent 的 `task` 工具中，无需手写 LangGraph 的 StateGraph 节点和边。
2. **SkillsMiddleware**：原生支持 Agent Skills 规范，能从 SKILL.md 动态加载领域知识注入 system prompt。
3. **FilesystemBackend 抽象**：统一文件操作接口，支持 skills 加载与文件工具的权限隔离。

如果用原生 LangChain，SubAgent 的路由、消息传递、工具隔离都要手写大量胶水代码；deepagents 把这些沉淀为中间件，开箱即用。

#### Q2: 主智能体和子智能体是如何通信的？数据怎么传递？
**答**：
deepagents 的 SubAgentMiddleware 为主智能体注入一个 `task` 工具，参数包含 `subagent_type` 和 `description`。主智能体 LLM 决策调用 `task` 时：
1. 中间件根据 `subagent_type` 匹配到对应的 SubAgent 字典
2. 用该 SubAgent 的 system_prompt + tools 创建一个独立的子 agent（有自己的 checkpointer）
3. 子 agent 独立执行多轮工具调用，完成后返回 `summary`
4. 主智能体拿到 summary 继续推理

子智能体的执行对主智能体是**黑盒**的——主智能体只看到最终的 summary，不感知子智能体内部调用了哪些工具。这实现了关注点分离。

#### Q3: 你的主智能体 tools=[] 是空的，它怎么完成任务？
**答**：
主智能体是纯协调者（Orchestrator），不直接执行任何工具操作。它的能力来自：
1. **`task` 工具**（框架自动注入）：调度子智能体
2. **LLM 推理**：拆解需求、决定调用哪个子智能体、整合两个子智能体的返回结果

这种设计的好处是职责单一：主智能体专注"想"（规划与整合），子智能体专注"做"（查数据库/搜网络）。避免主智能体直接操作工具导致的能力边界混乱。

#### Q4: 两个子智能体能并行执行吗？
**答**：
当前用的是同步 SubAgentMiddleware（`task` 工具串行调用）。deepagents 还提供了 `AsyncSubAgentMiddleware`，支持并行调度多个子智能体。我选择串行是因为地化分析任务通常有依赖关系：先确认指标公式（网络搜索），再查数据计算（数据库）。如果任务无依赖，可以切换到 AsyncSubAgent 并行执行，通过 `asyncio.gather` 加速。

---

### 模块 B：Agent Skills 机制

#### Q5: 什么是 Agent Skills 规范？你是怎么用的？
**答**：
Agent Skills 是 Anthropic 提出的智能体技能规范（agentskills.io）。每个 skill 是一个目录，包含：
- `SKILL.md`：YAML frontmatter（name、description 必填）+ Markdown 正文（指令/公式/工作流）
- 可选的辅助文件（templates、脚本）

我在项目中创建了 `geochemical-data-analysis` skill，封装了地化指标计算公式（N、均值、方差、CV、GSD、EF）、背景值标准（UCC/PAAS）、异常圈定方法（Mean±2SD、MAD）。通过 SubAgent 的 `skills: ['skills']` 字段配置，`SkillsMiddleware` 在 agent 启动时扫描该目录，解析 frontmatter，将 skill 元数据和内容注入到子智能体的 system prompt 中。

#### Q6: 为什么 skill 挂在子智能体上而不是主智能体上？
**答**：
业务逻辑决定的——「地化数析」技能是数据库查询助手计算指标时需要的专业知识。主智能体是协调者，不做具体计算。把 skill 挂在执行实际工作的子智能体上，符合**就近原则**：谁用谁加载。

但这也带来一个问题：用户问主智能体"你有哪些技能"时，主智能体看不到 skill 信息（skill 只注入到子智能体的 prompt）。我的解决方案是在主智能体的 system_prompt 中**显式声明**已加载的 skill 清单，让主智能体也能回答这类元问题。

#### Q7: SKILL.md 的格式有什么坑？
**答**：
1. **文件名必须全大写 `SKILL.md`**，不能是 `Skill.md`，否则中间件扫描不到
2. **必须有 YAML frontmatter**，用 `---` 分隔，否则解析失败会跳过（warning 但不报错）
3. **name 字段必须与目录名一致**，且仅允许小写字母和连字符（`geochemical-data-analysis`），用下划线会触发规范警告
4. **description 最大 1024 字符**，超出会被截断
5. skill 内容会按 progressive disclosure 加载——先只暴露 name+description 到 prompt，agent 主动调用时才加载完整内容

#### Q8: SkillsMiddleware 是怎么加载 skill 的？FilesystemBackend 的作用？
**答**：
加载流程：
1. `SkillsMiddleware` 调用 `backend.ls(source_path)` 列出 `skills/` 下的子目录
2. 对每个子目录，调用 `backend.download_files(['子目录/SKILL.md'])` 读取内容
3. 用正则 `^---\s*\n(.*?)\n---\s*\n` 提取 YAML frontmatter
4. `yaml.safe_load` 解析出 name/description 等元数据
5. 将 skill 列表格式化后追加到 agent 的 system prompt

`FilesystemBackend` 是 deepagents 的存储后端抽象，`root_dir` 指向项目根目录，让中间件能从本地磁盘读取 skill 文件。默认的 `StateBackend` 是内存后端，需要通过 `invoke(files={...})` 预加载文件，不适合本地 skill 场景。

---

### 模块 C：MCP 协议集成

#### Q9: 为什么既用 Tavily SDK 又用 Tavily MCP？不重复吗？
**答**：
是**容错降级策略**：
- **SDK 工具（tavily_search）**：同步可用，无外部依赖，作为保底
- **MCP 工具**：通过 MCP 协议提供更丰富的搜索能力（如深度搜索、AI 提取），但依赖 Node.js/npx 环境

两者并存的原因：MCP server 是 stdio 子进程，启动可能失败（node 未安装、网络问题、进程崩溃）。我设计了 `_is_mcp_available()` 前置检查 + try-except 容错，MCP 不可用时返回空列表，subagent 退回到 SDK 工具，**服务不中断**。

#### Q10: MCP 工具是怎么加载的？为什么需要异步？
**答**：
通过 `langchain-mcp-adapters` 的 `MultiServerMCPClient`：
```python
client = MultiServerMCPClient({
    "tavily": {
        "command": "npx", "args": ["-y", "tavily-mcp@latest"],
        "transport": "stdio",
        "env": {"TAVILY_API_KEY": "..."}
    }
})
tools = await client.get_tools()  # 异步！
```
`get_tools()` 是异步的，因为它要：启动 npx 子进程 → 建立 stdio 通道 → MCP 握手 → 获取工具列表。这个过程涉及 IO 等待，必须用 async。

这也导致了一个架构问题：SubAgent 的 tools 字段在构建时就要确定，但 MCP 工具要 async 加载。所以我设计了 `build_internet_search_subagent()` 异步工厂函数，在应用启动时一次性加载 MCP 工具并构建 subagent。

#### Q11: MCP server 反复启动的问题怎么解决？
**答**：
通过 `get_main_agent()` 的**异步双重检查锁单例**解决：
```python
async def get_main_agent():
    if _main_agent is None:
        async with _init_lock:  # asyncio.Lock
            if _main_agent is None:  # double-check
                _main_agent = await _build_main_agent()
    return _main_agent
```
agent 只构建一次，MCP 工具只加载一次，后续请求复用单例。`asyncio.Lock` 保证并发请求时只有一个协程执行初始化。

#### Q12: MCP 的 stdio 传输和 SSE/HTTP 传输有什么区别？
**答**：
- **stdio**：MCP server 作为子进程运行，通过 stdin/stdout 通信。优点是本地隔离、无需端口；缺点是每个 client 启动一个进程，不适合多实例共享。
- **SSE/HTTP**：MCP server 作为远程服务运行，通过 HTTP SSE 通信。优点是多 client 共享、可远程部署；缺点是需要网络和端口管理。

我用 stdio 是因为 Tavily MCP 是本地工具，无需远程部署，stdio 最简单。

---

### 模块 D：并发与上下文隔离

#### Q13: 多个用户同时发请求，会话数据会串台吗？
**答**：
不会。我用 Python 的 `ContextVar` 实现请求级隔离：
```python
_session_dir_ctx: ContextVar[Optional[str]] = ContextVar("session_dir")
```
每个请求在 `run_main_agent` 入口处 `set_session_context(path)` 设置自己的 session_dir，拿到 token。在同一个 asyncio 任务链路中（包括子智能体、工具函数），`get_session_context()` 都能取到正确的值。请求结束时 `reset_session_context(token)` 恢复。

`ContextVar` 是 Python 3.7+ 的上下文变量，专为 async 场景设计，**每个 Task 有独立的上下文副本**，不会跨任务泄漏。

#### Q14: 为什么用 ContextVar 而不是函数参数传递？
**答**：
工具函数（如 `read_file_content`、`generate_markdown`）是 LangChain `@tool` 装饰的，**签名由 LLM 决定**，不能随意加参数。ContextVar 让工具函数内部"隔空取物"获取会话目录，不污染工具签名，也不需要层层传递。

#### Q15: WebSocket 推送时，为什么有 `create_task` 和 `run_coroutine_threadsafe` 两种方式？
**答**：
因为 agent 可能在不同执行上下文中调用工具：
- **同一事件循环**（FastAPI 的 `asyncio.create_task` 触发）：直接 `loop.create_task(coro)`，效率最高
- **不同线程/循环**（同步工具函数中调用）：必须用 `asyncio.run_coroutine_threadsafe(coro, loop)`，否则报"协程在错误的循环中运行"

`ToolMonitor._emit()` 中先检测 `current_loop == manager_loop`，自适应选择调度方式。这是 FastAPI 异步 + 同步工具混用场景的常见坑。

---

### 模块 E：流式输出与实时通信

#### Q16: agent 的流式输出是怎么实现的？
**答**：
用 LangGraph 的 `astream()` 异步流式迭代：
```python
async for chunk in main_agent.astream({"messages": [...]}, config=config):
    for node_name, state in chunk.items():
        # node_name: 'model' / 'tools'
        # state['messages'][-1]: 最新消息
```
每个 chunk 是一个节点的输出增量。`node_name == 'model'` 时检查 `tool_calls`（调用子智能体）或 `content`（最终结果），通过 WebSocket 实时推送给前端。

#### Q17: WebSocket 连接怎么管理的？
**答**：
`ConnectionManager` 单例管理所有活跃连接，按 `thread_id` 索引：
```python
class ConnectionManager:
    active_connections: Dict[str, WebSocket]
```
连接建立时 `connect(websocket, thread_id)` 注册，断开时 `disconnect` 清理。推送时 `send_to_thread(message, thread_id)` 精确定向。前端在 `onMounted` 时建立连接，断开后 3 秒自动重连。

---

### 模块 F：领域逻辑与工程实践

#### Q18: 地化指标计算的准确性怎么保证？LLM 不会算错吗？
**答**：
三层保障：
1. **Skill 注入公式**：SKILL.md 中明确写出 CV = S/X̄、GSD = exp(S_lnX)、EF = (Ci/Cref)_sample / (Ci/Cref)_background 等公式，LLM 严格遵循
2. **网络搜索助手验证**：计算前先查询 UCC 背景值、参考元素选择标准，确保参数正确
3. **数据库助手执行 SQL 聚合**：均值、方差等用 SQL 的 AVG/STDDEV 计算，不依赖 LLM 算术

LLM 负责公式选择和解释，数据库负责精确计算，分工降低错误率。

#### Q19: 路径安全怎么做的？防止路径遍历攻击？
**答**：
`resolve_path()` 工具函数做多层防护：
1. **虚拟路径清洗**：剥离 `/workspace`、`/mnt/data`、`/home/user` 等 LLM 常见虚拟前缀
2. **会话目录隔离**：相对路径拼接到当前 session_dir，绝对路径校验是否在 session_dir 内
3. **嵌套防护**：检测 `session_id/session_id` 连续重复并修正
4. **下载接口校验**：`/api/download` 用 `Path.is_relative_to(output_abs)` 确保只能访问 output 目录

#### Q20: 这个项目如果让你优化，你会做什么？
**答**：
1. **持久化 checkpointer**：当前用 `InMemorySaver`，重启丢失对话历史，可换 SQLite/PostgreSQL checkpointer
2. **AsyncSubAgent 并行**：无依赖的任务（如同时查 Cu 和 Pb 数据）可并行执行
3. **MCP 连接池**：复用 MCP server 进程，避免重复启动
4. **Skill 热更新**：当前 skill 在 agent 构建时加载，修改后需重启；可监听文件变化热加载
5. **结构化输出**：用 `response_format` 让 agent 返回 JSON，便于前端渲染表格
6. **可观测性**：接入 LangSmith 追踪 agent 的完整调用链

---

## 三、技术关键词速查表

| 关键词 | 一句话解释 |
|--------|-----------|
| deepagents | LangGraph 之上的多智能体编排框架，提供 SubAgent/Skills/Filesystem 中间件 |
| SubAgent | 声明式子智能体，主智能体通过 `task` 工具调度 |
| SkillsMiddleware | 从 SKILL.md 加载领域知识注入 agent prompt 的中间件 |
| FilesystemBackend | deepagents 的本地文件存储后端，供 Skills 读取 |
| MCP (Model Context Protocol) | Anthropic 提出的工具协议标准，通过 stdio/HTTP 暴露工具 |
| langchain-mcp-adapters | LangChain 与 MCP 的适配层，`MultiServerMCPClient` 加载 MCP 工具 |
| ContextVar | Python 3.7+ 上下文变量，async 安全的请求级隔离机制 |
| InMemorySaver | LangGraph 的内存检查点保存器，存储对话状态 |
| astream | LangGraph 异步流式迭代，按节点增量返回 |
| run_coroutine_threadsafe | 跨事件循环调度协程的线程安全方法 |

---

## 四、可能的反问环节

如果面试官问"你还有什么问题"，可以反问：
1. "你们的多智能体系统是如何做工具权限隔离的？有没有用沙箱？"
2. "生产环境的 agent 可观测性你们怎么做的？LangSmith 还是自建？"
3. "MCP 在你们生产环境是用 stdio 还是远程 HTTP？并发量大时怎么管理进程？"
