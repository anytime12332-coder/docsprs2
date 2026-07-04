"""Celery tasks for async document processing."""

import asyncio
import uuid
from datetime import datetime, timezone

from celery import Celery
from loguru import logger

from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "documind",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.PROCESSING_TIMEOUT_SECONDS,
    worker_max_tasks_per_child=100,
    worker_prefetch_multiplier=1,
)


def run_async(coro):
    """Helper to run async code in Celery tasks."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_document_task(self, document_id: str, options: dict = None):
    """Process a document asynchronously."""
    from app.core.database import AsyncSessionLocal
    from app.processing.pipeline import processing_pipeline
    from app.services.document_service import DocumentService
    from app.services.extraction_service import ExtractionService
    from app.services.storage_service import storage_service

    options = options or {}
    doc_uuid = uuid.UUID(document_id)

    async def _process():
        async with AsyncSessionLocal() as db:
            try:
                doc_service = DocumentService(db)
                ext_service = ExtractionService(db)

                # Get document
                doc = await doc_service.get_document(doc_uuid)
                await doc_service.update_status(doc_uuid, "processing")

                # Read file
                file_content = await storage_service.read_file(doc.file_path)

                # Get template fields if template assigned
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

                # Run pipeline
                result = await processing_pipeline.process_document(
                    file_content=file_content,
                    filename=doc.original_filename,
                    mime_type=doc.mime_type,
                    template_fields=template_fields,
                    validation_rules=validation_rules,
                    extraction_method=options.get("extraction_method", "auto"),
                    force_ocr=options.get("force_ocr", False),
                    language=options.get("language"),
                )

                # Update document
                doc.document_type = result.get("classification", {}).get("document_type")
                doc.classification_confidence = result.get("classification", {}).get("confidence")
                doc.page_count = result.get("metadata", {}).get("page_count", 1)
                doc.requires_review = result.get("requires_review", False)
                doc.metadata_json = result.get("metadata", {})

                if result["status"] == "completed":
                    # Save extraction results
                    extraction = result.get("extraction", {})
                    fields = extraction.get("fields", [])
                    tables = result.get("tables", [])

                    table_data = [
                        {
                            "table_name": t.get("table_name", f"Table {i+1}"),
                            "headers": t.get("headers", []),
                            "rows": t.get("rows", []),
                            "page_number": t.get("page_number"),
                            "confidence": t.get("confidence"),
                        }
                        for i, t in enumerate(tables)
                    ]

                    await ext_service.create_extraction_result(
                        document_id=doc_uuid,
                        extraction_method=extraction.get("method", "auto"),
                        fields=fields,
                        tables=table_data,
                        overall_confidence=result.get("classification", {}).get("confidence"),
                        raw_output=result,
                    )

                    await doc_service.update_status(doc_uuid, "completed")
                else:
                    await doc_service.update_status(
                        doc_uuid, "failed", result.get("error", "Unknown error")
                    )

                await db.commit()
                return {"status": result["status"], "document_id": document_id}

            except Exception as e:
                logger.error(f"Document processing failed: {e}")
                await doc_service.update_status(doc_uuid, "failed", str(e))
                await db.commit()
                raise

    try:
        return run_async(_process())
    except Exception as e:
        logger.error(f"Task failed: {e}")
        self.retry(exc=e)


@celery_app.task
def cleanup_temp_files():
    """Periodic task to clean up temporary files."""
    from app.services.storage_service import storage_service

    run_async(storage_service.cleanup_temp())
    logger.info("Temp files cleaned up")


# Periodic tasks
celery_app.conf.beat_schedule = {
    "cleanup-temp-files": {
        "task": "app.processing.celery_tasks.cleanup_temp_files",
        "schedule": 3600.0,  # Every hour
    },
}
