from langchain_core.tools import tool

from api.monitor import monitor
from rag_flow.ragflow_client import ragflow_client


# 查询聊天助手和相应的知识库
@tool
def get_assistant_dataset()->str:
    """
    查询聊天助手的名字、功能描述、知识库的名称
    :return: f'聊天助手的名称：{assistant.name},聊天助手的功能：{assistant.description},知识库的名称：{','.join(dataset_name)}\n'
    """
    monitor.report_tool(tool_name='获取助手列表')
    try:
        # 列出所有的assistant
        # 兼容 data 是列表/字典两种情况
        assistant_list = ragflow_client.list_chats()
        if not assistant_list:
            return '没有聊天助手可用'
        # 列出每一个assistant的dataset,希望返回助手和知识库的信息: assistant_name,assistant_description,dataset_name
        total_information = ''
        for assistant in assistant_list:
            dataset_name = []
            datasets = assistant.datasets
            if datasets and isinstance(datasets,list):
                for dataset in datasets:
                    dataset_name.append(dataset['name'])
            total_information += f'聊天助手的名称：{assistant.name},聊天助手的功能：{assistant.description},知识库的名称：{','.join(dataset_name)}\n'

        return total_information
    except Exception as e:
        return f'遇到未知错误：{str(e)}'


@tool
def ask_assistant_close(assistant_name,user_question)->str:
    """
       向某个助手发起提问： 1. 创建一个会话 2.提问 3.关闭会话！
       :param assistant_name: 助手的名字！上一个工具get_assistant_dataset告诉大模型的只有名字
       :param user_question: 本次提问的问题
       :return: 返回提问的结果
       """
    """
                                                ---> dataset 
       agent 我们 ----》 session  --》 chat(助手) ---> dataset 
                                                ---> dataset 
    """
    monitor.report_tool(tool_name='助手查询', args={"assistant_name": assistant_name, "user_question": user_question})
    try:
        # 1. 通过assistant创建session
        assistant_list = ragflow_client.list_chats(name=assistant_name)
        if not assistant_list:
            return '没有聊天助手'
        assistant = assistant_list[0]
        session = assistant.create_session(name='session_create')

        # 2. 通过session进行对话
        streams = session.ask(question=user_question,stream=True)
        result = ''
        for stream in streams:
            result = stream.content

        # 3. 关闭session,通过assistant关闭session
        assistant.delete_sessions(ids=[session.id])

        return result

    except Exception as e:
        return f'存在未知的错误：{str(e)}'





if __name__ == '__main__':
    print(ask_assistant_close(assistant_name='小智',user_question='我杀了人一定会被判刑吗'))