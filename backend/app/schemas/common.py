"""Common schemas."""

from typing import Any, Optional

from pydantic import BaseModel


class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None


class PaginationParams(BaseModel):
    page: int = 1
    per_page: int = 20
    sort_by: str = "created_at"
    sort_order: str = "desc"  # asc | desc


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    redis: str
    storage: str


class SystemStatsResponse(BaseModel):
    total_documents: int
    total_pages_processed: int
    total_extractions: int
    documents_today: int
    processing_queue_size: int
    storage_used_mb: float
    avg_processing_time_seconds: float
    success_rate: float
    active_users: int
    active_templates: int
    active_webhooks: int
