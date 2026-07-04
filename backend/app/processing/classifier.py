"""Document classification engine."""

import re
from typing import Any, Optional

from loguru import logger


# Keyword-based classification rules
DOCUMENT_TYPE_RULES = {
    "invoice": {
        "keywords": [
            "invoice", "inv", "bill to", "ship to", "subtotal", "total due",
            "payment terms", "due date", "invoice number", "invoice date",
            "tax", "vat", "amount due", "remit to", "purchase order",
        ],
        "patterns": [
            r"invoice\s*#?\s*\d+",
            r"inv[\s-]*\d+",
            r"total\s*:?\s*\$?[\d,]+\.\d{2}",
        ],
    },
    "receipt": {
        "keywords": [
            "receipt", "transaction", "paid", "change", "cashier",
            "store", "thank you", "total", "subtotal", "cash", "card",
        ],
        "patterns": [
            r"receipt\s*#?\s*\d+",
            r"transaction\s*#?\s*\d+",
        ],
    },
    "contract": {
        "keywords": [
            "agreement", "contract", "parties", "whereas", "hereby",
            "terms and conditions", "effective date", "termination",
            "governing law", "jurisdiction", "signature", "witness",
            "indemnification", "liability", "confidential",
        ],
        "patterns": [
            r"this\s+agreement",
            r"entered\s+into",
            r"party\s+of\s+the\s+first",
        ],
    },
    "resume": {
        "keywords": [
            "resume", "curriculum vitae", "cv", "experience",
            "education", "skills", "objective", "references",
            "employment history", "work experience", "qualifications",
        ],
        "patterns": [
            r"\b\d{4}\s*[-–]\s*(\d{4}|present)\b",
        ],
    },
    "form": {
        "keywords": [
            "form", "application", "please fill", "check box",
            "signature", "date of birth", "social security",
            "applicant", "submit", "required fields",
        ],
        "patterns": [
            r"form\s*#?\s*\w+",
            r"\[\s*\]",  # Empty checkboxes
        ],
    },
    "report": {
        "keywords": [
            "report", "summary", "findings", "analysis",
            "conclusion", "recommendation", "executive summary",
            "methodology", "results", "appendix",
        ],
        "patterns": [
            r"table\s+of\s+contents",
            r"figure\s+\d+",
        ],
    },
    "letter": {
        "keywords": [
            "dear", "sincerely", "regards", "to whom it may concern",
            "yours truly", "respectfully", "enclosed",
        ],
        "patterns": [
            r"dear\s+\w+",
            r"sincerely,?",
        ],
    },
    "id_document": {
        "keywords": [
            "passport", "driver license", "identification",
            "national id", "date of birth", "expiry date",
            "issuing authority", "nationality",
        ],
        "patterns": [
            r"passport\s*no",
            r"license\s*no",
            r"id\s*no",
        ],
    },
}


class DocumentClassifier:
    """Classifies documents based on content analysis."""

    def __init__(self, custom_rules: Optional[dict] = None):
        self.rules = {**DOCUMENT_TYPE_RULES}
        if custom_rules:
            self.rules.update(custom_rules)

    def classify(self, text: str) -> tuple[str, float]:
        """Classify document text and return (type, confidence)."""
        if not text or not text.strip():
            return "unknown", 0.0

        text_lower = text.lower()
        scores = {}

        for doc_type, rules in self.rules.items():
            score = 0.0

            # Keyword matching
            keywords = rules.get("keywords", [])
            keyword_matches = sum(
                1 for kw in keywords if kw.lower() in text_lower
            )
            if keywords:
                score += (keyword_matches / len(keywords)) * 0.7

            # Pattern matching
            patterns = rules.get("patterns", [])
            pattern_matches = sum(
                1
                for pattern in patterns
                if re.search(pattern, text_lower)
            )
            if patterns:
                score += (pattern_matches / len(patterns)) * 0.3

            scores[doc_type] = score

        if not scores:
            return "unknown", 0.0

        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]

        # Minimum threshold
        if best_score < 0.1:
            return "unknown", best_score

        # Normalize confidence to 0-1 range
        confidence = min(best_score, 1.0)

        logger.info(
            f"Classified as '{best_type}' with confidence {confidence:.2f}"
        )
        return best_type, confidence

    def classify_with_template_keywords(
        self, text: str, template_keywords: dict[str, list[str]]
    ) -> tuple[str, float]:
        """Classify using custom template keywords."""
        text_lower = text.lower()
        scores = {}

        for doc_type, keywords in template_keywords.items():
            matches = sum(1 for kw in keywords if kw.lower() in text_lower)
            scores[doc_type] = matches / len(keywords) if keywords else 0

        if not scores:
            return self.classify(text)

        best_type = max(scores, key=scores.get)
        if scores[best_type] < 0.1:
            return self.classify(text)

        return best_type, min(scores[best_type], 1.0)


classifier = DocumentClassifier()
