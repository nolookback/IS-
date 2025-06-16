import math
from collections import defaultdict
import time

class Timer:
    def __init__(self, name=""):
        self.name = name
        self.start = None
        self.end = None
        self.interval = 0

    def __enter__(self):
        self.start = time.time()
        return self
    
    def __exit__(self, *args):
        self.end = time.time()
        self.interval = self.end - self.start
        if self.name:
            print(f"[Timer] {self.name} 耗时: {self.interval * 1000:.2f} ms")
    
    @property
    def elapsed_ms(self):
        if self.end is None:
            return (time.time() - self.start) * 1000 if self.start else 0
        return self.interval * 1000

def compute_cosine_similarity(vec1: dict, vec2: dict) -> float:
    # 示例余弦相似度实现
    intersection = set(vec1) & set(vec2)
    numerator = sum(vec1[t] * vec2[t] for t in intersection)

    sum1 = sum(val ** 2 for val in vec1.values())
    sum2 = sum(val ** 2 for val in vec2.values())
    denominator = math.sqrt(sum1) * math.sqrt(sum2)

    if denominator == 0:
        return 0.0
    else:
        return numerator / denominator

def sort_results(results: list[tuple[str, float]]) -> list[tuple[str, float]]:
    return sorted(results, key=lambda x: x[1], reverse=True)
