"""Document management service."""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import (
    DocumentNotFoundError,
    FileTooLargeError,
    InvalidFileTypeError,
)
from app.models.document import Document, DocumentPage
from app.models.extraction import ExtractionResult
from app.models.processing_job import ProcessingJob
from app.schemas.document import DocumentUpdate
from app.services.storage_service import storage_service


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upload_document(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str,
        uploaded_by: uuid.UUID,
        tags: Optional[list[str]] = None,
        notes: Optional[str] = None,
    ) -> Document:
        # Validate file type
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in settings.supported_formats_list:
            raise InvalidFileTypeError(ext)

        # Validate file size
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > settings.MAX_FILE_SIZE_MB:
            raise FileTooLargeError(settings.MAX_FILE_SIZE_MB)

        # Save file
        file_path, file_hash, file_size = await storage_service.save_file(
            file_content, filename
        )

        # Check for duplicates
        existing = await self.db.execute(
            select(Document).where(Document.file_hash == file_hash)
        )
        is_duplicate = existing.scalar_one_or_none() is not None

        # Create document record
        doc = Document(
            filename=file_path.split("/")[-1],
            original_filename=filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            file_hash=file_hash,
            uploaded_by=uploaded_by,
            is_duplicate=is_duplicate,
            tags=tags,
            notes=notes,
            status="uploaded",
        )
        self.db.add(doc)
        await self.db.flush()
        return doc

    async def get_document(self, document_id: uuid.UUID) -> Document:
        result = await self.db.execute(
            select(Document)
            .options(
                selectinload(Document.pages),
                selectinload(Document.extraction_results).selectinload(
                    ExtractionResult.fields
                ),
                selectinload(Document.extraction_results).selectinload(
                    ExtractionResult.tables
                ),
                selectinload(Document.processing_jobs),
            )
            .where(Document.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise DocumentNotFoundError(str(document_id))
        return doc

    async def list_documents(
        self,
        page: int = 1,
        per_page: int = 20,
        status: Optional[str] = None,
        document_type: Optional[str] = None,
        search: Optional[str] = None,
        is_archived: Optional[bool] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Document], int]:
        query = select(Document)

        if status:
            query = query.where(Document.status == status)
        if document_type:
            query = query.where(Document.document_type == document_type)
        if is_archived is not None:
            query = query.where(Document.is_archived == is_archived)
        if search:
            query = query.where(
                or_(
                    Document.original_filename.ilike(f"%{search}%"),
                    Document.document_type.ilike(f"%{search}%"),
                    Document.notes.ilike(f"%{search}%"),
                )
            )

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar()

        sort_col = getattr(Document, sort_by, Document.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        docs = list(result.scalars().all())
        return docs, total

    async def update_document(
        self, document_id: uuid.UUID, data: DocumentUpdate
    ) -> Document:
        doc = await self.get_document(document_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(doc, field, value)
        await self.db.flush()
        return doc

    async def delete_document(self, document_id: uuid.UUID) -> None:
        doc = await self.get_document(document_id)
        await storage_service.delete_file(doc.file_path)
        for page in doc.pages:
            if page.image_path:
                await storage_service.delete_file(page.image_path)
        await self.db.delete(doc)
        await self.db.flush()

    async def get_stats(self) -> dict[str, Any]:
        total = (await self.db.execute(select(func.count(Document.id)))).scalar()

        status_result = await self.db.execute(
            select(Document.status, func.count(Document.id)).group_by(Document.status)
        )
        by_status = {row[0]: row[1] for row in status_result.all()}

        type_result = await self.db.execute(
            select(Document.document_type, func.count(Document.id))
            .where(Document.document_type.isnot(None))
            .group_by(Document.document_type)
        )
        by_type = {row[0]: row[1] for row in type_result.all()}

        pages = (
            await self.db.execute(select(func.sum(Document.page_count)))
        ).scalar() or 0

        storage_used = await storage_service.get_storage_usage()

        return {
            "total_documents": total,
            "by_status": by_status,
            "by_type": by_type,
            "total_pages_processed": pages,
            "storage_used_bytes": storage_used,
        }

    async def update_status(
        self,
        document_id: uuid.UUID,
        status: str,
        error_message: Optional[str] = None,
    ) -> Document:
        doc = await self.get_document(document_id)
        doc.status = status
        doc.error_message = error_message
        if status == "processing":
            doc.processing_started_at = datetime.now(timezone.utc)
        elif status in ("completed", "failed"):
            doc.processing_completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return doc
