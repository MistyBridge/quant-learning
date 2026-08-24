# -*- coding: utf-8 -*-
"""
RAG 知识库构建脚本
功能: 加载文档 -> 切片 -> 向量化 -> 存入 Milvus
用法: python scripts/build_rag.py [文档目录]
"""
import os, sys, time, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ============================================================
# 配置
# ============================================================
COLLECTION_NAME = "quant_knowledge"
MODEL_NAME = os.path.expanduser("~/.cache/huggingface/hub/models--BAAI--bge-small-zh-v1.5/snapshots/main")
DIM = 512
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
BATCH_SIZE = 64
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"

# ============================================================
# 1. 加载并切片文档
# ============================================================
def load_and_split(doc_dir):
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_core.documents import Document

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n```", "\n\n", "\n", " "]
    )

    docs = []
    for root, _, files in os.walk(doc_dir):
        for fname in sorted(files):
            if not fname.endswith(".md"):
                continue
            filepath = os.path.join(root, fname)
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
            if len(text.strip()) < 50:
                continue
            chunks = splitter.split_text(text)
            for chunk in chunks:
                docs.append(Document(
                    page_content=chunk,
                    metadata={"source": fname}
                ))

    return docs

# ============================================================
# 2. 创建 Milvus Collection
# ============================================================
def create_collection():
    from pymilvus import (
        connections, Collection, FieldSchema,
        CollectionSchema, DataType, utility
    )

    connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)

    if utility.has_collection(COLLECTION_NAME):
        print(f"Collection '{COLLECTION_NAME}' 已存在，删除重建...")
        utility.drop_collection(COLLECTION_NAME)

    fields = [
        FieldSchema("id", DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema("text", DataType.VARCHAR, max_length=4096),
        FieldSchema("source", DataType.VARCHAR, max_length=256),
        FieldSchema("embedding", DataType.FLOAT_VECTOR, dim=DIM),
    ]
    schema = CollectionSchema(fields, description="Quant knowledge base")
    collection = Collection(COLLECTION_NAME, schema)

    index_params = {
        "metric_type": "COSINE",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 128}
    }
    collection.create_index("embedding", index_params)
    print(f"Collection '{COLLECTION_NAME}' 创建完成")
    return collection

# ============================================================
# 3. 向量化并插入
# ============================================================
def insert_docs(collection, docs, model):
    total = len(docs)
    print(f"\n开始向量化并插入 {total} 个文档片段...")

    for i in range(0, total, BATCH_SIZE):
        batch = docs[i:i + BATCH_SIZE]
        texts = [d.page_content for d in batch]
        sources = [d.metadata.get("source", "") for d in batch]

        embeddings = model.encode(texts, show_progress_bar=False).tolist()

        collection.insert([texts, sources, embeddings])

        done = min(i + BATCH_SIZE, total)
        pct = done / total * 100
        print(f"  [{done}/{total}] {pct:.0f}%", flush=True)

    collection.flush()
    print(f"\n插入完成！共 {collection.num_entities} 条记录")

# ============================================================
# 4. 测试检索
# ============================================================
def test_search(collection, model):
    collection.load()

    test_queries = [
        "怎么获取股票的历史价格数据",
        "如何下单买入股票",
        "均线策略怎么写",
    ]

    print("\n=== 检索测试 ===\n")
    for query in test_queries:
        query_vec = model.encode([query]).tolist()
        results = collection.search(
            data=query_vec,
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {"nprobe": 16}},
            limit=3,
            output_fields=["text", "source"]
        )
        print(f"问题: {query}")
        for hit in results[0]:
            score = hit.score
            source = hit.entity.get("source", "")
            text = hit.entity.get("text", "")[:80].replace("\n", " ")
            print(f"  [{score:.3f}] {source}: {text}...")
        print()

# ============================================================
# 主流程
# ============================================================
def main():
    if len(sys.argv) > 1:
        doc_dir = sys.argv[1]
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        doc_dir = os.path.join(script_dir, "..", "docs", "joinquant_api")

    doc_dir = os.path.normpath(doc_dir)
    if not os.path.isdir(doc_dir):
        print(f"错误: 目录不存在 {doc_dir}")
        sys.exit(1)

    print("=" * 50)
    print("RAG 知识库构建")
    print("=" * 50)
    print(f"文档目录: {doc_dir}")
    print(f"Embedding: {MODEL_NAME}")
    print(f"Milvus: {MILVUS_HOST}:{MILVUS_PORT}")

    # Step 1: 加载文档
    print("\n[1/4] 加载并切片文档...")
    docs = load_and_split(doc_dir)
    print(f"  共 {len(docs)} 个文档片段")
    sources = set(d.metadata["source"] for d in docs)
    print(f"  来源文件: {len(sources)} 个")
    for s in sorted(sources):
        count = sum(1 for d in docs if d.metadata["source"] == s)
        print(f"    {s}: {count} 片段")

    # Step 2: 加载模型
    print(f"\n[2/4] 加载 Embedding 模型 ({MODEL_NAME})...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME)
    print("  模型加载完成")

    # Step 3: 创建 Collection 并插入
    print(f"\n[3/4] 创建 Milvus Collection 并插入向量...")
    collection = create_collection()
    insert_docs(collection, docs, model)

    # Step 4: 测试
    print(f"\n[4/4] 测试检索...")
    test_search(collection, model)

    print("=" * 50)
    print("RAG 知识库构建完成！")
    print("=" * 50)

if __name__ == "__main__":
    main()
