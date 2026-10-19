from fastapi import FastAPI, status
from app.config import get_settings
from app.api import query

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI service for document ingestion, embedding, and generation",
)

app.include_router(query.router)


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {
        "status": "healthy",
        "service": "ai-service",
        "version": "0.1.0",
    }


@app.get("/")
async def root():
    return {"message": "InsightEngine AI Service", "docs": "/docs"}
