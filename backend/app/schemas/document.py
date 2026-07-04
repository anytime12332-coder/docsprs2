"""Document schemas."""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    document_type: Optional[str] = None
    classification_confidence: Optional[float] = None
    language: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    page_count: Optional[int] = None
    metadata_json: Optional[dict] = None
    tags: Optional[list] = None
    notes: Optional[str] = None
    is_duplicate: bool
    requires_review: bool
    is_archived: bool
    uploaded_by: uuid.UUID
    template_id: Optional[uuid.UUID] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
    page: int
    per_page: int


class DocumentUpdate(BaseModel):
    document_type: Optional[str] = None
    tags: Optional[list[str]] = None
    notes: Optional[str] = None
    template_id: Optional[uuid.UUID] = None
    is_archived: Optional[bool] = None


class DocumentProcessRequest(BaseModel):
    template_id: Optional[uuid.UUID] = None
    force_ocr: bool = False
    extraction_method: str = "auto"  # auto, template, ai, llm
    language: Optional[str] = None
    options: Optional[dict[str, Any]] = None


class BulkProcessRequest(BaseModel):
    document_ids: list[uuid.UUID]
    template_id: Optional[uuid.UUID] = None
    extraction_method: str = "auto"


class DocumentStatsResponse(BaseModel):
    total_documents: int
    by_status: dict[str, int]
    by_type: dict[str, int]
    total_pages_processed: int
    avg_processing_time_seconds: Optional[float] = None
    storage_used_bytes: int
