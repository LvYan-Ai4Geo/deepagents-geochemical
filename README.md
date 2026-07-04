# 地球化学数据分析助手 (Geochemical Data Analysis Agent)

基于 **deepagents** 框架构建的地球化学数据分析多智能体系统。主智能体（Orchestrator）协调两个专业子智能体，完成地质样品元素含量数据的查询、统计指标计算与地球化学解释。

---

## 项目架构

```
deep-research-agents/
├── agent/                              # 智能体核心
│   ├── config/
│   │   └── conf.py                     # OmegaConf 加载 prompts.yaml
│   ├── llm.py                          # LLM 模型初始化
│   ├── main_agent.py                   # 主智能体（Orchestrator)
│   └── subagents/
│       ├── dataset_subagent.py         # 地化数据库查询子智能体（+skills 配置）
│       └── network_search_subagent.py  # 地化指标查询子智能体（SDK + MCP 工具）
│
├── api/                                # FastAPI 后端
│   ├── server.py                       # 路由、WebSocket、文件上传/下载
│   ├── monitor.py                      # 实时进度推送（单例）
│   └── context.py                      # ContextVar 会话级上下文隔离
│
├── tools/                              # 智能体工具
│   ├── db_tools.py                     # MySQL 数据库操作
│   ├── tavily_search_tool.py           # Tavily SDK 网络搜索
│   ├── upload_file_read_tool.py        # 上传文件读取（md/docx/pdf/xlsx）
│   └── mcp_tools.py                    # Tavily MCP 工具加载（langchain-mcp-adapters）
│
├── skills/                             # Agent Skills（deepagents 规范）
│   └── geochemical-data-analysis/
│       ├── SKILL.md                    # 地化数析技能（YAML frontmatter + 公式）
│       └── templates/                  # 输出模板（Excel）
│
├── prompt/
│   └── prompts.yaml                    # 主智能体 & 子智能体 System Prompt
│
├── utils/
│   └── path_utils.py                   # 路径解析与安全校验
│
├── output/                             # 运行时输出目录（按 session 隔离，gitignore）
├── updated/                            # 用户上传文件目录（按 session 隔离，gitignore）
│
├── .env                                # 环境变量（密钥）
├── pyproject.toml                      # Python 依赖（uv 管理）
├── requirements.txt                    # 依赖列表（同步）
└── README.md
```

---

## 技术栈

| 层 | 技术 |
|---|---|
| **AI 框架** | deepagents 0.6.8 + LangChain 1.3 + LangGraph |
| **LLM** | DeepSeek (deepseek-v4-flash) |
| **后端** | Python 3.12 + FastAPI + Uvicorn |
| **数据库** | MySQL (mysql-connector-python) |
| **网络搜索** | Tavily SDK + Tavily MCP (langchain-mcp-adapters) |
| **Skills** | deepagents SkillsMiddleware + FilesystemBackend |
| **实时通信** | WebSocket |

---

## 智能体协作流程

```
用户输入地化数据分析需求
        │
        ▼
┌───────────────────────────────────┐
│     主智能体（Orchestrator）        │
│  - 解析地化数据分析需求             │
│  - 协调两个子智能体                │
│  - 整合结果返回文本                 │
└──────┬──────────────────┬─────────┘
       │                  │
       ▼                  ▼
┌──────────────┐  ┌──────────────────┐
│ 地化指标查询  │  │  地化数据库查询    │
│   助手       │  │    助手           │
│ (网络搜索)   │  │  (数据库+Skill)   │
│              │  │                  │
│ Tavily SDK   │  │ MySQL 查询       │
│ Tavily MCP   │  │ 文件读取         │
│              │  │ 地化数析 Skill   │
│ 查询公式/标准 │  │ 计算统计指标     │
└──────────────┘  └──────────────────┘
        │                  │
        └────────┬─────────┘
                 ▼
        文本结果返回前端
       (Markdown 表格 + 地质解释)
```

### 两个子智能体

#### 1. 地化数据库查询助手（dataset_subagent）
- **工具**：`list_tables_name` / `get_table_data` / `execute_sql_query` / `read_file_content`
- **Skills**：加载 `geochemical-data-analysis` 技能，严格遵循标准公式计算：
  - 基础统计：N、算术均值、方差/标准差、极值、四分位数（Q1/Q2/Q3）
  - 离散特征：变异系数 CV、几何标准差 GSD
  - 富集评价：富集系数 EF（默认参考元素 Al，背景基准 UCC）
- **数据来源**：MySQL 数据库 或 用户上传的 Excel/CSV 文件

#### 2. 地化指标查询助手（network_search_subagent）
- **工具**：`tavily_search`（SDK）+ Tavily MCP 工具（异步加载，容错降级）
- **职责**：检索地化指标计算公式、背景值标准（UCC/PAAS）、参考元素选择原则，确保数据库助手的指标计算不出错

---

## 关键设计

### Skills 加载
- `dataset_subagent` 通过 `skills: ['skills']` 配置，`SkillsMiddleware` 从 `FilesystemBackend` 扫描 `skills/` 下的子目录
- 每个 skill 目录须包含 `SKILL.md`（全大写）+ YAML frontmatter（`name`、`description` 必填，name 须与目录名一致且仅含小写字母与连字符）
- 主智能体使用 `FilesystemBackend(root_dir=项目根目录)` 作为 backend

### MCP 集成

- `tools/mcp_tools.py` 通过 `MultiServerMCPClient` 以 stdio 启动 `npx -y tavily-mcp@latest`
- **容错策略**：node/npx 不可用或 MCP 启动失败时，返回空列表，网络搜索 subagent 退回到 SDK 工具，不阻断服务
- MCP 工具在应用启动时通过 `build_internet_search_subagent()` 异步加载

### 主智能体懒加载
- 因 MCP 工具需异步加载，`main_agent` 改为 `get_main_agent()` 异步工厂单例
- 首次调用时加载 MCP 工具并构建 agent，后续复用

---

## 快速开始

### 1. 环境配置

编辑 `.env`：
```env
# LLM
MODEL=deepseek-v4-flash
MODEL_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-key

# Tavily（SDK + MCP 共用）
TAVILY_API_KEY=tvly-your-key

# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=地化数据
```

### 2. 安装依赖

```bash
uv sync
```

> MCP 需要 Node.js / npx 环境。若未安装，网络搜索将退回到 SDK 工具。

### 3. 启动后端

```bash
python -m api.server
```

服务启动在 http://localhost:8000

---

## API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/task` | 提交地化分析任务 |
| POST | `/api/upload` | 上传地化数据文件（Excel/CSV） |
| GET | `/api/files?path=...` | 查询输出文件列表 |
| GET | `/api/download?path=...` | 下载文件 |
| WS | `/ws/{thread_id}` | 实时推送执行进度 |

---

## 使用示例

**任务请求**：
```json
POST /api/task
{
  "query": "查询数据库中 Cu、Pb、Zn 元素含量数据，计算 CV、GSD、EF 指标并给出地质解释"
}
```

**上传数据文件**：

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "files=@地化数据.xlsx" \
  -F "thread_id=session-001"
```

---

## 注意事项

1. **MCP 依赖 Node.js**：Tavily MCP server 通过 `npx` 启动，需本地安装 Node.js。无 Node 环境时自动降级到 SDK。
2. **Skills 规范**：`SKILL.md` 必须全大写，frontmatter 的 `name` 须与目录名一致且仅含小写字母与连字符。
3. **文件读取**：上传文件存于 `updated/session_{id}/`，数据库助手通过 `read_file_content(filename="session_{id}/文件名")` 读取。
4. **路径安全**：文件下载/列举接口限制在 `output/` 目录下，防止路径遍历。
