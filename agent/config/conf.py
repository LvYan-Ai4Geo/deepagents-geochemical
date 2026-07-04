from dataclasses import dataclass
from pathlib import Path

from omegaconf import OmegaConf


@dataclass
class Main_Agent:
    system_prompt: str


@dataclass
class Tavily:
    name: str
    description: str
    system_prompt: str


@dataclass
class Database:
    name: str
    description: str
    system_prompt: str


@dataclass
class Sub_Agents:
    tavily: Tavily
    db: Database


@dataclass
class PromptsConfig:
    main_agent: Main_Agent
    sub_agents: Sub_Agents


# 1. 拿到yaml文件路径
root = Path(__file__).parent.parent.parent  # 根目录
file_path = root / 'prompt' / 'prompts.yaml'

# 2. 加载yaml文件
content = OmegaConf.load(file_path)  # dictconfig
schema = OmegaConf.structured(PromptsConfig)

# 3. 将schema与content合并
prompts_config: PromptsConfig = OmegaConf.to_object(OmegaConf.merge(content, schema))


if __name__ == '__main__':
    print(prompts_config.main_agent.system_prompt)
