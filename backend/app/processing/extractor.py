"""Intelligent data extraction engine."""

import re
from typing import Any, Optional

from loguru import logger


# Common extraction patterns
EXTRACTION_PATTERNS = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone": r"(?:\+?1?[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}",
    "date": r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}",
    "currency": r"\$[\d,]+\.?\d{0,2}|USD\s*[\d,]+\.?\d{0,2}|EUR\s*[\d,]+\.?\d{0,2}",
    "percentage": r"\d+\.?\d*\s*%",
    "url": r"https?://[^\s<>\"]+",
    "address": r"\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct)[.,]?\s*(?:[A-Za-z\s]+,\s*)?[A-Z]{2}\s+\d{5}(?:-\d{4})?",
    "ssn": r"\d{3}-\d{2}-\d{4}",
    "invoice_number": r"(?:Invoice|INV|Inv)\s*#?\s*:?\s*([A-Z0-9-]+)",
    "po_number": r"(?:PO|P\.O\.|Purchase Order)\s*#?\s*:?\s*([A-Z0-9-]+)",
    "total_amount": r"(?:Total|Amount Due|Grand Total|Balance Due)\s*:?\s*\$?([\d,]+\.\d{2})",
    "tax_amount": r"(?:Tax|VAT|GST|Sales Tax)\s*:?\s*\$?([\d,]+\.\d{2})",
    "subtotal": r"(?:Subtotal|Sub-total|Sub Total)\s*:?\s*\$?([\d,]+\.\d{2})",
}

# Key-value pair patterns
KV_PATTERNS = [
    r"([A-Za-z][A-Za-z\s]{1,40})\s*:\s*(.+?)(?=\n|$)",
    r"([A-Za-z][A-Za-z\s]{1,40})\s*-\s*(.+?)(?=\n|$)",
]


class DataExtractor:
    """Extracts structured data from document text."""

    def extract_all(
        self,
        text: str,
        document_type: Optional[str] = None,
        template_fields: Optional[list[dict]] = None,
    ) -> dict[str, Any]:
        """Extract all data from text."""
        result = {
            "fields": [],
            "entities": {},
            "key_value_pairs": {},
            "tables": [],
        }

        # Extract named entities using patterns
        result["entities"] = self._extract_entities(text)

        # Extract key-value pairs
        result["key_value_pairs"] = self._extract_key_value_pairs(text)

        # Template-based extraction
        if template_fields:
            result["fields"] = self._extract_template_fields(
                text, template_fields
            )
        else:
            # Auto-extract based on document type
            result["fields"] = self._auto_extract_fields(
                text, document_type, result["entities"], result["key_value_pairs"]
            )

        return result

    def _extract_entities(self, text: str) -> dict[str, list[str]]:
        """Extract named entities using regex patterns."""
        entities = {}
        for entity_type, pattern in EXTRACTION_PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Deduplicate
                entities[entity_type] = list(dict.fromkeys(matches))
        return entities

    def _extract_key_value_pairs(self, text: str) -> dict[str, str]:
        """Extract key-value pairs from text."""
        kv_pairs = {}
        for pattern in KV_PATTERNS:
            matches = re.findall(pattern, text)
            for key, value in matches:
                key = key.strip()
                value = value.strip()
                if (
                    len(key) > 1
                    and len(value) > 0
                    and len(key) < 50
                    and not key.isdigit()
                ):
                    kv_pairs[key] = value
        return kv_pairs

    def _extract_template_fields(
        self, text: str, template_fields: list[dict]
    ) -> list[dict[str, Any]]:
        """Extract fields based on template definition."""
        fields = []
        for tf in template_fields:
            field_name = tf["field_name"]
            field_type = tf.get("field_type", "text")
            extraction_hint = tf.get("extraction_hint", "")
            validation_regex = tf.get("validation_regex")

            value = None
            confidence = 0.0

            # Try extraction hint as regex
            if extraction_hint:
                try:
                    match = re.search(extraction_hint, text, re.IGNORECASE)
                    if match:
                        value = match.group(1) if match.groups() else match.group(0)
                        confidence = 0.9
                except re.error:
                    pass

            # Try anchor text
            if not value and tf.get("anchor_text"):
                anchor = tf["anchor_text"]
                pattern = rf"{re.escape(anchor)}\s*:?\s*(.+?)(?=\n|$)"
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    confidence = 0.8

            # Try field name as key in key-value pairs
            if not value:
                kv = self._extract_key_value_pairs(text)
                for key, val in kv.items():
                    if field_name.lower() in key.lower() or key.lower() in field_name.lower():
                        value = val
                        confidence = 0.6
                        break

            # Try pattern matching based on field type
            if not value and field_type in EXTRACTION_PATTERNS:
                matches = re.findall(
                    EXTRACTION_PATTERNS[field_type], text, re.IGNORECASE
                )
                if matches:
                    value = matches[0]
                    confidence = 0.5

            # Validate if regex provided
            if value and validation_regex:
                if not re.match(validation_regex, value):
                    confidence *= 0.5  # Reduce confidence if validation fails

            fields.append(
                {
                    "field_name": field_name,
                    "field_value": value,
                    "field_type": field_type,
                    "confidence": confidence,
                }
            )

        return fields

    def _auto_extract_fields(
        self,
        text: str,
        document_type: Optional[str],
        entities: dict,
        kv_pairs: dict,
    ) -> list[dict[str, Any]]:
        """Auto-extract fields based on document type."""
        fields = []

        # Add all key-value pairs as fields
        for key, value in kv_pairs.items():
            field_type = self._infer_field_type(value)
            fields.append(
                {
                    "field_name": key,
                    "field_value": value,
                    "field_type": field_type,
                    "confidence": 0.7,
                }
            )

        # Add entities as fields
        for entity_type, values in entities.items():
            for i, value in enumerate(values):
                field_name = (
                    entity_type if len(values) == 1 else f"{entity_type}_{i + 1}"
                )
                fields.append(
                    {
                        "field_name": field_name,
                        "field_value": value,
                        "field_type": entity_type,
                        "confidence": 0.8,
                    }
                )

        # Document-type specific extractions
        if document_type == "invoice":
            fields.extend(self._extract_invoice_fields(text))
        elif document_type == "receipt":
            fields.extend(self._extract_receipt_fields(text))

        return fields

    def _extract_invoice_fields(self, text: str) -> list[dict[str, Any]]:
        """Extract invoice-specific fields."""
        fields = []
        specific_patterns = {
            "invoice_number": EXTRACTION_PATTERNS["invoice_number"],
            "po_number": EXTRACTION_PATTERNS["po_number"],
            "total_amount": EXTRACTION_PATTERNS["total_amount"],
            "tax_amount": EXTRACTION_PATTERNS["tax_amount"],
            "subtotal": EXTRACTION_PATTERNS["subtotal"],
        }

        for field_name, pattern in specific_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1) if match.groups() else match.group(0)
                fields.append(
                    {
                        "field_name": field_name,
                        "field_value": value.strip(),
                        "field_type": "currency" if "amount" in field_name or "total" in field_name else "text",
                        "confidence": 0.85,
                    }
                )
        return fields

    def _extract_receipt_fields(self, text: str) -> list[dict[str, Any]]:
        """Extract receipt-specific fields."""
        fields = []
        patterns = {
            "total": r"(?:Total|TOTAL)\s*:?\s*\$?([\d,]+\.\d{2})",
            "subtotal": r"(?:Subtotal|SUBTOTAL)\s*:?\s*\$?([\d,]+\.\d{2})",
            "tax": r"(?:Tax|TAX)\s*:?\s*\$?([\d,]+\.\d{2})",
            "payment_method": r"(?:Paid by|Payment|Method)\s*:?\s*(\w+)",
        }

        for field_name, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields.append(
                    {
                        "field_name": field_name,
                        "field_value": match.group(1).strip(),
                        "field_type": "currency" if field_name in ("total", "subtotal", "tax") else "text",
                        "confidence": 0.8,
                    }
                )
        return fields

    def _infer_field_type(self, value: str) -> str:
        """Infer the field type from the value."""
        if re.match(r"^\$?[\d,]+\.\d{2}$", value):
            return "currency"
        if re.match(EXTRACTION_PATTERNS["email"], value):
            return "email"
        if re.match(EXTRACTION_PATTERNS["phone"], value):
            return "phone"
        if re.match(EXTRACTION_PATTERNS["date"], value):
            return "date"
        if re.match(r"^\d+\.?\d*$", value):
            return "number"
        return "text"


data_extractor = DataExtractor()
