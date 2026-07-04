"""地球化学指标查询子智能体（网络搜索）。

工具来源：
1. tavily_search：基于 tavily-python SDK，同步可用，作为保底工具。
2. Tavily MCP 工具：通过 langchain-mcp-adapters 异步加载，扩展搜索能力。

由于 MCP 工具需异步加载，本模块提供 build_internet_search_subagent() 工厂函数，
在应用启动时调用以合并 SDK + MCP 工具并构建 subagent 字典。
若未调用工厂（例如直接导入），则仅使用 SDK 工具。
"""
import asyncio
import logging

from agent.config.conf import prompts_config
from tools.tavily_search_tool import tavily_search
from tools.mcp_tools import get_tavily_mcp_tools

logger = logging.getLogger(__name__)

# 默认仅含 SDK 工具（兼容直接导入场景）
_base_tools = [tavily_search]


def _build_subagent(tools: list) -> dict:
    return {
        'name': prompts_config.sub_agents.tavily.name,
        'description': prompts_config.sub_agents.tavily.description,
        'system_prompt': prompts_config.sub_agents.tavily.system_prompt,
        'tools': tools,
    }


# 默认 subagent（仅 SDK 工具），供无法异步初始化的场景使用
internet_search_subagent = _build_subagent(_base_tools)


async def build_internet_search_subagent() -> dict:
    """异步构建网络搜索 subagent，合并 SDK 与 MCP 工具。

    应在应用启动时调用，例如 FastAPI startup 事件中：
        from agent.subagents.network_search_subagent import build_internet_search_subagent
        subagent = await build_internet_search_subagent()

    Returns:
        合并了 SDK + MCP 工具的 subagent 字典。
    """
    mcp_tools = await get_tavily_mcp_tools()
    tools = [*_base_tools, *mcp_tools]
    logger.info(
        "网络搜索 subagent 工具列表：SDK=%d, MCP=%d, 合计=%d",
        len(_base_tools), len(mcp_tools), len(tools),
    )

    return _build_subagent(tools)


if __name__ == '__main__':
    subagent = asyncio.run(build_internet_search_subagent())
    print(f"工具数量: {len(subagent['tools'])}")
