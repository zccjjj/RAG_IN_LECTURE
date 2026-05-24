import logging
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """文本向量化模型封装"""

    def __init__(self, model_name="BAAI/bge-small-zh-v1.5"):
        """
        初始化嵌入模型。

        Args:
            model_name: sentence-transformers 模型名称
                - "BAAI/bge-small-zh-v1.5": 中文向量化模型
                - "all-MiniLM-L6-v2": 英文/多语言模型
        """
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"Embedding dimension: {self.dimension}")

    def encode(self, texts):
        """
        将文本列表编码为向量。

        Args:
            texts: 文本列表

        Returns:
            numpy 数组，形状为 (len(texts), dimension)
        """
        if not texts:
            return np.array([])
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return embeddings

    def encode_single(self, text):
        """编码单条文本"""
        return self.encode([text])[0]
