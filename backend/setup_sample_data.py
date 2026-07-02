"""
v3.2 示例数据生成脚本
创建 4 个知识库 + Markdown 文档：化学、计算机科学、AI Agent、RAG
"""
import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import async_session_factory, init_db
from app.models.knowledge_base import KnowledgeBase
from app.models.topology import TopologyNode, TopologyEdge
from sqlalchemy import select


MARKDOWN_DOCS = {
    "化学": [
        {
            "filename": "有机化学基础.md",
            "content": """# 有机化学基础

## 1. 有机化合物概述

有机化学是研究含碳化合物的结构、性质、组成、反应和制备的化学分支。碳原子能够形成四个共价键，这是有机化合物多样性的基础。

### 1.1 碳的杂化轨道

碳原子通过 **sp³、sp² 和 sp** 杂化轨道形成单键、双键和三键：
- **sp³ 杂化**：四个等价的杂化轨道，指向正四面体的四个顶点（如甲烷 CH₄），键角约 109.5°
- **sp² 杂化**：三个杂化轨道在同一平面，夹角 120°（如乙烯 C₂H₄），剩余一个 p 轨道形成 π 键
- **sp 杂化**：两个杂化轨道呈直线排列，夹角 180°（如乙炔 C₂H₂），剩余两个 p 轨道形成两个 π 键

## 2. 官能团分类

| 官能团 | 结构 | 示例 | 特征反应 |
|--------|------|------|----------|
| 羟基 | -OH | 乙醇 C₂H₅OH | 酯化、氧化 |
| 羰基 | >C=O | 丙酮 CH₃COCH₃ | 亲核加成 |
| 羧基 | -COOH | 乙酸 CH₃COOH | 酸性、酯化 |
| 氨基 | -NH₂ | 甲胺 CH₃NH₂ | 碱性、酰化 |
| 卤素 | -X | 氯甲烷 CH₃Cl | 亲核取代 |

## 3. 重要反应类型

### 3.1 亲核取代反应 (SN1 / SN2)

**SN2 反应**特征：
- 双分子速率决定步骤
- 构型翻转（瓦尔登翻转）
- 偏好伯卤代烃
- 极性非质子溶剂有利

**SN1 反应**特征：
- 单分子速率决定步骤
- 外消旋化
- 偏好叔卤代烃
- 极性质子溶剂有利

### 3.2 消除反应 (E1 / E2)

E2 反应中，碱夺取 β-氢的同时离去基团离去，形成双键。查依采夫规则指出：主要产物是双键上取代基较多的烯烃。
""",
        },
        {
            "filename": "化学热力学与动力学.md",
            "content": """# 化学热力学与动力学

## 热力学基础

### 热力学第一定律

能量既不会凭空产生，也不会凭空消失，只能从一种形式转化为另一种形式。

$$\\Delta U = Q - W$$

其中 $\\Delta U$ 为内能变化，$Q$ 为吸收的热量，$W$ 为对外做的功。

### 吉布斯自由能

$$\\Delta G = \\Delta H - T\\Delta S$$

- $\\Delta G < 0$：反应自发进行
- $\\Delta G = 0$：反应达到平衡
- $\\Delta G > 0$：反应非自发

### 化学平衡常数

对于反应 $aA + bB \\rightleftharpoons cC + dD$：

$$K_c = \\frac{[C]^c[D]^d}{[A]^a[B]^b}$$

## 化学动力学

### 反应速率方程

对于反应 $A + B \\rightarrow C$，速率方程通常表示为：

$$r = k[A]^m[B]^n$$

其中 $k$ 为速率常数，$m$ 和 $n$ 为反应级数（需实验确定）。

### 阿伦尼乌斯方程

$$k = Ae^{-E_a/RT}$$

$E_a$ 为活化能，$A$ 为指前因子，$R$ 为气体常数。

### 催化剂作用机理

催化剂通过降低反应的活化能来加速反应，自身在反应前后保持不变。催化剂的类型包括：
- **均相催化剂**：与反应物处于同一相
- **多相催化剂**：与反应物处于不同相（如固体催化剂催化气体反应）
- **酶催化剂**：生物催化剂，具有高度专一性
""",
        },
    ],
    "计算机科学": [
        {
            "filename": "数据结构与算法.md",
            "content": """# 数据结构与算法

## 常用数据结构

### 数组与链表

| 操作 | 数组 | 链表 |
|------|------|------|
| 随机访问 | O(1) | O(n) |
| 插入/删除 | O(n) | O(1) |
| 空间利用 | 连续内存 | 分散存储 |
| 缓存友好 | 是 | 否 |

### 栈与队列

- **栈 (Stack)**：后进先出 (LIFO)，用于函数调用、括号匹配、撤销操作
- **队列 (Queue)**：先进先出 (FIFO)，用于 BFS、任务调度、消息队列
- **优先队列 (Priority Queue)**：基于堆实现，每次取出优先级最高的元素

### 二叉搜索树 (BST)

左子树所有节点值 < 根节点值 < 右子树所有节点值。

**平衡二叉树 (AVL Tree)**：
- 任意节点的左右子树高度差不超过 1
- 插入/删除后通过旋转操作恢复平衡
- 查找、插入、删除均为 O(log n)

### 哈希表

通过哈希函数将键映射到槽位。解决冲突的方法：
1. **链地址法** — 每个槽位维护一个链表
2. **开放地址法** — 线性探测/二次探测/双重哈希

## 经典算法

### 排序算法对比

| 算法 | 最优 | 平均 | 最差 | 空间 | 稳定 |
|------|------|------|------|------|------|
| 快速排序 | O(n log n) | O(n log n) | O(n²) | O(log n) | 否 |
| 归并排序 | O(n log n) | O(n log n) | O(n log n) | O(n) | 是 |
| 堆排序 | O(n log n) | O(n log n) | O(n log n) | O(1) | 否 |
| 插入排序 | O(n) | O(n²) | O(n²) | O(1) | 是 |

### 图算法

**Dijkstra 最短路径**：
- 贪心策略，每次选择距离起点最近的未访问节点
- 不能处理负权边
- 使用优先队列优化后时间复杂度 O(E log V)

**A* 搜索**：
- 启发式搜索，$f(n) = g(n) + h(n)$
- $g(n)$：从起点到节点 n 的实际代价
- $h(n)$：从节点 n 到目标的估计代价（启发函数）
- 当 $h(n)$ 可接受（不高估）时保证找到最优解
""",
        },
        {
            "filename": "操作系统原理.md",
            "content": """# 操作系统原理

## 进程管理

### 进程状态转换

进程在其生命周期中经历以下状态切换：
- **就绪态 (Ready)** → **运行态 (Running)**：被调度器选中
- **运行态** → **就绪态**：时间片用完
- **运行态** → **阻塞态 (Blocked)**：等待 I/O 或事件
- **阻塞态** → **就绪态**：I/O 完成或事件到达

### 进程调度算法

| 算法 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| FCFS | 先来先服务 | 简单公平 | 护航效应 |
| SJF | 最短作业优先 | 最小平均等待时间 | 长作业可能饥饿 |
| Round Robin | 时间片轮转 | 公平响应快 | 上下文切换开销 |
| 多级反馈队列 | 动态优先级调整 | 兼顾交互与批处理 | 实现复杂 |

## 内存管理

### 虚拟内存

每个进程拥有独立的虚拟地址空间，通过 **MMU (Memory Management Unit)** 映射到物理内存。

### 分页系统

- 物理内存划分为固定大小的**帧 (Frame)**
- 逻辑内存划分为相同大小的**页 (Page)**
- 页表维护页号到帧号的映射

### 页面置换算法

当物理内存满时需要换出页面：
1. **FIFO**：换出最早进入的页面（Belady 异常）
2. **LRU**：换出最久未使用的页面
3. **Clock 算法**：LRU 的近似实现，使用访问位
4. **LFU**：换出使用频率最低的页面

## 文件系统

### inode 结构

Unix/Linux 文件系统中，每个文件对应一个 inode，存储：
- 文件类型与权限
- 所有者与组信息
- 文件大小
- 数据块指针（直接、间接、双重间接、三重间接）
- 时间戳（访问时间、修改时间、状态变更时间）
""",
        },
    ],
    "AI Agent": [
        {
            "filename": "ReAct Agent 设计模式.md",
            "content": """# ReAct Agent 设计模式

## 概述

ReAct (Reasoning + Acting) 是一种将推理与行动交织进行的 Agent 架构范式。Agent 在每一步中首先进行推理（Thought），然后采取行动（Action），观察结果（Observation），并根据观察调整后续推理。

## 核心流程

```
用户问题 → Thought → Action → Observation → Thought → Action → ... → Final Answer
```

### 1. Thought（思考）

Agent 分析当前状态，决定需要什么信息、下一步做什么。思考内容包括：
- 分解复杂问题为子问题
- 评估已有信息是否充分
- 规划工具调用策略
- 反思之前的行动结果

### 2. Action（行动）

Agent 选择并调用工具。常用工具类型：
- **检索工具**：向量搜索、关键词搜索、图谱遍历
- **计算工具**：数学计算、代码执行
- **外部工具**：API 调用、数据库查询、网络搜索

### 3. Observation（观察）

工具返回的结果。Agent 需要：
- 理解工具输出的结构和含义
- 判断信息是否相关和充分
- 决定是否继续调用工具

## 工具注册机制

```python
TOOL_REGISTRY = {
    "vector_search": {
        "function": vector_search,
        "description": "语义向量检索",
        "parameters": {"query": "搜索查询文本"},
    },
    "graph_traverse": {
        "function": graph_traverse,
        "description": "知识图谱多跳遍历",
        "parameters": {"entity_name": "起始实体", "max_hops": "最大跳数"},
    },
}
```

## 置信度回退策略

当本地检索结果的最高相似度低于阈值（如 0.6）时，Agent 应：
1. 判断是否需要联网搜索
2. 告知用户当前知识库的局限性
3. 如果启用了联网功能，调用 web_search 工具

## 记忆系统

### 三层记忆架构

| 层级 | 作用域 | 存储内容 | 生命周期 |
|------|--------|----------|----------|
| 工作记忆 | 单次推理 | Thought-Action-Observation | 一次 Agent 调用 |
| 情景记忆 | 对话会话 | Q&A 对话摘要 | 单次会话 |
| 语义记忆 | 知识库 | 结构化知识图谱 | 持久化 |

工作记忆使 Agent 能够参考之前的推理步骤，避免重复调用相同的工具或陷入循环。
""",
        },
        {
            "filename": "Multi-Agent 协作框架.md",
            "content": """# Multi-Agent 协作框架

## 概述

Multi-Agent 系统由多个自治的 Agent 组成，它们通过通信、协调和协作来完成单个 Agent 无法完成的复杂任务。

## 协作模式

### 1. 层次式 (Hierarchical)

一个管理者 Agent 将任务分解并分配给多个执行者 Agent。

```
          ┌─────────┐
          │ Manager │
          └────┬────┘
      ┌────────┼────────┐
  ┌───┴───┐ ┌───┴───┐ ┌───┴───┐
  │Worker1│ │Worker2│ │Worker3│
  └───────┘ └───────┘ └───────┘
```

### 2. 对话式 (Debate)

多个 Agent 通过讨论和辩论达成共识。例如：
- 一个 Agent 提出方案
- 另一个 Agent 批判和质疑
- 通过多轮辩论优化最终答案

### 3. 投票式 (Voting)

多个 Agent 独立生成答案，通过投票机制选择最佳答案。可以结合：
- 多数投票 (Majority Voting)
- 加权投票 (Weighted Voting)
- 置信度筛选

## 通信协议

### 消息格式

```json
{
  "from": "agent_researcher",
  "to": "agent_writer",
  "type": "research_result",
  "content": "...",
  "metadata": {
    "confidence": 0.85,
    "sources": ["source1", "source2"]
  }
}
```

### 黑板模式 (Blackboard)

所有 Agent 共享一个公共知识库（黑板），各自读取和写入信息：
- 优点：松耦合，便于扩展
- 缺点：难以保证信息一致性

## Agent 评估指标

- **任务完成率**：成功完成任务的比例
- **工具使用效率**：完成任务所需的平均工具调用次数
- **幻觉率**：生成不实信息的比例
- **响应时间**：端到端的响应延迟
- **用户满意度**：基于用户反馈的评分
""",
        },
    ],
    "RAG": [
        {
            "filename": "RAG 系统架构.md",
            "content": """# RAG (Retrieval-Augmented Generation) 系统架构

## 概述

RAG 结合了信息检索与文本生成，在生成回答前先从知识库中检索相关信息，将检索结果作为上下文注入 LLM。

## 核心组件

### 1. 文档处理流水线

```
原始文档 → 文件解析 → 文本清洗 → 语义分块 → 向量嵌入 → 索引构建
```

#### 分块策略

- **固定大小分块**：按 token 数切分（如 512 tokens），重叠 50-100 tokens
- **语义分块**：基于句子边界和语义相似度切分
- **父子块策略**：大块（parent）保留上下文，小块（child）用于精确检索

#### 嵌入模型选择

| 模型 | 维度 | 中文支持 | 适用场景 |
|------|------|----------|----------|
| BGE-small-zh | 512 | 优秀 | 中文语义检索 |
| BGE-large-zh | 1024 | 最优 | 高精度需求 |
| text2vec-large | 1024 | 良好 | 通用场景 |
| M3E-base | 768 | 良好 | 轻量部署 |

### 2. 检索引擎

#### 向量检索

使用近似最近邻（ANN）搜索：
- **LanceDB**：基于 Lance 列存格式，支持增量写入
- **FAISS**：Meta 出品，GPU 加速
- **ChromaDB**：轻量级，易于集成

#### 混合检索 (Hybrid Search)

```
用户查询
  ├── 向量检索 (语义匹配, weight=0.7)
  ├── BM25 关键词检索 (精确匹配, weight=0.3)
  └── 图谱检索 (关系推理, weight=0.3)
              ↓
         RRF 融合排序
              ↓
       Cross-Encoder 重排序
              ↓
           最终结果
```

RRF (Reciprocal Rank Fusion) 公式：

$$RRF(d) = \\sum_{r \\in R} \\frac{1}{k + rank_r(d)}$$

其中 $k=60$ 为平滑常数。

### 3. 生成增强

检索到的文档片段被注入 LLM 的上下文窗口：

```
System: 你是一个知识问答助手。基于以下检索结果回答用户问题。
        [检索结果...]
User: 用户的实际问题
```

关键设计考量：
- **上下文窗口管理**：控制注入的文档总量，不超过模型 token 限制
- **来源引用**：标注每条信息的来源文档
- **相关性排序**：最相关的片段放在提示词最前面或最后面
""",
        },
        {
            "filename": "GraphRAG 与知识图谱增强.md",
            "content": """# GraphRAG 与知识图谱增强

## 从 RAG 到 GraphRAG

传统 RAG 基于非结构化文本检索，存在以下局限：
- 无法理解实体间的关系
- 多跳推理能力弱
- 全局摘要困难

GraphRAG 通过引入知识图谱解决这些问题。

## 知识图谱构建

### 实体抽取

从文本中识别关键实体：
- **命名实体识别 (NER)**：人名、地名、机构名、时间、数值
- **术语抽取**：领域专业术语
- **概念抽取**：抽象概念和类别

### 关系抽取

识别实体间的语义关系：
- 基于规则：`(实体A, 动词短语, 实体B)` → `(实体A, 关系, 实体B)`
- 基于 LLM：使用大模型理解句子语义并抽取关系三元组
- 混合方法：规则匹配 + LLM 精炼

### 实体对齐

合并指代同一实体的不同名称：
- 同义词合并（如 "CNN" 与 "卷积神经网络"）
- 指代消解（如 "它" → 具体实体）
- 属性匹配（同名同类型实体合并）

## 图检索策略

### 局部检索 (Local Search)

1. 用查询匹配种子实体
2. BFS/DFS 展开邻居子图
3. 提取子图中的实体和关系信息
4. 作为上下文注入 LLM

### 全局检索 (Global Search)

1. Louvain 社区检测
2. 对每个社区生成摘要
3. Map-Reduce 合并所有社区摘要
4. 生成全局性回答

适合"总结知识库内容"、"这个领域包含哪些方面"等宏观问题。

## 图增强 Prompt 模板

```
基于知识图谱回答用户问题。

## 相关实体
- 实体A (类型: 概念): 描述...
- 实体B (类型: 人物): 描述...

## 实体间关系
- 实体A → [属于] → 实体B
- 实体A → [提出] → 实体C

## 用户问题
{query}
```

## 社区摘要生成

对于 Louvain 检测到的每个社区：
1. 收集社区内所有实体和关系
2. 选取权重最高的实体作为"代表"
3. 用 LLM 生成该社区的文本摘要
4. 构建全局知识概览
""",
        },
    ],
}


async def setup_sample_data():
    """创建示例知识库、文档，并设置拓扑节点"""
    await init_db()

    async with async_session_factory() as session:
        # 1. 检查是否已有根节点
        root_stmt = select(TopologyNode).where(TopologyNode.is_root == True)
        root_result = await session.execute(root_stmt)
        root = root_result.scalar_one_or_none()

        if not root:
            root = TopologyNode(
                name="我的知识宇宙", icon="🧠", kb_id=None,
                position_x=0, position_y=0, is_root=True,
            )
            session.add(root)
            await session.commit()
            await session.refresh(root)
            print(f"✅ 创建根节点: {root.name}")
        else:
            print(f"ℹ️ 根节点已存在: {root.name}")

        # 2. 创建知识库
        created_kbs = {}
        for kb_name, docs in MARKDOWN_DOCS.items():
            # 检查 KB 是否已存在
            kb_stmt = select(KnowledgeBase).where(KnowledgeBase.name == kb_name)
            kb_result = await session.execute(kb_stmt)
            existing_kb = kb_result.scalar_one_or_none()

            if existing_kb:
                print(f"ℹ️ 知识库已存在: {kb_name}")
                created_kbs[kb_name] = existing_kb
                continue

            kb = KnowledgeBase(name=kb_name, description=f"示例知识库：{kb_name}")
            session.add(kb)
            await session.commit()
            await session.refresh(kb)
            created_kbs[kb_name] = kb
            print(f"✅ 创建知识库: {kb_name} (id={kb.id[:8]}...)")

            # 3. 为每个 KB 创建拓扑节点（连接到根节点）
            node_stmt = select(TopologyNode).where(TopologyNode.kb_id == kb.id)
            node_result = await session.execute(node_stmt)
            existing_node = node_result.scalar_one_or_none()

            if not existing_node:
                node = TopologyNode(
                    name=kb_name,
                    icon="📚",
                    kb_id=kb.id,
                    position_x=0, position_y=0,
                    is_root=False,
                )
                session.add(node)
                await session.commit()
                await session.refresh(node)

                # 连接到根节点
                edge = TopologyEdge(source_id=root.id, target_id=node.id)
                session.add(edge)
                await session.commit()
                print(f"   📎 拓扑节点已创建并连接到根节点")

        # 4. 创建 Markdown 文档文件
        inputs_dir = os.path.join(os.path.dirname(__file__), "inputs", "files")
        os.makedirs(inputs_dir, exist_ok=True)

        for kb_name, docs in MARKDOWN_DOCS.items():
            kb = created_kbs[kb_name]
            kb_dir = os.path.join(inputs_dir, kb.id)
            os.makedirs(kb_dir, exist_ok=True)
            for doc in docs:
                filepath = os.path.join(kb_dir, doc["filename"])
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(doc["content"])
            print(f"📄 {kb_name}: {len(docs)} 个文档已写入 {kb_dir}")

    print(f"\n🎉 示例数据创建完成！")
    print(f"   4 个知识库已就绪")
    print(f"   共 {sum(len(docs) for docs in MARKDOWN_DOCS.values())} 个 Markdown 文档")
    print(f"\n请重启后端服务以处理文档，或通过前端上传。")


if __name__ == "__main__":
    asyncio.run(setup_sample_data())
