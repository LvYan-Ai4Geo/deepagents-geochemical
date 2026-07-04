import os
from dotenv import load_dotenv, find_dotenv
from ragflow_sdk import RAGFlow

# 加载配置文件
load_dotenv(find_dotenv())

ragflow_client = RAGFlow(api_key=os.getenv("RAGFLOW_API_KEY"),base_url=os.getenv("RAGFLOW_API_URL"))