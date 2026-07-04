"""OCR engine with multi-backend support."""

import io
from typing import Any, Optional

from PIL import Image
from loguru import logger

from app.core.config import settings
from app.processing.preprocessor import ImagePreprocessor


class OCRResult:
    """Structured OCR output."""

    def __init__(
        self,
        text: str,
        confidence: float,
        blocks: list[dict[str, Any]],
        language: Optional[str] = None,
    ):
        self.text = text
        self.confidence = confidence
        self.blocks = blocks
        self.language = language


class OCREngine:
    """Multi-backend OCR engine."""

    def __init__(self, engine: Optional[str] = None):
        self.engine = engine or settings.OCR_ENGINE
        self.preprocessor = ImagePreprocessor()
        self._paddle_ocr = None
        self._paddle_available = None

    def _check_paddle_available(self) -> bool:
        if self._paddle_available is None:
            try:
                import paddleocr  # noqa: F401
                self._paddle_available = True
            except ImportError:
                self._paddle_available = False
                if self.engine == "paddleocr":
                    logger.warning("PaddleOCR not installed, falling back to Tesseract")
                    self.engine = "tesseract"
        return self._paddle_available

    def _get_paddle_ocr(self):
        if not self._check_paddle_available():
            return None
        if self._paddle_ocr is None:
            from paddleocr import PaddleOCR
            self._paddle_ocr = PaddleOCR(
                use_angle_cls=True,
                lang="en",
                show_log=False,
                use_gpu=False,
            )
        return self._paddle_ocr

    async def process_image(self, image: Image.Image) -> OCRResult:
        """Run OCR on a single image."""
        processed = self.preprocessor.process(image)

        if self.engine == "paddleocr" and self._check_paddle_available():
            return await self._paddle_ocr_process(processed)
        else:
            return await self._tesseract_process(processed)

    async def process_image_bytes(self, image_bytes: bytes) -> OCRResult:
        """Run OCR on image bytes."""
        image = Image.open(io.BytesIO(image_bytes))
        return await self.process_image(image)

    async def _paddle_ocr_process(self, image: Image.Image) -> OCRResult:
        """Process with PaddleOCR."""
        try:
            import numpy as np

            ocr = self._get_paddle_ocr()
            if ocr is None:
                return await self._tesseract_process(image)

            img_array = np.array(image)
            results = ocr.ocr(img_array, cls=True)

            blocks = []
            all_text = []
            total_confidence = 0.0
            count = 0

            if results and results[0]:
                for line in results[0]:
                    bbox = line[0]
                    text_val = line[1][0]
                    confidence = line[1][1]

                    blocks.append(
                        {
                            "text": text_val,
                            "confidence": confidence,
                            "bbox": [
                                int(bbox[0][0]),
                                int(bbox[0][1]),
                                int(bbox[2][0]),
                                int(bbox[2][1]),
                            ],
                        }
                    )
                    all_text.append(text_val)
                    total_confidence += confidence
                    count += 1

            avg_confidence = total_confidence / count if count > 0 else 0.0
            full_text = "\n".join(all_text)

            return OCRResult(
                text=full_text,
                confidence=avg_confidence,
                blocks=blocks,
            )
        except Exception as e:
            logger.error(f"PaddleOCR failed, falling back to Tesseract: {e}")
            return await self._tesseract_process(image)

    async def _tesseract_process(self, image: Image.Image) -> OCRResult:
        """Process with Tesseract."""
        try:
            import pytesseract

            data = pytesseract.image_to_data(
                image, output_type=pytesseract.Output.DICT, lang=settings.OCR_LANGUAGES
            )

            blocks = []
            all_text = []
            total_confidence = 0.0
            count = 0

            for i in range(len(data["text"])):
                text_val = data["text"][i].strip()
                conf = float(data["conf"][i])

                if text_val and conf > 0:
                    blocks.append(
                        {
                            "text": text_val,
                            "confidence": conf / 100.0,
                            "bbox": [
                                data["left"][i],
                                data["top"][i],
                                data["left"][i] + data["width"][i],
                                data["top"][i] + data["height"][i],
                            ],
                        }
                    )
                    all_text.append(text_val)
                    total_confidence += conf / 100.0
                    count += 1

            avg_confidence = total_confidence / count if count > 0 else 0.0
            full_text = pytesseract.image_to_string(image, lang=settings.OCR_LANGUAGES)

            return OCRResult(
                text=full_text.strip(),
                confidence=avg_confidence,
                blocks=blocks,
            )
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}")
            return OCRResult(text="", confidence=0.0, blocks=[])


ocr_engine = OCREngine()
