"""地球化学数据分析主智能体（Orchestrator）。

重构说明：
- 移除文档生成工具（generate_markdown / convert_md_to_pdf）与文件复制逻辑
- 移除 ragflow_subagent
- 主智能体仅负责协调两个 subagent（数据库 + 网络搜索）并返回文本结果
- 改用 FilesystemBackend，使 SkillsMiddleware 能从本地 skills/ 目录加载 SKILL.md
- 网络搜索 subagent 需异步加载 MCP 工具，故 main_agent 改为懒加载工厂模式
"""
import asyncio
import logging
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from langgraph.checkpoint.memory import InMemorySaver

from agent.config.conf import prompts_config
from agent.llm import model
from agent.subagents.dataset_subagent import db_subagent
from agent.subagents.network_search_subagent import (
    internet_search_subagent as _default_search_subagent,
    build_internet_search_subagent,
)
from api.context import set_session_context, set_thread_context, reset_session_context
from api.monitor import monitor

logger = logging.getLogger(__name__)

# 项目根目录
projected_dir = Path(__file__).parents[1].resolve()

# FilesystemBackend：以项目根目录为根，供 SkillsMiddleware 从 skills/ 读取 SKILL.md
_fs_backend = FilesystemBackend(root_dir=str(projected_dir), virtual_mode=False)

# main_agent 实例（懒加载）
_main_agent = None
# 用于保护异步初始化
_init_lock = asyncio.Lock()


async def _build_main_agent():
    """异步构建主智能体：先加载网络搜索 subagent（含 MCP 工具），再创建 agent。"""
    search_subagent = await build_internet_search_subagent()
    return create_deep_agent(
        model=model,
        system_prompt=prompts_config.main_agent.system_prompt,
        tools=[],  # 主智能体不持有工具，仅协调
        checkpointer=InMemorySaver(),
        subagents=[db_subagent, search_subagent],
        backend=_fs_backend,
    )


async def get_main_agent():
    """获取（必要时初始化）主智能体单例。"""
    global _main_agent
    if _main_agent is None:
        async with _init_lock:
            if _main_agent is None:
                logger.info("正在初始化主智能体（含 MCP 工具加载）...")
                _main_agent = await _build_main_agent()
                logger.info("主智能体初始化完成。")
    return _main_agent




async def run_main_agent(user_query, session_id):
    """
    :param user_query: 前端的问题
    :param session_id: 每个会话的标识
    """
    print(f'当前会话的main_agent开始执行，会话id：{session_id}')

    session_dir = projected_dir / 'output' / f'session_{session_id}'
    session_dir.mkdir(parents=True, exist_ok=True)
    session_dir_str = str(session_dir).replace('\\', '/')

    # 存储会话地址和session_id（供工具内部通过 ContextVar 访问）
    session_dir_token = set_session_context(session_dir_str)
    session_id_token = set_thread_context(session_id)

    # 将会话地址推送给前端
    monitor.report_session_dir(session_dir_str)

    # 检查用户上传的地化数据文件（存放于 updated/session_{id}/）
    upload_dir = projected_dir / 'updated' / f'session_{session_id}'
    upload_info_prompt = ""
    if upload_dir.exists():
        files = [f.name for f in upload_dir.iterdir() if f.is_file()]
        if files:
            upload_info_prompt = (
                f"\n    [已上传文件] 用户已上传以下地化数据文件（位于 updated/session_{session_id}/）：\n"
                + "\n".join([f"    - {f}" for f in files])
                + "\n    如需分析这些文件，请调用数据库查询助手使用 read_file_content 工具读取，"
                f"filename 参数传 'session_{session_id}/文件名'。"
            )

    # 获取主智能体实例（含 MCP 工具）
    main_agent = await get_main_agent()

    config = {
        "configurable": {
            "thread_id": session_id
        }
    }

    try:
        async for chunk in main_agent.astream({
            "messages": [
                {
                    "role": "user", "content": user_query + upload_info_prompt
                }
            ]
        }, config=config):
            for node_name, state in chunk.items():
                if not state or "messages" not in state:
                    continue
                messages = state["messages"]
                if messages and isinstance(messages, list):
                    last_msg = messages[-1]
                    if node_name == 'model':
                        if last_msg.tool_calls:
                            for tool_call in last_msg.tool_calls:
                                if tool_call['name'] == 'task':
                                    monitor.report_assistant(
                                        tool_call['args']['subagent_type'],
                                        {'description': tool_call['args']['description']}
                                    )
                        elif last_msg.content:
                            print(f"主智能体执行结果，最终结果：{last_msg.content[:100]}")
                            monitor.report_task_result(last_msg.content)

    except Exception as e:
        monitor._emit("error", f"执行主智能发生异常信息：{str(e)}")
    finally:
        reset_session_context(session_dir_token, session_id_token)
