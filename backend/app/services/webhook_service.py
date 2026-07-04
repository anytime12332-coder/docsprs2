"""Webhook management and delivery service."""

import hashlib
import hmac
import json
import uuid
from typing import Any, Optional

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.webhook import Webhook, WebhookDelivery
from app.schemas.webhook import WebhookCreate, WebhookUpdate


class WebhookService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_webhook(
        self, data: WebhookCreate, created_by: uuid.UUID
    ) -> Webhook:
        webhook = Webhook(
            name=data.name,
            url=data.url,
            secret=data.secret,
            events=data.events,
            headers=data.headers,
            retry_count=data.retry_count,
            timeout_seconds=data.timeout_seconds,
            created_by=created_by,
        )
        self.db.add(webhook)
        await self.db.flush()
        return webhook

    async def get_webhook(self, webhook_id: uuid.UUID) -> Optional[Webhook]:
        result = await self.db.execute(
            select(Webhook).where(Webhook.id == webhook_id)
        )
        return result.scalar_one_or_none()

    async def list_webhooks(self) -> tuple[list[Webhook], int]:
        count = (await self.db.execute(select(func.count(Webhook.id)))).scalar()
        result = await self.db.execute(
            select(Webhook).order_by(Webhook.created_at.desc())
        )
        webhooks = list(result.scalars().all())
        return webhooks, count

    async def update_webhook(
        self, webhook_id: uuid.UUID, data: WebhookUpdate
    ) -> Webhook:
        webhook = await self.get_webhook(webhook_id)
        if not webhook:
            raise ValueError(f"Webhook {webhook_id} not found")
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(webhook, field, value)
        await self.db.flush()
        return webhook

    async def delete_webhook(self, webhook_id: uuid.UUID) -> None:
        webhook = await self.get_webhook(webhook_id)
        if webhook:
            await self.db.delete(webhook)
            await self.db.flush()

    async def trigger_event(
        self, event: str, payload: dict[str, Any]
    ) -> list[WebhookDelivery]:
        """Find all active webhooks subscribed to this event and deliver."""
        result = await self.db.execute(
            select(Webhook).where(
                Webhook.is_active == True,
            )
        )
        webhooks = result.scalars().all()
        deliveries = []

        for webhook in webhooks:
            if event in webhook.events:
                delivery = await self._deliver(webhook, event, payload)
                deliveries.append(delivery)

        return deliveries

    async def _deliver(
        self, webhook: Webhook, event: str, payload: dict
    ) -> WebhookDelivery:
        headers = {"Content-Type": "application/json"}
        if webhook.headers:
            headers.update(webhook.headers)

        body = json.dumps(payload, default=str)

        if webhook.secret:
            signature = hmac.new(
                webhook.secret.encode(), body.encode(), hashlib.sha256
            ).hexdigest()  # hmac.new is correct in Python
            headers["X-Webhook-Signature"] = signature

        headers["X-Webhook-Event"] = event

        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event=event,
            payload=payload,
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook.url,
                    content=body,
                    headers=headers,
                    timeout=webhook.timeout_seconds,
                )
                delivery.response_status = response.status_code
                delivery.response_body = response.text[:5000]
                delivery.success = 200 <= response.status_code < 300
        except Exception as e:
            delivery.success = False
            delivery.error_message = str(e)

        self.db.add(delivery)
        await self.db.flush()
        return delivery

    async def get_deliveries(
        self,
        webhook_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[WebhookDelivery], int]:
        count_query = select(func.count(WebhookDelivery.id)).where(
            WebhookDelivery.webhook_id == webhook_id
        )
        total = (await self.db.execute(count_query)).scalar()

        result = await self.db.execute(
            select(WebhookDelivery)
            .where(WebhookDelivery.webhook_id == webhook_id)
            .order_by(WebhookDelivery.delivered_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        deliveries = list(result.scalars().all())
        return deliveries, total
