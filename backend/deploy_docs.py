"""部署示例文档到正确的知识库目录 (v3.2: 按KB名称命名文件夹)"""
import os

base = os.path.join(os.path.dirname(__file__), "inputs", "files")

DOCS = {
    "初中化学": {
        "元素周期表与化学式.md": r"""# 元素周期表与化学式
...""",
        "酸碱盐基础.md": r"""# 酸碱盐基础
...""",
    },
}

# 实际文档内容太长，此处省略，直接调用 API 或手动上传即可
if __name__ == "__main__":
    for kb_name, docs in DOCS.items():
        kb_dir = os.path.join(base, kb_name)
        os.makedirs(kb_dir, exist_ok=True)
        for filename, content in docs.items():
            filepath = os.path.join(kb_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        print(f"{kb_name}: {len(docs)} 个文档已写入")
    print("完成")
