# AURI.AI Architecture

## Privacy-first design

| Mode | Transcription | LLM | Embeddings | Data leaves infrastructure |
|------|---------------|-----|------------|----------------------------|
| **strict_private** | Local / Whisper | Ollama only | Ollama only | Never |
| **hybrid** | Deepgram / AssemblyAI | Ollama preferred | Ollama preferred | Only audio for STT |
| **cloud** | Deepgram / AssemblyAI | Claude / GPT | OpenAI / Voyage | Yes (encrypted in transit) |

Default for enterprise / funds: `strict_private`.

## Components

1. **API** (FastAPI) — auth, RBAC, rate limiting, audit
2. **Workers** (Celery) — ingest → transcribe → embed → summarize → index
3. **AI Router** — providers by org `ai_mode`
4. **Ollama** — local LLM + embeddings
5. **Postgres** — multi-tenant transactional data
6. **Qdrant** — vector search filtered by org_id
7. **MinIO / S3** — audio & artifacts
8. **Frontend** — Next.js App Router

## Pipeline

```
Upload / Zoom webhook
  → S3
  → Transcribe
  → Diarize + chunk + embed
  → Qdrant upsert
  → LLM summary (Ollama in private mode)
  → Postgres + notifications
```
