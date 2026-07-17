# RAG API

## Endpoints

### `GET /health`

Returns service status.

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

### `POST /ask`

Retrieval-Augmented Generation — embeds a question, searches Qdrant for the most relevant news chunks, and generates an answer using an LLM.

**Request** (`application/json`):

```jsonc
{
  "text": "What are the main challenges facing the US economy?",
  "top_k": 5,               // optional, default: 5 — number of chunks to retrieve
  "llm_provider": null,      // optional, default: from .env LLM_PROVIDER
  "timeout": null            // optional, default: 600.0 (10 min) — LLM API timeout in seconds
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `text` | `string` | yes | — | The user question |
| `top_k` | `int` | no | `5` | Number of most relevant chunks to retrieve from Qdrant (1–100) |
| `llm_provider` | `"openai" \| "llamacpp" \| "stub"` | no | From `.env` | Override LLM provider per request |
| `timeout` | `float` | no | `600.0` | LLM API call timeout in seconds |

**Response** (`application/json`):

```json
{
  "answer": "The US economy faces challenges from bond market volatility, trade policy uncertainty...",
  "sources": [
    "https://www.economist.com/finance-and-economics/...",
    "https://finance.yahoo.com/markets/stocks/articles/..."
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `answer` | `string` | LLM-generated answer based on retrieved context |
| `sources` | `list[string]` | URLs of source articles used in the answer |

## LLM Provider Behavior

### `llamacpp` (local)
- Calls a local llama.cpp server at `LLM_BASE_URL` (e.g., `http://llama-server:8080/v1`)
- Uses OpenAI-compatible chat completions API
- Requires `LLM_BASE_URL` set; any non-empty `OPENAI_API_KEY` is accepted
- **Timeout**: 600s default (adjust for model size/speed)
- Best for: offline operation, privacy, no API costs, custom models

### `openai` (cloud)
- Calls OpenAI API with `OPENAI_API_KEY`
- Respects `LLM_BASE_URL` if set (for Azure/OpenRouter/etc.)
- Best for: fast inference, GPT-quality answers, production

### `stub` (offline/dev)
- Returns retrieved context verbatim with prefix `[stub llm]`
- No LLM call — zero latency, zero cost
- Response format: `"[stub llm] No LLM was called (LLM_PROVIDER=stub).\n\nContext:\n[1] Title\nURL: ...\ntext\n\n---\n\n[2]..."`
- Best for: debugging retrieval quality, offline development, CI/testing

## Request Examples

```bash
# Default behavior (5 chunks, provider from .env, 10-min timeout)
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"text": "What is the market outlook?"}'

# 10 chunks with local llama.cpp, 5-minute timeout
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"text": "Summarize global economic trends", "top_k": 10, "llm_provider": "llamacpp", "timeout": 300.0}'

# Offline stub (no LLM) — verify retrieval quality
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"text": "What about crypto markets?", "llm_provider": "stub"}'

# OpenAI with custom model per-request
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"text": "Bond market analysis", "top_k": 3, "llm_provider": "openai", "timeout": 30.0}'
```

## Pipeline Internals

```
POST /ask
    │
    ▼
embed(query) ─── sentence-transformers/all-mpnet-base-v2 (768-dim)
    │
    ▼
Qdrant.query_points(collection="news_embeddings", query=vector, limit=top_k, with_payload=True)
    │
    ▼
RetrievedDoc[](url, title, chunk_text, cosine_score) ─── sorted by relevance
    │
    ▼
build_context(docs) ─── formats as numbered text blocks:
        [1] Article Title
        URL: https://...
        Chunk text content...
        ---
        [2] ...
    │
    ▼
LLMClient.complete(
  system="You are a news analyst. Answer user questions using ONLY the provided context.
          Cite source URLs. If the context is insufficient, say I don't have enough information.",
  user="Context:\n[1]...\n\nQuestion: What is the market outlook?"
)
    │
    ▼ (llamacpp)         ▼ (openai)           ▼ (stub)
  llama-server          OpenAI API           returns context
  /v1/chat/completions  /v1/chat/completions  verbatim
    │
    ▼
RagAnswer(answer="...", sources=["https://...", ...])
    │
    ▼
HTTP 200 JSON {"answer": "...", "sources": [...]}
```

## Error Handling

| Condition | Response |
|-----------|----------|
| No relevant chunks found (empty Qdrant results) | `{"answer": "I don't have enough information.", "sources": []}` |
| LLM timeout (`timeout` seconds elapsed) | HTTP 500 `openai.APITimeoutError` |
| Invalid `llm_provider` value | HTTP 422 validation error |
| LLM API unreachable | HTTP 500 `openai.APIConnectionError` |

## OpenAPI Documentation

When the service is running, interactive API docs are available at:

```
http://localhost:8000/docs       # Swagger UI
http://localhost:8000/redoc      # ReDoc
```

## Environment Variables

See `.env.example` for full configuration. Key LLM variables:

```env
LLM_PROVIDER=openai              # openai | llamacpp | stub
LLM_MODEL=gpt-4o-mini           # Model name sent to LLM API
LLM_TEMPERATURE=0.2             # Generation temperature (0.0–1.0)
LLM_BASE_URL=                   # OpenAI-compatible base URL (required for llamacpp)
OPENAI_API_KEY=                 # API key (required for openai; arbitrary for llamacpp)
```