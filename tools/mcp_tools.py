"""Tavily MCP 工具加载模块。

通过 langchain-mcp-adapters 的 MultiServerMCPClient 以 stdio 方式启动
Tavily 官方 MCP server，将其暴露的工具转换为 LangChain BaseTool，
供网络搜索 subagent 使用。

容错策略：
- 若 langchain-mcp-adapters 未安装或 node/npx 不可用，返回空列表，
  不阻断服务启动；网络搜索 subagent 仍可使用 tavily_search SDK 工具。
"""

import os
import shutil
import logging
from typing import Any

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
logger = logging.getLogger(__name__)

# Tavily MCP server 启动命令（需 node/npx 环境）
TAVILY_MCP_COMMAND = "npx"
TAVILY_MCP_ARGS = ["-y", "tavily-mcp@latest"]


def _is_mcp_available() -> bool:
    """前置检查：langchain-mcp-adapters 与 npx 是否可用。"""
    try:
        import langchain_mcp_adapters  # noqa: F401
    except ImportError:
        logger.warning(
            "[MCP] langchain-mcp-adapters 未安装，Tavily MCP 工具将不可用。"
            "请运行 `uv add langchain-mcp-adapters` 安装。"
        )
        return False

    if not shutil.which(TAVILY_MCP_COMMAND):
        logger.warning(
            "[MCP] 未在 PATH 中找到 npx（需要 Node.js 环境），Tavily MCP 工具将不可用。"
            "网络搜索 subagent 将退回到 tavily-python SDK 工具。"
        )
        return False

    if not os.getenv("TAVILY_API_KEY"):
        logger.warning("[MCP] 未配置 TAVILY_API_KEY 环境变量，Tavily MCP 工具将不可用。")
        return False

    return True


async def get_tavily_mcp_tools() -> list[Any]:
    """异步加载 Tavily MCP server 暴露的工具列表。

    Returns:
        LangChain BaseTool 列表；不可用时返回空列表。
    """
    if not _is_mcp_available():
        return []

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient

        client = MultiServerMCPClient(
            {
                "tavily": {
                    "command": TAVILY_MCP_COMMAND,
                    "args": TAVILY_MCP_ARGS,
                    "transport": "stdio",
                    "env": {
                        "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", ""),
                    },
                }
            }
        )
        tools = await client.get_tools()
        logger.info("[MCP] Tavily MCP 工具加载成功，共 %d 个工具。", len(tools))
        return tools
    except Exception as e:
        logger.warning(
            "[MCP] Tavily MCP server 启动失败：%s。将退回到 SDK 工具。", e,
            exc_info=False,
        )
        return []


if __name__ == "__main__":
    import asyncio

    async def _main():
        tools = await get_tavily_mcp_tools()
        for t in tools:
            print(f"- {t.name}: {t.description[:80] if t.description else ''}")

    asyncio.run(_main())
