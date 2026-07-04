"""Extraction management service."""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.extraction import ExtractionField, ExtractionResult, ExtractionTable


class ExtractionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_extraction_result(
        self,
        document_id: uuid.UUID,
        extraction_method: str,
        fields: list[dict[str, Any]],
        tables: Optional[list[dict[str, Any]]] = None,
        overall_confidence: Optional[float] = None,
        raw_output: Optional[dict] = None,
    ) -> ExtractionResult:
        result = ExtractionResult(
            document_id=document_id,
            extraction_method=extraction_method,
            overall_confidence=overall_confidence,
            raw_output=raw_output,
        )
        self.db.add(result)
        await self.db.flush()

        for field_data in fields:
            field = ExtractionField(
                extraction_result_id=result.id,
                field_name=field_data["field_name"],
                field_value=field_data.get("field_value"),
                field_type=field_data.get("field_type", "text"),
                confidence=field_data.get("confidence"),
                page_number=field_data.get("page_number"),
                bounding_box=field_data.get("bounding_box"),
            )
            self.db.add(field)

        if tables:
            for table_data in tables:
                table = ExtractionTable(
                    extraction_result_id=result.id,
                    table_name=table_data.get("table_name"),
                    headers=table_data.get("headers"),
                    rows=table_data.get("rows"),
                    page_number=table_data.get("page_number"),
                    confidence=table_data.get("confidence"),
                )
                self.db.add(table)

        await self.db.flush()
        return result

    async def get_extraction_result(
        self, extraction_id: uuid.UUID
    ) -> Optional[ExtractionResult]:
        result = await self.db.execute(
            select(ExtractionResult)
            .options(
                selectinload(ExtractionResult.fields),
                selectinload(ExtractionResult.tables),
            )
            .where(ExtractionResult.id == extraction_id)
        )
        return result.scalar_one_or_none()

    async def get_document_extractions(
        self, document_id: uuid.UUID
    ) -> list[ExtractionResult]:
        result = await self.db.execute(
            select(ExtractionResult)
            .options(
                selectinload(ExtractionResult.fields),
                selectinload(ExtractionResult.tables),
            )
            .where(ExtractionResult.document_id == document_id)
            .order_by(ExtractionResult.version.desc())
        )
        return list(result.scalars().all())

    async def correct_field(
        self,
        field_id: uuid.UUID,
        corrected_value: str,
    ) -> ExtractionField:
        result = await self.db.execute(
            select(ExtractionField).where(ExtractionField.id == field_id)
        )
        field = result.scalar_one_or_none()
        if not field:
            raise ValueError(f"Field {field_id} not found")

        if not field.is_corrected:
            field.original_value = field.field_value
        field.field_value = corrected_value
        field.is_corrected = True
        await self.db.flush()
        return field

    async def validate_extraction(
        self,
        extraction_id: uuid.UUID,
        validated_by: uuid.UUID,
        corrections: Optional[list[dict]] = None,
    ) -> ExtractionResult:
        extraction = await self.get_extraction_result(extraction_id)
        if not extraction:
            raise ValueError(f"Extraction {extraction_id} not found")

        if corrections:
            for correction in corrections:
                await self.correct_field(
                    correction["field_id"], correction["corrected_value"]
                )

        extraction.validated = True
        extraction.validated_by = validated_by
        extraction.validated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return extraction

    async def export_extraction(
        self, extraction_id: uuid.UUID, format: str = "json"
    ) -> dict[str, Any]:
        extraction = await self.get_extraction_result(extraction_id)
        if not extraction:
            raise ValueError(f"Extraction {extraction_id} not found")

        data = {
            "extraction_id": str(extraction.id),
            "document_id": str(extraction.document_id),
            "method": extraction.extraction_method,
            "confidence": extraction.overall_confidence,
            "validated": extraction.validated,
            "fields": {},
            "tables": [],
        }

        for field in extraction.fields:
            data["fields"][field.field_name] = {
                "value": field.field_value,
                "type": field.field_type,
                "confidence": field.confidence,
                "corrected": field.is_corrected,
            }

        for table in extraction.tables:
            data["tables"].append(
                {
                    "name": table.table_name,
                    "headers": table.headers,
                    "rows": table.rows,
                }
            )

        return data
