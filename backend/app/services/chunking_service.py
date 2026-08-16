"""
语义分块服务 - 支持语义分块和父子块架构
"""
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """文档块"""
    id: str
    text: str
    parent_id: str | None = None       # 父子块架构中指向父块
    chunk_level: str = "child"            # "parent" or "child"
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "parent_id": self.parent_id,
            "chunk_level": self.chunk_level,
            **self.metadata,
        }


class SemanticChunker:
    """
    语义分块器 - 支持两种策略：
    1. 简单句段分块（基于句子边界 + 段落）
    2. 父子块架构（父块大上下文 + 子块精检索）
    """

    def __init__(
        self,
        parent_chunk_size: int = 1200,
        child_chunk_size: int = 300,
        chunk_overlap: int = 100,
        strategy: str = "parent_child",  # "parent_child" or "sentence"
    ):
        self.parent_chunk_size = parent_chunk_size
        self.child_chunk_size = child_chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy

    def chunk(self, text: str, doc_id: str = "") -> list[Chunk]:
        """对文本分块，返回 Chunk 列表"""
        if self.strategy == "parent_child":
            return self._parent_child_chunk(text, doc_id)
        else:
            return self._sentence_chunk(text, doc_id)

    def _parent_child_chunk(self, text: str, doc_id: str) -> list[Chunk]:
        """
        父子块架构：
        - 父块：较大的上下文窗口，用于 LLM 回答
        - 子块：较小的精度块，用于向量检索
        LanceDB 仅存储子块向量，检索时返回对应父块。
        """
        paragraphs = self._split_paragraphs(text)
        chunks = []
        parent_idx = 0
        child_idx = 0

        # 先构建父块
        parent_chunks = []
        current = ""
        for para in paragraphs:
            if len(current) + len(para) > self.parent_chunk_size and current:
                parent_id = f"{doc_id}_p{parent_idx}"
                parent_chunks.append(Chunk(
                    id=parent_id,
                    text=current.strip(),
                    chunk_level="parent",
                    metadata={"doc_id": doc_id, "para_range": f"{parent_idx}"},
                ))
                current = para
                parent_idx += 1
            else:
                current += ("\n" if current else "") + para

        if current.strip():
            parent_id = f"{doc_id}_p{parent_idx}"
            parent_chunks.append(Chunk(
                id=parent_id,
                text=current.strip(),
                chunk_level="parent",
                metadata={"doc_id": doc_id, "para_range": f"{parent_idx}"},
            ))

        # 对每个父块构建子块
        for parent in parent_chunks:
            sentences = self._split_sentences(parent.text)
            sub_current = ""
            for sent in sentences:
                if len(sub_current) + len(sent) > self.child_chunk_size and sub_current:
                    child_id = f"{doc_id}_c{child_idx}"
                    chunks.append(Chunk(
                        id=child_id,
                        text=sub_current.strip(),
                        parent_id=parent.id,
                        chunk_level="child",
                        metadata={"doc_id": doc_id},
                    ))
                    sub_current = sent
                    child_idx += 1
                else:
                    sub_current += sent

            if sub_current.strip():
                child_id = f"{doc_id}_c{child_idx}"
                chunks.append(Chunk(
                    id=child_id,
                    text=sub_current.strip(),
                    parent_id=parent.id,
                    chunk_level="child",
                    metadata={"doc_id": doc_id},
                ))
                child_idx += 1

            # 父块也加入输出（用于检索后还原上下文）
            chunks.append(parent)

        logger.info(f"父子分块完成: {len(parent_chunks)} 父块, {child_idx} 子块")
        return chunks

    def _sentence_chunk(self, text: str, doc_id: str) -> list[Chunk]:
        """基于句子的简单分块"""
        sentences = self._split_sentences(text)
        chunks = []
        current = ""
        idx = 0

        for sent in sentences:
            if len(current) + len(sent) > self.child_chunk_size and current:
                chunks.append(Chunk(
                    id=f"{doc_id}_c{idx}",
                    text=current.strip(),
                    chunk_level="child",
                    metadata={"doc_id": doc_id},
                ))
                # 重叠处理
                overlap_text = current[-self.chunk_overlap:] if len(current) > self.chunk_overlap else ""
                current = overlap_text + sent
                idx += 1
            else:
                current += sent

        if current.strip():
            chunks.append(Chunk(
                id=f"{doc_id}_c{idx}",
                text=current.strip(),
                chunk_level="child",
                metadata={"doc_id": doc_id},
            ))

        return chunks

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """按中英文句子边界分割"""
        # 匹配中英文句子结束符
        sentences = re.split(r'(?<=[。！？.!?\n])\s*', text)
        return [s for s in sentences if s.strip()]

    @staticmethod
    def _split_paragraphs(text: str) -> list[str]:
        """按段落分割（双换行或 Markdown 标题边界）"""
        # 先在标题前分割
        parts = re.split(r'(\n#{1,6}\s)', text)
        paragraphs = []
        for i, part in enumerate(parts):
            if part.strip():
                if i > 0 and re.match(r'#{1,6}\s', parts[i - 1].strip()):
                    paragraphs[-1] = parts[i - 1] + part
                else:
                    paragraphs.append(part)

        # 合并结果并按双换行继续分割
        result = []
        for para in paragraphs:
            sub_paras = para.split('\n\n')
            result.extend([p.strip() for p in sub_paras if p.strip()])

        return result

    @staticmethod
    def get_parent_text(child_chunk: Chunk, all_chunks: list[Chunk]) -> str:
        """给定子块，返回父块的完整文本"""
        if child_chunk.parent_id:
            for chunk in all_chunks:
                if chunk.id == child_chunk.parent_id:
                    return chunk.text
        return child_chunk.text
