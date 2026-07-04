"""Image pre-processing pipeline for OCR optimization."""

import io
from typing import Optional

from PIL import Image, ImageEnhance, ImageFilter
from loguru import logger


class ImagePreprocessor:
    """Pre-processes images to improve OCR accuracy."""

    def __init__(
        self,
        deskew: bool = True,
        denoise: bool = True,
        enhance_contrast: bool = True,
        binarize: bool = False,
        target_dpi: int = 300,
    ):
        self.deskew = deskew
        self.denoise = denoise
        self.enhance_contrast = enhance_contrast
        self.binarize = binarize
        self.target_dpi = target_dpi

    def process(self, image: Image.Image) -> Image.Image:
        """Run the full pre-processing pipeline."""
        logger.debug(f"Pre-processing image: {image.size}, mode={image.mode}")

        # Convert to RGB if needed
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        # Resize if too small (upscale for better OCR)
        image = self._ensure_minimum_resolution(image)

        # Denoise
        if self.denoise:
            image = self._denoise(image)

        # Enhance contrast
        if self.enhance_contrast:
            image = self._enhance_contrast(image)

        # Sharpen
        image = self._sharpen(image)

        # Binarize (convert to black and white)
        if self.binarize:
            image = self._binarize(image)

        logger.debug(f"Pre-processing complete: {image.size}")
        return image

    def _ensure_minimum_resolution(self, image: Image.Image) -> Image.Image:
        """Upscale image if resolution is too low."""
        min_width = 1000
        if image.width < min_width:
            scale = min_width / image.width
            new_size = (int(image.width * scale), int(image.height * scale))
            image = image.resize(new_size, Image.LANCZOS)
        return image

    def _denoise(self, image: Image.Image) -> Image.Image:
        """Apply denoising filter."""
        return image.filter(ImageFilter.MedianFilter(size=3))

    def _enhance_contrast(self, image: Image.Image) -> Image.Image:
        """Enhance image contrast."""
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)

        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.1)

        return image

    def _sharpen(self, image: Image.Image) -> Image.Image:
        """Sharpen the image."""
        enhancer = ImageEnhance.Sharpness(image)
        return enhancer.enhance(2.0)

    def _binarize(self, image: Image.Image) -> Image.Image:
        """Convert to binary (black and white)."""
        grayscale = image.convert("L")
        threshold = 128
        return grayscale.point(lambda x: 255 if x > threshold else 0, "1")

    def image_to_bytes(self, image: Image.Image, format: str = "PNG") -> bytes:
        """Convert PIL Image to bytes."""
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        buffer.seek(0)
        return buffer.read()

    def bytes_to_image(self, data: bytes) -> Image.Image:
        """Convert bytes to PIL Image."""
        return Image.open(io.BytesIO(data))
