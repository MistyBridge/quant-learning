# -*- coding: utf-8 -*-
"""
RAG 知识库查询工具
用法: python scripts/query_rag.py "你的问题"
交互模式: python scripts/query_rag.py
"""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

MODEL_PATH = os.path.expanduser("~/.cache/huggingface/hub/models--BAAI--bge-small-zh-v1.5/snapshots/main")
COLLECTION_NAME = "quant_knowledge"

def search(query, collection, model, top_k=5):
    collection.load()
    query_vec = model.encode([query]).tolist()
    results = collection.search(
        data=query_vec,
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {"nprobe": 16}},
        limit=top_k,
        output_fields=["text", "source"]
    )
    hits = []
    for hit in results[0]:
        hits.append({
            "text": hit.entity.get("text"),
            "source": hit.entity.get("source"),
            "score": hit.score
        })
    return hits

def main():
    from sentence_transformers import SentenceTransformer
    from pymilvus import connections, Collection

    print("正在加载模型和连接数据库...")
    model = SentenceTransformer(MODEL_PATH)
    connections.connect("default", host="localhost", port="19530")
    collection = Collection(COLLECTION_NAME)
    print(f"就绪！知识库共 {collection.num_entities} 条记录\n")

    # 命令行参数模式
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        hits = search(query, collection, model)
        print(f"问题: {query}\n")
        for i, h in enumerate(hits, 1):
            print(f"--- [{i}] 相似度: {h['score']:.3f} | 来源: {h['source']} ---")
            print(h["text"])
            print()
        return

    # 交互模式
    print("=" * 50)
    print("聚宽 API 知识库问答（输入 q 退出）")
    print("=" * 50)
    while True:
        try:
            query = input("\n你的问题: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not query or query.lower() == 'q':
            break

        hits = search(query, collection, model, top_k=3)
        for i, h in enumerate(hits, 1):
            print(f"\n--- [{i}] 相似度: {h['score']:.3f} | 来源: {h['source']} ---")
            print(h["text"])

    print("\n再见！")

if __name__ == "__main__":
    main()
