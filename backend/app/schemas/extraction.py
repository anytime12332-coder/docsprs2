"""Extraction schemas."""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class ExtractionFieldResponse(BaseModel):
    id: uuid.UUID
    field_name: str
    field_value: Optional[str] = None
    field_type: str
    confidence: Optional[float] = None
    page_number: Optional[int] = None
    bounding_box: Optional[dict] = None
    is_corrected: bool
    original_value: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ExtractionTableResponse(BaseModel):
    id: uuid.UUID
    table_name: Optional[str] = None
    headers: Optional[list[str]] = None
    rows: Optional[list[list[Any]]] = None
    page_number: Optional[int] = None
    confidence: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ExtractionResultResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    extraction_method: str
    overall_confidence: Optional[float] = None
    validated: bool
    validated_by: Optional[uuid.UUID] = None
    validated_at: Optional[datetime] = None
    version: int
    fields: list[ExtractionFieldResponse] = []
    tables: list[ExtractionTableResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class FieldCorrectionRequest(BaseModel):
    field_id: uuid.UUID
    corrected_value: str


class BulkFieldCorrectionRequest(BaseModel):
    corrections: list[FieldCorrectionRequest]


class ValidateExtractionRequest(BaseModel):
    extraction_id: uuid.UUID
    corrections: Optional[list[FieldCorrectionRequest]] = None
