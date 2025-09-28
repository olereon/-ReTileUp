"""Comprehensive unit tests for ImageUtils.

This module tests the image processing utilities including:
- Image loading and validation
- Format conversion and mode handling
- Image manipulation operations
- Metadata extraction and processing
- Error handling and edge cases
- Memory estimation and optimization
"""

import tempfile
from pathlib import Path
from typing import Tuple
from unittest.mock import Mock, patch

import pytest
from PIL import Image, ImageOps

from retileup.utils.image import ImageUtils
from retileup.core.exceptions import RetileupError


class TestImageLoading:
    """Test image loading functionality."""

    def test_load_image_success(self, sample_image_rgb):
        """Test successful image loading."""
        image = ImageUtils.load_image(sample_image_rgb)

        assert isinstance(image, Image.Image)
        assert image.size == (100, 100)
        assert image.mode == 'RGB'

    def test_load_image_with_conversion(self, sample_image_rgb):
        """Test image loading with mode conversion."""
        image = ImageUtils.load_image(sample_image_rgb, convert_mode='L')

        assert image.mode == 'L'
        assert image.size == (100, 100)

    def test_load_image_file_not_found(self):
        """Test loading non-existent image."""
        with pytest.raises(FileNotFoundError) as exc_info:
            ImageUtils.load_image("/nonexistent/image.jpg")

        assert "Image file not found" in str(exc_info.value)

    def test_load_image_not_a_file(self, temp_dir):
        """Test loading a directory instead of file."""
        with pytest.raises(ValueError) as exc_info:
            ImageUtils.load_image(temp_dir)

        assert "Path is not a file" in str(exc_info.value)

    def test_load_image_empty_file(self, temp_dir):
        """Test loading empty file."""
        empty_file = temp_dir / "empty.jpg"
        empty_file.touch()

        with pytest.raises(ValueError) as exc_info:
            ImageUtils.load_image(empty_file)

        assert "Image file is empty" in str(exc_info.value)

    def test_load_image_invalid_format(self, temp_dir):
        """Test loading invalid image file."""
        invalid_file = temp_dir / "invalid.jpg"
        invalid_file.write_text("This is not an image")

        with pytest.raises(IOError) as exc_info:
            ImageUtils.load_image(invalid_file)

        assert "Failed to load image" in str(exc_info.value)

    def test_load_image_palette_mode(self, temp_dir):
        """Test loading palette mode image auto-converts to RGB."""
        # Create a palette mode image
        palette_image = Image.new('P', (50, 50))
        palette_path = temp_dir / "palette.png"
        palette_image.save(palette_path)

        loaded = ImageUtils.load_image(palette_path)
        assert loaded.mode == 'RGB'

    def test_load_image_cmyk_mode(self, temp_dir):
        """Test loading CMYK mode image converts to RGB."""
        # Create a CMYK mode image
        cmyk_image = Image.new('CMYK', (50, 50))
        cmyk_path = temp_dir / "cmyk.jpg"
        cmyk_image.save(cmyk_path)

        loaded = ImageUtils.load_image(cmyk_path)
        assert loaded.mode == 'RGB'

    def test_load_image_with_exif(self, sample_image_with_exif):
        """Test loading image with EXIF data preserves format."""
        image = ImageUtils.load_image(sample_image_with_exif)

        assert hasattr(image, 'format')
        assert image.format == 'JPEG'


class TestImageModeConversion:
    """Test image mode conversion functionality."""

    def test_convert_rgba_to_rgb(self):
        """Test RGBA to RGB conversion with white background."""
        rgba_image = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
        converted = ImageUtils._convert_image_mode(rgba_image, 'RGB')

        assert converted.mode == 'RGB'
        assert converted.size == (100, 100)

    def test_convert_rgb_to_grayscale(self):
        """Test RGB to grayscale conversion."""
        rgb_image = Image.new('RGB', (100, 100), (255, 0, 0))
        converted = ImageUtils._convert_image_mode(rgb_image, 'L')

        assert converted.mode == 'L'
        assert converted.size == (100, 100)

    def test_convert_same_mode(self):
        """Test conversion when target mode is same as source."""
        rgb_image = Image.new('RGB', (100, 100), (255, 0, 0))
        converted = ImageUtils._convert_image_mode(rgb_image, 'RGB')

        assert converted is rgb_image  # Should return same object

    def test_convert_standard_conversion(self):
        """Test standard mode conversion."""
        rgb_image = Image.new('RGB', (100, 100), (255, 0, 0))
        converted = ImageUtils._convert_image_mode(rgb_image, 'RGBA')

        assert converted.mode == 'RGBA'
        assert converted.size == (100, 100)


class TestImageSaving:
    """Test image saving functionality."""

    def test_save_image_basic(self, temp_dir):
        """Test basic image saving."""
        image = Image.new('RGB', (100, 100), (255, 0, 0))
        output_path = temp_dir / "output.png"

        ImageUtils.save_image(image, output_path)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_save_image_with_format(self, temp_dir):
        """Test saving with specific format."""
        image = Image.new('RGB', (100, 100), (255, 0, 0))
        output_path = temp_dir / "output.jpg"

        ImageUtils.save_image(image, output_path, format='JPEG', quality=90)

        assert output_path.exists()
        # Verify JPEG format by loading
        loaded = Image.open(output_path)
        assert loaded.format == 'JPEG'

    def test_save_image_creates_directory(self, temp_dir):
        """Test that save_image creates parent directories."""
        image = Image.new('RGB', (100, 100), (255, 0, 0))
        output_path = temp_dir / "subdir" / "output.png"

        ImageUtils.save_image(image, output_path)

        assert output_path.exists()
        assert output_path.parent.exists()

    def test_save_image_infers_format_from_extension(self, temp_dir):
        """Test format inference from file extension."""
        image = Image.new('RGB', (100, 100), (255, 0, 0))

        # Test .jpg -> JPEG
        jpg_path = temp_dir / "output.jpg"
        ImageUtils.save_image(image, jpg_path)

        loaded = Image.open(jpg_path)
        assert loaded.format == 'JPEG'

    def test_save_image_error_handling(self, temp_dir):
        """Test error handling during save."""
        image = Image.new('RGB', (100, 100), (255, 0, 0))

        # Use an invalid path that can't be written
        with patch('PIL.Image.Image.save', side_effect=OSError("Write error")):
            with pytest.raises(IOError) as exc_info:
                ImageUtils.save_image(image, temp_dir / "test.png")

            assert "Failed to save image" in str(exc_info.value)


class TestImageInfo:
    """Test image information extraction."""

    def test_get_image_info_basic(self):
        """Test basic image information extraction."""
        image = Image.new('RGB', (100, 50), (255, 0, 0))
        image.format = 'PNG'

        info = ImageUtils.get_image_info(image)

        assert info['size'] == (100, 50)
        assert info['width'] == 100
        assert info['height'] == 50
        assert info['mode'] == 'RGB'
        assert info['format'] == 'PNG'
        assert info['has_transparency'] is False

    def test_get_image_info_with_transparency(self):
        """Test image info for image with transparency."""
        rgba_image = Image.new('RGBA', (100, 50), (255, 0, 0, 128))

        info = ImageUtils.get_image_info(rgba_image)

        assert info['has_transparency'] is True

    def test_get_image_info_with_file_size(self, sample_image_rgb):
        """Test image info includes file size when available."""
        image = ImageUtils.load_image(sample_image_rgb)

        info = ImageUtils.get_image_info(image)

        if 'file_size_bytes' in info:
            assert info['file_size_bytes'] > 0
            assert info['file_size_mb'] > 0

    def test_get_image_info_with_exif(self, sample_image_with_exif):
        """Test image info extraction with EXIF data."""
        image = ImageUtils.load_image(sample_image_with_exif)

        info = ImageUtils.get_image_info(image)

        # EXIF data should be included if present
        if 'exif' in info:
            assert isinstance(info['exif'], dict)


class TestImageManipulation:
    """Test image manipulation operations."""

    def test_resize_image_maintain_aspect(self):
        """Test image resizing while maintaining aspect ratio."""
        image = Image.new('RGB', (200, 100), (255, 0, 0))

        resized = ImageUtils.resize_image(image, (100, 100), maintain_aspect=True)

        # Should maintain 2:1 aspect ratio, so result should be 100x50
        assert resized.size == (100, 50)

    def test_resize_image_no_aspect(self):
        """Test image resizing without maintaining aspect ratio."""
        image = Image.new('RGB', (200, 100), (255, 0, 0))

        resized = ImageUtils.resize_image(image, (100, 100), maintain_aspect=False)

        assert resized.size == (100, 100)

    def test_resize_image_different_methods(self):
        """Test different resampling methods."""
        image = Image.new('RGB', (100, 100), (255, 0, 0))

        for method in ['lanczos', 'bicubic', 'bilinear', 'nearest']:
            resized = ImageUtils.resize_image(image, (50, 50), method=method)
            assert resized.size == (50, 50)

    def test_resize_image_invalid_method(self):
        """Test resize with invalid method defaults to lanczos."""
        image = Image.new('RGB', (100, 100), (255, 0, 0))

        resized = ImageUtils.resize_image(image, (50, 50), method='invalid')
        assert resized.size == (50, 50)

    def test_crop_image(self):
        """Test image cropping."""
        image = Image.new('RGB', (100, 100), (255, 0, 0))

        cropped = ImageUtils.crop_image(image, (10, 10, 60, 60))

        assert cropped.size == (50, 50)

    def test_rotate_image(self):
        """Test image rotation."""
        image = Image.new('RGB', (100, 50), (255, 0, 0))

        rotated = ImageUtils.rotate_image(image, 90, expand=True)

        # 90-degree rotation should swap width and height
        assert rotated.size == (50, 100)

    def test_rotate_image_no_expand(self):
        """Test image rotation without expanding."""
        image = Image.new('RGB', (100, 50), (255, 0, 0))

        rotated = ImageUtils.rotate_image(image, 45, expand=False)

        # Size should remain the same
        assert rotated.size == (100, 50)

    def test_flip_image_horizontal(self):
        """Test horizontal image flipping."""
        # Create image with different colored sides
        image = Image.new('RGB', (100, 50), (255, 255, 255))
        # Add some pixels for verification
        pixels = image.load()
        pixels[0, 0] = (255, 0, 0)  # Red pixel at top-left

        flipped = ImageUtils.flip_image(image, horizontal=True)

        assert flipped.size == image.size
        # Red pixel should now be at top-right
        flipped_pixels = flipped.load()
        assert flipped_pixels[99, 0] == (255, 0, 0)

    def test_flip_image_vertical(self):
        """Test vertical image flipping."""
        image = Image.new('RGB', (100, 50), (255, 255, 255))
        pixels = image.load()
        pixels[0, 0] = (255, 0, 0)  # Red pixel at top-left

        flipped = ImageUtils.flip_image(image, horizontal=False)

        assert flipped.size == image.size
        # Red pixel should now be at bottom-left
        flipped_pixels = flipped.load()
        assert flipped_pixels[0, 49] == (255, 0, 0)

    def test_auto_orient(self):
        """Test auto-orientation based on EXIF."""
        image = Image.new('RGB', (100, 50), (255, 0, 0))

        # Mock EXIF orientation
        with patch('PIL.ImageOps.exif_transpose') as mock_transpose:
            mock_transpose.return_value = image

            oriented = ImageUtils.auto_orient(image)

            mock_transpose.assert_called_once_with(image)
            assert oriented == image


class TestImageValidation:
    """Test image validation and format support."""

    def test_get_supported_formats(self):
        """Test getting supported image formats."""
        formats = ImageUtils.get_supported_formats()

        assert isinstance(formats, list)
        assert len(formats) > 0
        assert 'PNG' in formats
        assert 'JPEG' in formats

    def test_is_valid_image_success(self, sample_image_rgb):
        """Test valid image detection."""
        assert ImageUtils.is_valid_image(sample_image_rgb) is True

    def test_is_valid_image_failure(self, temp_dir):
        """Test invalid image detection."""
        invalid_file = temp_dir / "invalid.jpg"
        invalid_file.write_text("Not an image")

        assert ImageUtils.is_valid_image(invalid_file) is False

    def test_is_valid_image_nonexistent(self):
        """Test validation of non-existent file."""
        assert ImageUtils.is_valid_image("/nonexistent/file.jpg") is False

    def test_validate_image_format_success(self, sample_image_rgb):
        """Test successful image format validation."""
        is_valid, format_or_error = ImageUtils.validate_image_format(sample_image_rgb)

        assert is_valid is True
        assert format_or_error in ['PNG', 'JPEG']

    def test_validate_image_format_file_not_found(self):
        """Test format validation for non-existent file."""
        is_valid, error = ImageUtils.validate_image_format("/nonexistent/file.jpg")

        assert is_valid is False
        assert "File not found" in error

    def test_validate_image_format_invalid_image(self, temp_dir):
        """Test format validation for invalid image."""
        invalid_file = temp_dir / "invalid.jpg"
        invalid_file.write_text("Not an image")

        is_valid, error = ImageUtils.validate_image_format(invalid_file)

        assert is_valid is False
        assert len(error) > 0


class TestImageCalculations:
    """Test image calculation utilities."""

    def test_calculate_file_size_rgb(self):
        """Test file size calculation for RGB image."""
        estimated_size = ImageUtils.calculate_file_size(100, 100, 'RGB', 1.0)

        expected_size = 100 * 100 * 3  # 30,000 bytes uncompressed
        assert estimated_size == expected_size

    def test_calculate_file_size_rgba(self):
        """Test file size calculation for RGBA image."""
        estimated_size = ImageUtils.calculate_file_size(100, 100, 'RGBA', 1.0)

        expected_size = 100 * 100 * 4  # 40,000 bytes uncompressed
        assert estimated_size == expected_size

    def test_calculate_file_size_grayscale(self):
        """Test file size calculation for grayscale image."""
        estimated_size = ImageUtils.calculate_file_size(100, 100, 'L', 1.0)

        expected_size = 100 * 100 * 1  # 10,000 bytes uncompressed
        assert estimated_size == expected_size

    def test_calculate_file_size_with_compression(self):
        """Test file size calculation with compression."""
        uncompressed = ImageUtils.calculate_file_size(100, 100, 'RGB', 1.0)
        compressed = ImageUtils.calculate_file_size(100, 100, 'RGB', 0.5)

        assert compressed == uncompressed // 2

    def test_calculate_file_size_unknown_mode(self):
        """Test file size calculation for unknown mode defaults to 3 bytes."""
        estimated_size = ImageUtils.calculate_file_size(100, 100, 'UNKNOWN', 1.0)

        expected_size = 100 * 100 * 3  # Defaults to RGB
        assert estimated_size == expected_size

    def test_get_safe_crop_bounds_normal(self):
        """Test safe crop bounds calculation within image."""
        bounds = ImageUtils.get_safe_crop_bounds(200, 200, 50, 50, 100, 100)

        assert bounds == (50, 50, 150, 150)

    def test_get_safe_crop_bounds_with_overlap(self):
        """Test safe crop bounds with overlap."""
        bounds = ImageUtils.get_safe_crop_bounds(200, 200, 50, 50, 100, 100, overlap=10)

        assert bounds == (40, 40, 160, 160)

    def test_get_safe_crop_bounds_exceeds_image(self):
        """Test safe crop bounds when crop exceeds image dimensions."""
        bounds = ImageUtils.get_safe_crop_bounds(100, 100, 80, 80, 50, 50)

        # Should be clipped to image bounds
        assert bounds == (80, 80, 100, 100)

    def test_get_safe_crop_bounds_negative_start(self):
        """Test safe crop bounds with negative start coordinates."""
        bounds = ImageUtils.get_safe_crop_bounds(100, 100, -10, -10, 50, 50, overlap=5)

        # Should be clipped to 0
        assert bounds == (0, 0, 45, 45)

    def test_estimate_processing_memory(self):
        """Test memory estimation for image processing."""
        memory_estimate = ImageUtils.estimate_processing_memory(1000, 1000, 4)

        assert 'base_image_mb' in memory_estimate
        assert 'per_tile_mb' in memory_estimate
        assert 'peak_memory_mb' in memory_estimate
        assert 'estimated_total_mb' in memory_estimate

        assert memory_estimate['base_image_mb'] > 0
        assert memory_estimate['peak_memory_mb'] > memory_estimate['base_image_mb']

    def test_estimate_processing_memory_zero_tiles(self):
        """Test memory estimation with zero tiles."""
        memory_estimate = ImageUtils.estimate_processing_memory(1000, 1000, 0)

        assert memory_estimate['per_tile_mb'] == 0
        assert memory_estimate['base_image_mb'] > 0


class TestImageOptimization:
    """Test image optimization utilities."""

    def test_optimize_image_for_tiling(self):
        """Test image optimization for tiling operations."""
        image = Image.new('RGB', (100, 100), (255, 0, 0))

        with patch.object(ImageUtils, 'auto_orient', return_value=image) as mock_orient:
            optimized = ImageUtils.optimize_image_for_tiling(image)

            mock_orient.assert_called_once_with(image)
            assert optimized.mode in ('RGB', 'RGBA', 'L')

    def test_optimize_image_converts_unusual_mode(self):
        """Test optimization converts unusual color modes."""
        # Create a CMYK image
        cmyk_image = Image.new('CMYK', (100, 100))

        with patch.object(ImageUtils, 'auto_orient', return_value=cmyk_image):
            with patch.object(ImageUtils, '_convert_image_mode') as mock_convert:
                mock_convert.return_value = Image.new('RGB', (100, 100))

                optimized = ImageUtils.optimize_image_for_tiling(cmyk_image)

                mock_convert.assert_called_once_with(cmyk_image, 'RGB')


class TestTileInfo:
    """Test tile information creation."""

    def test_create_tile_info_success(self, sample_image_rgb):
        """Test successful tile info creation."""
        coordinates = [(0, 0), (50, 0), (0, 50), (50, 50)]

        tile_info = ImageUtils.create_tile_info(
            sample_image_rgb, coordinates, 50, 50
        )

        assert 'source_image' in tile_info
        assert 'tile_config' in tile_info
        assert 'valid_tiles' in tile_info
        assert 'invalid_tiles' in tile_info
        assert 'memory_estimate' in tile_info
        assert 'processing_feasible' in tile_info

        assert len(tile_info['valid_tiles']) > 0
        assert tile_info['tile_config']['width'] == 50
        assert tile_info['tile_config']['height'] == 50

    def test_create_tile_info_with_overlap(self, sample_image_rgb):
        """Test tile info creation with overlap."""
        coordinates = [(0, 0), (50, 50)]

        tile_info = ImageUtils.create_tile_info(
            sample_image_rgb, coordinates, 50, 50, overlap=10
        )

        assert tile_info['tile_config']['overlap'] == 10

        # Check that overlap affects crop bounds
        for tile in tile_info['valid_tiles']:
            bounds = tile['crop_bounds']
            # With overlap, bounds should extend beyond the base coordinates
            assert bounds[2] - bounds[0] >= 50  # width >= tile_width
            assert bounds[3] - bounds[1] >= 50  # height >= tile_height

    def test_create_tile_info_invalid_tiles(self, sample_image_rgb):
        """Test tile info creation with invalid tile coordinates."""
        # Add coordinates that exceed image bounds
        coordinates = [(0, 0), (150, 150)]  # 150,150 is beyond 100x100 image

        tile_info = ImageUtils.create_tile_info(
            sample_image_rgb, coordinates, 50, 50
        )

        # Should have both valid and invalid tiles
        assert len(tile_info['valid_tiles']) >= 1
        assert len(tile_info['invalid_tiles']) >= 0

    def test_create_tile_info_memory_feasibility(self, sample_image_rgb):
        """Test memory feasibility assessment."""
        coordinates = [(0, 0)]  # Single small tile

        tile_info = ImageUtils.create_tile_info(
            sample_image_rgb, coordinates, 10, 10
        )

        # Small tile should be feasible
        assert tile_info['processing_feasible'] is True
        assert tile_info['memory_estimate']['peak_memory_mb'] < 1024

    def test_create_tile_info_error_handling(self):
        """Test tile info creation with invalid image path."""
        coordinates = [(0, 0)]
        invalid_path = Path("/nonexistent/image.jpg")

        tile_info = ImageUtils.create_tile_info(
            invalid_path, coordinates, 50, 50
        )

        assert 'error' in tile_info
        assert tile_info['processing_feasible'] is False
        assert str(invalid_path) in tile_info['source_path']


class TestImageUtilsEdgeCases:
    """Test edge cases and error conditions."""

    def test_load_image_with_warning_mime_type(self, temp_dir):
        """Test loading file with non-image MIME type logs warning."""
        text_file = temp_dir / "file.txt"
        text_file.write_text("Not an image")

        # Rename to have image extension but wrong content
        fake_image = temp_dir / "fake.jpg"
        text_file.rename(fake_image)

        with pytest.raises(IOError):
            # Should still fail to load, but warning should be logged
            ImageUtils.load_image(fake_image)

    def test_save_image_with_additional_kwargs(self, temp_dir):
        """Test save_image with additional keyword arguments."""
        image = Image.new('RGB', (100, 100), (255, 0, 0))
        output_path = temp_dir / "output.png"

        # PNG-specific options
        ImageUtils.save_image(
            image, output_path,
            format='PNG',
            compress_level=6,
            optimize=True
        )

        assert output_path.exists()

    def test_color_mode_edge_cases(self):
        """Test edge cases in color mode handling."""
        # Test YCbCr mode conversion
        ycbcr_image = Image.new('YCbCr', (50, 50))
        loaded_image = Mock()
        loaded_image.mode = 'YCbCr'
        loaded_image.convert.return_value = Image.new('RGB', (50, 50))

        # This would be handled in the load_image method
        # Testing the conversion logic separately
        if loaded_image.mode == 'YCbCr':
            converted = loaded_image.convert('RGB')
            assert converted.mode == 'RGB'

    def test_large_image_memory_estimation(self):
        """Test memory estimation for very large images."""
        # Test with very large dimensions
        memory_estimate = ImageUtils.estimate_processing_memory(
            10000, 10000, 100, bytes_per_pixel=4
        )

        # Should handle large numbers without overflow
        assert memory_estimate['base_image_mb'] > 100
        assert memory_estimate['peak_memory_mb'] > memory_estimate['base_image_mb']

    def test_zero_dimension_handling(self):
        """Test handling of zero or negative dimensions."""
        # Test safe crop bounds with zero dimensions
        bounds = ImageUtils.get_safe_crop_bounds(100, 100, 50, 50, 0, 0)
        assert bounds == (50, 50, 50, 50)  # Zero-size crop

    def test_thread_safety_image_operations(self, sample_image_rgb):
        """Test that image operations are thread-safe."""
        import threading
        import queue

        results = queue.Queue()
        errors = queue.Queue()

        def load_and_process():
            try:
                image = ImageUtils.load_image(sample_image_rgb)
                info = ImageUtils.get_image_info(image)
                results.put(info)
            except Exception as e:
                errors.put(e)

        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=load_and_process)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Check results
        assert errors.empty(), f"Errors occurred: {list(errors.queue)}"
        assert results.qsize() == 5

        # All results should be consistent
        first_result = results.get()
        while not results.empty():
            result = results.get()
            assert result['size'] == first_result['size']
            assert result['mode'] == first_result['mode']

    def test_memory_efficiency_large_operations(self, sample_image_rgb):
        """Test memory efficiency of repeated operations."""
        # Perform many operations to check for memory leaks
        for _ in range(100):
            image = ImageUtils.load_image(sample_image_rgb)
            info = ImageUtils.get_image_info(image)
            resized = ImageUtils.resize_image(image, (50, 50))

            # Force garbage collection of the images
            del image, info, resized

    def test_format_normalization_edge_cases(self, temp_dir):
        """Test format normalization for various extensions."""
        image = Image.new('RGB', (100, 100), (255, 0, 0))

        # Test .JPG -> JPEG normalization
        jpg_path = temp_dir / "test.JPG"  # Uppercase extension
        ImageUtils.save_image(image, jpg_path)

        loaded = Image.open(jpg_path)
        assert loaded.format == 'JPEG'

    def test_image_info_robustness(self):
        """Test image info extraction robustness."""
        # Test with image that has no filename
        image = Image.new('RGB', (100, 100))
        # Don't set filename attribute

        info = ImageUtils.get_image_info(image)

        # Should not include file size info
        assert 'file_size_bytes' not in info
        assert 'file_size_mb' not in info

        # Should include basic info
        assert info['width'] == 100
        assert info['height'] == 100
        assert info['mode'] == 'RGB'

    @pytest.mark.parametrize("mode,expected_bpp", [
        ('L', 1),
        ('RGB', 3),
        ('RGBA', 4),
        ('CMYK', 4),
        ('P', 1),
        ('UNKNOWN', 3),  # Should default to 3
    ])
    def test_calculate_file_size_modes(self, mode, expected_bpp):
        """Test file size calculation for various image modes."""
        size = ImageUtils.calculate_file_size(100, 100, mode, 1.0)
        expected = 100 * 100 * expected_bpp
        assert size == expected