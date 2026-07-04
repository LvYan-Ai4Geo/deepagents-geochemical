# 通过字典形式创建智能体
from agent.config.conf import prompts_config
from tools.db_tools import list_tables_name, get_table_data, execute_sql_query


db_subagent = {
    'name':prompts_config.sub_agents.db.name,
    'description':prompts_config.sub_agents.db.description,
    'system_prompt':prompts_config.sub_agents.db.system_prompt,
    'tools':[list_tables_name,get_table_data,execute_sql_query]
}