import os
import sys
import math
import json
import time
import re
import struct
import zlib
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set, Any
from .tokenizer import tokenize
from .utils import compute_cosine_similarity, Timer
sys.stdout.reconfigure(encoding='utf-8')

class CompressedIndex:
    """压缩索引类，用于优化存储空间"""
    def __init__(self):
        self.term_to_docids = {}  # term -> 压缩的docid列表
        self.term_to_tfs = {}     # term -> 压缩的tf列表
        self.doc_lengths = {}     # 文档长度信息
        self.doc_contents = {}    # 压缩的文档内容
        self.terms = set()        # 所有词项集合

    def add_posting(self, term: str, doc_id: int, tf: int):
        """添加倒排记录"""
        if term not in self.term_to_docids:
            self.term_to_docids[term] = bytearray()
            self.term_to_tfs[term] = bytearray()
            self.terms.add(term)
        
        # 使用变长编码存储doc_id
        self._encode_varint(doc_id, self.term_to_docids[term])
        # 使用变长编码存储tf
        self._encode_varint(tf, self.term_to_tfs[term])

    def add_document(self, doc_id: int, content: str, length: int):
        """添加文档内容"""
        # 压缩文档内容
        compressed = zlib.compress(content.encode('utf-8'))
        self.doc_contents[doc_id] = compressed
        self.doc_lengths[doc_id] = length

    def keys(self):
        """返回所有词项"""
        return self.terms

    def get_postings(self, term: str) -> List[Tuple[int, int]]:
        """获取倒排记录"""
        if term not in self.term_to_docids:
            return []
        
        docids = self._decode_varints(self.term_to_docids[term])
        tfs = self._decode_varints(self.term_to_tfs[term])
        return list(zip(docids, tfs))

    def get_document(self, doc_id: int) -> str:
        """获取文档内容"""
        if doc_id not in self.doc_contents:
            return ""
        return zlib.decompress(self.doc_contents[doc_id]).decode('utf-8')

    def _encode_varint(self, value: int, buffer: bytearray):
        """变长整数编码"""
        while value > 0x7f:
            buffer.append((value & 0x7f) | 0x80)
            value >>= 7
        buffer.append(value)

    def _decode_varints(self, buffer: bytearray) -> List[int]:
        """变长整数解码"""
        result = []
        value = 0
        shift = 0
        for byte in buffer:
            value |= (byte & 0x7f) << shift
            if byte & 0x80 == 0:
                result.append(value)
                value = 0
                shift = 0
            else:
                shift += 7
        return result

class SearchEngine:
    def __init__(self):
        # 使用压缩索引替代原来的索引结构
        self.index = CompressedIndex()
        # 文档总数 & 文档长度信息
        self.doc_count = 0
        self.doc_ids = []
        self.doc_norm = {}  # 每个文档的向量长度
        # IDF 缓存
        self.idf = {}
        # 词项到文档频率的映射
        self.term_df = defaultdict(int)
        # 文档词频：doc_id -> Counter(term -> count)
        self.doc_term_freq = {}

    def build_index(self, docs_dir: str):
        """
        构建压缩索引
        :param docs_dir: 文档目录，每个 .txt 为一个文档
        """
        for filename in os.listdir(docs_dir):
            if filename.endswith(".txt"):
                doc_id = len(self.doc_ids)  # 使用数字ID
                self.doc_ids.append(filename)
                path = os.path.join(docs_dir, filename)
                
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
                    terms = tokenize(text)
                    term_freq = Counter(terms)
                    
                    # 存储文档词频
                    self.doc_term_freq[doc_id] = term_freq

                    # 更新文档频率
                    for term in set(terms):
                        self.term_df[term] += 1
                    
                    # 添加倒排记录
                    for term, tf in term_freq.items():
                        self.index.add_posting(term, doc_id, tf)
                    
                    # 添加文档内容
                    self.index.add_document(doc_id, text, len(terms))

        self.doc_count = len(self.doc_ids)
        self._compute_idf()
        self._compute_doc_norm()
        # print("[DEBUG] Index Building Completed. First 10 IDF values:")
        # for i, (term, idf_val) in enumerate(self.idf.items()):
        #     if i >= 10: break
        #     print(f"[DEBUG]   Term: {term}, IDF: {idf_val}")
        # print("[DEBUG] Index Building Completed. First 10 Doc Norm values:")
        # for i in range(min(10, self.doc_count)):
        #     print(f"[DEBUG]   Doc ID: {i}, Doc Norm: {self.doc_norm.get(i)}")

    def _compute_idf(self):
        """
        计算每个 term 的逆文档频率 IDF
        """
        for term, df in self.term_df.items():
            self.idf[term] = math.log((self.doc_count + 1) / (df + 1)) + 1

    def _compute_doc_norm(self):
        """
        预计算每个文档的向量长度
        """
        for doc_id in range(self.doc_count):
            norm = 0.0
            # 使用存储的doc_term_freq来计算范数
            term_freq = self.doc_term_freq.get(doc_id, Counter())
            # print(f"[DEBUG] Doc ID: {doc_id}, Term Freq: {term_freq}")
            for term, tf in term_freq.items():
                idf_val = self.idf.get(term, 0)
                tfidf = tf * idf_val
                #print(f"[DEBUG] Term: {term}, TF: {tf}, IDF: {idf_val}, TFIDF: {tfidf}") 
                norm += tfidf ** 2
            self.doc_norm[doc_id] = math.sqrt(norm)
            # print(f"[DEBUG] Doc ID: {doc_id}, Final Norm: {self.doc_norm[doc_id]}") 

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

    def _match_wildcard(self, pattern: str, terms: Set[str]) -> List[str]:
        """
        匹配通配符模式
        :param pattern: 通配符模式，支持 * 和 ?
        :param terms: 词项集合
        :return: 匹配的词项列表
        """
        # 将通配符模式转换为正则表达式
        regex_pattern = pattern.replace('*', '.*').replace('?', '.')
        regex = re.compile(f'^{regex_pattern}$')
        
        # 返回所有匹配的词项
        return [term for term in terms if regex.match(term)]

    def _expand_wildcard_query(self, query_terms: List[str]) -> List[str]:
        """
        展开包含通配符的查询词
        :param query_terms: 原始查询词列表
        :return: 展开后的查询词列表
        """
        expanded_terms = []
        all_terms = self.index.keys()  # 获取所有索引词项
        
        for term in query_terms:
            if '*' in term or '?' in term:
                # 如果包含通配符，展开匹配的词项
                matched_terms = self._match_wildcard(term, all_terms)
                expanded_terms.extend(matched_terms)
            else:
                # 不包含通配符，直接添加
                expanded_terms.append(term)
        
        return expanded_terms

    def query(self, query_text: str, top_k=10, use_proximity=False) -> Tuple[List[Dict], float]:
        """
        查询接口，支持普通搜索、邻近搜索和通配符查询
        """
        results = []
        elapsed_ms = 0.0
        
        with Timer(name="搜索查询") as timer:
            time.sleep(0.000001)
            
            query_terms = tokenize(query_text)
            expanded_terms = self._expand_wildcard_query(query_terms)
            
            if use_proximity and len(expanded_terms) >= 2:
                results = self.proximity_search(expanded_terms)
            else:
                query_tf = Counter(expanded_terms)
                query_vec = {}
                
                for term, tf in query_tf.items():
                    idf = self.idf.get(term, 0)
                    query_vec[term] = tf * idf
                
                query_norm = math.sqrt(sum([v ** 2 for v in query_vec.values()]))
                
                if query_norm != 0:
                    scores = defaultdict(float)
                    for term, q_wt in query_vec.items():
                        for doc_id, tf in self.index.get_postings(term):
                            doc_wt = tf * self.idf.get(term, 0)
                            scores[doc_id] += q_wt * doc_wt
                    
                    for doc_id in scores:
                        doc_norm_val = self.doc_norm.get(doc_id, 1e-9)
                        scores[doc_id] /= (doc_norm_val * query_norm)
                    
                    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
                    
                    for doc_id, score in ranked:
                        content = self.index.get_document(doc_id)
                        snippet = content[:200] + "..." if len(content) > 200 else content
                        results.append({
                            "doc_id": self.doc_ids[doc_id],
                            "score": score,
                            "snippet": snippet,
                            "link": f"/docs/{self.doc_ids[doc_id]}"
                        })
            
            elapsed_ms = timer.elapsed_ms
            
        return results, elapsed_ms

    def save(self, path: str):
        """
        将压缩索引保存到文件
        """
        with open(path, "wb") as f:
            # 保存文档ID列表
            f.write(struct.pack("!I", len(self.doc_ids)))
            for doc_id in self.doc_ids:
                f.write(struct.pack("!H", len(doc_id)))
                f.write(doc_id.encode('utf-8'))
            
            # 将bytearray转换为list of int以便JSON序列化
            serializable_term_to_docids = {k: list(v) for k, v in self.index.term_to_docids.items()}
            serializable_term_to_tfs = {k: list(v) for k, v in self.index.term_to_tfs.items()}
            serializable_doc_contents = {k: list(v) for k, v in self.index.doc_contents.items()}

            # 保存索引数据
            index_data = {
                "term_df": dict(self.term_df),
                "idf": self.idf,
                "doc_norm": self.doc_norm,
                "doc_count": self.doc_count,
                "compressed_index_terms": list(self.index.terms),
                "compressed_index_term_to_docids": serializable_term_to_docids,
                "compressed_index_term_to_tfs": serializable_term_to_tfs,
                "compressed_index_doc_contents": serializable_doc_contents,
                "compressed_index_doc_lengths": self.index.doc_lengths,
                "doc_term_freq": {k: dict(v) for k, v in self.doc_term_freq.items()}
            }
            f.write(zlib.compress(json.dumps(index_data).encode('utf-8')))

    def load(self, path: str):
        """
        从文件加载压缩索引
        """
        with open(path, "rb") as f:
            # 加载文档ID列表
            doc_count = struct.unpack("!I", f.read(4))[0]
            self.doc_ids = []
            for _ in range(doc_count):
                length = struct.unpack("!H", f.read(2))[0]
                doc_id = f.read(length).decode('utf-8')
                self.doc_ids.append(doc_id)
            
            # 加载索引数据
            compressed_data = f.read()
            index_data = json.loads(zlib.decompress(compressed_data).decode('utf-8'))
            self.term_df = defaultdict(int, index_data["term_df"])
            self.idf = index_data["idf"]
            self.doc_norm = {int(k): v for k, v in index_data["doc_norm"].items()}
            self.doc_count = index_data["doc_count"]
            
            # 加载CompressedIndex数据，并从list of int转换回bytearray或bytes
            self.index.terms = set(index_data["compressed_index_terms"])
            self.index.term_to_docids = {k: bytearray(v) for k, v in index_data["compressed_index_term_to_docids"].items()}
            self.index.term_to_tfs = {k: bytearray(v) for k, v in index_data["compressed_index_term_to_tfs"].items()}
            self.index.doc_contents = {int(k): bytes(v) for k, v in index_data["compressed_index_doc_contents"].items()}
            self.index.doc_lengths = index_data["compressed_index_doc_lengths"]
            # 加载doc_term_freq
            self.doc_term_freq = {int(k): Counter(v) for k, v in index_data["doc_term_freq"].items()}
            
            # print("[DEBUG] Index Loading Completed. First 10 IDF values:")
            # for i, (term, idf_val) in enumerate(self.idf.items()):
            #     if i >= 10: break
            #     print(f"[DEBUG]   Term: {term}, IDF: {idf_val}")
            # print("[DEBUG] Index Loading Completed. First 10 Doc Norm values:")
            # for i in range(min(10, self.doc_count)):
            #     print(f"[DEBUG]   Doc ID: {i}, Doc Norm: {self.doc_norm.get(i)}")
