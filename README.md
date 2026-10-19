# InsightEngine — Enterprise Document Intelligence Platform
The InsightEngine platform supports PDF document ingestion. Documents are parsed, chunked into overlapping segments, embedded using OpenAI's text-embedding-3-small model, and stored in Qdrant for semantic retrieval. Each chunk retains metadata including source page number and tenant identifier for access control.
A production-style RAG (Retrieval-Augmented Generation) system demonstrating polyglot AI engineering.

## Architecture

| Layer | Technology | Responsibility |
|-------|-----------|----------------|
| API Gateway | Spring Boot (Java 21) | Auth, multi-tenancy, orchestration, business logic |
| AI Service | FastAPI (Python 3.11) | Document parsing, embedding, retrieval, generation |
| Vector Store | Qdrant | Semantic search, payload filtering |
| Relational DB | PostgreSQL 16 | Metadata, users, documents, feedback, analytics |
| Cache & Queue | Redis | Background jobs, response caching |
| Frontend | React 18 | Document upload, chat UI, admin dashboard |

## Quick Start

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Start infrastructure
docker compose up -d postgres qdrant redis

# 3. Start AI Service (Python)
cd ai-service
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 4. Start Backend (Java)
cd backend
./gradlew bootRun

# 5. Verify
curl http://localhost:8080/api/health
curl http://localhost:8000/health
```
