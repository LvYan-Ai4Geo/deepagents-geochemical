import os

from dotenv import load_dotenv, find_dotenv
from langchain.chat_models import init_chat_model

# 加载env
load_dotenv(find_dotenv())

model = init_chat_model(model=os.getenv('MODEL'),
                        model_provider=os.getenv('MODEL_PROVIDER'))

if __name__ == '__main__':
    result = model.invoke('你是谁')
    print(result)