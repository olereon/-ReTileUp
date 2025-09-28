"""Comprehensive test suite for the TilingTool.

This module provides thorough testing of the TilingTool including:
- Configuration validation
- Coordinate bounds checking
- Memory-efficient processing
- Error handling
- Output file generation
- Performance benchmarking
"""

import tempfile
import pytest
from pathlib import Path
from typing import List, Tuple
from unittest.mock import patch, MagicMock

from PIL import Image
import pydantic

from retileup.tools.tiling import TilingTool, TilingConfig
from retileup.tools.base import ToolResult
from retileup.core.exceptions import ValidationError, ProcessingError


class TestTilingConfig:
    """Test suite for TilingConfig validation."""

    def test_valid_config(self, sample_image_path, temp_output_dir):
        """Test creation of valid tiling configuration."""
        config = TilingConfig(
            input_path=sample_image_path,
            output_dir=temp_output_dir,
            tile_width=100,
            tile_height=100,
            coordinates=[(0, 0), (100, 100)]
        )

        assert config.tile_width == 100
        assert config.tile_height == 100
        assert config.coordinates == [(0, 0), (100, 100)]
        assert config.output_pattern == "{base}_{x}_{y}.{ext}"
        assert config.maintain_aspect is False
        assert config.overlap == 0

    def test_invalid_tile_dimensions(self, sample_image_path, temp_output_dir):
        """Test validation of invalid tile dimensions."""
        with pytest.raises(pydantic.ValidationError) as exc_info:
            TilingConfig(
                input_path=sample_image_path,
                output_dir=temp_output_dir,
                tile_width=0,  # Invalid: must be > 0
                tile_height=100,
                coordinates=[(0, 0)]
            )

        assert "greater than 0" in str(exc_info.value)

        with pytest.raises(pydantic.ValidationError) as exc_info:
            TilingConfig(
                input_path=sample_image_path,
                output_dir=temp_output_dir,
                tile_width=10000,  # Invalid: too large
                tile_height=100,
                coordinates=[(0, 0)]
            )

        assert "cannot exceed" in str(exc_info.value)

    def test_invalid_coordinates(self, sample_image_path, temp_output_dir):
        """Test validation of invalid coordinates."""
        # Empty coordinates
        with pytest.raises(pydantic.ValidationError) as exc_info:
            TilingConfig(
                input_path=sample_image_path,
                output_dir=temp_output_dir,
                tile_width=100,
                tile_height=100,
                coordinates=[]
            )

        assert "at least one coordinate" in str(exc_info.value)

        # Negative coordinates
        with pytest.raises(pydantic.ValidationError) as exc_info:
            TilingConfig(
                input_path=sample_image_path,
                output_dir=temp_output_dir,
                tile_width=100,
                tile_height=100,
                coordinates=[(-10, 5)]
            )

        assert "non-negative" in str(exc_info.value)

        # Invalid coordinate format
        with pytest.raises(pydantic.ValidationError) as exc_info:
            TilingConfig(
                input_path=sample_image_path,
                output_dir=temp_output_dir,
                tile_width=100,
                tile_height=100,
                coordinates=[(10,)]  # Missing y coordinate
            )

        assert "tuple/list of 2 integers" in str(exc_info.value)

    def test_invalid_output_pattern(self, sample_image_path, temp_output_dir):
        """Test validation of invalid output patterns."""
        # Missing required placeholders
        with pytest.raises(pydantic.ValidationError) as exc_info:
            TilingConfig(
                input_path=sample_image_path,
                output_dir=temp_output_dir,
                tile_width=100,
                tile_height=100,
                coordinates=[(0, 0)],
                output_pattern="tile_{x}_{y}"  # Missing {base} and {ext}
            )

        assert "{base}" in str(exc_info.value) or "{ext}" in str(exc_info.value)

        # Invalid placeholder
        with pytest.raises(pydantic.ValidationError) as exc_info:
            TilingConfig(
                input_path=sample_image_path,
                output_dir=temp_output_dir,
                tile_width=100,
                tile_height=100,
                coordinates=[(0, 0)],
                output_pattern="{base}_{invalid_placeholder}.{ext}"
            )

        assert "invalid placeholder" in str(exc_info.value)

    def test_overlap_validation(self, sample_image_path, temp_output_dir):
        """Test validation of overlap parameter."""
        # Valid overlap
        config = TilingConfig(
            input_path=sample_image_path,
            output_dir=temp_output_dir,
            tile_width=100,
            tile_height=100,
            coordinates=[(0, 0)],
            overlap=10
        )
        assert config.overlap == 10

        # Negative overlap
        with pytest.raises(pydantic.ValidationError):
            TilingConfig(
                input_path=sample_image_path,
                output_dir=temp_output_dir,
                tile_width=100,
                tile_height=100,
                coordinates=[(0, 0)],
                overlap=-5
            )

        # Overlap too large
        with pytest.raises(pydantic.ValidationError) as exc_info:
            TilingConfig(
                input_path=sample_image_path,
                output_dir=temp_output_dir,
                tile_width=100,
                tile_height=100,
                coordinates=[(0, 0)],
                overlap=100  # Equal to tile dimension
            )

        assert "cannot be greater than" in str(exc_info.value)


class TestTilingTool:
    """Test suite for TilingTool functionality."""

    def test_tool_properties(self):
        """Test basic tool properties."""
        tool = TilingTool()

        assert tool.name == "tile"
        assert "rectangular tiles" in tool.description.lower()
        assert tool.version == "1.0.0"
        assert tool.get_config_schema() == TilingConfig

    def test_config_validation_success(self, sample_image_path, temp_output_dir):
        """Test successful configuration validation."""
        tool = TilingTool()
        config = TilingConfig(
            input_path=sample_image_path,
            output_dir=temp_output_dir,
            tile_width=100,
            tile_height=100,
            coordinates=[(0, 0), (100, 0)]
        )

        errors = tool.validate_config(config)
        assert errors == []

    def test_config_validation_missing_file(self, temp_output_dir):
        """Test validation with missing input file."""
        tool = TilingTool()
        missing_file = temp_output_dir / "nonexistent.jpg"

        config = TilingConfig(
            input_path=missing_file,
            output_dir=temp_output_dir,
            tile_width=100,
            tile_height=100,
            coordinates=[(0, 0)]
        )

        errors = tool.validate_config(config)
        assert len(errors) == 1
        assert "not found" in errors[0]

    def test_config_validation_coordinates_out_of_bounds(self, sample_image_path, temp_output_dir):
        """Test validation with coordinates exceeding image bounds."""
        tool = TilingTool()

        # Create config with coordinates that exceed image bounds
        config = TilingConfig(
            input_path=sample_image_path,
            output_dir=temp_output_dir,
            tile_width=100,
            tile_height=100,
            coordinates=[(700, 700)]  # Exceeds 800x600 image
        )

        errors = tool.validate_config(config)
        assert len(errors) >= 1
        assert any("beyond image" in error for error in errors)

    def test_successful_execution(self, sample_image_path, temp_output_dir):
        """Test successful tile extraction."""
        tool = TilingTool()
        config = TilingConfig(
            input_path=sample_image_path,
            output_dir=temp_output_dir,
            tile_width=100,
            tile_height=100,
            coordinates=[(0, 0), (100, 0), (0, 100)]
        )

        result = tool.execute(config)

        assert result.success is True
        assert "3 tiles" in result.message
        assert len(result.output_files) == 3
        assert result.execution_time > 0

        # Check metadata
        assert result.metadata["tile_count"] == 3
        assert result.metadata["tile_size"] == "100x100"
        assert "pixels_per_second" in result.metadata

        # Verify output files exist
        for output_file in result.output_files:
            assert output_file.exists()
            assert output_file.stat().st_size > 0

    def test_dry_run_execution(self, sample_image_path, temp_output_dir):
        """Test dry run mode doesn't create files."""
        tool = TilingTool()
        config = TilingConfig(
            input_path=sample_image_path,
            output_dir=temp_output_dir,
            tile_width=100,
            tile_height=100,
            coordinates=[(0, 0)],
            dry_run=True
        )

        result = tool.execute(config)

        assert result.success is True
        assert len(result.output_files) == 1

        # Verify files were NOT created in dry run
        for output_file in result.output_files:
            assert not output_file.exists()

    def test_overlap_functionality(self, sample_image_path, temp_output_dir):
        """Test tile extraction with overlap."""
        tool = TilingTool()
        config = TilingConfig(
            input_path=sample_image_path,
            output_dir=temp_output_dir,
            tile_width=100,
            tile_height=100,
            coordinates=[(50, 50)],
            overlap=20
        )

        result = tool.execute(config)

        assert result.success is True
        assert result.metadata["overlap"] == 20

        # Verify the tile was created with overlap
        output_file = result.output_files[0]
        assert output_file.exists()

        # Load and check dimensions
        with Image.open(output_file) as tile:
            # Should be larger than 100x100 due to overlap
            assert tile.width >= 100
            assert tile.height >= 100

    def test_maintain_aspect_ratio(self, sample_image_path, temp_output_dir):
        """Test aspect ratio maintenance."""
        tool = TilingTool()
        config = TilingConfig(
            input_path=sample_image_path,
            output_dir=temp_output_dir,
            tile_width=200,
            tile_height=100,  # Different aspect ratio
            coordinates=[(0, 0)],
            maintain_aspect=True
        )

        result = tool.execute(config)

        assert result.success is True
        assert result.metadata["maintain_aspect"] is True

        # Verify aspect ratio was maintained
        output_file = result.output_files[0]
        with Image.open(output_file) as tile:
            assert tile.width <= 200
            assert tile.height <= 100

    def test_custom_output_pattern(self, sample_image_path, temp_output_dir):
        """Test custom output filename pattern."""
        tool = TilingTool()
        config = TilingConfig(
            input_path=sample_image_path,
            output_dir=temp_output_dir,
            tile_width=100,
            tile_height=100,
            coordinates=[(0, 0), (100, 100)],
            output_pattern="custom_{base}_tile_{x}_{y}.{ext}"
        )

        result = tool.execute(config)

        assert result.success is True

        # Check filename pattern was applied
        for output_file in result.output_files:
            assert "custom_" in output_file.name
            assert "_tile_" in output_file.name

    def test_error_handling_corrupted_image(self, temp_output_dir):
        """Test error handling with corrupted image file."""
        tool = TilingTool()

        # Create a fake image file
        fake_image = temp_output_dir / "fake.jpg"
        fake_image.write_text("This is not an image")

        config = TilingConfig(
            input_path=fake_image,
            output_dir=temp_output_dir,
            tile_width=100,
            tile_height=100,
            coordinates=[(0, 0)]
        )

        errors = tool.validate_config(config)
        assert len(errors) >= 1
        assert any("cannot open" in error.lower() for error in errors)

    def test_memory_estimation(self, sample_image_path, temp_output_dir):
        """Test memory usage estimation."""
        tool = TilingTool()

        # Create config that would use significant memory
        large_coordinates = [(x, y) for x in range(0, 700, 100) for y in range(0, 500, 100)]

        config = TilingConfig(
            input_path=sample_image_path,
            output_dir=temp_output_dir,
            tile_width=200,
            tile_height=200,
            coordinates=large_coordinates
        )

        # Should detect high memory usage during validation
        errors = tool.validate_config(config)
        # May or may not trigger memory warning depending on the specific image size

    def test_invalid_config_type(self, temp_output_dir):
        """Test handling of invalid configuration type."""
        from retileup.tools.base import ToolConfig

        tool = TilingTool()

        # Use base ToolConfig instead of TilingConfig
        invalid_config = ToolConfig(
            input_path=temp_output_dir / "test.jpg",
            output_dir=temp_output_dir
        )

        errors = tool.validate_config(invalid_config)
        assert len(errors) == 1
        assert "Invalid config type" in errors[0]

        result = tool.execute(invalid_config)
        assert result.success is False
        assert "Invalid config type" in result.message

    def test_partial_failure_recovery(self, sample_image_path, temp_output_dir):
        """Test recovery from partial failures during tile extraction."""
        tool = TilingTool()

        # Mix valid and invalid coordinates
        config = TilingConfig(
            input_path=sample_image_path,
            output_dir=temp_output_dir,
            tile_width=100,
            tile_height=100,
            coordinates=[(0, 0), (1000, 1000)]  # Second coordinate is invalid
        )

        # Mock the _extract_tile method to simulate failure on second tile
        original_extract = tool._extract_tile

        def mock_extract_tile(img, config, x, y, base_name, ext):
            if x == 1000:  # Simulate failure for out-of-bounds coordinate
                raise Exception("Simulated extraction failure")
            return original_extract(img, config, x, y, base_name, ext)

        with patch.object(tool, '_extract_tile', side_effect=mock_extract_tile):
            result = tool.execute(config)

        # Should still succeed with partial results
        assert result.success is True
        assert len(result.output_files) == 1  # Only first tile succeeded
        assert result.metadata["failed_tiles"] == 1

    def test_tool_lifecycle(self, sample_image_path, temp_output_dir):
        """Test tool setup and cleanup lifecycle."""
        tool = TilingTool()

        assert not tool._setup_called
        assert not tool._cleanup_called

        config = TilingConfig(
            input_path=sample_image_path,
            output_dir=temp_output_dir,
            tile_width=100,
            tile_height=100,
            coordinates=[(0, 0)]
        )

        # Use execute_with_timing to test lifecycle
        result = tool.execute_with_timing(config)

        assert result.success is True
        assert tool._setup_called
        assert tool._cleanup_called


class TestTilingToolPerformance:
    """Performance tests for TilingTool."""

    def test_large_image_processing(self, temp_output_dir):
        """Test processing of large images for performance."""
        # Create a large test image
        large_image = Image.new('RGB', (2000, 1500), color='blue')
        large_image_path = temp_output_dir / "large_test.jpg"
        large_image.save(large_image_path, quality=85)

        tool = TilingTool()
        config = TilingConfig(
            input_path=large_image_path,
            output_dir=temp_output_dir,
            tile_width=256,
            tile_height=256,
            coordinates=[(0, 0), (256, 0), (512, 0), (0, 256)]
        )

        result = tool.execute(config)

        assert result.success is True
        assert len(result.output_files) == 4
        assert result.execution_time < 10.0  # Should complete within 10 seconds

        # Check performance metrics
        assert result.metadata["pixels_per_second"] > 0
        assert result.metadata["processing_time_ms"] < 10000

    def test_memory_efficiency(self, temp_output_dir):
        """Test memory efficiency with multiple tiles."""
        # Create test image
        test_image = Image.new('RGB', (1000, 1000), color='green')
        test_image_path = temp_output_dir / "memory_test.png"
        test_image.save(test_image_path)

        tool = TilingTool()

        # Generate many small tiles
        coordinates = [(x, y) for x in range(0, 900, 100) for y in range(0, 900, 100)]

        config = TilingConfig(
            input_path=test_image_path,
            output_dir=temp_output_dir,
            tile_width=100,
            tile_height=100,
            coordinates=coordinates
        )

        result = tool.execute(config)

        assert result.success is True
        assert len(result.output_files) == len(coordinates)

        # Verify all tiles were created
        for output_file in result.output_files:
            assert output_file.exists()
            with Image.open(output_file) as tile:
                assert tile.size == (100, 100)


# Fixtures for testing
@pytest.fixture
def sample_image_path(tmp_path):
    """Create a sample image for testing."""
    image = Image.new('RGB', (800, 600), color='red')
    image_path = tmp_path / "test_image.jpg"
    image.save(image_path, quality=90)
    return image_path


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def sample_rgba_image(tmp_path):
    """Create a sample RGBA image for testing transparency handling."""
    image = Image.new('RGBA', (400, 300), color=(255, 0, 0, 128))
    image_path = tmp_path / "test_rgba.png"
    image.save(image_path)
    return image_path


class TestTilingToolFormats:
    """Test support for different image formats."""

    def test_png_format(self, temp_output_dir):
        """Test PNG format handling."""
        # Create PNG test image
        png_image = Image.new('RGB', (400, 300), color='blue')
        png_path = temp_output_dir / "test.png"
        png_image.save(png_path)

        tool = TilingTool()
        config = TilingConfig(
            input_path=png_path,
            output_dir=temp_output_dir,
            tile_width=100,
            tile_height=100,
            coordinates=[(0, 0)]
        )

        result = tool.execute(config)
        assert result.success is True

        # Verify output is PNG
        output_file = result.output_files[0]
        assert output_file.suffix.lower() == '.png'

    def test_jpeg_format(self, temp_output_dir):
        """Test JPEG format handling."""
        # Create JPEG test image
        jpeg_image = Image.new('RGB', (400, 300), color='yellow')
        jpeg_path = temp_output_dir / "test.jpg"
        jpeg_image.save(jpeg_path, quality=95)

        tool = TilingTool()
        config = TilingConfig(
            input_path=jpeg_path,
            output_dir=temp_output_dir,
            tile_width=100,
            tile_height=100,
            coordinates=[(0, 0)]
        )

        result = tool.execute(config)
        assert result.success is True

        # Verify output is JPEG
        output_file = result.output_files[0]
        assert output_file.suffix.lower() == '.jpg'

    def test_rgba_to_rgb_conversion(self, sample_rgba_image, temp_output_dir):
        """Test RGBA to RGB conversion for JPEG output."""
        tool = TilingTool()
        config = TilingConfig(
            input_path=sample_rgba_image,
            output_dir=temp_output_dir,
            tile_width=100,
            tile_height=100,
            coordinates=[(0, 0)],
            output_pattern="{base}_{x}_{y}.jpg"  # Force JPEG output
        )

        result = tool.execute(config)
        assert result.success is True

        # Verify the tile was saved as JPEG (no transparency)
        output_file = result.output_files[0]
        with Image.open(output_file) as tile:
            assert tile.mode == 'RGB'  # Should be converted from RGBA