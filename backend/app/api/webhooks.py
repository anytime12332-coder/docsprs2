"""Webhook management routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_client_ip, require_admin
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.webhook import (
    WebhookCreate,
    WebhookDeliveryResponse,
    WebhookListResponse,
    WebhookResponse,
    WebhookUpdate,
)
from app.services.audit_service import AuditService
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("", response_model=WebhookResponse)
async def create_webhook(
    data: WebhookCreate,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new webhook."""
    webhook_service = WebhookService(db)
    webhook = await webhook_service.create_webhook(data, admin.id)

    audit = AuditService(db)
    await audit.log(
        action="webhook.create",
        resource_type="webhook",
        resource_id=str(webhook.id),
        user_id=admin.id,
        details={"name": data.name, "url": data.url, "events": data.events},
        ip_address=get_client_ip(request),
    )

    return webhook


@router.get("", response_model=WebhookListResponse)
async def list_webhooks(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all webhooks."""
    webhook_service = WebhookService(db)
    webhooks, total = await webhook_service.list_webhooks()
    return WebhookListResponse(webhooks=webhooks, total=total)


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific webhook."""
    webhook_service = WebhookService(db)
    webhook = await webhook_service.get_webhook(webhook_id)
    if not webhook:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Webhook not found")
    return webhook


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: uuid.UUID,
    data: WebhookUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a webhook."""
    webhook_service = WebhookService(db)
    return await webhook_service.update_webhook(webhook_id, data)


@router.delete("/{webhook_id}", response_model=SuccessResponse)
async def delete_webhook(
    webhook_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a webhook."""
    webhook_service = WebhookService(db)
    await webhook_service.delete_webhook(webhook_id)

    audit = AuditService(db)
    await audit.log(
        action="webhook.delete",
        resource_type="webhook",
        resource_id=str(webhook_id),
        user_id=admin.id,
        ip_address=get_client_ip(request),
    )

    return SuccessResponse(message="Webhook deleted successfully")


@router.get("/{webhook_id}/deliveries", response_model=list[WebhookDeliveryResponse])
async def get_webhook_deliveries(
    webhook_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get delivery history for a webhook."""
    webhook_service = WebhookService(db)
    deliveries, _ = await webhook_service.get_deliveries(
        webhook_id, page, per_page
    )
    return deliveries


@router.post("/{webhook_id}/test", response_model=SuccessResponse)
async def test_webhook(
    webhook_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Send a test event to a webhook."""
    webhook_service = WebhookService(db)
    webhook = await webhook_service.get_webhook(webhook_id)
    if not webhook:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Webhook not found")

    delivery = await webhook_service._deliver(
        webhook,
        "test.ping",
        {"message": "Test webhook delivery from DocuMind IDP"},
    )

    return SuccessResponse(
        message="Test webhook sent",
        data={"success": delivery.success, "status": delivery.response_status},
    )
