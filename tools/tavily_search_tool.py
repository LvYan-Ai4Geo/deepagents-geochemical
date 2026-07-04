# 导入env
import os
from typing import Literal

from dotenv import load_dotenv, find_dotenv
from langchain_core.tools import tool
from tavily import TavilyClient

from api.monitor import monitor

load_dotenv(find_dotenv())

# 创建tavily客户端
Tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

@tool
def tavily_search(query: str,
                  topic:Literal["general", "news", "finance"]='general',
                  max_results:int=10,
                  include_raw_contents:bool=False,
                  ):
    """
    根据用户问题，进行网络信息收！
    注意：主要搜索公开的网络信息！如果指定查询数据库或者rag不能使用此工具！
    :param query: 用户的查询信息
    :param topic: 查询的类型
    :param max_results: 返回的最大条数
    :param include_raw_contents: 是否返回原内容 False 精简 True 详细
    :return:
    """

    monitor.report_tool(tool_name='网络搜索工具',args={"query":query,"topic":topic,"max_results":max_results})
    return Tavily_client.search(query=query,topic=topic,max_results=max_results,include_raw_contents=include_raw_contents)




if __name__ == '__main__':
    result = tavily_search(query='查询一下北京的天气')
    print(result)