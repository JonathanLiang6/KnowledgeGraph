"""
Embedding 服务 - 优先使用本地 BGE 模型，回退到 DeepSeek API
"""
import logging
from typing import List
from app.core.config import config

logger = logging.getLogger(__name__)

# 延迟加载本地模型（启动时按需初始化）
_local_model = None


def _get_local_model():
    """懒加载本地 SentenceTransformer 模型"""
    global _local_model
    if _local_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"加载本地 Embedding 模型: {config.EMBEDDING_MODEL}")
            _local_model = SentenceTransformer(
                config.EMBEDDING_MODEL,
                device=config.EMBEDDING_DEVICE,
            )
            logger.info(f"本地 Embedding 模型加载完成 (dim={_local_model.get_sentence_embedding_dimension()})")
        except Exception as e:
            logger.warning(f"本地 Embedding 模型加载失败: {e}，将回退到 DeepSeek API")
            _local_model = None
    return _local_model


class EmbeddingService:
    """
    Embedding 服务封装。
    优先使用本地 BGE 模型（快速、免费），失败时回退到 DeepSeek API。
    """

    @classmethod
    def encode(cls, texts: List[str]) -> List[List[float]]:
        """
        对文本列表生成向量

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        if not texts:
            return []

        # 尝试本地模型
        model = _get_local_model()
        if model is not None:
            try:
                embeddings = model.encode(
                    texts,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
                return [emb.tolist() for emb in embeddings]
            except Exception as e:
                logger.warning(f"本地 Embedding 失败: {e}")

        # 回退到 DeepSeek API（异步调用包装为同步）
        logger.info("使用 DeepSeek API 进行 Embedding")
        return cls._deepseek_encode(texts)

    @classmethod
    def encode_single(cls, text: str) -> List[float]:
        """对单个文本生成向量"""
        results = cls.encode([text])
        return results[0] if results else []

    @classmethod
    def _deepseek_encode(cls, texts: List[str]) -> List[List[float]]:
        """回退方案：使用 DeepSeek API"""
        import asyncio
        from app.services.deepseek_client import DeepSeekClient

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 在异步上下文中，创建新的事件循环
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run, DeepSeekClient.embed(texts)
                    )
                    return future.result(timeout=60)
            else:
                return loop.run_until_complete(DeepSeekClient.embed(texts))
        except Exception as e:
            logger.error(f"DeepSeek Embedding 失败: {e}")
            # 最终回退：返回零向量
            import numpy as np
            dim = config.EMBEDDING_DIM
            logger.warning(f"回退到零向量 (dim={dim})")
            return [np.zeros(dim).tolist() for _ in texts]

    @classmethod
    @property
    def dimension(cls) -> int:
        """获取向量维度"""
        model = _get_local_model()
        if model is not None:
            return model.get_sentence_embedding_dimension()
        return config.EMBEDDING_DIM
