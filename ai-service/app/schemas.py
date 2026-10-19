from typing import List, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    tenant_id: str = "default"


class Citation(BaseModel):
    document_id: str
    chunk_index: int
    page_number: int
    score: float


class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation]


class DocumentStatusResponse(BaseModel):
    document_id: str
    status: str
    original_name: str
    error_message: Optional[str] = None

class ErrorResponse(BaseModel):
    detail: str