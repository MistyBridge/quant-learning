# RAG 知识库搭建指南

> 本文档记录了基于 Milvus 向量数据库搭建 RAG（检索增强生成）知识库的完整流程。
> 适用于后续扩展数据库、接入新的文档源。

---

## 一、整体架构

```
文档源 -> 文档处理(切片+清洗) -> 向量化(Embedding) -> Milvus存储
                                                       |
用户提问 -> 问题向量化 -> Milvus检索(Top-K) <-----------+
                       |
                拼装Prompt(资料+问题) -> LLM -> 回答
```

## 二、环境依赖

### 2.1 基础设施

| 组件 | 用途 | 启动方式 |
|------|------|--------|
| Docker Desktop | 容器运行环境 | Windows 托盘启动（需管理员权限） |
| Milvus | 向量数据库 | cd infra/milvus && docker compose up -d |
| Attu | Milvus Web 管理界面 | 随 Milvus 一起启动，访问 localhost:8000 |

### 2.2 Docker 镜像

所有镜像存储在 D:\DockerData\wsl\disk\docker_data.vhdx。

镜像拉取使用 DaoCloud 镜像源（国内加速）：

```bash
docker pull docker.m.daocloud.io/milvusdb/milvus:v2.5.11
docker pull docker.m.daocloud.io/minio/minio:RELEASE.2023-03-20T20-16-18Z
docker pull quay.io/coreos/etcd:v3.5.18
docker pull docker.m.daocloud.io/zilliz/attu:v2.5
```

### 2.3 Python 依赖

```bash
pip install pymilvus sentence-transformers langchain langchain-community
```

---

## 三、文档采集

### 3.1 聚宽数据字典（API 接口）

聚宽数据字典通过 HTTP API 直接获取，无需浏览器渲染。

**接口**: `GET https://www.joinquant.com/help/api/getContent?name={板块名}&token={TOKEN}`

**获取 token**: 访问 `https://www.joinquant.com/api`，查看页面源码中 `window.tokenData.value` 的值。

**板块列表**（15个）:

| 板块名 | 说明 |
|--------|------|
| Stock | 股票数据 |
| plateData | 板块/行业数据 |
| index | 指数数据 |
| macroData | 宏观经济数据 |
| Future | 期货数据 |
| Option | 期权数据 |
| fund | 场内基金数据 |
| OTCfund | 场外基金数据 |
| technicalanalysis | 技术分析指标 |
| Alpha101 | Alpha101 因子库 |
| Alpha191 | Alpha191 因子库 |
| bond | 债券数据 |
| factor_values | 因子数据 |
| Public | 公共数据 |
| ssymmetry | 对称数据 |


**采集脚本**:

```python
import urllib.request, json, re, html, os

TOKEN = "从页面获取的token"
BASE_URL = "https://www.joinquant.com/help/api/getContent"
DOC_DIR = "docs/joinquant_api"
SECTIONS = [
    "Stock", "plateData", "index", "macroData", "Future",
    "Option", "fund", "OTCfund", "technicalanalysis",
    "Alpha101", "Alpha191", "bond", "factor_values",
    "Public", "ssymmetry"
]

def html_to_md(data):
    text = re.sub(r'<h([1-6])[^>]*id="([^"]*)"[^>]*>',
                  lambda m: '#' * int(m.group(1)) + ' ' + m.group(2) + '\n', data)
    text = re.sub(r'<h[1-6][^>]*>', '\n### ', text)
    text = re.sub(r'</h[1-6]>', '\n', text)
    text = re.sub(r'<pre><code[^>]*>', '\n```python\n', text)
    text = re.sub(r'</code></pre>', '\n```\n', text)
    text = re.sub(r'<li>', '- ', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

for section in SECTIONS:
    url = f"{BASE_URL}?name={section}&token={TOKEN}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    md = html_to_md(raw.get("data", ""))
    with open(f"{DOC_DIR}/{section}.md", "w", encoding="utf-8") as f:
        f.write(md)
    print(f"{section}.md -> {len(md)} chars")
```

> **注意**: TOKEN 有时效性，过期后需要重新从页面获取。

### 3.2 聚宽平台 API（策略函数）

平台 API 文档是 SPA（单页应用），需要浏览器渲染才能获取内容。

**使用 Playwright 采集**:

```python
import asyncio, re, html
from playwright.async_api import async_playwright

async def fetch_platform_api():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.joinquant.com/api",
                        wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(5000)

        content = await page.evaluate("""() => {
            const el = document.querySelector("#jq-api-content");
            return el ? el.innerHTML : "";
        }""")

        text = re.sub(r'<h([1-6])[^>]*id="([^"]*)"[^>]*>',
                      lambda m: '\n' + '#' * int(m.group(1)) + ' ' + m.group(2) + '\n',
                      content)
        text = re.sub(r'<pre><code[^>]*>', '\n```python\n', text)
        text = re.sub(r'</code></pre>', '\n```\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = html.unescape(text)
        text = re.sub(r'\n{3,}', '\n\n', text).strip()

        with open("docs/joinquant_api/平台API_完整文档.md", "w", encoding="utf-8") as f:
            f.write("# 聚宽平台 API 完整文档\n\n" + text)
        await browser.close()
        print(f"完成: {len(text)} chars")

asyncio.run(fetch_platform_api())
```

### 3.3 扩展：添加新文档源

添加新文档源只需遵循统一格式:

```
docs/
├── joinquant_api/       # 聚宽 API 文档
├── strategies/          # 策略笔记（可扩展）
├── quant_books/         # 读书笔记（可扩展）
└── market_rules/        # 交易规则（可扩展）
```

**要求**:
- 文件格式: `.md`（Markdown）或 `.txt`
- 编码: UTF-8
- 内容结构化: 有标题层级，便于按语义切片

---

## 四、文档处理（切片）

### 4.1 切片原则

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| chunk_size | 500~1000 字符 | 太小丢失上下文，太大检索不精准 |
| chunk_overlap | 50~100 字符 | 避免在切片边界丢失信息 |
| 分隔符优先级 | h2 > h3 > 代码块 > 段落 > 换行 | 优先按标题切分 |

### 4.2 切片脚本

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,
    separators=["\n## ", "\n### ", "\n```", "\n\n", "\n", " "]
)

with open("docs/joinquant_api/Stock.md", "r", encoding="utf-8") as f:
    text = f.read()

chunks = splitter.split_text(text)
print(f"切分为 {len(chunks)} 个片段")
```

### 4.3 批量切片

```python
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800, chunk_overlap=100,
    separators=["\n## ", "\n### ", "\n```", "\n\n", "\n", " "]
)

def load_and_split(doc_dir):
    all_docs = []
    for root, _, files in os.walk(doc_dir):
        for fname in sorted(files):
            if not fname.endswith(".md"):
                continue
            filepath = os.path.join(root, fname)
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
            chunks = splitter.split_text(text)
            for chunk in chunks:
                all_docs.append(Document(
                    page_content=chunk,
                    metadata={"source": fname}
                ))
    return all_docs

docs = load_and_split("docs/joinquant_api")
print(f"共 {len(docs)} 个文档片段")
```

---

## 五、向量化与存储

### 5.1 选择 Embedding 模型

| 模型 | 维度 | 特点 | 推荐场景 |
|------|------|------|---------|
| BAAI/bge-small-zh-v1.5 | 512 | 轻量，中文效果好 | 本地运行，资源有限 |
| BAAI/bge-large-zh-v1.5 | 1024 | 中文 SOTA | 追求精度 |
| text-embedding-3-small | 1536 | OpenAI，需 API Key | 有 OpenAI Key |
| text2vec-base-chinese | 768 | 中文通用 | 入门使用 |

**推荐**: `BAAI/bge-small-zh-v1.5`（本地运行，首次自动下载约 90MB）

### 5.2 存入 Milvus

```python
from pymilvus import (
    connections, Collection, FieldSchema,
    CollectionSchema, DataType, utility
)
from sentence_transformers import SentenceTransformer

# 1. 连接 Milvus
connections.connect("default", host="localhost", port="19530")

# 2. 加载 Embedding 模型
model = SentenceTransformer("BAAI/bge-small-zh-v1.5")

# 3. 定义 Collection Schema
def create_collection(name, dim=512):
    if utility.has_collection(name):
        utility.drop_collection(name)
    fields = [
        FieldSchema("id", DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema("text", DataType.VARCHAR, max_length=4096),
        FieldSchema("source", DataType.VARCHAR, max_length=256),
        FieldSchema("embedding", DataType.FLOAT_VECTOR, dim=dim),
    ]
    schema = CollectionSchema(fields, description=f"{name} knowledge base")
    collection = Collection(name, schema)
    index_params = {
        "metric_type": "COSINE",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 128}
    }
    collection.create_index("embedding", index_params)
    return collection

# 4. 批量插入
def insert_docs(collection, docs, model, batch_size=100):
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i+batch_size]
        texts = [d.page_content for d in batch]
        sources = [d.metadata.get("source", "") for d in batch]
        embeddings = model.encode(texts).tolist()
        collection.insert([texts, sources, embeddings])
        print(f"  插入 {i+len(batch)}/{len(docs)}")
    collection.flush()
    print(f"完成，共 {collection.num_entities} 条记录")

# 5. 执行
collection = create_collection("quant_knowledge", dim=512)
insert_docs(collection, docs, model)
```

---

## 六、检索与问答

### 6.1 向量检索

```python
def search(query, collection, model, top_k=5):
    collection.load()
    query_embedding = model.encode([query]).tolist()
    results = collection.search(
        data=query_embedding,
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

results = search("怎么获取股票的历史价格数据", collection, model)
for r in results:
    print(f"[{r['score']:.3f}] {r['source']}: {r['text'][:100]}...")
```

### 6.2 RAG 问答（接入 LLM）

```python
def rag_answer(question, collection, model, llm_func, top_k=5):
    hits = search(question, collection, model, top_k)
    context = "\n\n---\n\n".join([h["text"] for h in hits])
    prompt = f"""你是一个量化投资助手。请根据以下参考资料回答用户问题。
如果资料中没有相关内容，请如实说明。

## 参考资料

{context}

## 用户问题

{question}

## 回答"""
    answer = llm_func(prompt)
    return answer, hits

# 示例: 使用 OpenAI
def llm_openai(prompt):
    from openai import OpenAI
    client = OpenAI()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content

answer, sources = rag_answer(
    "聚宽平台怎么获取股票的收盘价？",
    collection, model, llm_openai
)
print(answer)
```

---

## 七、运维命令

### 7.1 Milvus 管理

```bash
# 启动
cd infra/milvus && docker compose up -d

# 停止（保留数据）
docker compose down

# 停止并删除数据（慎用）
docker compose down -v

# 查看状态
docker ps | grep milvus

# 查看日志
docker logs milvus-standalone --tail 50
```

### 7.2 Milvus 数据管理（Python）

```python
from pymilvus import connections, Collection, utility

connections.connect("default", host="localhost", port="19530")

# 列出所有 Collection
print(utility.list_collections())

# 查看 Collection 信息
col = Collection("quant_knowledge")
print(f"记录数: {col.num_entities}")

# 清空 Collection（重新导入时用）
col.drop()

# 释放内存
col.release()
```

---

## 八、扩展新文档源的标准流程

```
1. 准备文档
   └─ 保存为 .md 文件到 docs/ 目录下

2. 运行切片
   └─ load_and_split("docs/新目录")

3. 存入 Milvus
   └─ insert_docs(collection, new_docs, model)

4. 测试检索
   └─ search("测试问题", collection, model)
```

### 完整的一键导入脚本

```python
"""
一键导入新文档到 Milvus 知识库
用法: python import_docs.py docs/新目录
"""
import sys, os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from pymilvus import connections, Collection
from sentence_transformers import SentenceTransformer

COLLECTION_NAME = "quant_knowledge"
MODEL_NAME = "BAAI/bge-small-zh-v1.5"

def load_and_split(doc_dir, chunk_size=800, chunk_overlap=100):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap,
        separators=["\n## ", "\n### ", "\n```", "\n\n", "\n", " "]
    )
    docs = []
    for root, _, files in os.walk(doc_dir):
        for fname in sorted(files):
            if not fname.endswith(".md"):
                continue
            with open(os.path.join(root, fname), "r", encoding="utf-8") as f:
                text = f.read()
            for chunk in splitter.split_text(text):
                docs.append(Document(
                    page_content=chunk,
                    metadata={"source": fname}
                ))
    return docs

def main():
    if len(sys.argv) < 2:
        print("用法: python import_docs.py <文档目录>")
        sys.exit(1)

    doc_dir = sys.argv[1]
    print(f"加载文档: {doc_dir}")
    docs = load_and_split(doc_dir)
    print(f"切分为 {len(docs)} 个片段")

    print("连接 Milvus...")
    connections.connect("default", host="localhost", port="19530")
    collection = Collection(COLLECTION_NAME)

    print("加载 Embedding 模型...")
    model = SentenceTransformer(MODEL_NAME)

    print("生成向量并插入...")
    batch_size = 100
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i+batch_size]
        texts = [d.page_content for d in batch]
        sources = [d.metadata["source"] for d in batch]
        embeddings = model.encode(texts).tolist()
        collection.insert([texts, sources, embeddings])
        print(f"  {i+len(batch)}/{len(docs)}")

    collection.flush()
    print(f"完成！Collection 现有 {collection.num_entities} 条记录")

if __name__ == "__main__":
    main()
```

---

## 九、当前状态

| 组件 | 状态 | 说明 |
|------|------|------|
| Milvus | ✅ 运行中 | localhost:19530 |
| Attu | ✅ 运行中 | localhost:8000 |
| 聚宽数据字典 | ✅ 已采集 | 15 个文件，1.8MB |
| 聚宽平台 API | ✅ 已采集 | 1 个文件，310KB |
| 文档切片 | ⬜ 待完成 | |
| 向量化入库 | ⬜ 待完成 | |
| RAG 问答 | ⬜ 待完成 | |
