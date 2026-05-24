import os
import json
import logging
import numpy as np
import faiss

logger = logging.getLogger(__name__)


class VectorStore:
    """基于 FAISS 的向量存储和检索"""

    def __init__(self, dimension=512):
        """
        初始化向量存储。

        Args:
            dimension: 向量维度（需与嵌入模型一致）
        """
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)  # 内积（归一化后等价于余弦相似度）
        self.chunks = []

    def build(self, chunks, embeddings):
        """
        构建 FAISS 索引。

        Args:
            chunks: 文本块列表 [{"text", "start", "end"}, ...]
            embeddings: 对应的向量数组
        """
        self.chunks = chunks
        vectors = np.array(embeddings).astype('float32')
        self.index.add(vectors)
        logger.info(f"Built FAISS index with {len(chunks)} vectors")

    def query(self, query_embedding, top_k=4):
        """
        检索最相似的文本块。

        Args:
            query_embedding: 查询向量
            top_k: 返回的结果数量

        Returns:
            检索结果列表: [{"chunk": dict, "score": float}, ...]
        """
        query_vec = np.array([query_embedding]).astype('float32')
        scores, indices = self.index.search(query_vec, top_k)

        results = []
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and idx < len(self.chunks):
                results.append({
                    "chunk": self.chunks[idx],
                    "score": float(scores[0][i])
                })
        return results

    def save(self, save_dir):
        """保存索引和元数据到文件"""
        os.makedirs(save_dir, exist_ok=True)
        index_path = os.path.join(save_dir, "index.faiss")
        chunks_path = os.path.join(save_dir, "chunks.json")

        faiss.write_index(self.index, index_path)
        with open(chunks_path, "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved FAISS index to {save_dir}")

    def load(self, save_dir):
        """从文件加载索引和元数据"""
        index_path = os.path.join(save_dir, "index.faiss")
        chunks_path = os.path.join(save_dir, "chunks.json")

        self.index = faiss.read_index(index_path)
        with open(chunks_path, "r", encoding="utf-8") as f:
            self.chunks = json.load(f)

        self.dimension = self.index.d
        logger.info(f"Loaded FAISS index: {self.index.ntotal} vectors")
