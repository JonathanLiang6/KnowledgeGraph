"""
Embedding 服务 - v2.1 自包含实现
仅依赖 torch + tokenizers（纯 Rust），零 scipy/sklearn/transformers 依赖。
解决 Windows 下 scipy C 扩展 ABI 不兼容问题。
"""
import os
import json
import logging
import threading
from typing import List, Optional
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from tokenizers import Tokenizer

from app.core.config import config

logger = logging.getLogger(__name__)

# ─── 全局状态 ─────────────────────────────────────────────────────

_embedding_model = None
_model_lock = threading.Lock()

# v4.1 (#51): 本地模型目录从 EMBEDDING_MODEL 派生（此前硬编码 bge-small-zh-v1.5，
# 修改 EMBEDDING_MODEL 配置时实际加载路径不变，配置形同虚设）
MODEL_NAME = config.EMBEDDING_MODEL  # "BAAI/bge-small-zh-v1.5"
MODEL_DIR = os.path.join(config.DATA_DIR, "models", MODEL_NAME.split("/")[-1])


# ─── 最小 BERT 模型（仅编码器，无依赖）───────────────────────────


class BertSelfAttention(nn.Module):
    """BERT Self-Attention（无 dropout）"""
    def __init__(self, hidden_size: int, num_attention_heads: int):
        super().__init__()
        if hidden_size % num_attention_heads != 0:
            raise ValueError(f"hidden_size {hidden_size} not divisible by num_heads {num_attention_heads}")
        self.num_heads = num_attention_heads
        self.head_dim = hidden_size // num_attention_heads
        self.all_head_size = num_attention_heads * self.head_dim
        self.query = nn.Linear(hidden_size, self.all_head_size)
        self.key = nn.Linear(hidden_size, self.all_head_size)
        self.value = nn.Linear(hidden_size, self.all_head_size)

    def forward(self, hidden_states: torch.Tensor, attention_mask: torch.Tensor):
        batch_size = hidden_states.size(0)
        seq_len = hidden_states.size(1)

        def reshape(x):
            return x.view(batch_size, -1, self.num_heads, self.head_dim).transpose(1, 2)

        q = reshape(self.query(hidden_states))
        k = reshape(self.key(hidden_states))
        v = reshape(self.value(hidden_states))

        scores = torch.matmul(q, k.transpose(-2, -1)) / (self.head_dim ** 0.5)
        # attention_mask: 1 for valid, 0 for padding → large negative for padding
        mask = (1.0 - attention_mask[:, None, None, :]) * -10000.0
        scores = scores + mask
        attn = F.softmax(scores, dim=-1)
        context = torch.matmul(attn, v)
        context = context.transpose(1, 2).contiguous().view(batch_size, -1, self.all_head_size)
        return context


class BertSelfOutput(nn.Module):
    def __init__(self, hidden_size: int):
        super().__init__()
        self.dense = nn.Linear(hidden_size, hidden_size)
        self.LayerNorm = nn.LayerNorm(hidden_size, eps=1e-12)

    def forward(self, hidden_states, input_tensor):
        return self.LayerNorm(self.dense(hidden_states) + input_tensor)


class BertAttention(nn.Module):
    def __init__(self, hidden_size: int, num_attention_heads: int):
        super().__init__()
        self.self_attn = BertSelfAttention(hidden_size, num_attention_heads)
        self.self_output = BertSelfOutput(hidden_size)

    def forward(self, hidden_states, attention_mask):
        attn_out = self.self_attn(hidden_states, attention_mask)
        return self.self_output(attn_out, hidden_states)


class BertIntermediate(nn.Module):
    def __init__(self, hidden_size: int, intermediate_size: int):
        super().__init__()
        self.dense = nn.Linear(hidden_size, intermediate_size)

    def forward(self, hidden_states):
        return F.gelu(self.dense(hidden_states))


class BertOutput(nn.Module):
    def __init__(self, intermediate_size: int, hidden_size: int):
        super().__init__()
        self.dense = nn.Linear(intermediate_size, hidden_size)
        self.out_norm = nn.LayerNorm(hidden_size, eps=1e-12)

    def forward(self, hidden_states, input_tensor):
        return self.out_norm(self.dense(hidden_states) + input_tensor)


class BertLayer(nn.Module):
    def __init__(self, hidden_size: int, num_attention_heads: int, intermediate_size: int):
        super().__init__()
        self.attn_layer = BertAttention(hidden_size, num_attention_heads)
        self.inter_layer = BertIntermediate(hidden_size, intermediate_size)
        self.out_layer = BertOutput(intermediate_size, hidden_size)

    def forward(self, hidden_states, attention_mask):
        attn_out = self.attn_layer(hidden_states, attention_mask)
        return self.out_layer(self.inter_layer(attn_out), attn_out)


class BertEmbeddings(nn.Module):
    def __init__(self, vocab_size: int, hidden_size: int, max_position_embeddings: int,
                 type_vocab_size: int):
        super().__init__()
        self.word_embeddings = nn.Embedding(vocab_size, hidden_size, padding_idx=0)
        self.position_embeddings = nn.Embedding(max_position_embeddings, hidden_size)
        self.token_type_embeddings = nn.Embedding(type_vocab_size, hidden_size)
        self.LayerNorm = nn.LayerNorm(hidden_size, eps=1e-12)

    def forward(self, input_ids, token_type_ids=None):
        seq_len = input_ids.size(1)
        position_ids = torch.arange(seq_len, dtype=torch.long, device=input_ids.device).unsqueeze(0)

        words = self.word_embeddings(input_ids)
        positions = self.position_embeddings(position_ids)

        if token_type_ids is None:
            token_type_ids = torch.zeros_like(input_ids)
        token_types = self.token_type_embeddings(token_type_ids)

        return self.LayerNorm(words + positions + token_types)


class BertEncoder(nn.Module):
    def __init__(self, hidden_size: int, num_hidden_layers: int, num_attention_heads: int,
                 intermediate_size: int):
        super().__init__()
        self.layer = nn.ModuleList([
            BertLayer(hidden_size, num_attention_heads, intermediate_size)
            for _ in range(num_hidden_layers)
        ])

    def forward(self, hidden_states, attention_mask):
        for layer in self.layer:
            hidden_states = layer(hidden_states, attention_mask)
        return hidden_states


class BertModel(nn.Module):
    """最小 BERT 模型 — 仅编码器，用于生成句子嵌入"""

    def __init__(self, config_dict: dict):
        super().__init__()
        self.embeddings = BertEmbeddings(
            vocab_size=config_dict["vocab_size"],
            hidden_size=config_dict["hidden_size"],
            max_position_embeddings=config_dict["max_position_embeddings"],
            type_vocab_size=config_dict["type_vocab_size"],
        )
        self.encoder = BertEncoder(
            hidden_size=config_dict["hidden_size"],
            num_hidden_layers=config_dict["num_hidden_layers"],
            num_attention_heads=config_dict["num_attention_heads"],
            intermediate_size=config_dict["intermediate_size"],
        )

    def forward(self, input_ids, attention_mask, token_type_ids=None):
        embedding = self.embeddings(input_ids, token_type_ids)
        encoder_output = self.encoder(embedding, attention_mask)
        return encoder_output


# ─── 模型加载（线程安全）───────────────────────────────────────────


def _load_model():
    """
    加载 BGE 模型：config.json + model.safetensors + tokenizer.json。
    完全绕过 transformers/sentence-transformers/scipy。
    """
    global _embedding_model

    if _embedding_model is not None:
        return _embedding_model

    with _model_lock:
        if _embedding_model is not None:
            return _embedding_model

        model_path = MODEL_DIR

        # 如果本地没有，尝试从 HF Hub 下载
        if not os.path.exists(os.path.join(model_path, "config.json")):
            _download_model(model_path)

        # 加载配置
        config_path = os.path.join(model_path, "config.json")
        with open(config_path, "r") as f:
            cfg = json.load(f)

        logger.info(f"加载 Embedding 模型: {MODEL_NAME} (dim={cfg['hidden_size']})")

        # 创建模型结构
        model = BertModel(cfg)
        model.eval()

        # 加载权重（优先 safetensors，回退 pytorch_model.bin）
        safetensors_path = os.path.join(model_path, "model.safetensors")
        bin_path = os.path.join(model_path, "pytorch_model.bin")

        if os.path.exists(safetensors_path):
            from safetensors.torch import load_file
            state_dict = load_file(safetensors_path)
        elif os.path.exists(bin_path):
            state_dict = torch.load(bin_path, map_location="cpu", weights_only=True)
        else:
            raise FileNotFoundError(f"模型权重文件不存在: {safetensors_path}")

        # 处理权重键名：HuggingFace 命名 → 我们的模块名
        # HF: encoder.layer.N.attention.self.query → encoder.layer.N.attn_layer.self_attn.query
        # HF: encoder.layer.N.attention.output.dense → encoder.layer.N.attn_layer.self_output.dense
        # HF: encoder.layer.N.intermediate.dense → encoder.layer.N.inter_layer.dense
        # HF: encoder.layer.N.output.dense → encoder.layer.N.out_layer.dense
        # HF: encoder.layer.N.output.LayerNorm → encoder.layer.N.out_layer.out_norm
        # Also: embeddings.LayerNorm stays, embeddings.word_embeddings stays etc.
        mapped_state = {}
        for key, value in state_dict.items():
            new_key = key
            if key.startswith("bert."):
                new_key = key[5:]  # 去掉 "bert." 前缀
            elif key.startswith("cls."):
                continue  # 跳过分类头

            # HF submodule name → our submodule name
            new_key = new_key.replace(".attention.self.", ".attn_layer.self_attn.")
            new_key = new_key.replace(".attention.output.", ".attn_layer.self_output.")
            new_key = new_key.replace(".intermediate.", ".inter_layer.")
            new_key = new_key.replace(".output.LayerNorm.", ".out_layer.out_norm.")
            new_key = new_key.replace(".output.dense.", ".out_layer.dense.")

            mapped_state[new_key] = value

        model.load_state_dict(mapped_state, strict=False)
        model.to(config.EMBEDDING_DEVICE)

        # 加载分词器
        tokenizer_path = os.path.join(model_path, "tokenizer.json")
        tokenizer = Tokenizer.from_file(tokenizer_path)

        _embedding_model = {
            "model": model,
            "tokenizer": tokenizer,
            "dim": cfg["hidden_size"],
            "max_length": cfg.get("max_position_embeddings", 512),
        }

        # v4.1 (#51): EMBEDDING_DIM 配置接线 — 与模型实际维度不一致时告警
        # （向量索引维度以模型实际输出为准，配置仅作声明性校验）
        if config.EMBEDDING_DIM and config.EMBEDDING_DIM != _embedding_model["dim"]:
            logger.warning(
                f"EMBEDDING_DIM 配置为 {config.EMBEDDING_DIM}，"
                f"但模型 {MODEL_NAME} 实际维度为 {_embedding_model['dim']}，"
                f"以模型实际维度为准（请修正 .env 中的 EMBEDDING_DIM）"
            )

        logger.info(f"Embedding 模型加载完成: dim={cfg['hidden_size']}, device={config.EMBEDDING_DEVICE}")
        return _embedding_model


def _download_model(target_dir: str):
    """从 HuggingFace Hub 下载模型"""
    from huggingface_hub import snapshot_download
    os.makedirs(target_dir, exist_ok=True)
    logger.info(f"下载模型 {MODEL_NAME} 到 {target_dir} ...")
    snapshot_download(MODEL_NAME, local_dir=target_dir)
    logger.info("模型下载完成")


# ─── Embedding 服务 ────────────────────────────────────────────────


class EmbeddingService:
    """
    Embedding 服务 — 自包含实现。
    使用本地 BGE 模型，零外部 ML 库依赖。
    """

    @classmethod
    def encode(cls, texts: List[str]) -> List[List[float]]:
        """
        对文本列表生成向量（同步，用于非 async 上下文）。

        对于 CPU 密集型编码，建议在 async 路由中使用 encode_async()。
        """
        if not texts:
            return []

        model_data = _load_model()
        model = model_data["model"]
        tokenizer = model_data["tokenizer"]
        max_length = model_data["max_length"]
        device = config.EMBEDDING_DEVICE
        batch_size = config.EMBEDDING_BATCH_SIZE

        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            # 分词
            encodings = tokenizer.encode_batch(batch)
            input_ids = []
            attention_masks = []
            for enc in encodings:
                ids = enc.ids[:max_length]
                # 截断到 max_length
                pad_len = max_length - len(ids) if len(ids) < max_length else 0
                ids = ids[:max_length]
                mask = [1] * len(ids) + [0] * pad_len
                ids = ids + [0] * pad_len
                input_ids.append(ids)
                attention_masks.append(mask)

            ids_tensor = torch.tensor(input_ids, dtype=torch.long, device=device)
            mask_tensor = torch.tensor(attention_masks, dtype=torch.float, device=device)

            with torch.no_grad():
                outputs = model(ids_tensor, mask_tensor)
                # Mean pooling（BGE 标准做法）
                mask_expanded = mask_tensor.unsqueeze(-1).expand(outputs.size()).float()
                pooled = (outputs * mask_expanded).sum(1) / mask_expanded.sum(1).clamp(min=1e-9)
                # L2 归一化
                pooled = F.normalize(pooled, p=2, dim=1)

            embeddings = pooled.cpu().numpy()
            all_embeddings.extend(embeddings.tolist())

        return all_embeddings

    @classmethod
    async def encode_async(cls, texts: List[str]) -> List[List[float]]:
        """
        异步编码（在线程池中执行，避免阻塞事件循环）。
        """
        if not texts:
            return []
        import asyncio
        from app.core.cpu_pool import get_cpu_pool
        loop = asyncio.get_running_loop()
        # v4.1 (#51): 使用专用 CPU 线程池（受 CPU_WORKER_THREADS 配置约束）
        return await loop.run_in_executor(get_cpu_pool(), cls.encode, texts)

    @classmethod
    async def encode_single_async(cls, text: str) -> List[float]:
        """单文本异步编码（不阻塞事件循环）"""
        if not text:
            return []
        results = await cls.encode_async([text])
        return results[0] if results else []

    @classmethod
    def encode_single(cls, text: str) -> List[float]:
        """单文本编码"""
        results = cls.encode([text])
        return results[0] if results else []

    @classmethod
    def get_dimension(cls) -> int:
        """获取向量维度"""
        model_data = _load_model()
        return model_data["dim"]
