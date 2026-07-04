"""Extraction validation engine."""

import re
from datetime import datetime
from typing import Any, Optional

from loguru import logger


class ValidationResult:
    def __init__(self):
        self.is_valid = True
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []

    def add_error(self, field: str, message: str, rule: str):
        self.is_valid = False
        self.errors.append({"field": field, "message": message, "rule": rule})

    def add_warning(self, field: str, message: str, rule: str):
        self.warnings.append({"field": field, "message": message, "rule": rule})

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }


class ValidationEngine:
    """Validates extracted data against rules."""

    def validate(
        self,
        fields: list[dict[str, Any]],
        validation_rules: Optional[dict[str, Any]] = None,
        template_fields: Optional[list[dict]] = None,
    ) -> ValidationResult:
        """Run all validation checks."""
        result = ValidationResult()

        # Required field checks
        if template_fields:
            self._check_required_fields(fields, template_fields, result)

        # Type validation
        for field in fields:
            self._validate_field_type(field, result)

        # Regex validation from template
        if template_fields:
            self._validate_regex(fields, template_fields, result)

        # Custom validation rules
        if validation_rules:
            self._apply_custom_rules(fields, validation_rules, result)

        # Cross-field validation
        self._cross_field_validation(fields, result)

        # Confidence checks
        self._check_confidence(fields, result)

        return result

    def _check_required_fields(
        self,
        fields: list[dict],
        template_fields: list[dict],
        result: ValidationResult,
    ):
        """Check that all required fields have values."""
        extracted_names = {
            f["field_name"]: f["field_value"] for f in fields
        }

        for tf in template_fields:
            if tf.get("is_required") and tf["field_name"] not in extracted_names:
                result.add_error(
                    tf["field_name"],
                    f"Required field '{tf['field_name']}' is missing",
                    "required",
                )
            elif (
                tf.get("is_required")
                and not extracted_names.get(tf["field_name"])
            ):
                result.add_error(
                    tf["field_name"],
                    f"Required field '{tf['field_name']}' is empty",
                    "required",
                )

    def _validate_field_type(
        self, field: dict, result: ValidationResult
    ):
        """Validate field value matches expected type."""
        value = field.get("field_value")
        if not value:
            return

        field_type = field.get("field_type", "text")
        field_name = field["field_name"]

        if field_type == "number":
            try:
                float(value.replace(",", ""))
            except (ValueError, AttributeError):
                result.add_error(
                    field_name,
                    f"Value '{value}' is not a valid number",
                    "type_check",
                )

        elif field_type == "currency":
            cleaned = re.sub(r"[\$,\s]", "", str(value))
            try:
                float(cleaned)
            except ValueError:
                result.add_error(
                    field_name,
                    f"Value '{value}' is not a valid currency amount",
                    "type_check",
                )

        elif field_type == "email":
            if not re.match(
                r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", str(value)
            ):
                result.add_error(
                    field_name,
                    f"Value '{value}' is not a valid email",
                    "type_check",
                )

        elif field_type == "date":
            date_formats = [
                "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d",
                "%m-%d-%Y", "%B %d, %Y", "%b %d, %Y",
            ]
            valid = False
            for fmt in date_formats:
                try:
                    datetime.strptime(str(value), fmt)
                    valid = True
                    break
                except ValueError:
                    continue
            if not valid:
                result.add_warning(
                    field_name,
                    f"Value '{value}' may not be a valid date",
                    "type_check",
                )

    def _validate_regex(
        self,
        fields: list[dict],
        template_fields: list[dict],
        result: ValidationResult,
    ):
        """Validate fields against template regex patterns."""
        regex_map = {
            tf["field_name"]: tf["validation_regex"]
            for tf in template_fields
            if tf.get("validation_regex")
        }

        for field in fields:
            regex = regex_map.get(field["field_name"])
            if regex and field.get("field_value"):
                if not re.match(regex, str(field["field_value"])):
                    result.add_error(
                        field["field_name"],
                        f"Value does not match expected pattern",
                        "regex",
                    )

    def _apply_custom_rules(
        self,
        fields: list[dict],
        rules: dict[str, Any],
        result: ValidationResult,
    ):
        """Apply custom validation rules."""
        field_map = {f["field_name"]: f.get("field_value") for f in fields}

        # Range checks
        for rule in rules.get("range_checks", []):
            field_name = rule["field"]
            value = field_map.get(field_name)
            if value:
                try:
                    num_val = float(str(value).replace(",", "").replace("$", ""))
                    if "min" in rule and num_val < rule["min"]:
                        result.add_error(
                            field_name,
                            f"Value {num_val} is below minimum {rule['min']}",
                            "range",
                        )
                    if "max" in rule and num_val > rule["max"]:
                        result.add_error(
                            field_name,
                            f"Value {num_val} exceeds maximum {rule['max']}",
                            "range",
                        )
                except ValueError:
                    pass

        # Sum checks (e.g., subtotal + tax = total)
        for rule in rules.get("sum_checks", []):
            addends = rule.get("addends", [])
            total_field = rule.get("total_field")
            tolerance = rule.get("tolerance", 0.01)

            try:
                addend_sum = sum(
                    float(
                        str(field_map.get(f, "0")).replace(",", "").replace("$", "")
                    )
                    for f in addends
                )
                total_val = float(
                    str(field_map.get(total_field, "0"))
                    .replace(",", "")
                    .replace("$", "")
                )
                if abs(addend_sum - total_val) > tolerance:
                    result.add_warning(
                        total_field,
                        f"Sum of {addends} ({addend_sum}) does not match {total_field} ({total_val})",
                        "sum_check",
                    )
            except (ValueError, TypeError):
                pass

    def _cross_field_validation(
        self, fields: list[dict], result: ValidationResult
    ):
        """Cross-field validation checks."""
        field_map = {f["field_name"]: f.get("field_value") for f in fields}

        # Check date ordering (start_date < end_date)
        start_fields = [
            k for k in field_map if "start" in k.lower() and "date" in k.lower()
        ]
        end_fields = [
            k for k in field_map if "end" in k.lower() and "date" in k.lower()
        ]

        # Check for duplicate values in fields that should be unique
        values = [f["field_value"] for f in fields if f.get("field_value")]
        seen = set()
        for v in values:
            if v in seen and len(v) > 3:
                result.add_warning(
                    "_duplicate",
                    f"Duplicate value found: '{v}'",
                    "duplicate_check",
                )
            seen.add(v)

    def _check_confidence(
        self, fields: list[dict], result: ValidationResult
    ):
        """Flag low-confidence extractions."""
        for field in fields:
            confidence = field.get("confidence", 1.0)
            if confidence is not None and confidence < 0.5:
                result.add_warning(
                    field["field_name"],
                    f"Low confidence extraction ({confidence:.2f})",
                    "confidence",
                )


validation_engine = ValidationEngine()
