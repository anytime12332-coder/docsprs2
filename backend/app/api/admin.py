"""Admin dashboard and management routes."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.dependencies import get_client_ip, require_admin
from app.models.document import Document
from app.models.extraction import ExtractionResult
from app.models.template import ExtractionTemplate
from app.models.user import User
from app.models.webhook import Webhook
from app.schemas.common import SuccessResponse, SystemStatsResponse
from app.schemas.user import UserCreate, UserListResponse, UserResponse, UserUpdate
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.storage_service import storage_service

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get system-wide statistics for the admin dashboard."""
    # Documents
    total_docs = (await db.execute(select(func.count(Document.id)))).scalar() or 0
    total_pages = (
        await db.execute(select(func.sum(Document.page_count)))
    ).scalar() or 0
    total_extractions = (
        await db.execute(select(func.count(ExtractionResult.id)))
    ).scalar() or 0

    # Today's documents
    from datetime import datetime, timezone
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    docs_today = (
        await db.execute(
            select(func.count(Document.id)).where(
                Document.created_at >= today_start
            )
        )
    ).scalar() or 0

    # Processing stats
    completed = (
        await db.execute(
            select(func.count(Document.id)).where(Document.status == "completed")
        )
    ).scalar() or 0
    failed = (
        await db.execute(
            select(func.count(Document.id)).where(Document.status == "failed")
        )
    ).scalar() or 0
    success_rate = completed / (completed + failed) if (completed + failed) > 0 else 1.0

    # Queue size
    processing = (
        await db.execute(
            select(func.count(Document.id)).where(
                Document.status.in_(["queued", "processing"])
            )
        )
    ).scalar() or 0

    # Avg processing time
    avg_time_result = await db.execute(
        select(
            func.avg(
                func.extract(
                    "epoch",
                    Document.processing_completed_at - Document.processing_started_at,
                )
            )
        ).where(
            Document.processing_completed_at.isnot(None),
            Document.processing_started_at.isnot(None),
        )
    )
    avg_time = avg_time_result.scalar() or 0.0

    # Storage
    storage_used = await storage_service.get_storage_usage()

    # Active counts
    active_users = (
        await db.execute(
            select(func.count(User.id)).where(User.is_active == True)
        )
    ).scalar() or 0
    active_templates = (
        await db.execute(
            select(func.count(ExtractionTemplate.id)).where(
                ExtractionTemplate.is_active == True
            )
        )
    ).scalar() or 0
    active_webhooks = (
        await db.execute(
            select(func.count(Webhook.id)).where(Webhook.is_active == True)
        )
    ).scalar() or 0

    return SystemStatsResponse(
        total_documents=total_docs,
        total_pages_processed=total_pages,
        total_extractions=total_extractions,
        documents_today=docs_today,
        processing_queue_size=processing,
        storage_used_mb=storage_used / (1024 * 1024),
        avg_processing_time_seconds=float(avg_time),
        success_rate=success_rate,
        active_users=active_users,
        active_templates=active_templates,
        active_webhooks=active_webhooks,
    )


@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users."""
    auth_service = AuthService(db)
    users, total = await auth_service.list_users(page, per_page)
    return UserListResponse(
        users=users, total=total, page=page, per_page=per_page
    )


@router.post("/users", response_model=UserResponse)
async def create_user(
    data: UserCreate,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user."""
    auth_service = AuthService(db)
    user = await auth_service.create_user(data)

    audit = AuditService(db)
    await audit.log(
        action="user.create",
        resource_type="user",
        resource_id=str(user.id),
        user_id=admin.id,
        details={"email": data.email, "is_admin": data.is_admin},
        ip_address=get_client_ip(request),
    )

    return user


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a user."""
    auth_service = AuthService(db)
    return await auth_service.update_user(user_id, data)


@router.delete("/users/{user_id}", response_model=SuccessResponse)
async def delete_user(
    user_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user."""
    auth_service = AuthService(db)
    await auth_service.delete_user(user_id)

    audit = AuditService(db)
    await audit.log(
        action="user.delete",
        resource_type="user",
        resource_id=str(user_id),
        user_id=admin.id,
        ip_address=get_client_ip(request),
    )

    return SuccessResponse(message="User deleted successfully")


@router.get("/audit-logs")
async def get_audit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    user_id: Optional[uuid.UUID] = Query(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get audit logs."""
    audit_service = AuditService(db)
    logs, total = await audit_service.get_logs(
        page=page,
        per_page=per_page,
        action=action,
        resource_type=resource_type,
        user_id=user_id,
    )
    return {
        "logs": [
            {
                "id": str(log.id),
                "user_id": str(log.user_id) if log.user_id else None,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/config")
async def get_system_config(
    admin: User = Depends(require_admin),
):
    """Get current system configuration (non-sensitive)."""
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
        "max_pages_per_document": settings.MAX_PAGES_PER_DOCUMENT,
        "supported_formats": settings.supported_formats_list,
        "ocr_engine": settings.OCR_ENGINE,
        "ocr_languages": settings.OCR_LANGUAGES,
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
        "storage_backend": settings.STORAGE_BACKEND,
        "max_concurrent_jobs": settings.MAX_CONCURRENT_JOBS,
        "processing_timeout_seconds": settings.PROCESSING_TIMEOUT_SECONDS,
    }
