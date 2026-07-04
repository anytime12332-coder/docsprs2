"""LLM-powered intelligent extraction."""

import json
from typing import Any, Optional

from loguru import logger

from app.core.config import settings


class LLMExtractor:
    """Uses LLMs for intelligent document understanding and extraction."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None and settings.OPENAI_API_KEY:
            try:
                from langchain_openai import ChatOpenAI
                self._client = ChatOpenAI(
                    model=settings.LLM_MODEL,
                    api_key=settings.OPENAI_API_KEY,
                    temperature=0,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize LLM client: {e}")
        return self._client

    async def extract_fields(
        self,
        text: str,
        fields_to_extract: list[dict[str, str]],
        document_type: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Extract specific fields using LLM."""
        client = self._get_client()
        if not client:
            logger.warning("LLM client not available, skipping LLM extraction")
            return []

        fields_desc = "\n".join(
            f"- {f['field_name']} ({f.get('field_type', 'text')}): {f.get('extraction_hint', 'Extract this field')}"
            for f in fields_to_extract
        )

        prompt = f"""You are a document data extraction expert. Extract the following fields from the document text below.

Document Type: {document_type or 'Unknown'}

Fields to extract:
{fields_desc}

Document Text:
---
{text[:8000]}
---

Return a JSON array where each element has:
- "field_name": the field name
- "field_value": the extracted value (null if not found)
- "field_type": the data type
- "confidence": your confidence score (0.0 to 1.0)

Return ONLY the JSON array, no other text."""

        try:
            response = await client.ainvoke(prompt)
            content = response.content.strip()

            # Clean up response
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            fields = json.loads(content.strip())
            return fields
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return []

    async def summarize_document(self, text: str) -> str:
        """Generate a document summary."""
        client = self._get_client()
        if not client:
            return ""

        prompt = f"""Summarize the following document in 2-3 sentences:

{text[:6000]}

Summary:"""

        try:
            response = await client.ainvoke(prompt)
            return response.content.strip()
        except Exception as e:
            logger.error(f"LLM summarization failed: {e}")
            return ""

    async def classify_document(self, text: str) -> tuple[str, float]:
        """Classify document using LLM."""
        client = self._get_client()
        if not client:
            return "unknown", 0.0

        prompt = f"""Classify the following document into one of these categories:
- invoice
- receipt
- contract
- resume
- form
- report
- letter
- id_document
- other

Document text:
---
{text[:4000]}
---

Return ONLY a JSON object with "type" and "confidence" (0.0 to 1.0)."""

        try:
            response = await client.ainvoke(prompt)
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            result = json.loads(content)
            return result.get("type", "unknown"), result.get("confidence", 0.5)
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return "unknown", 0.0

    async def extract_tables_from_text(self, text: str) -> list[dict[str, Any]]:
        """Extract tabular data from unstructured text using LLM."""
        client = self._get_client()
        if not client:
            return []

        prompt = f"""Extract any tabular data from the following text. Return as a JSON array of tables.
Each table should have "table_name", "headers" (array of strings), and "rows" (array of arrays).

Text:
---
{text[:6000]}
---

Return ONLY the JSON array. If no tables found, return []."""

        try:
            response = await client.ainvoke(prompt)
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(content)
        except Exception as e:
            logger.error(f"LLM table extraction failed: {e}")
            return []


llm_extractor = LLMExtractor()
