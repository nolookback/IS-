import numpy as np
from typing import List, Tuple
from collections import Counter
import jieba
import re
from .tokenizer import tokenize

class QueryCorrector:
    def __init__(self, inverted_index: dict, vocabulary: set):
        """
        初始化查询纠错器
        :param inverted_index: 倒排索引
        :param vocabulary: 词汇表
        """
        self.inverted_index = inverted_index
        self.vocabulary = vocabulary
        self.word_freq = self._calculate_word_frequency()
        
    def _calculate_word_frequency(self) -> dict:
        """计算词频统计"""
        word_freq = {}
        for term, postings in self.inverted_index.items():
            word_freq[term] = len(postings)
        return word_freq

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """计算两个字符串之间的编辑距离"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    def _get_candidates(self, word: str, max_distance: int = 2) -> List[Tuple[str, int]]:
        """获取候选词列表"""
        candidates = []
        for vocab_word in self.vocabulary:
            distance = self._levenshtein_distance(word, vocab_word)
            if distance <= max_distance:
                # 使用词频作为权重
                weight = self.word_freq.get(vocab_word, 0)
                candidates.append((vocab_word, weight))
        
        # 按权重排序
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:3]  # 返回前3个候选词

    def correct_query(self, query: str) -> List[str]:
        """
        对查询进行纠错和建议
        :param query: 原始查询
        :return: 候选查询列表
        """
        # 分词
        words = tokenize(query)
        corrected_queries = []
        
        # 对每个词进行纠错
        for i, word in enumerate(words):
            if word in self.vocabulary:
                continue
                
            candidates = self._get_candidates(word)
            if candidates:
                # 生成候选查询
                for candidate, _ in candidates:
                    new_query = words.copy()
                    new_query[i] = candidate
                    corrected_queries.append(''.join(new_query))
        
        # 如果没有找到纠错建议，返回原始查询
        if not corrected_queries:
            return [query]
            
        return corrected_queries[:3]  # 返回最多3个候选查询 