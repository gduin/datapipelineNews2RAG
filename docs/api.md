# RAG API

## Health
`GET /health` -> `{"status":"ok"}`

## Ask
`POST /ask`
```json
{ "text": "What happened in world news today?", "top_k": 5 }
```
Response:
```json
{ "answer": "...", "sources": ["https://...", "https://..."] }
```
