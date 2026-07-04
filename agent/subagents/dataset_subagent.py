"""地球化学数据库查询子智能体。

配置说明：
- tools：MySQL 数据库操作工具 + 用户上传文件读取工具
- skills：加载「地化数析」技能，提供标准地化指标计算公式与地质学解释规范
"""
from agent.config.conf import prompts_config
from tools.db_tools import list_tables_name, get_table_data, execute_sql_query
from tools.upload_file_read_tool import read_file_content

db_subagent = {
    'name': prompts_config.sub_agents.db.name,
    'description': prompts_config.sub_agents.db.description,
    'system_prompt': prompts_config.sub_agents.db.system_prompt,
    'tools': [list_tables_name, get_table_data, execute_sql_query, read_file_content],
    # deepagents SkillsMiddleware 从该父目录扫描子目录中的 SKILL.md
    'skills': ['skills'],
}
