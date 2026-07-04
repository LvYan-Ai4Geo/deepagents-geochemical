from agent.config.conf import prompts_config
from tools.ragflow_tools import get_assistant_dataset, ask_assistant_close

ragflow_subagent = {
    'name':prompts_config.sub_agents.ragflow.name,
    'description':prompts_config.sub_agents.ragflow.description,
    'system_prompt':prompts_config.sub_agents.ragflow.system_prompt,
    'tools':[get_assistant_dataset,ask_assistant_close]
}
