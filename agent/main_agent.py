import shutil
from pathlib import Path
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import InMemorySaver
from agent.config.conf import prompts_config
from agent.llm import model
from agent.subagents.dataset_subagent import db_subagent
from agent.subagents.network_search_subagent import internet_search_subagent
from agent.subagents.ragflow_subagent import ragflow_subagent
from api.context import set_session_context, set_thread_context, reset_session_context
from api.monitor import monitor
from tools.markdown_tools import generate_markdown
from tools.pdf_tools import convert_md_to_pdf
from tools.upload_file_read_tool import read_file_content

# 创建主智能体
main_agent = create_deep_agent(
   model = model,
   system_prompt=prompts_config.main_agent.system_prompt,
   tools= [generate_markdown,convert_md_to_pdf,read_file_content],
   checkpointer=InMemorySaver(),
   subagents=[
       db_subagent,
       internet_search_subagent,
       ragflow_subagent,
   ]
)

# 项目根目录
projected_dir = Path(__file__).parents[1].resolve()

async def run_main_agent(user_query,session_id):
    """
    :param user_query: 前端的问题
    :param session_id: 每个会话的表示
    :return:
    """
    print(f'当前会话的main_agent开始执行，会话id：{session_id}')

    session_dir = projected_dir / 'output' / f'session_{session_id}'
    session_dir.mkdir(parents=True, exist_ok=True)
    # 字符串形式
    session_dir_str = str(session_dir).replace('\\', '/')
    # 获取相对路径  -> why?   a: 存储会话文件，文件形式是str
    relative_session_dir = str(session_dir.relative_to(projected_dir)).replace('\\', '/')

    # 获取上传文件的路径
    update_dir = projected_dir / 'update' / f'session_{session_id}'
    update_dir.mkdir(parents=True, exist_ok=True)
    files = [f.name for f in update_dir.iterdir() if f.is_file()]
    update_info_prompt = ""  # 有上传文件，就要拼接提示词
    # 将所有上传区域的文件  复制到  session_dir中
    if files:
        for file_name in files:
            shutil.copy2(update_dir / file_name, session_dir / file_name)

        # 告诉大模型，有这些上传的文件
        update_info_prompt = (f"\n    [已上传文件] 已加载到工作目录:\n" +
                             "\n".join([f"    - {f}" for f in files]) +
                             "\n    请优先使用工具（read_file_content）读取并参考这些文件。")

    # 存储会话地址和session_id
    session_dir_token = set_session_context(session_dir_str)
    session_id_token = set_thread_context(session_id)

    # 将会话地址推送给前端
    monitor.report_session_dir(session_dir_str)

    # 执行main_agent
    config = {
        "configurable": {
            "thread_id": session_id
        }
    }

    # 构建提示词
    path_instruction = f"""
        【工作环境指令】
        工作目录: {relative_session_dir}
        {update_info_prompt}

        规则：
        1. 新生成文件必须保存到工作目录：'{relative_session_dir}/filename'
        2. 读取已上传的文件时，请直接将文件名（例如：'开篇.txt'）作为 filename 参数传入（read_file_content）读取工具，不要带上任何目录前缀。
        3. 使用相对路径，禁止使用绝对路径
        4. 若存在上传文件，请先分析内容
        """
    # 反馈结果
    try:
        # 执行
        async for chunk in main_agent.astream({
            "messages": [
                {
                    "role": "user", "content": user_query + path_instruction
                }
            ]
        }, config=config):
            # {"model [大模型决定调用工具 子智能体  最终结果] / tools" : {messages:[xxx...]}}
            for node_name, state in chunk.items():
                if not state or "messages" not in state: continue
                messages = state["messages"]
                if messages and isinstance(messages, list):
                    last_msg = messages[-1]
                    if node_name == 'model':
                        if last_msg.tool_calls:
                            # 工具和子智能体
                            for tool_call in last_msg.tool_calls:
                                """
                                  tool_call = {
                                      name: task
                                      args:{
                                          subagent_type:子智能体的名字
                                          description:子智能体的描述
                                      }
                                  }                                
                                """
                                if tool_call['name'] == 'task':
                                    # 调用某个子智能体
                                    monitor.report_assistant(tool_call['args']['subagent_type'],
                                                             {'description': tool_call['args']['description']})
                        elif last_msg.content:
                            # 最终结果
                            print(f"主智能体执行结果，最终结果：{last_msg.content[:100]}")
                            monitor.report_task_result(last_msg.content)

    except Exception as e:
        # 报错推送错误信息给前端
        monitor._emit("error", f"执行主智能发生异常信息：{str(e)}")
    finally:
        # 释放存储的地址和session_id
        reset_session_context(session_dir_token, session_id_token)

