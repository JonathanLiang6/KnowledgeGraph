"""
文档解析器 - 支持 PDF, DOCX, Markdown, TXT
"""
import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def read_file_content(filepath: str) -> Optional[str]:
    """
    解析文件内容，根据扩展名调用对应的解析器。
    返回文件文本内容，解析失败返回 None。
    """
    ext = Path(filepath).suffix.lower()

    if not os.path.exists(filepath):
        logger.error(f"文件不存在: {filepath}")
        return None

    parsers = {
        ".txt": _read_text,
        ".md": _read_text,
        ".markdown": _read_text,
        ".pdf": _read_pdf,
        ".docx": _read_docx,
    }

    parser = parsers.get(ext)
    if parser is None:
        logger.warning(f"不支持的文件类型: {ext}")
        return _read_text(filepath)  # 尝试直接读取

    try:
        return parser(filepath)
    except Exception as e:
        logger.error(f"解析文件失败 {filepath}: {e}")
        return None


def _read_text(filepath: str) -> str:
    """读取纯文本文件"""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def _read_pdf(filepath: str) -> str:
    """读取 PDF 文件"""
    from PyPDF2 import PdfReader

    reader = PdfReader(filepath)
    texts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            texts.append(text.strip())
    return "\n\n".join(texts)


def _read_docx(filepath: str) -> str:
    """读取 Word 文档"""
    from docx import Document

    doc = Document(filepath)
    texts = []
    for para in doc.paragraphs:
        if para.text.strip():
            # 根据样式区分标题和正文
            if para.style.name.startswith("Heading"):
                level = para.style.name.split()[-1]
                try:
                    level_num = int(level)
                    prefix = "#" * level_num
                except ValueError:
                    prefix = "#"
                texts.append(f"{prefix} {para.text.strip()}")
            else:
                texts.append(para.text.strip())
    return "\n\n".join(texts)


def get_file_info(filepath: str) -> dict:
    """获取文件基本信息"""
    path = Path(filepath)
    ext = path.suffix.lower()
    type_map = {
        ".md": "Markdown",
        ".markdown": "Markdown",
        ".txt": "Text",
        ".pdf": "PDF",
        ".docx": "Word",
    }
    return {
        "name": path.name,
        "path": str(path),
        "size": path.stat().st_size if path.exists() else 0,
        "type": type_map.get(ext, "Unknown"),
    }
