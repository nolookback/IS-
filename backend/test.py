import openai
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

PLATFORM = "CHATGLM"
API_KEY = "644280ce7b3b4675a32c55e20b2fe63c.K0i96zJySHbVMrGe"  # 申请的API Key

if PLATFORM == "DEEPSEEK":
    global_model = "deepseek-chat"
    base_url = "https://api.deepseek.com/v1/"
elif PLATFORM == "CHATGLM":
    global_model = "GLM-4-Flash-250414"
    base_url = "https://open.bigmodel.cn/api/paas/v4/"
elif PLATFORM == "QWEN":
    global_model = "qwen-plus"
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/"
elif PLATFORM == "SILICONFLOW":
    global_model = "deepseek-ai/DeepSeek-V3"
    base_url = "https://api.siliconflow.cn/v1/"
else:
    global_model = "chatgpt-4o-latest"
    base_url = "https://api.pisces.ink/v1/"

client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY", API_KEY),
    base_url=base_url,
)

# 用于单轮对话
def get_completion(prompt, model=global_model, temperature=0):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,  # 控制模型输出的随机程度
        )
        return response.choices[0].message.content
    except Exception as e:
        # print(f"API 调用出错: {e}")
        return f"API Error: {e}"

# 用于多轮对话
def get_completion_from_messages(messages, model=global_model, temperature=0):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature  # 控制模型输出的随机程度
            )
            return response.choices[0].message.content
        except Exception as e:
            # print(f"API 调用出错: {e}")
            return f"API Error: {e}"

original_prompt ='''
从下面的食谱描述中提取主要食材列表。
食谱:一份美味的番茄炒蛋需要新鲜的番茄、几个鸡蛋、少许葱花、盐和油。
首先将鸡蛋打散，番茄切块。热锅倒油，先炒鸡蛋，然后盛出。再加点油，放入番茄块翻炒，加盐调味，最后倒入炒好的鸡蛋和葱花，快速翻炒均匀即可。'''

iter1_prompt = '''
从下面的食谱描述中提取**非调味料**的食材，并**去重**。
食谱：一份美味的番茄炒蛋需要新鲜的番茄、几个鸡蛋、少许葱花、盐和油。首先将鸡蛋打散，番茄切块。热锅倒油，先炒鸡蛋，然后盛出。再加点油，放入番茄块翻炒，加盐调味，最后倒入炒好的鸡蛋和葱花，快速翻炒均匀即可。
'''
print(get_completion(original_prompt))



