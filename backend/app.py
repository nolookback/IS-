from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from search_engine.index import SearchEngine
from search_engine.tokenizer import tokenize
from search_engine.utils import Timer
from search_engine.llm_summary import generate_summary
from config import USE_LLM, DATA_DIR, INDEX_FILE
import os

app = Flask(__name__)
CORS(app)

search_engine = SearchEngine()

# 文档路径：data/docs/*.txt
DOCS_PATH = os.path.join(DATA_DIR, "docs")

def init_app():
    """
    初始化应用，构建倒排索引。
    """
    global search_engine
    
    # 创建搜索引擎实例
    search_engine = SearchEngine()
    
    # 优先尝试加载已存在的索引
    if os.path.exists(INDEX_FILE):
        print("[INFO] 从文件加载索引...")
        try:
            search_engine.load(INDEX_FILE)
            print(f"[INFO] 索引加载完成，共索引文档数：{search_engine.doc_count}")
            return
        except Exception as e:
            print(f"[WARNING] 加载索引失败：{e}")
            print("[INFO] 将重新构建索引...")
    
    # 如果加载失败或索引文件不存在，则构建新索引
    print("[INFO] 开始构建索引...")
    search_engine.build_index(DOCS_PATH)
    print(f"[INFO] 索引构建完成，共索引文档数：{search_engine.doc_count}")
    
    # 保存新构建的索引
    print("[INFO] 保存索引到文件...")
    search_engine.save(INDEX_FILE)
    print("[INFO] 索引保存完成")

@app.route("/api/search", methods=["POST"])
def search():
    """
    处理前端查询请求，返回匹配文档及相关分数和摘要。
    支持普通搜索、邻近搜索和查询纠错。
    """
    if request.method == "OPTIONS":
        return '', 200
    try:
        data = request.get_json()
        print("请求体内容：", data)
        query = data.get("query", "")
        use_proximity = data.get("use_proximity", False)  # 是否使用邻近搜索
        print("搜索关键词：", query)
        print("使用邻近搜索：", use_proximity)
        
        if not query.strip():
            return jsonify({"error": "Query is empty"}), 400

        with Timer() as timer:
            # 使用 search_engine 封装好的接口
            results, elapsed_ms = search_engine.query(query, use_proximity=use_proximity)
            
            # 获取查询纠错建议
            corrected_queries = search_engine.query_corrector.correct_query(query)
            if query in corrected_queries:
                corrected_queries.remove(query)
            
            # 生成总结
            summary = generate_summary(query, results)

        return jsonify({
            "query": query,
            "use_llm": USE_LLM,
            "use_proximity": use_proximity,
            "elapsed_ms": round(elapsed_ms, 2),
            "results": results,
            "gpt_summary": summary,
            "corrected_queries": corrected_queries[:3]  # 返回最多3个纠错建议
        })
    except Exception as e:
        print("[ERROR] 查询出错：", e)
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/summary", methods=["POST"])
def query_llm_summary():
    """
    （可选）使用大模型 API，对查询和结果生成一个摘要或自然语言补充。
    """
    from search_engine.llm_summary import generate_summary  # 可选模块
    data = request.get_json()
    query = data.get("query", "")
    documents = data.get("documents", [])
    response = generate_summary(query, documents)
    return jsonify({"summary": response})

@app.route("/segment", methods=["POST", "OPTIONS"])
def segment():
    """
    文本分词接口，用于前端调试，返回分词结果。
    """
    if request.method == "OPTIONS":
        # 直接返回 200 响应，允许预检通过
        return '', 200
    try:
        data = request.get_json()
        text = data.get("text", "")
        tokens = tokenize(text)
        return jsonify({"tokens": tokens})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/docs/<doc_id>")
def get_document(doc_id):
    """
    获取文档内容。
    :param doc_id: 文档ID（文件名）
    :return: 文档内容
    """
    try:
        # 从缓存中获取文档内容
        content = search_engine.documents.get(doc_id)
        if content is None:
            # 如果缓存中没有，尝试从文件系统读取
            file_path = os.path.join(DOCS_PATH, doc_id)
            if not os.path.exists(file_path):
                return jsonify({"error": "Document not found"}), 404
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        
        # 返回文档内容
        return jsonify({
            "doc_id": doc_id,
            "content": content
        })
    except Exception as e:
        print(f"[ERROR] 获取文档失败：{e}")
        return jsonify({"error": str(e)}), 500

@app.route("/")
def index_page():
    return "信息检索系统 API 已启动，支持 /api/search 接口。"

if __name__ == "__main__":
    # 在启动服务器前初始化应用
    init_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
