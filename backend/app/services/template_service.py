"""Template management service."""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import TemplateNotFoundError
from app.models.template import ExtractionTemplate, TemplateField
from app.schemas.template import TemplateCreate, TemplateFieldCreate, TemplateUpdate


class TemplateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_template(
        self, data: TemplateCreate, created_by: uuid.UUID
    ) -> ExtractionTemplate:
        template = ExtractionTemplate(
            name=data.name,
            description=data.description,
            document_type=data.document_type,
            preprocessing_config=data.preprocessing_config,
            classification_keywords=data.classification_keywords,
            validation_rules=data.validation_rules,
            post_processing_config=data.post_processing_config,
            created_by=created_by,
        )
        self.db.add(template)
        await self.db.flush()

        for field_data in data.fields:
            field = TemplateField(
                template_id=template.id,
                field_name=field_data.field_name,
                field_label=field_data.field_label,
                field_type=field_data.field_type,
                is_required=field_data.is_required,
                default_value=field_data.default_value,
                validation_regex=field_data.validation_regex,
                extraction_hint=field_data.extraction_hint,
                order=field_data.order,
                anchor_text=field_data.anchor_text,
                relative_position=field_data.relative_position,
            )
            self.db.add(field)

        await self.db.flush()
        return template

    async def get_template(
        self, template_id: uuid.UUID
    ) -> ExtractionTemplate:
        result = await self.db.execute(
            select(ExtractionTemplate)
            .options(selectinload(ExtractionTemplate.fields))
            .where(ExtractionTemplate.id == template_id)
        )
        template = result.scalar_one_or_none()
        if not template:
            raise TemplateNotFoundError(str(template_id))
        return template

    async def list_templates(
        self,
        document_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[list[ExtractionTemplate], int]:
        query = select(ExtractionTemplate).options(
            selectinload(ExtractionTemplate.fields)
        )

        if document_type:
            query = query.where(
                ExtractionTemplate.document_type == document_type
            )
        if is_active is not None:
            query = query.where(ExtractionTemplate.is_active == is_active)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar()

        query = query.order_by(ExtractionTemplate.created_at.desc())
        result = await self.db.execute(query)
        templates = list(result.scalars().all())
        return templates, total

    async def update_template(
        self, template_id: uuid.UUID, data: TemplateUpdate
    ) -> ExtractionTemplate:
        template = await self.get_template(template_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(template, field, value)
        template.version += 1
        await self.db.flush()
        return template

    async def delete_template(self, template_id: uuid.UUID) -> None:
        template = await self.get_template(template_id)
        await self.db.delete(template)
        await self.db.flush()

    async def add_field(
        self, template_id: uuid.UUID, field_data: TemplateFieldCreate
    ) -> TemplateField:
        await self.get_template(template_id)  # Ensure exists
        field = TemplateField(
            template_id=template_id,
            field_name=field_data.field_name,
            field_label=field_data.field_label,
            field_type=field_data.field_type,
            is_required=field_data.is_required,
            default_value=field_data.default_value,
            validation_regex=field_data.validation_regex,
            extraction_hint=field_data.extraction_hint,
            order=field_data.order,
            anchor_text=field_data.anchor_text,
            relative_position=field_data.relative_position,
        )
        self.db.add(field)
        await self.db.flush()
        return field

    async def remove_field(self, field_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(TemplateField).where(TemplateField.id == field_id)
        )
        field = result.scalar_one_or_none()
        if field:
            await self.db.delete(field)
            await self.db.flush()
