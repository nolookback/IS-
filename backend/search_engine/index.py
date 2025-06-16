import os
import sys
import math
import json
import time
from collections import defaultdict, Counter
from typing import Dict, List, Tuple
from .tokenizer import tokenize
from .utils import compute_cosine_similarity, Timer
sys.stdout.reconfigure(encoding='utf-8')

class SearchEngine:
    def __init__(self):
        # 倒排索引：term -> list of (doc_id, tf)
        self.index = defaultdict(list)
        # 位置索引：term -> dict(doc_id -> list of positions)
        self.positional_index = defaultdict(dict)
        # 文档词频：doc_id -> Counter(term -> count)
        self.doc_term_freq = {}
        # 文档总数 & 文档长度信息
        self.doc_count = 0
        self.doc_ids = []
        self.doc_norm = {}  # 每个文档的向量长度（用于余弦相似度）
        # 文档内容缓存
        self.documents = {}
        # IDF 缓存
        self.idf = {}

    def build_index(self, docs_dir: str):
        """
        构建倒排索引和位置索引。
        :param docs_dir: 文档目录，每个 .txt 为一个文档
        """
        for filename in os.listdir(docs_dir):
            if filename.endswith(".txt"):
                doc_id = filename
                path = os.path.join(docs_dir, filename)
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
                    self.documents[doc_id] = text  # 缓存文档内容
                    terms = tokenize(text)   # 分词
                    term_freq = Counter(terms)    # 统计文档内词频
                    self.doc_term_freq[doc_id] = term_freq
                    self.doc_ids.append(doc_id)
                    
                    # 构建倒排索引和位置索引
                    for pos, term in enumerate(terms):
                        # 更新倒排索引
                        if not any(doc_id == d for d, _ in self.index[term]):
                            self.index[term].append((doc_id, term_freq[term]))
                        
                        # 更新位置索引
                        if doc_id not in self.positional_index[term]:
                            self.positional_index[term][doc_id] = []
                        self.positional_index[term][doc_id].append(pos)

        self.doc_count = len(self.doc_ids)
        self._compute_idf()
        self._compute_doc_norm()

    def _compute_idf(self):
        """
        计算每个 term 的逆文档频率 IDF
        """
        for term, posting in self.index.items():
            df = len(posting)
            self.idf[term] = math.log((self.doc_count + 1) / (df + 1)) + 1  # 平滑

    def _compute_doc_norm(self):
        """
        预计算每个文档的向量长度（余弦相似度分母）
        """
        for doc_id in self.doc_ids:
            term_freq = self.doc_term_freq[doc_id]
            norm = 0.0
            for term, tf in term_freq.items():
                tfidf = tf * self.idf.get(term, 0)
                norm += tfidf ** 2
            self.doc_norm[doc_id] = math.sqrt(norm)

    def proximity_search(self, terms: List[str], max_distance: int = 5) -> List[Dict]:
        """
        执行邻近搜索
        :param terms: 搜索词列表
        :param max_distance: 词之间的最大距离
        :return: 匹配的文档列表
        """
        if len(terms) < 2:
            return []
            
        results = []
        # 获取包含所有搜索词的文档
        common_docs = set.intersection(*[set(self.positional_index[term].keys()) for term in terms])
        
        for doc_id in common_docs:
            # 获取每个词在文档中的位置
            positions = [self.positional_index[term][doc_id] for term in terms]
            
            # 检查是否存在满足距离要求的词序
            found = False
            for pos1 in positions[0]:
                for pos2 in positions[1]:
                    if abs(pos2 - pos1) <= max_distance:
                        found = True
                        break
                if found:
                    break
            
            if found:
                # 获取文档内容
                content = self.documents.get(doc_id, "")
                # 生成摘要（简单截取前200个字符）
                snippet = content[:200] + "..." if len(content) > 200 else content
                
                results.append({
                    "doc_id": doc_id,
                    "score": 1.0,  # 邻近搜索的简单评分
                    "snippet": snippet,
                    "link": f"/docs/{doc_id}"
                })
        
        return results

    def query(self, query_text: str, top_k=10, use_proximity=False) -> Tuple[List[Dict], float]:
        """
        查询接口，支持普通搜索和邻近搜索
        :param query_text: 用户输入的 query
        :param top_k: 返回文档数
        :param use_proximity: 是否使用邻近搜索
        :return: (results, elapsed_ms)
        """
        results = []
        elapsed_ms = 0.0
        
        with Timer(name="搜索查询") as timer:
            # 添加延时以模拟搜索过程
            time.sleep(0.000001)  
            
            query_terms = tokenize(query_text)
            
            if use_proximity and len(query_terms) >= 2:
                # 使用邻近搜索
                results = self.proximity_search(query_terms)
            else:
                # 使用普通向量空间模型搜索
                query_tf = Counter(query_terms)
                
                # 构建 query 向量
                query_vec = {}
                for term, tf in query_tf.items():
                    idf = self.idf.get(term, 0)
                    query_vec[term] = tf * idf
                
                query_norm = math.sqrt(sum([v ** 2 for v in query_vec.values()]))
                
                if query_norm != 0:
                    # 计算余弦相似度
                    scores = defaultdict(float)
                    for term, q_wt in query_vec.items():
                        for doc_id, tf in self.index.get(term, []):
                            doc_wt = tf * self.idf.get(term, 0)
                            scores[doc_id] += q_wt * doc_wt
                    
                    # 归一化
                    for doc_id in scores:
                        scores[doc_id] /= (self.doc_norm.get(doc_id, 1e-9) * query_norm)
                    
                    # 排序取前 top-k
                    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
                    
                    # 构建返回结果
                    for doc_id, score in ranked:
                        content = self.documents.get(doc_id, "")
                        snippet = content[:200] + "..." if len(content) > 200 else content
                        results.append({
                            "doc_id": doc_id,
                            "score": score,
                            "snippet": snippet,
                            "link": f"/docs/{doc_id}"
                        })
            
            elapsed_ms = timer.elapsed_ms
            
        return results, elapsed_ms

    def save(self, path: str):
        """
        将索引保存到 json 文件
        """
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "index": self.index,
                "positional_index": self.positional_index,
                "idf": self.idf,
                "doc_ids": self.doc_ids,
                "documents": self.documents
            }, f, ensure_ascii=False, indent=2)

    def load(self, path: str):
        """
        从 json 文件加载索引
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.index = defaultdict(list, {k: v for k, v in data["index"].items()})
            self.positional_index = defaultdict(dict, {k: v for k, v in data["positional_index"].items()})
            self.idf = data["idf"]
            self.doc_ids = data["doc_ids"]
            self.documents = data["documents"]
            # 重新构建 doc_term_freq 和 norm
            for doc_id in self.doc_ids:
                self.doc_term_freq[doc_id] = Counter()
            self._compute_doc_norm()
