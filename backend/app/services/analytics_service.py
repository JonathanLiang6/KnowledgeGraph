"""
知识覆盖分析服务 - v3.2 Q9

提供知识库实体分类聚合与覆盖诊断功能。
使用内置关键词映射表将实体归类，支持前端 ECharts Treemap 渲染。
"""
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.graph_entity import GraphEntity

logger = logging.getLogger(__name__)

# 内置关键词映射表：关键词 → 分类名
CATEGORY_KEYWORDS: Dict[str, str] = {
    # 编程语言
    "Python": "编程语言", "Java": "编程语言", "JavaScript": "编程语言",
    "TypeScript": "编程语言", "C++": "编程语言", "Go": "编程语言",
    "Rust": "编程语言", "C": "编程语言", "Ruby": "编程语言",
    "PHP": "编程语言", "Swift": "编程语言", "Kotlin": "编程语言",
    # 深度学习
    "CNN": "深度学习", "RNN": "深度学习", "LSTM": "深度学习",
    "Transformer": "深度学习", "BERT": "深度学习", "GPT": "深度学习",
    "GAN": "深度学习", "ResNet": "深度学习", "注意力机制": "深度学习",
    "深度学习": "深度学习", "神经网络": "深度学习", "反向传播": "深度学习",
    "BatchNorm": "深度学习", "Dropout": "深度学习",
    # 机器学习
    "机器学习": "机器学习", "监督学习": "机器学习", "无监督学习": "机器学习",
    "强化学习": "机器学习", "迁移学习": "机器学习", "SVM": "机器学习",
    "决策树": "机器学习", "随机森林": "机器学习", "XGBoost": "机器学习",
    "逻辑回归": "机器学习", "K-Means": "机器学习",
    "PCA": "机器学习", "梯度下降": "机器学习",
    # 自然语言处理
    "NLP": "自然语言处理", "自然语言处理": "自然语言处理",
    "分词": "自然语言处理", "词向量": "自然语言处理",
    "Word2Vec": "自然语言处理", "Tokenization": "自然语言处理",
    # 计算机视觉
    "CV": "计算机视觉", "计算机视觉": "计算机视觉",
    "图像识别": "计算机视觉", "目标检测": "计算机视觉",
    "图像分割": "计算机视觉", "YOLO": "计算机视觉",
    # 数据库
    "SQL": "数据库", "MySQL": "数据库", "PostgreSQL": "数据库",
    "MongoDB": "数据库", "Redis": "数据库", "SQLite": "数据库",
    "数据库": "数据库", "索引": "数据库",
    # 数学/统计
    "数学": "数学与统计", "概率": "数学与统计", "线性代数": "数学与统计",
    "微积分": "数学与统计", "统计学": "数学与统计",
    # 操作系统
    "Linux": "操作系统", "操作系统": "操作系统", "进程": "操作系统",
    "内存管理": "操作系统", "文件系统": "操作系统",
    # 网络
    "HTTP": "计算机网络", "TCP": "计算机网络", "IP": "计算机网络",
    "DNS": "计算机网络", "网络协议": "计算机网络", "Socket": "计算机网络",
    # AI 伦理/安全
    "安全": "安全与伦理", "隐私": "安全与伦理", "加密": "安全与伦理",
    "AI伦理": "安全与伦理", "对抗攻击": "安全与伦理",
    # 强化学习
    "Q-Learning": "强化学习", "DQN": "强化学习", "Policy Gradient": "强化学习",
    "马尔可夫": "强化学习", "PPO": "强化学习",
    # 知识图谱
    "知识图谱": "知识图谱", "图数据库": "知识图谱", "Neo4j": "知识图谱",
    "RDF": "知识图谱", "本体": "知识图谱",
    # 框架/工具
    "PyTorch": "框架与工具", "TensorFlow": "框架与工具", "Keras": "框架与工具",
    "Docker": "框架与工具", "Kubernetes": "框架与工具", "Git": "框架与工具",
    "FastAPI": "框架与工具", "Vue": "框架与工具", "React": "框架与工具",
}


class AnalyticsService:
    """知识覆盖分析服务 — 所有方法均为 staticmethod，无状态"""

    @staticmethod
    def _classify_entity(name: str, entity_type: str) -> str:
        """
        根据实体名称和类型进行分类。

        策略：
        1. 精确匹配关键词映射表
        2. 部分关键词匹配
        3. 基于实体类型分类（如"人物"→"人物与组织"）
        4. 未命中归为"通用/其他"
        """
        # 精确匹配
        if name in CATEGORY_KEYWORDS:
            return CATEGORY_KEYWORDS[name]

        # 部分匹配（关键词包含在实体名中）
        best_match = None
        best_len = 0
        for keyword, category in CATEGORY_KEYWORDS.items():
            if keyword.lower() in name.lower() and len(keyword) > best_len:
                best_match = category
                best_len = len(keyword)

        if best_match:
            return best_match

        # 按实体类型归类
        type_mapping = {
            "人物": "人物与组织",
            "组织": "人物与组织",
            "地点": "地点与地理",
            "学科": "学科与领域",
            "理论": "理论与概念",
            "概念": "理论与概念",
            "方法": "方法与技术",
            "技术": "方法与技术",
            "应用": "应用与实践",
            "事件": "事件与历史",
        }
        if entity_type in type_mapping:
            return type_mapping[entity_type]

        return "通用/其他"

    @staticmethod
    async def get_kb_coverage(db: AsyncSession, kb_id: str) -> List[dict]:
        """
        获取知识库的实体覆盖分析。

        Returns:
            [{"name": "分类名", "count": 实体数, "last_updated_days": 最近更新距今天数}, ...]
        """
        # 获取该 KB 下所有实体
        stmt = select(GraphEntity).where(GraphEntity.kb_id == kb_id)
        result = await db.execute(stmt)
        entities = result.scalars().all()

        if not entities:
            return []

        # 归类聚合
        category_entities: Dict[str, list] = {}
        for e in entities:
            cat = AnalyticsService._classify_entity(e.name, e.entity_type)
            if cat not in category_entities:
                category_entities[cat] = []
            category_entities[cat].append(e)

        # 构建返回数据
        now = datetime.now(timezone.utc)
        coverage = []
        for cat, ents in category_entities.items():
            # 计算最近更新天数
            last_updated = max(
                (e.updated_at for e in ents if e.updated_at),
                default=now,
            )
            if last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=timezone.utc)
            days = max(0, (now - last_updated).days)

            coverage.append({
                "name": cat,
                "count": len(ents),
                "last_updated_days": days,
            })

        return coverage
