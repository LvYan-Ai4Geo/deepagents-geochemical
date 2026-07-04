# DeepAgents — 多智能体协作研究与报告生成系统

DeepAgents 是一个基于 **DeepAgents 框架** + **LangChain / LangGraph** 构建的 AI 多智能体协作平台。它通过一个**主智能体（Orchestrator）**统一调度三个专业子智能体（网络搜索、数据库查询、RAGFlow 知识库问答），完成复杂的信息收集、分析、文档生成任务。

系统采用 **FastAPI** 作为后端服务，**Vue 3 + Vite** 作为前端界面，通过 **WebSocket** 实时推送智能体的执行进度与结果。

---

## 项目架构

```
deep-research-agents/
├── agent/                          # 智能体核心
│   ├── config/
│   │   └── prompts.py              # 加载 YAML 提示词配置（OmegaConf）
│   ├── llm.py                      # LLM 模型初始化（LangChain）
│   ├── main_agent.py               # 主智能体（Orchestrator）协调器
│   └── subagents/                  # 三个专业子智能体
│       ├── dataset_subagent.py     # 数据库查询子智能体
│       ├── network_search_subagent.py  # 网络搜索子智能体
│       └── ragflow_subagent.py     # RAGFlow 知识库子智能体
│
├── api/                            # FastAPI 后端服务
│   ├── server.py                   # API 服务入口（路由、WebSocket、文件上传/下载）
│   ├── monitor.py                  # WebSocket 实时进度推送（单例）
│   └── context.py                  # 基于 ContextVar 的会话级上下文隔离
│
├── tools/                          # 智能体工具函数
│   ├── db_tools.py                 # MySQL 数据库操作（查询表、查看数据、执行 SQL）
│   ├── markdown_tools.py           # Markdown 文档生成工具
│   ├── pdf_tools.py                # Markdown → PDF 转换工具（基于 Word COM）
│   ├── ragflow_tools.py            # RAGFlow 助手列表查询与问答工具
│   ├── tavily_search_tool.py       # Tavily 网络搜索工具
│   └── upload_file_read_tool.py    # 用户上传文件读取工具（md/docx/pdf/xlsx）
│
├── rag_flow/                       # RAGFlow SDK 客户端
│   ├── ragflow_client.py           # RAGFlow 单例客户端
│   └── knowledge_demo.py           # （占位文件）
│
├── utils/                          # 工具函数
│   ├── path_utils.py               # 路径解析与安全校验
│   └── word_converter.py           # MD → PDF Word COM 转换器（Windows 仅限）
│
├── prompt/                         # 智能体提示词
│   └── prompts.yaml                # 主智能体 & 子智能体的 System Prompt
│
├── ui/                             # Vue 3 前端
│   ├── src/
│   │   ├── App.vue                 # 主聊天界面（SPA）
│   │   ├── main.ts                 # Vue 应用入口
│   │   └── style.css               # 全局样式
│   ├── index.html                  # 入口 HTML
│   ├── package.json                # 依赖与脚本
│   └── vite.config.ts              # Vite 构建配置
│
├── output/                         # 生成的文档输出目录（按 session 隔离）
├── updated/                        # 用户上传文件目录（按 session 隔离）
├── tools/exports/                  # SQL 查询结果 CSV 导出目录
│
├── .env                            # 环境变量（数据库、LLM、API 密钥）
├── .python-version                 # Python 3.12
├── pyproject.toml                  # Python 项目依赖与元数据
├── requirements.txt                # Python 依赖列表
└── README.md                       # 本文件
```

---

## 技术栈

| 层      | 技术 |
|----------|------|
| **前端**   | Vue 3 (Composition API + `<script setup>` + TypeScript) + Vite |
| **后端**   | Python 3.12 + FastAPI (port 8000) + Uvicorn |
| **AI 框架** | DeepAgents + LangChain / LangGraph |
| **LLM**   | DeepSeek (deepseek-v4-flash via langchain-deepseek) |
| **数据库** | MySQL (mysql-connector-python) |
| **知识库** | RAGFlow (ragflow-sdk) |
| **网络搜索** | Tavily (tavily-python) |
| **实时通信** | WebSocket |
| **文档生成** | Markdown + PDF（通过 Microsoft Word COM 转换，Windows 仅限） |

---

## 功能特性

### 🤖 多智能体协作
- **主智能体（Orchestrator）**：作为"团队负责人"，接收用户问题，规划执行步骤，协调三个子智能体
- **网络搜索助手**：使用 Tavily API 搜索互联网公开信息，支持 general / news / finance 三种主题
- **数据库查询助手**：连接 MySQL 数据库，可列出表名、预览表数据、执行自定义 SQL 查询
- **RAGFlow 助手**：查询企业 RAGFlow 知识库，向指定助手提问获取内部知识

### 📄 文档自动生成
- 支持生成 **Markdown (.md)** 文档
- 支持 Markdown → **PDF** 格式转换（基于 Word COM 自动化）
- **严格的执行顺序**：先收集信息，再生成文档，避免内容空洞

### 🔌 文件上传与下载
- 支持上传 **.md / .docx / .pdf / .xlsx** 等多种格式文件供智能体读取
- 支持下载生成的文件，浏览器自动触发

### 💬 实时交互
- **WebSocket** 实时推送智能体执行进度（工具调用、子智能体调用、任务完成等）
- 前端展示思考过程日志（可折叠），支持 Markdown 渲染

### 🔒 会话隔离
- 每个会话（thread_id）有独立的**工作目录、上传目录、WebSocket 连接**
- 基于 Python `ContextVar` 实现线程安全的上下文传递

---

## 环境要求

| 依赖 | 版本 |
|----------|-------|
| Python | **3.12.3** |
| Node.js | ≥ 18.x |
| npm | ≥ 9.x |
| MySQL | ≥ 8.0（可选，取决于你的数据库需求） |
| Microsoft Word | 仅 PDF 转换需要（Windows） |

---

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd deep-research-agents
```

### 2. 环境变量配置

复制并编辑 `.env` 文件，填写必要的 API 密钥和数据库配置：

```env
# ——— LLM 配置 ———
MODEL=deepseek-v4-flash
MODEL_PROVIDER=deepseek
BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=sk-your-deepseek-api-key

# ——— Tavily 搜索 ———
TAVILY_API_KEY=tvly-your-tavily-api-key

# ——— RAGFlow 知识库 ———
RAGFLOW_API_URL=http://your-ragflow-server
RAGFLOW_API_KEY=ragflow-your-api-key

# ——— MySQL 数据库 ———
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=your-database
```

> **注意**：`TAVILY_API_KEY` 在代码中读取的是 `TWITTER_API_KEY` 环境变量名（tools/tavily_search_tool.py 第 14 行）。请确保 `.env` 中配置的是 `TWITTER_API_KEY` 或修改代码中的变量名。

### 3. 启动后端（FastAPI）

```bash
# 推荐使用虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务（热重载）
python -m api.server
```

后端服务默认启动在 **http://localhost:8000**，Uvicorn 开启 `reload` 模式，代码修改后自动重启。

### 4. 启动前端（Vue + Vite）

```bash
cd ui

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端开发服务器默认启动在 **http://localhost:5173**，支持 HMR 热更新。

### 5. 生产构建

```bash
cd ui
npm run build       # TypeScript 类型检查 + Vite 构建
npm run preview     # 预览构建产物（默认 http://localhost:4173）
```

---

## API 接口

| 方法 | 路径 | 说明 |
|--------|------|-------------|
| POST | `/api/task` | 提交任务请求，返回 `thread_id`，异步执行 |
| POST | `/api/upload` | 上传文件（支持多文件），关联到指定会话 |
| GET | `/api/files?path=...` | 查询指定目录下生成的文件列表 |
| GET | `/api/download?path=...` | 下载指定文件（仅限 output 目录） |
| WS | `/ws/{thread_id}` | WebSocket 实时推送智能体执行进度 |

### 任务请求示例

```json
POST /api/task
{
  "query": "查询数据库中商品销量数据，并生成一份分析报告",
  "thread_id": "optional-custom-id"
}
```

### WebSocket 消息格式

后端通过 WebSocket 推送如下事件：

```json
// 会话创建
{ "type": "monitor_event", "event": "session_created", "data": { "path": "..." } }

// 工具调用开始
{ "type": "monitor_event", "event": "tool_start", "data": { "tool_name": "...", "args": {...} } }

// 子智能体调用
{ "type": "monitor_event", "event": "assistant_call", "data": { "assistant_name": "...", "args": {...} } }

// 任务结果
{ "type": "monitor_event", "event": "task_result", "data": { "result": "..." } }

// 错误
{ "type": "monitor_event", "event": "error", "message": "..." }
```

---

## 智能体工作流程

```
用户输入问题
    │
    ▼
┌─────────────────────────────────────┐
│        主智能体（Orchestrator）        │
│  - 解析用户需求                      │
│  - 规划执行步骤                      │
│  - 协调子智能体                      │
│  - 生成文档（Markdown/PDF）          │
└──────┬──────────┬──────────┬────────┘
       │          │          │
       ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ 网络搜索  │ │ 数据库查询 │ │ RAGFlow  │
│  助手     │ │  助手     │ │  助手     │
│          │ │          │ │          │
│ Tavily   │ │ MySQL    │ │ RAGFlow  │
│ 搜索     │ │ SQL 查询  │ │ 知识库问答│
└──────────┘ └──────────┘ └──────────┘
       │          │          │
       └──────────┼──────────┘
                  ▼
          ┌──────────────┐
          │  文档生成工具   │
          │ Markdown / PDF│
          └──────────────┘
                  ▼
            输出到 session 目录
            并通过 WebSocket 推送给前端
```

**执行顺序约束**：
1. 必须先调用子智能体收集信息（网络搜索 / 数据库 / RAGFlow）
2. **不允许**在未获取信息前调用文件生成工具
3. 生成 PDF 时，需先生成 Markdown，再转换为 PDF
4. 所有文件操作限制在会话工作目录内，防止路径越权

---

## 项目依赖

### Python（核心）
| 包 | 用途 |
|-----|---------|
| `deepagents` | 多智能体框架 |
| `fastapi` + `uvicorn` | Web 服务 |
| `langchain` / `langchain-deepseek` | LLM 集成 |
| `mysql-connector-python` | MySQL 数据库连接 |
| `ragflow-sdk` | RAGFlow 知识库 SDK |
| `tavily-python` | Tavily 网络搜索 |
| `openpyxl` / `pandas` / `pypdf` / `python-docx` | 文件读写 |
| `omegaconf` | YAML 配置加载 |
| `python-multipart` | 文件上传支持 |
| `python-dotenv` | 环境变量加载 |

### 前端（Node.js）
| 包 | 用途 |
|-----|---------|
| `vue` | 前端框架 |
| `vite` | 构建工具 |
| `axios` | HTTP 请求 |
| `marked` | Markdown 渲染 |
| `vue-tsc` / `typescript` | 类型检查 |

---

## 注意事项

1. **PDF 转换**：依赖 Microsoft Word COM 自动化，仅在 Windows + 已安装 Word 的环境下可用
2. **网络搜索**：需要有效的 Tavily API Key，搜索次数受 Tavily 套餐限制
3. **RAGFlow**：需要部署并配置 RAGFlow 服务端地址和 API Key
4. **路径安全**：文件下载与列举接口对请求路径做了严格校验，仅允许访问 `output/` 目录下的文件，防止路径遍历攻击
5. **环境变量名**：Tavily 的 API Key 在代码中读取的是 `TWITTER_API_KEY`（历史遗留），建议在 `.env` 中设置 `TWITTER_API_KEY` 而非 `TAVILY_API_KEY`
