import json
import requests
from config import LLM_API_KEY, LLM_API_URL, GLOBAL_MODEL

def generate_summary(query: str, documents: list) -> str:
    """
    使用大模型API对搜索结果生成总结
    
    Args:
        query: 用户的搜索查询
        documents: 搜索结果列表，每个文档包含doc_id、score、snippet等信息
    
    Returns:
        str: 生成的总结文本
    """
    if not documents:
        return "未找到相关结果。"
    
    # 准备请求头
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}"
    }
    
    # 构建提示词
    prompt = (
        "请对以下搜索结果进行结构化总结，要求：\n"
        "1. 总结要简洁明了，突出重要信息\n"
        "2. 如果结果涉及多个主题，请分类总结\n"
        "3. 总结要客观，不要添加主观评价\n"
        "4. 如果发现结果之间有矛盾，请指出\n"
        "5. 输出格式要求：\n"
        "   - 使用Markdown格式\n"
        "   - 使用二级标题(##)分隔不同主题\n"
        "   - 使用无序列表(-)列举要点\n"
        "   - 使用引用(>)标注重要信息\n"
        "   - 适当使用加粗(**文字**)强调关键词\n\n"
        f"搜索关键词：**{query}**\n\n"
        "搜索结果：\n"
    )
    
    # 添加文档内容到提示词
    for i, doc in enumerate(documents, 1):
        prompt += f"\n文档{i}：\n{doc.get('snippet', '')}\n"
    
    # 构建请求数据
    data = {
        "model": GLOBAL_MODEL,
        "messages": [
            {"role": "system", "content": "你是一个专业的搜索结果总结助手，擅长使用Markdown格式进行结构化输出。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3  # 使用较低的温度以获得更稳定的输出
    }
    
    try:
        # 发送请求到API
        response = requests.post(LLM_API_URL, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        result = response.json()
        
        # 获取生成的总结
        summary = result["choices"][0]["message"]["content"].strip()
        return summary
        
    except Exception as e:
        print(f"[ERROR] 生成总结失败：{e}")
        return "抱歉，生成总结时出现错误，请稍后重试。" 