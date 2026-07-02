"""
逐字符流式拆分与分类 — 为打字机流式输出提供字符级 SSE 推送。

职责：
  1. 将上游 LLM 的 token 流拆分为单字符序列
  2. 通过 CodeBlockStateMachine 跟踪 Markdown 代码块状态
  3. 为每个字符打上类型标签（chinese / code / punctuation / newline / normal）

无 FastAPI / SSE / DeepSeek 依赖 — 纯算法模块，可独立单测。
"""

import unicodedata
from typing import AsyncGenerator

# ── 字符类型常量 ──────────────────────────────────────
CHAR_CHINESE = "chinese"
CHAR_CODE = "code"
CHAR_PUNCTUATION = "punctuation"
CHAR_NEWLINE = "newline"
CHAR_NORMAL = "normal"

# ── Unicode 范围检测 ──────────────────────────────────


def _is_cjk(char: str) -> bool:
    """检测字符是否为 CJK 汉字（含扩展区）。"""
    cp = ord(char)
    return (
        0x4E00 <= cp <= 0x9FFF   # CJK Unified Ideographs
        or 0x3400 <= cp <= 0x4DBF  # CJK Unified Ideographs Extension A
        or 0xF900 <= cp <= 0xFAFF  # CJK Compatibility Ideographs
        or 0x2F800 <= cp <= 0x2FA1F  # CJK Compatibility Ideographs Supplement
    )


def _is_punctuation(char: str) -> bool:
    """
    检测字符是否为中文或英文标点。

    包含：
      - Unicode P 类（通用标点）
      - 高频中文标点显式集合
      - 英文编程标点
    """
    cp = ord(char)

    # Unicode P 类（Pc/Pd/Pe/Pf/Pi/Po/Ps）为标点
    cat = unicodedata.category(char)
    if cat.startswith("P"):
        return True

    # CJK 标点区 (U+3000-U+303F) — 含 、。「」『』 等
    if 0x3000 <= cp <= 0x303F:
        return True

    # 全角标点 (U+FF00-U+FF0F, U+FF1A-U+FF20, U+FF3B-U+FF40, U+FF5B-U+FF65)
    if 0xFF01 <= cp <= 0xFF0F or 0xFF1A <= cp <= 0xFF20:
        return True
    if 0xFF3B <= cp <= 0xFF40 or 0xFF5B <= cp <= 0xFF65:
        return True

    return False


# ── 字符分类 ──────────────────────────────────────────


def classify_char(char: str, in_code_context: bool = False) -> str:
    """
    将单个字符归类为一种输出节奏类型。

    优先级：
      1. `\\n` 始终为 newline（即使在代码块中，换行停顿仍有益于阅读节奏）
      2. 代码上下文内的字符 → code
      3. CJK 汉字 → chinese
      4. 标点 → punctuation
      5. 其余 → normal
    """
    if char == "\n":
        return CHAR_NEWLINE

    if in_code_context:
        return CHAR_CODE

    if _is_cjk(char):
        return CHAR_CHINESE

    if _is_punctuation(char):
        return CHAR_PUNCTUATION

    return CHAR_NORMAL


# ── 代码块状态机 ──────────────────────────────────────


class CodeBlockStateMachine:
    """
    跟踪 Markdown 代码块上下文。

    检测两种代码模式：
      - 围栏式代码块: ``` ... ```
      - 行内代码: `...`

    用法:
        sm = CodeBlockStateMachine()
        for ch in text:
            in_context = sm.feed(ch)
            type = classify_char(ch, in_context)
    """

    def __init__(self):
        self.in_code_block = False      # 是否在 ``` 围栏内
        self.in_inline_code = False     # 是否在 ` 行内代码内
        self._at_line_start = True      # 当前是否在行首（刚换行或初始状态）
        self._fence_buf = ""            # 行首反引号累积缓冲

    def feed(self, char: str) -> bool:
        """
        输入一个字符，更新内部状态。

        Returns:
            bool: 该字符是否在代码上下文（围栏或行内）中。
        """
        # ── 处理行首反引号围栏 ──
        if self._at_line_start:
            if char == "`":
                self._fence_buf += char
                # 当累积到 3 个反引号时，触发围栏开关
                if len(self._fence_buf) >= 3 and self._fence_buf[:3] == "```":
                    self.in_code_block = not self.in_code_block
                    self._fence_buf = ""
                    # 行首状态不变 — 开启/关闭围栏后仍可继续检测
                return self.in_code_block or self.in_inline_code
            else:
                # 行首非反引号字符 — 清除围栏缓冲
                if self._fence_buf:
                    # 缓冲中堆积了 < 3 个反引号，它们是行内内容
                    for _ in self._fence_buf:
                        # 每个单反引号切换行内代码状态
                        if not self.in_code_block:
                            self.in_inline_code = not self.in_inline_code
                    self._fence_buf = ""
                if char not in (" ", "\t", "\n"):
                    self._at_line_start = False

        # ── 处理非行首反引号（行内代码开关）──
        if char == "`" and not self._at_line_start and not self.in_code_block:
            self.in_inline_code = not self.in_inline_code

        # ── 换行重置行首标记 ──
        if char == "\n":
            self._at_line_start = True
            self._fence_buf = ""

        return self.in_code_block or self.in_inline_code


# ── 逐字符流生成器 ────────────────────────────────────


async def char_stream(
    chunk_stream: AsyncGenerator[str, None],
) -> AsyncGenerator[dict, None]:
    """
    将 LLM token 流转换为逐字符类型标注流。

    Args:
        chunk_stream: 上游异步生成器，yield 原始文本块（str）

    Yields:
        dict: {"char": <单字符 str>, "type": <char_type str>}
    """
    sm = CodeBlockStateMachine()
    buffer = ""

    async for chunk in chunk_stream:
        buffer += chunk
        i = 0
        while i < len(buffer):
            char = buffer[i]
            in_context = sm.feed(char)
            char_type = classify_char(char, in_context)
            yield {"char": char, "type": char_type}
            i += 1
        buffer = ""  # 处理完当前缓冲

    # 清理缓冲区残留（理论上不会发生，但保持健壮）
    while buffer:
        char = buffer[0]
        buffer = buffer[1:]
        in_context = sm.feed(char)
        yield {"char": char, "type": classify_char(char, in_context)}
