"""Image utilities for ReTileUp.

This module provides comprehensive image processing utilities including
loading, saving, validation, metadata extraction, and format conversion
optimized for tiling operations and memory efficiency.
"""

import logging
import mimetypes
from pathlib import Path
from typing import List, Optional, Tuple, Union, Dict, Any

from PIL import Image, ImageOps, ImageFile
from PIL.ExifTags import TAGS

# Enable loading of truncated images for robustness
ImageFile.LOAD_TRUNCATED_IMAGES = True

logger = logging.getLogger(__name__)


class ImageUtils:
    """Utility class for image operations."""

    @staticmethod
    def load_image(path: Union[str, Path], convert_mode: Optional[str] = None) -> Image.Image:
        """Load an image from file with format detection and validation.

        Args:
            path: Path to the image file
            convert_mode: Optional mode to convert image to ('RGB', 'RGBA', 'L', etc.)

        Returns:
            PIL Image object

        Raises:
            FileNotFoundError: If image file doesn't exist
            IOError: If image cannot be loaded
            ValueError: If image format is not supported
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {path}")

        # Validate file size
        file_size = path.stat().st_size
        if file_size == 0:
            raise ValueError(f"Image file is empty: {path}")

        # Check MIME type for basic validation
        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type and not mime_type.startswith('image/'):
            logger.warning(f"File {path} may not be an image (MIME type: {mime_type})")

        try:
            # Load image with error handling
            image = Image.open(path)

            # Verify image by loading it
            image.load()

            # Store original format information
            original_format = image.format

            # Convert mode if specified
            if convert_mode:
                image = ImageUtils._convert_image_mode(image, convert_mode)
            elif image.mode not in ('RGB', 'RGBA', 'L'):
                # Auto-convert unusual modes to RGB for compatibility
                if image.mode == 'P':
                    # Convert palette mode to RGB
                    image = image.convert('RGB')
                elif image.mode in ('CMYK', 'YCbCr'):
                    # Convert to RGB for common processing
                    image = image.convert('RGB')

            # Add format info back to image
            if not hasattr(image, 'format') or image.format is None:
                image.format = original_format

            logger.debug(f"Loaded image: {path} ({image.size[0]}x{image.size[1]}, "
                        f"{image.mode}, format: {original_format}, size: {file_size/1024:.1f}KB)")

            return image

        except Exception as e:
            raise IOError(f"Failed to load image {path}: {e}") from e

    @staticmethod
    def _convert_image_mode(image: Image.Image, target_mode: str) -> Image.Image:
        """Convert image to target mode with proper handling of transparency.

        Args:
            image: Source PIL Image
            target_mode: Target mode ('RGB', 'RGBA', 'L', etc.)

        Returns:
            Converted image
        """
        if image.mode == target_mode:
            return image

        if target_mode == 'RGB' and image.mode == 'RGBA':
            # Handle RGBA to RGB conversion with white background
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            return background
        elif target_mode == 'L' and image.mode in ('RGB', 'RGBA'):
            # Convert to grayscale
            return image.convert('L')
        else:
            # Standard conversion
            return image.convert(target_mode)

    @staticmethod
    def save_image(
        image: Image.Image,
        path: Union[str, Path],
        format: Optional[str] = None,
        quality: int = 95,
        optimize: bool = True,
        **kwargs
    ) -> None:
        """Save an image to file.

        Args:
            image: PIL Image to save
            path: Output file path
            format: Image format (inferred from extension if None)
            quality: JPEG quality (1-100)
            optimize: Whether to optimize the image
            **kwargs: Additional save parameters
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Determine format
        if format is None:
            format = path.suffix.upper().lstrip('.')
            if format == 'JPG':
                format = 'JPEG'

        # Prepare save parameters
        save_kwargs = {
            'optimize': optimize,
            **kwargs
        }

        # Add quality for JPEG
        if format.upper() == 'JPEG':
            save_kwargs['quality'] = quality

        try:
            image.save(path, format=format, **save_kwargs)
            logger.debug(f"Saved image: {path} ({image.size[0]}x{image.size[1]}, {format})")

        except Exception as e:
            raise IOError(f"Failed to save image {path}: {e}") from e

    @staticmethod
    def get_image_info(image: Image.Image) -> dict:
        """Get comprehensive information about an image.

        Args:
            image: PIL Image object

        Returns:
            Dictionary containing image information
        """
        info = {
            'size': image.size,
            'width': image.width,
            'height': image.height,
            'mode': image.mode,
            'format': image.format,
            'has_transparency': image.mode in ('RGBA', 'LA') or 'transparency' in image.info,
        }

        # Add file size if available
        if hasattr(image, 'filename') and image.filename:
            try:
                file_size = Path(image.filename).stat().st_size
                info['file_size_bytes'] = file_size
                info['file_size_mb'] = file_size / (1024 * 1024)
            except (OSError, AttributeError):
                pass

        # Add EXIF data if available
        exif_data = {}
        if hasattr(image, '_getexif') and image._getexif():
            exif = image._getexif()
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)
                exif_data[tag] = value

        if exif_data:
            info['exif'] = exif_data

        return info

    @staticmethod
    def resize_image(
        image: Image.Image,
        size: Tuple[int, int],
        method: str = 'lanczos',
        maintain_aspect: bool = True
    ) -> Image.Image:
        """Resize an image.

        Args:
            image: PIL Image to resize
            size: Target size (width, height)
            method: Resampling method ('lanczos', 'bicubic', 'bilinear', 'nearest')
            maintain_aspect: Whether to maintain aspect ratio

        Returns:
            Resized image
        """
        # Map method names to PIL constants
        methods = {
            'lanczos': Image.Resampling.LANCZOS,
            'bicubic': Image.Resampling.BICUBIC,
            'bilinear': Image.Resampling.BILINEAR,
            'nearest': Image.Resampling.NEAREST,
        }

        resample = methods.get(method.lower(), Image.Resampling.LANCZOS)

        if maintain_aspect:
            # Use thumbnail method to maintain aspect ratio
            image = image.copy()
            image.thumbnail(size, resample)
            return image
        else:
            # Direct resize
            return image.resize(size, resample)

    @staticmethod
    def crop_image(
        image: Image.Image,
        box: Tuple[int, int, int, int]
    ) -> Image.Image:
        """Crop an image.

        Args:
            image: PIL Image to crop
            box: Crop box (left, top, right, bottom)

        Returns:
            Cropped image
        """
        return image.crop(box)

    @staticmethod
    def rotate_image(
        image: Image.Image,
        angle: float,
        expand: bool = True,
        fillcolor: Tuple[int, int, int] = (255, 255, 255)
    ) -> Image.Image:
        """Rotate an image.

        Args:
            image: PIL Image to rotate
            angle: Rotation angle in degrees (counter-clockwise)
            expand: Whether to expand the image to fit the rotated content
            fillcolor: Fill color for empty areas

        Returns:
            Rotated image
        """
        return image.rotate(angle, expand=expand, fillcolor=fillcolor)

    @staticmethod
    def flip_image(image: Image.Image, horizontal: bool = True) -> Image.Image:
        """Flip an image.

        Args:
            image: PIL Image to flip
            horizontal: If True, flip horizontally; if False, flip vertically

        Returns:
            Flipped image
        """
        if horizontal:
            return image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        else:
            return image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

    @staticmethod
    def auto_orient(image: Image.Image) -> Image.Image:
        """Auto-orient an image based on EXIF data.

        Args:
            image: PIL Image to orient

        Returns:
            Oriented image
        """
        return ImageOps.exif_transpose(image)

    @staticmethod
    def get_supported_formats() -> List[str]:
        """Get list of supported image formats.

        Returns:
            List of supported format names
        """
        # Get formats supported by PIL
        formats = []
        for format_name, format_info in Image.registered_extensions().items():
            if format_info in Image.OPEN:
                formats.append(format_name.upper().lstrip('.'))

        # Remove duplicates and sort
        return sorted(set(formats))

    @staticmethod
    def is_valid_image(path: Union[str, Path]) -> bool:
        """Check if a file is a valid image.

        Args:
            path: Path to the file

        Returns:
            True if the file is a valid image, False otherwise
        """
        try:
            with Image.open(path) as img:
                img.verify()
            return True
        except (IOError, SyntaxError):
            return False

    @staticmethod
    def calculate_file_size(
        width: int,
        height: int,
        mode: str = 'RGB',
        compression: float = 1.0
    ) -> int:
        """Estimate file size for an image.

        Args:
            width: Image width
            height: Image height
            mode: Image mode ('RGB', 'RGBA', 'L', etc.)
            compression: Compression factor (0.1-1.0, where 1.0 is uncompressed)

        Returns:
            Estimated file size in bytes
        """
        # Bytes per pixel for different modes
        bytes_per_pixel = {
            'L': 1,     # Grayscale
            'RGB': 3,   # RGB
            'RGBA': 4,  # RGB with alpha
            'CMYK': 4,  # CMYK
            'P': 1,     # Palette
        }

        bpp = bytes_per_pixel.get(mode, 3)
        uncompressed_size = width * height * bpp

        # Apply compression factor
        estimated_size = int(uncompressed_size * compression)

        return estimated_size

    @staticmethod
    def validate_image_format(path: Union[str, Path]) -> Tuple[bool, str]:
        """Validate if a file is a supported image format.

        Args:
            path: Path to the file

        Returns:
            Tuple of (is_valid, format_or_error_message)
        """
        try:
            path = Path(path)
            if not path.exists():
                return False, f"File not found: {path}"

            with Image.open(path) as img:
                img.verify()
                return True, img.format or "Unknown"

        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_safe_crop_bounds(
        image_width: int,
        image_height: int,
        x: int,
        y: int,
        width: int,
        height: int,
        overlap: int = 0
    ) -> Tuple[int, int, int, int]:
        """Calculate safe crop bounds that don't exceed image dimensions.

        Args:
            image_width: Width of the source image
            image_height: Height of the source image
            x: X coordinate for crop start
            y: Y coordinate for crop start
            width: Desired crop width
            height: Desired crop height
            overlap: Additional overlap pixels

        Returns:
            Tuple of (left, top, right, bottom) coordinates
        """
        left = max(0, x - overlap)
        top = max(0, y - overlap)
        right = min(image_width, x + width + overlap)
        bottom = min(image_height, y + height + overlap)

        return left, top, right, bottom

    @staticmethod
    def estimate_processing_memory(
        image_width: int,
        image_height: int,
        tile_count: int,
        bytes_per_pixel: int = 3
    ) -> Dict[str, float]:
        """Estimate memory usage for image processing operations.

        Args:
            image_width: Width of source image
            image_height: Height of source image
            tile_count: Number of tiles to process
            bytes_per_pixel: Bytes per pixel (3 for RGB, 4 for RGBA)

        Returns:
            Dictionary with memory estimates in MB
        """
        # Base image memory
        base_image_bytes = image_width * image_height * bytes_per_pixel
        base_image_mb = base_image_bytes / (1024 * 1024)

        # Estimated tile memory (assuming average tile size)
        avg_tile_pixels = (image_width * image_height) / tile_count if tile_count > 0 else 0
        tile_memory_mb = (avg_tile_pixels * bytes_per_pixel) / (1024 * 1024)

        # Peak memory (image + processing overhead)
        peak_memory_mb = base_image_mb * 1.5 + tile_memory_mb * 2

        return {
            "base_image_mb": base_image_mb,
            "per_tile_mb": tile_memory_mb,
            "peak_memory_mb": peak_memory_mb,
            "estimated_total_mb": peak_memory_mb
        }

    @staticmethod
    def optimize_image_for_tiling(image: Image.Image) -> Image.Image:
        """Optimize an image for tiling operations.

        Args:
            image: Source PIL Image

        Returns:
            Optimized image
        """
        # Auto-orient based on EXIF
        optimized = ImageUtils.auto_orient(image)

        # Ensure RGB mode for consistent processing
        if optimized.mode not in ('RGB', 'RGBA', 'L'):
            optimized = ImageUtils._convert_image_mode(optimized, 'RGB')

        return optimized

    @staticmethod
    def create_tile_info(
        source_path: Path,
        tile_coordinates: List[Tuple[int, int]],
        tile_width: int,
        tile_height: int,
        overlap: int = 0
    ) -> Dict[str, Any]:
        """Create comprehensive tile information for planning.

        Args:
            source_path: Path to source image
            tile_coordinates: List of (x, y) coordinates
            tile_width: Width of each tile
            tile_height: Height of each tile
            overlap: Overlap in pixels

        Returns:
            Dictionary with tile information
        """
        try:
            with Image.open(source_path) as img:
                img_width, img_height = img.size
                img_info = ImageUtils.get_image_info(img)

            valid_tiles = []
            invalid_tiles = []

            for i, (x, y) in enumerate(tile_coordinates):
                left, top, right, bottom = ImageUtils.get_safe_crop_bounds(
                    img_width, img_height, x, y, tile_width, tile_height, overlap
                )

                tile_info = {
                    "index": i,
                    "coordinates": (x, y),
                    "crop_bounds": (left, top, right, bottom),
                    "actual_width": right - left,
                    "actual_height": bottom - top,
                    "is_valid": right > left and bottom > top
                }

                if tile_info["is_valid"]:
                    valid_tiles.append(tile_info)
                else:
                    invalid_tiles.append(tile_info)

            memory_estimate = ImageUtils.estimate_processing_memory(
                img_width, img_height, len(valid_tiles)
            )

            return {
                "source_image": img_info,
                "tile_config": {
                    "width": tile_width,
                    "height": tile_height,
                    "overlap": overlap,
                    "total_requested": len(tile_coordinates)
                },
                "valid_tiles": valid_tiles,
                "invalid_tiles": invalid_tiles,
                "memory_estimate": memory_estimate,
                "processing_feasible": memory_estimate["peak_memory_mb"] < 1024  # 1GB limit
            }

        except Exception as e:
            return {
                "error": str(e),
                "source_path": str(source_path),
                "processing_feasible": False
            }