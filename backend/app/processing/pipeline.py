"""Main document processing pipeline."""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from loguru import logger
from PIL import Image

from app.processing.classifier import classifier
from app.processing.document_parser import document_parser
from app.processing.extractor import data_extractor
from app.processing.llm_extractor import llm_extractor
from app.processing.ocr_engine import ocr_engine
from app.processing.validator import validation_engine


class ProcessingPipeline:
    """Orchestrates the full document processing pipeline."""

    async def process_document(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str,
        template_fields: Optional[list[dict]] = None,
        validation_rules: Optional[dict] = None,
        extraction_method: str = "auto",
        force_ocr: bool = False,
        language: Optional[str] = None,
    ) -> dict[str, Any]:
        """Run the full processing pipeline on a document."""
        result = {
            "status": "processing",
            "steps": [],
            "text": "",
            "pages": [],
            "classification": None,
            "extraction": None,
            "validation": None,
            "tables": [],
            "metadata": {},
        }

        try:
            # Step 1: Parse document
            logger.info(f"Step 1: Parsing document '{filename}'")
            parsed = await document_parser.parse(file_content, mime_type, filename)
            result["steps"].append({"step": "parse", "status": "completed"})
            result["metadata"] = parsed.get("metadata", {})
            result["metadata"]["page_count"] = parsed.get("page_count", 1)
            result["metadata"]["document_format"] = parsed.get("type", "unknown")

            # Step 2: OCR (if needed)
            text = parsed.get("text", "")
            pages_data = parsed.get("pages", [])

            if parsed.get("requires_ocr") or force_ocr:
                logger.info("Step 2: Running OCR")
                ocr_results = await self._run_ocr(
                    file_content, mime_type, filename, pages_data
                )
                if ocr_results["text"]:
                    text = ocr_results["text"]
                    pages_data = ocr_results.get("pages", pages_data)
                result["steps"].append(
                    {
                        "step": "ocr",
                        "status": "completed",
                        "confidence": ocr_results.get("avg_confidence", 0),
                    }
                )
            else:
                result["steps"].append({"step": "ocr", "status": "skipped"})

            result["text"] = text
            result["pages"] = pages_data

            # Step 3: Classification
            logger.info("Step 3: Classifying document")
            doc_type, class_confidence = classifier.classify(text)
            result["classification"] = {
                "document_type": doc_type,
                "confidence": class_confidence,
            }
            result["steps"].append(
                {
                    "step": "classification",
                    "status": "completed",
                    "type": doc_type,
                    "confidence": class_confidence,
                }
            )

            # Step 4: Extraction
            logger.info(f"Step 4: Extracting data (method={extraction_method})")
            extraction = await self._extract_data(
                text, doc_type, template_fields, extraction_method
            )
            result["extraction"] = extraction

            # Add tables from parsing
            tables = parsed.get("tables", [])
            if extraction.get("tables"):
                tables.extend(extraction["tables"])
            result["tables"] = tables

            result["steps"].append(
                {
                    "step": "extraction",
                    "status": "completed",
                    "method": extraction_method,
                    "fields_count": len(extraction.get("fields", [])),
                }
            )

            # Step 5: Validation
            logger.info("Step 5: Validating extraction")
            validation = validation_engine.validate(
                extraction.get("fields", []),
                validation_rules,
                template_fields,
            )
            result["validation"] = validation.to_dict()
            result["steps"].append(
                {
                    "step": "validation",
                    "status": "completed",
                    "is_valid": validation.is_valid,
                    "errors": len(validation.errors),
                    "warnings": len(validation.warnings),
                }
            )

            result["status"] = "completed"
            result["requires_review"] = (
                not validation.is_valid
                or any(
                    f.get("confidence", 1) < 0.7
                    for f in extraction.get("fields", [])
                )
            )

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            result["status"] = "failed"
            result["error"] = str(e)
            result["steps"].append(
                {"step": "error", "status": "failed", "message": str(e)}
            )

        return result

    async def _run_ocr(
        self,
        file_content: bytes,
        mime_type: str,
        filename: str,
        existing_pages: list[dict],
    ) -> dict[str, Any]:
        """Run OCR on document pages."""
        all_text = []
        total_confidence = 0.0
        page_count = 0
        ocr_pages = []

        if mime_type == "application/pdf":
            from app.processing.pdf_processor import pdf_processor

            images = await pdf_processor.pdf_to_images(file_content)
            for i, image in enumerate(images):
                ocr_result = await ocr_engine.process_image(image)
                all_text.append(ocr_result.text)
                total_confidence += ocr_result.confidence
                page_count += 1
                ocr_pages.append(
                    {
                        "page_number": i + 1,
                        "text": ocr_result.text,
                        "ocr_confidence": ocr_result.confidence,
                        "blocks": ocr_result.blocks,
                    }
                )
        elif mime_type.startswith("image/"):
            ocr_result = await ocr_engine.process_image_bytes(file_content)
            all_text.append(ocr_result.text)
            total_confidence = ocr_result.confidence
            page_count = 1
            ocr_pages.append(
                {
                    "page_number": 1,
                    "text": ocr_result.text,
                    "ocr_confidence": ocr_result.confidence,
                    "blocks": ocr_result.blocks,
                }
            )

        return {
            "text": "\n\n".join(all_text),
            "pages": ocr_pages,
            "avg_confidence": total_confidence / page_count if page_count > 0 else 0,
        }

    async def _extract_data(
        self,
        text: str,
        document_type: str,
        template_fields: Optional[list[dict]],
        method: str,
    ) -> dict[str, Any]:
        """Extract data using the specified method."""
        if method == "llm" or (method == "auto" and not template_fields):
            # Try LLM extraction first
            try:
                fields_to_extract = template_fields or [
                    {"field_name": "auto", "field_type": "text", "extraction_hint": "Extract all key information"}
                ]
                llm_fields = await llm_extractor.extract_fields(
                    text, fields_to_extract, document_type
                )
                if llm_fields:
                    return {
                        "fields": llm_fields,
                        "tables": [],
                        "method": "llm",
                    }
            except Exception as e:
                logger.warning(f"LLM extraction failed, falling back: {e}")

        # Regex/pattern-based extraction
        extraction = data_extractor.extract_all(
            text, document_type, template_fields
        )
        return {
            "fields": extraction["fields"],
            "tables": extraction.get("tables", []),
            "entities": extraction.get("entities", {}),
            "key_value_pairs": extraction.get("key_value_pairs", {}),
            "method": "template" if template_fields else "auto",
        }


processing_pipeline = ProcessingPipeline()
