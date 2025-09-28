"""Image tiling tool for ReTileUp.

This module provides the TilingTool class for extracting rectangular tiles from images
at specified coordinates. It supports various output formats, coordinate validation,
overlap handling, and memory-efficient processing.
"""

import logging
import time
from pathlib import Path
from typing import List, Tuple, Optional, Type, Dict, Any

from PIL import Image
from pydantic import BaseModel, Field, field_validator, model_validator

from .base import BaseTool, ToolConfig, ToolResult
from ..utils.image import ImageUtils
from ..core.exceptions import ValidationError, ProcessingError

logger = logging.getLogger(__name__)


class TilingConfig(ToolConfig):
    """Configuration for image tiling tool.

    This class defines all parameters needed for tile extraction operations,
    including tile dimensions, coordinates, output patterns, and processing options.
    """

    tile_width: int = Field(
        ...,
        description="Width of each tile in pixels",
        gt=0,
        le=8192
    )
    tile_height: int = Field(
        ...,
        description="Height of each tile in pixels",
        gt=0,
        le=8192
    )
    coordinates: List[Tuple[int, int]] = Field(
        ...,
        description="List of (x, y) coordinates for tile extraction",
        min_length=1
    )
    output_pattern: str = Field(
        "{base}_{x}_{y}.{ext}",
        description="Output filename pattern with placeholders",
        min_length=1
    )
    maintain_aspect: bool = Field(
        False,
        description="Whether to maintain aspect ratio when tiling"
    )
    overlap: int = Field(
        0,
        description="Overlap in pixels between adjacent tiles",
        ge=0,
        le=512
    )

    @field_validator('coordinates')
    @classmethod
    def validate_coordinates(cls, v: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Validate that all coordinates are non-negative."""
        if not v:
            raise ValueError('At least one coordinate pair is required')

        validated_coords = []
        for i, coord in enumerate(v):
            if not isinstance(coord, (tuple, list)) or len(coord) != 2:
                raise ValueError(f'Coordinate {i} must be a tuple/list of 2 integers')

            x, y = coord
            if not isinstance(x, int) or not isinstance(y, int):
                raise ValueError(f'Coordinate {i} must contain integers, got ({type(x)}, {type(y)})')

            if x < 0 or y < 0:
                raise ValueError(f'Coordinate {i} must be non-negative, got ({x}, {y})')

            validated_coords.append((x, y))

        return validated_coords

    @field_validator('output_pattern')
    @classmethod
    def validate_output_pattern(cls, v: str) -> str:
        """Validate output pattern contains required placeholders."""
        required_placeholders = ['{base}', '{ext}']
        for placeholder in required_placeholders:
            if placeholder not in v:
                raise ValueError(f'Output pattern must contain {placeholder} placeholder')

        # Test pattern with sample values
        try:
            test_result = v.format(base="test", x=0, y=0, ext="jpg")
            if not test_result:
                raise ValueError('Output pattern produces empty filename')
        except KeyError as e:
            raise ValueError(f'Output pattern contains invalid placeholder: {e}')
        except Exception as e:
            raise ValueError(f'Invalid output pattern: {e}')

        return v

    @model_validator(mode='after')
    def validate_dimensions(self) -> 'TilingConfig':
        """Validate that tile dimensions are reasonable."""
        max_dimension = 8192
        if self.tile_width > max_dimension or self.tile_height > max_dimension:
            raise ValueError(f'Tile dimensions cannot exceed {max_dimension}x{max_dimension}')

        # Check for extremely small tiles that might not be useful
        min_dimension = 1
        if self.tile_width < min_dimension or self.tile_height < min_dimension:
            raise ValueError(f'Tile dimensions must be at least {min_dimension}x{min_dimension}')

        # Validate overlap doesn't exceed tile dimensions
        if self.overlap >= min(self.tile_width, self.tile_height):
            raise ValueError('Overlap cannot be greater than or equal to smallest tile dimension')

        return self


class TilingTool(BaseTool):
    """Image tiling tool for extracting rectangular regions from images.

    This tool extracts rectangular tiles from images at specified coordinates,
    with support for overlap, aspect ratio maintenance, and various output formats.
    It includes comprehensive validation and memory-efficient processing.
    """

    def __init__(self) -> None:
        """Initialize the tiling tool."""
        super().__init__()
        self._image_cache: Optional[Image.Image] = None
        self._image_path_cache: Optional[Path] = None

    @property
    def name(self) -> str:
        """Tool name for CLI and registry identification."""
        return "tile"

    @property
    def description(self) -> str:
        """Tool description for help text and documentation."""
        return "Extract rectangular tiles from images at specified coordinates"

    @property
    def version(self) -> str:
        """Tool version for compatibility checking."""
        return "1.0.0"

    def get_config_schema(self) -> Type[ToolConfig]:
        """Get the configuration schema class for this tool."""
        return TilingConfig

    def validate_config(self, config: ToolConfig) -> List[str]:
        """Validate tool configuration and return any errors.

        Performs comprehensive validation including:
        - File existence and format validation
        - Image bounds checking for coordinates
        - Output directory creation feasibility
        - Memory usage estimation

        Args:
            config: TilingConfig instance to validate

        Returns:
            List of error messages (empty if valid)
        """
        if not isinstance(config, TilingConfig):
            return [f"Invalid config type: expected TilingConfig, got {type(config)}"]

        errors = []

        # Validate input file exists and is readable
        if not config.input_path.exists():
            errors.append(f"Input file not found: {config.input_path}")
            return errors  # Can't continue without input file

        if not config.input_path.is_file():
            errors.append(f"Input path is not a file: {config.input_path}")
            return errors

        # Validate image format and get dimensions
        try:
            with Image.open(config.input_path) as img:
                img_width, img_height = img.size
                image_format = img.format

                # Log image information
                logger.debug(f"Input image: {img_width}x{img_height}, format: {image_format}")

        except Exception as e:
            errors.append(f"Cannot open or read image file: {e}")
            return errors  # Can't continue without valid image

        # Validate output directory can be created
        if config.output_dir:
            try:
                config.output_dir.mkdir(parents=True, exist_ok=True)
                if not config.output_dir.is_dir():
                    errors.append(f"Output directory exists but is not a directory: {config.output_dir}")
            except PermissionError:
                errors.append(f"Permission denied creating output directory: {config.output_dir}")
            except Exception as e:
                errors.append(f"Cannot create output directory {config.output_dir}: {e}")

        # Validate coordinates are within image bounds
        for i, (x, y) in enumerate(config.coordinates):
            # Calculate actual tile bounds considering overlap
            tile_left = max(0, x - config.overlap)
            tile_top = max(0, y - config.overlap)
            tile_right = min(img_width, x + config.tile_width + config.overlap)
            tile_bottom = min(img_height, y + config.tile_height + config.overlap)

            # Check if tile extends beyond image boundaries
            if x + config.tile_width > img_width:
                errors.append(f"Tile {i} at ({x}, {y}) extends beyond image width "
                            f"(tile ends at x={x + config.tile_width}, image width={img_width})")

            if y + config.tile_height > img_height:
                errors.append(f"Tile {i} at ({x}, {y}) extends beyond image height "
                            f"(tile ends at y={y + config.tile_height}, image height={img_height})")

            # Check for zero-area tiles after overlap adjustment
            actual_width = tile_right - tile_left
            actual_height = tile_bottom - tile_top

            if actual_width <= 0 or actual_height <= 0:
                errors.append(f"Tile {i} at ({x}, {y}) results in zero area after bounds checking")

        # Estimate memory usage and warn if excessive
        estimated_memory_mb = self._estimate_memory_usage(config, img_width, img_height)
        max_memory_mb = 1024  # 1GB limit

        if estimated_memory_mb > max_memory_mb:
            errors.append(f"Estimated memory usage ({estimated_memory_mb:.1f}MB) exceeds limit "
                         f"({max_memory_mb}MB). Consider reducing tile count or size.")

        # Validate that output pattern will produce unique filenames
        if len(config.coordinates) > 1:
            test_filenames = set()
            base_name = config.input_path.stem
            ext = config.input_path.suffix[1:] or "png"

            for x, y in config.coordinates:
                filename = config.output_pattern.format(base=base_name, x=x, y=y, ext=ext)
                if filename in test_filenames:
                    errors.append(f"Output pattern will produce duplicate filename: {filename}")
                    break
                test_filenames.add(filename)

        return errors

    def execute(self, config: ToolConfig) -> ToolResult:
        """Execute the tiling operation with comprehensive error handling.

        Args:
            config: Validated TilingConfig instance

        Returns:
            ToolResult with success status, output files, and metadata
        """
        if not isinstance(config, TilingConfig):
            return ToolResult(
                success=False,
                message=f"Invalid config type: expected TilingConfig, got {type(config)}",
                error_code="INVALID_CONFIG"
            )

        start_time = time.time()
        output_files = []
        tiles_processed = 0

        try:
            logger.info(f"Starting tiling operation on {config.input_path}")
            logger.info(f"Extracting {len(config.coordinates)} tiles of size "
                       f"{config.tile_width}x{config.tile_height}")

            # Load image efficiently
            with Image.open(config.input_path) as img:
                # Auto-orient based on EXIF data
                img = ImageUtils.auto_orient(img)
                img_info = ImageUtils.get_image_info(img)

                logger.debug(f"Image loaded: {img_info}")

                # Prepare output directory
                if config.output_dir:
                    config.output_dir.mkdir(parents=True, exist_ok=True)
                else:
                    config.output_dir = config.input_path.parent / "tiles"
                    config.output_dir.mkdir(parents=True, exist_ok=True)

                # Extract base name and extension for filename generation
                base_name = config.input_path.stem
                original_ext = config.input_path.suffix[1:] or "png"

                # Process each tile
                for i, (x, y) in enumerate(config.coordinates):
                    try:
                        tile_result = self._extract_tile(
                            img, config, x, y, base_name, original_ext
                        )

                        if tile_result:
                            output_files.append(tile_result)
                            tiles_processed += 1

                            if config.verbose:
                                logger.info(f"Created tile {i+1}/{len(config.coordinates)}: {tile_result}")

                    except Exception as e:
                        error_msg = f"Failed to extract tile {i} at ({x}, {y}): {e}"
                        logger.error(error_msg)

                        # Continue with other tiles unless it's a critical error
                        if "memory" in str(e).lower() or "permission" in str(e).lower():
                            raise ProcessingError(error_msg) from e

            execution_time = time.time() - start_time

            # Calculate processing statistics
            total_pixels = config.tile_width * config.tile_height * tiles_processed
            pixels_per_second = total_pixels / execution_time if execution_time > 0 else 0

            success_message = (f"Successfully extracted {tiles_processed} tiles "
                             f"in {execution_time:.2f}s "
                             f"({pixels_per_second/1_000_000:.1f}MP/s)")

            logger.info(success_message)

            return ToolResult(
                success=True,
                message=success_message,
                output_files=output_files,
                metadata={
                    "tile_count": tiles_processed,
                    "tile_size": f"{config.tile_width}x{config.tile_height}",
                    "overlap": config.overlap,
                    "maintain_aspect": config.maintain_aspect,
                    "total_pixels_processed": total_pixels,
                    "pixels_per_second": pixels_per_second,
                    "input_image_info": img_info,
                    "processing_time_ms": execution_time * 1000,
                    "coordinates_processed": config.coordinates[:tiles_processed],
                    "failed_tiles": len(config.coordinates) - tiles_processed
                },
                execution_time=execution_time
            )

        except ProcessingError:
            # Re-raise processing errors as-is
            raise
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Tiling operation failed: {e}"
            logger.error(error_msg, exc_info=True)

            return ToolResult(
                success=False,
                message=error_msg,
                output_files=output_files,  # Include any partial results
                metadata={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "tiles_completed": tiles_processed,
                    "tiles_attempted": len(config.coordinates),
                    "partial_results": len(output_files)
                },
                execution_time=execution_time,
                error_code="PROCESSING_ERROR"
            )

    def _extract_tile(
        self,
        img: Image.Image,
        config: TilingConfig,
        x: int,
        y: int,
        base_name: str,
        original_ext: str
    ) -> Optional[Path]:
        """Extract a single tile from the image.

        Args:
            img: Source PIL Image
            config: Tiling configuration
            x: X coordinate for tile extraction
            y: Y coordinate for tile extraction
            base_name: Base filename for output
            original_ext: Original file extension

        Returns:
            Path to saved tile file, or None if extraction failed
        """
        try:
            # Calculate tile bounds with overlap
            left = max(0, x - config.overlap)
            top = max(0, y - config.overlap)
            right = min(img.width, x + config.tile_width + config.overlap)
            bottom = min(img.height, y + config.tile_height + config.overlap)

            # Ensure we have a valid crop area
            if right <= left or bottom <= top:
                logger.warning(f"Invalid crop area for tile at ({x}, {y}): "
                              f"({left}, {top}, {right}, {bottom})")
                return None

            # Extract tile using memory-efficient crop
            tile = img.crop((left, top, right, bottom))

            # Apply aspect ratio maintenance if requested
            if config.maintain_aspect:
                tile = self._apply_aspect_ratio(tile, config.tile_width, config.tile_height)

            # Generate output filename
            filename = config.output_pattern.format(
                base=base_name,
                x=x,
                y=y,
                ext=original_ext
            )

            output_path = config.output_dir / filename

            # Save tile with optimal settings
            if not config.dry_run:
                self._save_tile_optimized(tile, output_path, original_ext)

            return output_path

        except Exception as e:
            logger.error(f"Failed to extract tile at ({x}, {y}): {e}")
            raise

    def _apply_aspect_ratio(self, tile: Image.Image, target_width: int, target_height: int) -> Image.Image:
        """Apply aspect ratio maintenance to a tile.

        Args:
            tile: Source tile image
            target_width: Target width for the tile
            target_height: Target height for the tile

        Returns:
            Resized tile image
        """
        # Use thumbnail method to maintain aspect ratio
        tile_copy = tile.copy()
        tile_copy.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)

        # If the result is smaller than target, pad with background color
        if tile_copy.size != (target_width, target_height):
            # Create new image with target size and paste the thumbnail
            background = Image.new('RGB', (target_width, target_height), (255, 255, 255))

            # Center the thumbnail
            paste_x = (target_width - tile_copy.width) // 2
            paste_y = (target_height - tile_copy.height) // 2

            if tile_copy.mode == 'RGBA':
                background.paste(tile_copy, (paste_x, paste_y), tile_copy)
            else:
                background.paste(tile_copy, (paste_x, paste_y))

            return background

        return tile_copy

    def _save_tile_optimized(self, tile: Image.Image, output_path: Path, original_ext: str) -> None:
        """Save tile with format-specific optimizations.

        Args:
            tile: Tile image to save
            output_path: Output file path
            original_ext: Original file extension for format selection
        """
        # Determine optimal save parameters based on format
        save_kwargs = {'optimize': True}

        # Format-specific optimizations
        if original_ext.upper() in ('JPG', 'JPEG'):
            save_kwargs.update({
                'quality': 95,
                'progressive': True,
                'format': 'JPEG'
            })
            # Convert RGBA to RGB for JPEG
            if tile.mode == 'RGBA':
                background = Image.new('RGB', tile.size, (255, 255, 255))
                background.paste(tile, mask=tile.split()[-1])
                tile = background

        elif original_ext.upper() == 'PNG':
            save_kwargs.update({
                'format': 'PNG',
                'compress_level': 6  # Balance between speed and compression
            })

        elif original_ext.upper() == 'WEBP':
            save_kwargs.update({
                'quality': 90,
                'method': 4,  # Good balance of speed and compression
                'format': 'WEBP'
            })

        try:
            ImageUtils.save_image(tile, output_path, **save_kwargs)
        except Exception as e:
            logger.error(f"Failed to save tile to {output_path}: {e}")
            raise

    def _estimate_memory_usage(self, config: TilingConfig, img_width: int, img_height: int) -> float:
        """Estimate memory usage for the tiling operation.

        Args:
            config: Tiling configuration
            img_width: Source image width
            img_height: Source image height

        Returns:
            Estimated memory usage in MB
        """
        # Base image memory (assuming RGB, 3 bytes per pixel)
        base_image_mb = (img_width * img_height * 3) / (1024 * 1024)

        # Memory for each tile (with some overhead)
        tile_pixels = config.tile_width * config.tile_height
        tile_memory_mb = (tile_pixels * 3 * 1.5) / (1024 * 1024)  # 50% overhead

        # Total for concurrent processing (assume 2 tiles in memory at once)
        total_mb = base_image_mb + (tile_memory_mb * 2)

        return total_mb

    def setup(self) -> None:
        """Setup the tiling tool."""
        super().setup()
        logger.debug("TilingTool setup completed")

    def cleanup(self) -> None:
        """Cleanup resources after execution."""
        # Clear any cached images
        self._image_cache = None
        self._image_path_cache = None
        super().cleanup()
        logger.debug("TilingTool cleanup completed")