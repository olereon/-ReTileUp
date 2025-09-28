"""Integration tests for the TilingTool.

This module tests the complete integration of the TilingTool with the
ReTileUp framework, including registry integration, CLI compatibility,
and end-to-end workflows.
"""

import tempfile
import pytest
from pathlib import Path
from PIL import Image

from retileup.tools.tiling import TilingTool, TilingConfig
from retileup.utils.image import ImageUtils


class TestTilingIntegration:
    """Integration tests for TilingTool."""

    def test_end_to_end_workflow(self, sample_image_path, temp_output_dir):
        """Test complete end-to-end tiling workflow."""
        # Create tool instance
        tool = TilingTool()

        # Define tiling parameters
        coordinates = [(0, 0), (200, 0), (400, 0), (0, 200), (200, 200), (400, 200)]

        # Create configuration
        config = TilingConfig(
            input_path=sample_image_path,
            output_dir=temp_output_dir,
            tile_width=200,
            tile_height=200,
            coordinates=coordinates,
            output_pattern="tile_{x}_{y}_{base}.{ext}",
            overlap=10,
            verbose=True
        )

        # Validate configuration
        errors = tool.validate_config(config)
        assert errors == [], f"Configuration validation failed: {errors}"

        # Execute tiling
        result = tool.execute_with_timing(config)

        # Verify successful execution
        assert result.success is True
        assert len(result.output_files) == len(coordinates)
        assert result.execution_time > 0

        # Verify all output files exist and are valid
        for i, output_file in enumerate(result.output_files):
            assert output_file.exists(), f"Output file {i} does not exist: {output_file}"

            # Verify it's a valid image
            is_valid, format_info = ImageUtils.validate_image_format(output_file)
            assert is_valid, f"Output file {i} is not a valid image: {format_info}"

            # Verify dimensions (considering overlap)
            with Image.open(output_file) as tile:
                assert tile.width >= 200, f"Tile {i} width too small: {tile.width}"
                assert tile.height >= 200, f"Tile {i} height too small: {tile.height}"

        # Verify metadata
        metadata = result.metadata
        assert metadata["tile_count"] == len(coordinates)
        assert metadata["overlap"] == 10
        assert "processing_time_ms" in metadata
        assert "pixels_per_second" in metadata

    def test_large_image_tiling(self, temp_output_dir):
        """Test tiling of a large image with many tiles."""
        # Create a large test image
        large_image = Image.new('RGB', (1600, 1200), color=(100, 150, 200))

        # Add some visual pattern for testing
        for x in range(0, 1600, 100):
            for y in range(0, 1200, 100):
                # Create small colored rectangles
                for i in range(50):
                    for j in range(50):
                        if x + i < 1600 and y + j < 1200:
                            large_image.putpixel((x + i, y + j), (
                                (x // 10) % 255,
                                (y // 10) % 255,
                                ((x + y) // 20) % 255
                            ))

        large_image_path = temp_output_dir / "large_image.png"
        large_image.save(large_image_path)

        tool = TilingTool()

        # Generate grid of tile coordinates
        tile_size = 256
        coordinates = []
        for x in range(0, 1600 - tile_size, tile_size):
            for y in range(0, 1200 - tile_size, tile_size):
                coordinates.append((x, y))

        config = TilingConfig(
            input_path=large_image_path,
            output_dir=temp_output_dir / "tiles",
            tile_width=tile_size,
            tile_height=tile_size,
            coordinates=coordinates,
            output_pattern="grid_{x}_{y}.png"
        )

        # Validate and execute
        errors = tool.validate_config(config)
        assert errors == []

        result = tool.execute(config)

        assert result.success is True
        assert len(result.output_files) == len(coordinates)

        # Verify reasonable performance
        pixels_processed = tile_size * tile_size * len(coordinates)
        throughput = metadata["pixels_per_second"] if result.success else 0
        assert throughput > 1_000_000, f"Performance too slow: {throughput} pixels/second"

    def test_memory_limit_handling(self, temp_output_dir):
        """Test handling of memory limits during processing."""
        # Create a very large image that would exceed memory limits
        # Note: This creates the image info without actually allocating the full image
        tool = TilingTool()

        # Create a real but smaller image for validation
        test_image = Image.new('RGB', (2000, 1500), color='red')
        test_image_path = temp_output_dir / "test_memory.jpg"
        test_image.save(test_image_path, quality=85)

        # Create config that would theoretically use too much memory
        many_coordinates = [(x, y) for x in range(0, 1800, 200) for y in range(0, 1300, 200)]

        config = TilingConfig(
            input_path=test_image_path,
            output_dir=temp_output_dir,
            tile_width=400,
            tile_height=400,
            coordinates=many_coordinates,
            overlap=50
        )

        # The tool should handle this gracefully
        errors = tool.validate_config(config)
        # May or may not trigger memory warnings depending on system

        result = tool.execute(config)
        # Should complete successfully even with many tiles
        assert result.success is True

    def test_edge_case_handling(self, temp_output_dir):
        """Test various edge cases in tiling."""
        # Create small test image
        small_image = Image.new('RGB', (100, 100), color='green')
        small_image_path = temp_output_dir / "small.png"
        small_image.save(small_image_path)

        tool = TilingTool()

        # Test case 1: Tile larger than image
        config1 = TilingConfig(
            input_path=small_image_path,
            output_dir=temp_output_dir,
            tile_width=200,
            tile_height=200,
            coordinates=[(0, 0)]
        )

        errors1 = tool.validate_config(config1)
        assert len(errors1) > 0  # Should detect that tile exceeds image bounds

        # Test case 2: Coordinates at image boundary
        config2 = TilingConfig(
            input_path=small_image_path,
            output_dir=temp_output_dir,
            tile_width=50,
            tile_height=50,
            coordinates=[(50, 50)]  # Exactly at boundary
        )

        errors2 = tool.validate_config(config2)
        assert errors2 == []  # Should be valid

        result2 = tool.execute(config2)
        assert result2.success is True

        # Test case 3: Very small tiles
        config3 = TilingConfig(
            input_path=small_image_path,
            output_dir=temp_output_dir,
            tile_width=1,
            tile_height=1,
            coordinates=[(50, 50)]
        )

        result3 = tool.execute(config3)
        assert result3.success is True

        # Verify tiny tile was created
        output_file = result3.output_files[0]
        with Image.open(output_file) as tile:
            assert tile.size == (1, 1)

    def test_format_preservation(self, temp_output_dir):
        """Test that output format matches input format by default."""
        formats_to_test = [
            ('test.jpg', 'JPEG'),
            ('test.png', 'PNG'),
        ]

        tool = TilingTool()

        for filename, expected_format in formats_to_test:
            # Create test image in specific format
            test_image = Image.new('RGB', (200, 200), color='blue')
            test_path = temp_output_dir / filename
            test_image.save(test_path)

            config = TilingConfig(
                input_path=test_path,
                output_dir=temp_output_dir / f"format_test_{expected_format}",
                tile_width=100,
                tile_height=100,
                coordinates=[(0, 0)]
            )

            result = tool.execute(config)
            assert result.success is True

            # Verify output format matches input
            output_file = result.output_files[0]
            assert output_file.suffix.lower() == test_path.suffix.lower()

    def test_concurrent_safety(self, sample_image_path, temp_output_dir):
        """Test that multiple tool instances can run concurrently."""
        import threading
        import concurrent.futures

        def run_tiling(thread_id):
            """Run tiling in a separate thread."""
            tool = TilingTool()
            thread_output_dir = temp_output_dir / f"thread_{thread_id}"
            thread_output_dir.mkdir()

            config = TilingConfig(
                input_path=sample_image_path,
                output_dir=thread_output_dir,
                tile_width=100,
                tile_height=100,
                coordinates=[(thread_id * 50, 0)],
                output_pattern=f"thread_{thread_id}_{{x}}_{{y}}.{{ext}}"
            )

            return tool.execute(config)

        # Run multiple tiling operations concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(run_tiling, i) for i in range(3)]
            results = [future.result() for future in futures]

        # Verify all operations succeeded
        for i, result in enumerate(results):
            assert result.success is True, f"Thread {i} failed: {result.message}"
            assert len(result.output_files) == 1
            assert result.output_files[0].exists()

    def test_error_recovery_and_partial_results(self, temp_output_dir):
        """Test error recovery and partial result handling."""
        # Create test image
        test_image = Image.new('RGB', (300, 300), color='purple')
        test_image_path = temp_output_dir / "error_test.png"
        test_image.save(test_image_path)

        tool = TilingTool()

        # Mix valid and invalid coordinates
        coordinates = [
            (0, 0),      # Valid
            (100, 100),  # Valid
            (500, 500),  # Invalid (out of bounds)
            (200, 200),  # Valid
        ]

        config = TilingConfig(
            input_path=test_image_path,
            output_dir=temp_output_dir,
            tile_width=50,
            tile_height=50,
            coordinates=coordinates
        )

        # Should detect invalid coordinates during validation
        errors = tool.validate_config(config)
        assert len(errors) > 0  # Should detect out-of-bounds coordinates

        # If we force execution (simulating relaxed validation),
        # it should still produce partial results
        # Note: In practice, the validation should catch this


# Test fixtures
@pytest.fixture
def sample_image_path(tmp_path):
    """Create a sample image for integration testing."""
    # Create a more complex test image with patterns
    image = Image.new('RGB', (800, 600), color=(50, 100, 150))

    # Add some visual patterns
    for x in range(0, 800, 100):
        for y in range(0, 600, 100):
            # Create checkerboard pattern
            color = (200, 50, 50) if (x // 100 + y // 100) % 2 == 0 else (50, 200, 50)
            for i in range(50):
                for j in range(50):
                    if x + i < 800 and y + j < 600:
                        image.putpixel((x + i, y + j), color)

    image_path = tmp_path / "integration_test_image.jpg"
    image.save(image_path, quality=90)
    return image_path


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory for integration tests."""
    output_dir = tmp_path / "integration_output"
    output_dir.mkdir()
    return output_dir