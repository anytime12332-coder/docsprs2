"""Webhook schemas."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl


class WebhookCreate(BaseModel):
    name: str
    url: str
    secret: Optional[str] = None
    events: list[str]
    headers: Optional[dict[str, str]] = None
    retry_count: int = 3
    timeout_seconds: int = 30


class WebhookUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    secret: Optional[str] = None
    is_active: Optional[bool] = None
    events: Optional[list[str]] = None
    headers: Optional[dict[str, str]] = None
    retry_count: Optional[int] = None
    timeout_seconds: Optional[int] = None


class WebhookResponse(BaseModel):
    id: uuid.UUID
    name: str
    url: str
    is_active: bool
    events: list[str]
    headers: Optional[dict[str, str]] = None
    retry_count: int
    timeout_seconds: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WebhookDeliveryResponse(BaseModel):
    id: uuid.UUID
    webhook_id: uuid.UUID
    event: str
    payload: dict
    response_status: Optional[int] = None
    success: bool
    attempt: int
    error_message: Optional[str] = None
    delivered_at: datetime

    model_config = {"from_attributes": True}


class WebhookListResponse(BaseModel):
    webhooks: list[WebhookResponse]
    total: int
