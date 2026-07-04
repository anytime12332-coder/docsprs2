"""Template management routes."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_client_ip, require_admin
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.template import (
    TemplateCreate,
    TemplateFieldCreate,
    TemplateFieldResponse,
    TemplateListResponse,
    TemplateResponse,
    TemplateUpdate,
)
from app.services.audit_service import AuditService
from app.services.template_service import TemplateService

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.post("", response_model=TemplateResponse)
async def create_template(
    data: TemplateCreate,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new extraction template."""
    template_service = TemplateService(db)
    template = await template_service.create_template(data, admin.id)

    audit = AuditService(db)
    await audit.log(
        action="template.create",
        resource_type="template",
        resource_id=str(template.id),
        user_id=admin.id,
        details={"name": data.name, "document_type": data.document_type},
        ip_address=get_client_ip(request),
    )

    return template


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    document_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all extraction templates."""
    template_service = TemplateService(db)
    templates, total = await template_service.list_templates(
        document_type=document_type, is_active=is_active
    )
    return TemplateListResponse(templates=templates, total=total)


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific template."""
    template_service = TemplateService(db)
    return await template_service.get_template(template_id)


@router.patch("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    data: TemplateUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a template."""
    template_service = TemplateService(db)
    return await template_service.update_template(template_id, data)


@router.delete("/{template_id}", response_model=SuccessResponse)
async def delete_template(
    template_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a template."""
    template_service = TemplateService(db)
    await template_service.delete_template(template_id)

    audit = AuditService(db)
    await audit.log(
        action="template.delete",
        resource_type="template",
        resource_id=str(template_id),
        user_id=admin.id,
        ip_address=get_client_ip(request),
    )

    return SuccessResponse(message="Template deleted successfully")


@router.post("/{template_id}/fields", response_model=TemplateFieldResponse)
async def add_template_field(
    template_id: uuid.UUID,
    data: TemplateFieldCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Add a field to a template."""
    template_service = TemplateService(db)
    return await template_service.add_field(template_id, data)


@router.delete("/fields/{field_id}", response_model=SuccessResponse)
async def remove_template_field(
    field_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Remove a field from a template."""
    template_service = TemplateService(db)
    await template_service.remove_field(field_id)
    return SuccessResponse(message="Field removed successfully")
