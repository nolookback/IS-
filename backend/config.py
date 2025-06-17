# config.py
import os

# 是否启用大模型分词
USE_LLM = False

# 下面是 CHATGLM 大模型 API 配置
PLATFORM = "CHATGLM"
GLOBAL_MODEL = "GLM-4-Flash-250414"
BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
API_KEY = "644280ce7b3b4675a32c55e20b2fe63c.K0i96zJySHbVMrGe"

# 为方便调用大模型的tokenizer和其他地方，可直接导出变量
LLM_API_KEY = API_KEY
LLM_API_URL = BASE_URL + "chat/completions"   # CHATGLM 目前的聊天接口路径

# 数据目录配置
DATA_DIR = os.path.join(os.path.dirname(__file__), "dataset")
DOCS_DIR = os.path.join(DATA_DIR, "docs")

# 索引文件配置
INDEX_FILE = os.path.join(DATA_DIR, "index.bin")

# 下面是对openai客户端初始化相关的配置（如果需要，可写成函数供其他模块调用）
def get_openai_client():
    import openai
    import os
    client = openai.OpenAI(
        api_key=os.getenv("OPENAI_API_KEY", LLM_API_KEY),
        base_url=BASE_URL,
    )
    return client
