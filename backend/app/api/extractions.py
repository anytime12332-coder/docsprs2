"""Extraction routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_client_ip, require_admin
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.extraction import (
    BulkFieldCorrectionRequest,
    ExtractionResultResponse,
    ValidateExtractionRequest,
)
from app.services.audit_service import AuditService
from app.services.extraction_service import ExtractionService

router = APIRouter(prefix="/extractions", tags=["Extractions"])


@router.get("/document/{document_id}", response_model=list[ExtractionResultResponse])
async def get_document_extractions(
    document_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get all extraction results for a document."""
    ext_service = ExtractionService(db)
    return await ext_service.get_document_extractions(document_id)


@router.get("/{extraction_id}", response_model=ExtractionResultResponse)
async def get_extraction(
    extraction_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific extraction result."""
    ext_service = ExtractionService(db)
    result = await ext_service.get_extraction_result(extraction_id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Extraction not found")
    return result


@router.post("/correct", response_model=SuccessResponse)
async def correct_fields(
    data: BulkFieldCorrectionRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Correct extracted field values."""
    ext_service = ExtractionService(db)
    for correction in data.corrections:
        await ext_service.correct_field(
            correction.field_id, correction.corrected_value
        )

    audit = AuditService(db)
    await audit.log(
        action="extraction.correct",
        resource_type="extraction",
        user_id=admin.id,
        details={"corrections_count": len(data.corrections)},
        ip_address=get_client_ip(request),
    )

    return SuccessResponse(
        message=f"{len(data.corrections)} fields corrected"
    )


@router.post("/validate", response_model=SuccessResponse)
async def validate_extraction(
    data: ValidateExtractionRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Validate and approve an extraction result."""
    ext_service = ExtractionService(db)
    corrections = None
    if data.corrections:
        corrections = [
            {"field_id": c.field_id, "corrected_value": c.corrected_value}
            for c in data.corrections
        ]

    await ext_service.validate_extraction(
        data.extraction_id, admin.id, corrections
    )

    audit = AuditService(db)
    await audit.log(
        action="extraction.validate",
        resource_type="extraction",
        resource_id=str(data.extraction_id),
        user_id=admin.id,
        ip_address=get_client_ip(request),
    )

    return SuccessResponse(message="Extraction validated successfully")


@router.get("/{extraction_id}/export")
async def export_extraction(
    extraction_id: uuid.UUID,
    format: str = "json",
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Export extraction results."""
    ext_service = ExtractionService(db)
    data = await ext_service.export_extraction(extraction_id, format)

    if format == "csv":
        import csv
        import io

        from fastapi.responses import StreamingResponse

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Field Name", "Value", "Type", "Confidence", "Corrected"])
        for name, info in data["fields"].items():
            writer.writerow([
                name,
                info["value"],
                info["type"],
                info["confidence"],
                info["corrected"],
            ])

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=extraction_{extraction_id}.csv"},
        )

    return data
