import hashlib
from typing import List

EMBEDDING_DIM = 384


def embed_text(text: str) -> List[float]:
    """Embedding hash-based 384 chiều — không cần model, không tốn API."""
    if not text:
        text = " "
    vec = [0.0] * EMBEDDING_DIM
    tokens = text.lower().split()
    if not tokens:
        tokens = [" "]
    for tok in tokens:
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
        idx = h % EMBEDDING_DIM
        sign = 1.0 if (h >> 16) & 1 else -1.0
        vec[idx] += sign
    norm = sum(x * x for x in vec) ** 0.5
    if norm == 0:
        return vec
    return [x / norm for x in vec]


def vec_to_pg(embedding: List[float]) -> str:
    """Chuyển list float thành chuỗi pgvector."""
    return "[" + ",".join(str(x) for x in embedding) + "]"