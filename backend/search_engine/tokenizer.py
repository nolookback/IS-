import os
import re
import jieba
import requests
import json
from config import USE_LLM, LLM_API_KEY, LLM_API_URL, GLOBAL_MODEL

def tokenize_with_llm(text: str) -> list[str]:
    """
    使用大模型 API 对输入文本进行分词处理（默认使用 ChatGLM）。
    
    :param text: 待分词的中文或英文文本
    :return: 分词列表（按空格分隔）
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}"
    }

    # 提示词设计，要求返回词语用空格分开
    prompt = (
        "请对以下文本进行分词，要求：\n"
        "1. 中文使用标准分词规则\n"
        "2. 英文按单词分隔\n"
        "3. 结果仅返回以空格连接的词语，不包含其他内容\n"
         f"{text}"
    )

    data = {
        "model": GLOBAL_MODEL,  # 使用 config.py 中定义的模型
        "messages": [
            {"role": "system", "content": "你是一个中文与英文分词专家。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
  #  print(f"[请求参数] {json.dumps(data, ensure_ascii=False)}")
    try:
        response = requests.post(LLM_API_URL, headers=headers, data=json.dumps(data))
        print(f"[响应状态码] {response.status_code}")
    #    print(f"[响应内容] {response.text}")
        response.raise_for_status()
        result = response.json()

        # ChatGLM 返回格式：choices[0].message.content
        text_response = result["choices"][0]["message"]["content"].strip()

        # 按空格拆分返回的分词结果
        tokens = text_response.split()
        return tokens
    except Exception as e:
        print(f"[大模型分词失败] {e}")
        print("[警告] 正在使用jieba分词作为替代方案。")
        return tokenize_with_jieba(text)

def tokenize_with_jieba(text: str) -> list[str]:
    """
    使用jieba分词作为备用方案。
    
    :param text: 输入文本
    :return: 分词结果列表
    """
    seg_list = jieba.cut(text, cut_all=False)
    tokens = [token.strip() for token in seg_list if token.strip()]
    return tokens

def tokenize(text: str) -> list[str]:
    """
    根据配置选择分词方式。
    
    :param text: 输入文本
    :return: 词项列表
    """
    if USE_LLM:
        return tokenize_with_llm(text)
    else:
        return tokenize_with_jieba(text)

# 测试代码
if __name__ == "__main__":
    test_text = "欢迎来到深圳大学计算机与软件学院。"
    print("分词结果：", tokenize(test_text))
