"""Template schemas."""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class TemplateFieldCreate(BaseModel):
    field_name: str
    field_label: str
    field_type: str = "text"
    is_required: bool = False
    default_value: Optional[str] = None
    validation_regex: Optional[str] = None
    extraction_hint: Optional[str] = None
    order: int = 0
    anchor_text: Optional[str] = None
    relative_position: Optional[dict] = None


class TemplateFieldResponse(BaseModel):
    id: uuid.UUID
    field_name: str
    field_label: str
    field_type: str
    is_required: bool
    default_value: Optional[str] = None
    validation_regex: Optional[str] = None
    extraction_hint: Optional[str] = None
    order: int
    anchor_text: Optional[str] = None
    relative_position: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    document_type: str
    preprocessing_config: Optional[dict[str, Any]] = None
    classification_keywords: Optional[list[str]] = None
    validation_rules: Optional[dict[str, Any]] = None
    post_processing_config: Optional[dict[str, Any]] = None
    fields: list[TemplateFieldCreate] = []


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    document_type: Optional[str] = None
    is_active: Optional[bool] = None
    preprocessing_config: Optional[dict[str, Any]] = None
    classification_keywords: Optional[list[str]] = None
    validation_rules: Optional[dict[str, Any]] = None
    post_processing_config: Optional[dict[str, Any]] = None


class TemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    document_type: str
    is_active: bool
    version: int
    preprocessing_config: Optional[dict] = None
    classification_keywords: Optional[list[str]] = None
    validation_rules: Optional[dict] = None
    post_processing_config: Optional[dict] = None
    fields: list[TemplateFieldResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TemplateListResponse(BaseModel):
    templates: list[TemplateResponse]
    total: int
