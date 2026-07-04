"""Document management routes."""

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_client_ip, require_admin
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.document import (
    BulkProcessRequest,
    DocumentListResponse,
    DocumentProcessRequest,
    DocumentResponse,
    DocumentStatsResponse,
    DocumentUpdate,
)
from app.services.audit_service import AuditService
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    tags: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    auto_process: bool = Form(False),
    template_id: Optional[str] = Form(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document for processing."""
    content = await file.read()
    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    doc_service = DocumentService(db)
    doc = await doc_service.upload_document(
        file_content=content,
        filename=file.filename,
        mime_type=file.content_type or "application/octet-stream",
        uploaded_by=admin.id,
        tags=tag_list,
        notes=notes,
    )

    if template_id:
        doc.template_id = uuid.UUID(template_id)

    # Audit
    audit = AuditService(db)
    await audit.log(
        action="document.upload",
        resource_type="document",
        resource_id=str(doc.id),
        user_id=admin.id,
        details={"filename": file.filename, "size": len(content)},
        ip_address=get_client_ip(request),
    )

    # Auto-process if requested
    if auto_process:
        from app.processing.celery_tasks import process_document_task

        doc.status = "queued"
        # Persist the document (and template assignment / status) before
        # enqueuing so the worker cannot read the row before it is committed.
        await db.commit()
        await db.refresh(doc)
        process_document_task.delay(str(doc.id))

    return doc


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    document_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    is_archived: Optional[bool] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all documents with filtering and pagination."""
    doc_service = DocumentService(db)
    docs, total = await doc_service.list_documents(
        page=page,
        per_page=per_page,
        status=status,
        document_type=document_type,
        search=search,
        is_archived=is_archived,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return DocumentListResponse(
        documents=docs, total=total, page=page, per_page=per_page
    )


@router.get("/stats", response_model=DocumentStatsResponse)
async def get_document_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get document processing statistics."""
    doc_service = DocumentService(db)
    stats = await doc_service.get_stats()
    return DocumentStatsResponse(**stats)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific document."""
    doc_service = DocumentService(db)
    return await doc_service.get_document(document_id)


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: uuid.UUID,
    data: DocumentUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update document metadata."""
    doc_service = DocumentService(db)
    return await doc_service.update_document(document_id, data)


@router.delete("/{document_id}", response_model=SuccessResponse)
async def delete_document(
    document_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and its files."""
    doc_service = DocumentService(db)
    await doc_service.delete_document(document_id)

    audit = AuditService(db)
    await audit.log(
        action="document.delete",
        resource_type="document",
        resource_id=str(document_id),
        user_id=admin.id,
        ip_address=get_client_ip(request),
    )

    return SuccessResponse(message="Document deleted successfully")


@router.post("/{document_id}/process", response_model=SuccessResponse)
async def process_document(
    document_id: uuid.UUID,
    data: DocumentProcessRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Trigger document processing."""
    doc_service = DocumentService(db)
    doc = await doc_service.get_document(document_id)

    if data.template_id:
        doc.template_id = data.template_id

    await doc_service.update_status(document_id, "queued")

    from app.processing.celery_tasks import process_document_task

    # Commit status/template changes before enqueuing so the worker does not
    # observe a stale or missing row.
    await db.commit()

    task = process_document_task.delay(
        str(document_id),
        {
            "extraction_method": data.extraction_method,
            "force_ocr": data.force_ocr,
            "language": data.language,
        },
    )

    audit = AuditService(db)
    await audit.log(
        action="document.process",
        resource_type="document",
        resource_id=str(document_id),
        user_id=admin.id,
        details={"task_id": task.id, "method": data.extraction_method},
        ip_address=get_client_ip(request),
    )

    return SuccessResponse(
        message="Document processing started",
        data={"task_id": task.id},
    )


@router.post("/process/sync/{document_id}")
async def process_document_sync(
    document_id: uuid.UUID,
    data: DocumentProcessRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Process a document synchronously (for smaller documents)."""
    from app.processing.pipeline import processing_pipeline
    from app.services.extraction_service import ExtractionService
    from app.services.storage_service import storage_service

    doc_service = DocumentService(db)
    ext_service = ExtractionService(db)
    doc = await doc_service.get_document(document_id)

    await doc_service.update_status(document_id, "processing")

    # Read file
    file_content = await storage_service.read_file(doc.file_path)

    # Get template fields
    template_fields = None
    validation_rules = None
    if doc.template:
        template_fields = [
            {
                "field_name": f.field_name,
                "field_type": f.field_type,
                "is_required": f.is_required,
                "validation_regex": f.validation_regex,
                "extraction_hint": f.extraction_hint,
                "anchor_text": f.anchor_text,
            }
            for f in doc.template.fields
        ]
        validation_rules = doc.template.validation_rules

    # Process
    result = await processing_pipeline.process_document(
        file_content=file_content,
        filename=doc.original_filename,
        mime_type=doc.mime_type,
        template_fields=template_fields,
        validation_rules=validation_rules,
        extraction_method=data.extraction_method,
        force_ocr=data.force_ocr,
        language=data.language,
    )

    # Update document
    doc.document_type = result.get("classification", {}).get("document_type")
    doc.classification_confidence = result.get("classification", {}).get("confidence")
    doc.page_count = result.get("metadata", {}).get("page_count", 1)
    doc.requires_review = result.get("requires_review", False)
    doc.metadata_json = result.get("metadata", {})

    if result["status"] == "completed":
        extraction = result.get("extraction", {})
        tables = result.get("tables", [])

        table_data = [
            {
                "table_name": t.get("table_name", f"Table {i+1}"),
                "headers": t.get("headers", []),
                "rows": t.get("rows", []),
                "page_number": t.get("page_number"),
            }
            for i, t in enumerate(tables)
        ]

        ext_result = await ext_service.create_extraction_result(
            document_id=document_id,
            extraction_method=extraction.get("method", "auto"),
            fields=extraction.get("fields", []),
            tables=table_data,
            overall_confidence=result.get("classification", {}).get("confidence"),
            raw_output=result,
        )

        await doc_service.update_status(document_id, "completed")
    else:
        await doc_service.update_status(
            document_id, "failed", result.get("error", "Unknown error")
        )

    # Audit
    audit = AuditService(db)
    await audit.log(
        action="document.process.sync",
        resource_type="document",
        resource_id=str(document_id),
        user_id=admin.id,
        details={"status": result["status"]},
        ip_address=get_client_ip(request),
    )

    return result


@router.post("/bulk/process", response_model=SuccessResponse)
async def bulk_process(
    data: BulkProcessRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Process multiple documents."""
    from app.processing.celery_tasks import process_document_task

    doc_service = DocumentService(db)

    # Mark all targeted documents as queued and commit before enqueuing so
    # workers cannot read stale rows.
    for doc_id in data.document_ids:
        await doc_service.update_status(doc_id, "queued")
    await db.commit()

    task_ids = []
    for doc_id in data.document_ids:
        task = process_document_task.delay(
            str(doc_id),
            {"extraction_method": data.extraction_method},
        )
        task_ids.append(task.id)

    return SuccessResponse(
        message=f"Processing started for {len(data.document_ids)} documents",
        data={"task_ids": task_ids},
    )


@router.get("/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Download the original document file."""
    from fastapi.responses import Response

    from app.services.storage_service import storage_service

    doc_service = DocumentService(db)
    doc = await doc_service.get_document(document_id)
    content = await storage_service.read_file(doc.file_path)

    return Response(
        content=content,
        media_type=doc.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{doc.original_filename}"'
        },
    )
