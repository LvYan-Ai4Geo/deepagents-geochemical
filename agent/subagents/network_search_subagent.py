# 通过字典形式创建智能体
from agent.config.conf import prompts_config
from tools.tavily_search_tool import tavily_search

internet_search_subagent = {
    'name':prompts_config.sub_agents.tavily.name,
    'description':prompts_config.sub_agents.tavily.description,
    'system_prompt':prompts_config.sub_agents.tavily.system_prompt,
    'tools':[tavily_search]
}

