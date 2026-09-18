# Recipe: RAG (retrieval-augmented generation)

Retrieve relevant context, stuff it into the prompt, answer grounded in it.
This uses a tiny in-memory cosine-similarity store — swap in FAISS / Chroma /
pgvector for scale, but the shape is identical.

```python
import anthropic
import numpy as np

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY

DOCS = [
    "Refunds are issued within 14 days of purchase.",
    "Support hours are Mon-Fri, 9am-6pm Pacific.",
    "Standard shipping takes 3-5 business days.",
]

# --- Embeddings ---
# Anthropic has no embeddings endpoint; use a dedicated embedder. Two options:
#   pip install sentence-transformers   (local, free, no key)
#   or call Voyage AI / OpenAI embeddings.
from sentence_transformers import SentenceTransformer  # noqa: E402
embedder = SentenceTransformer("all-MiniLM-L6-v2")
DOC_VECS = embedder.encode(DOCS, normalize_embeddings=True)

def retrieve(query: str, k: int = 2) -> list[str]:
    q = embedder.encode([query], normalize_embeddings=True)[0]
    scores = DOC_VECS @ q                      # cosine sim (vectors normalized)
    top = np.argsort(scores)[::-1][:k]
    return [DOCS[i] for i in top]

def answer(question: str) -> str:
    context = "\n".join(f"- {c}" for c in retrieve(question))
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system="Answer ONLY from the provided context. If it's not there, say so.",
        messages=[{
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {question}",
        }],
    )
    return "".join(b.text for b in resp.content if b.type == "text")

print(answer("How long do refunds take?"))
```

Notes:
- Put the (large, stable) context block first and add `cache_control` to it to
  cache the retrieved prefix across turns.
- For agentic RAG, expose `retrieve` as a **tool** instead (see `tool-calling.md`)
  so the model decides when to search — that's what `templates/agent-app` does.
- Chunk long docs (~200-500 tokens) before embedding for better recall.
