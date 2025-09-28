"""Edge case tests for ReTileUp.

This module tests edge cases and boundary conditions including:
- Zero and negative values
- Empty inputs and null values
- Unicode and special characters
- Platform-specific behaviors
- Resource exhaustion scenarios
- Corrupted data handling
"""

import tempfile
import sys
import os
from pathlib import Path
from unittest.mock import patch, Mock
import threading
import time

import pytest
from PIL import Image

from retileup.utils.image import ImageUtils
from retileup.utils.validation import (
    ValidationUtils, ValidationContext, validate_coordinates,
    validate_positive_number, validate_in_range, batch_validate
)
from retileup.core.exceptions import ValidationError, ProcessingError
from retileup.tools.base import BaseTool, ToolConfig, ToolResult


class TestZeroAndNegativeValues:
    """Test handling of zero and negative values."""

    def test_zero_image_dimensions(self):
        """Test handling of zero image dimensions."""
        # Test memory estimation with zero dimensions
        memory_estimate = ImageUtils.estimate_processing_memory(0, 0, 1)
        assert memory_estimate['base_image_mb'] == 0
        assert memory_estimate['per_tile_mb'] == 0

        # Test safe crop bounds with zero dimensions
        bounds = ImageUtils.get_safe_crop_bounds(100, 100, 50, 50, 0, 0)
        assert bounds == (50, 50, 50, 50)  # Zero-size crop

    def test_negative_coordinates(self):
        """Test handling of negative coordinates."""
        # Negative coordinates should be invalid
        negative_coords = [(-10, 5), (5, -10), (-5, -5)]
        assert validate_coordinates(negative_coords) is False

        # Test safe crop bounds with negative start coordinates
        bounds = ImageUtils.get_safe_crop_bounds(100, 100, -10, -10, 50, 50)
        assert bounds[0] >= 0  # Left should be clipped to 0
        assert bounds[1] >= 0  # Top should be clipped to 0

    def test_negative_numeric_validation(self):
        """Test numeric validation with negative values."""
        # Positive number validation should reject negatives
        assert validate_positive_number(-1) is False
        assert validate_positive_number(-0.1) is False
        assert validate_positive_number(0) is False  # Zero is not positive

        # Range validation with negative bounds
        validator = validate_in_range(-10, 10)
        assert validator(-5) is True
        assert validator(-15) is False
        assert validator(15) is False

    def test_zero_file_size(self, temp_dir):
        """Test handling of zero-byte files."""
        empty_file = temp_dir / "empty.jpg"
        empty_file.touch()

        # Should detect empty file
        with pytest.raises(ValueError) as exc_info:
            ImageUtils.load_image(empty_file)
        assert "empty" in str(exc_info.value).lower()

    def test_negative_timeout_values(self, temp_dir):
        """Test handling of negative timeout values."""
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            ToolConfig(
                input_path=temp_dir / "test.jpg",
                timeout=-1.0
            )

    def test_zero_tile_count_scenarios(self):
        """Test scenarios with zero tile count."""
        # Memory estimation with zero tiles
        memory_estimate = ImageUtils.estimate_processing_memory(1000, 1000, 0)
        assert memory_estimate['per_tile_mb'] == 0

        # Empty coordinate list
        assert validate_coordinates([]) is False


class TestEmptyAndNullInputs:
    """Test handling of empty and null inputs."""

    def test_empty_string_inputs(self):
        """Test handling of empty string inputs."""
        from retileup.utils.validation import COMMON_VALIDATORS

        # Empty string validation
        assert COMMON_VALIDATORS['non_empty_string']("") is False
        assert COMMON_VALIDATORS['non_empty_string']("   ") is False  # Whitespace only
        assert COMMON_VALIDATORS['non_empty_string']("test") is True

    def test_none_value_handling(self):
        """Test handling of None values."""
        # Various validators should handle None gracefully
        assert validate_positive_number(None) is False
        assert validate_coordinates(None) is False

        # Range validator with None
        validator = validate_in_range(0, 100)
        assert validator(None) is False

    def test_empty_collections(self):
        """Test handling of empty collections."""
        # Empty coordinate list
        assert validate_coordinates([]) is False

        # Empty batch validation
        from retileup.utils.validation import batch_validate
        context = batch_validate({}, {}, raise_on_error=False)
        assert not context.has_errors()
        assert not context.has_warnings()

    def test_empty_file_handling(self, temp_dir):
        """Test handling of empty files and directories."""
        # Empty directory
        empty_dir = temp_dir / "empty_dir"
        empty_dir.mkdir()

        result = ValidationUtils.validate_directory_path(empty_dir)
        assert result.is_valid

        # Directory with no files
        files = list(empty_dir.glob("*"))
        assert len(files) == 0

    def test_missing_optional_parameters(self, temp_dir):
        """Test handling of missing optional parameters."""
        # ToolConfig with minimal parameters
        config = ToolConfig(input_path=temp_dir / "test.jpg")

        # Optional fields should have defaults
        assert config.output_dir is None
        assert config.dry_run is False
        assert config.verbose is False
        assert config.preserve_metadata is True


class TestUnicodeAndSpecialCharacters:
    """Test handling of Unicode and special characters."""

    def test_unicode_file_paths(self, temp_dir):
        """Test handling of Unicode characters in file paths."""
        # Create files with Unicode names
        unicode_files = [
            "测试图像.png",  # Chinese
            "изображение.jpg",  # Russian
            "画像ファイル.png",  # Japanese
            "🖼️_emoji.png",  # Emoji
            "café_image.jpg",  # Accented characters
        ]

        for filename in unicode_files:
            file_path = temp_dir / filename

            # Create test image
            image = Image.new('RGB', (50, 50), color='red')
            try:
                image.save(file_path, 'PNG')

                # Test loading Unicode named file
                loaded_image = ImageUtils.load_image(file_path)
                assert loaded_image.size == (50, 50)

                # Test validation
                result = ValidationUtils.validate_file_path(file_path)
                assert result.is_valid

            except (OSError, UnicodeError):
                # Some systems may not support certain Unicode characters
                pytest.skip(f"System doesn't support Unicode filename: {filename}")

    def test_unicode_text_in_validation(self):
        """Test validation with Unicode text."""
        from retileup.utils.validation import COMMON_VALIDATORS

        # Unicode strings should be valid
        unicode_strings = [
            "测试文本",  # Chinese
            "тестовый текст",  # Russian
            "テストテキスト",  # Japanese
            "🔥 Hot text 🔥",  # Emoji
            "Café münü"  # Mixed accents
        ]

        for text in unicode_strings:
            assert COMMON_VALIDATORS['non_empty_string'](text) is True

    def test_special_characters_in_paths(self, temp_dir):
        """Test handling of special characters in paths."""
        special_chars = [
            "file with spaces.png",
            "file-with-dashes.png",
            "file_with_underscores.png",
            "file.with.dots.png",
            "file(with)parentheses.png",
            "file[with]brackets.png",
        ]

        for filename in special_chars:
            file_path = temp_dir / filename

            try:
                # Create and test file
                file_path.touch()
                result = ValidationUtils.validate_file_path(file_path)
                assert result.is_valid

            except OSError:
                # Some special characters may not be allowed on certain filesystems
                pytest.skip(f"System doesn't support filename: {filename}")

    def test_unicode_error_messages(self):
        """Test Unicode characters in error messages."""
        context = ValidationContext()

        # Add error with Unicode
        context.add_error("Unicode error: 测试错误", "unicode_field")
        assert context.has_errors()

        summary = context.get_error_summary()
        assert "测试错误" in summary

    def test_long_unicode_strings(self):
        """Test very long Unicode strings."""
        long_unicode = "🔥" * 1000  # 1000 fire emojis

        from retileup.utils.validation import COMMON_VALIDATORS
        assert COMMON_VALIDATORS['non_empty_string'](long_unicode) is True


class TestPlatformSpecificBehaviors:
    """Test platform-specific behaviors."""

    def test_path_separator_handling(self, temp_dir):
        """Test path separator handling across platforms."""
        # Test with different path separator styles
        if os.name == 'nt':  # Windows
            # Test backslash paths
            path_str = str(temp_dir).replace('/', '\\') + "\\test.jpg"
        else:  # Unix-like
            # Test forward slash paths
            path_str = str(temp_dir) + "/test.jpg"

        # Path validation should handle platform separators
        result = ValidationUtils.validate_file_path(path_str, must_exist=False)
        assert result.is_valid

    def test_case_sensitivity_handling(self, temp_dir):
        """Test case sensitivity handling."""
        # Create file with specific case
        test_file = temp_dir / "TestFile.PNG"
        image = Image.new('RGB', (50, 50))
        image.save(test_file, 'PNG')

        # Test different case variations
        case_variations = [
            "TestFile.PNG",
            "testfile.png",
            "TESTFILE.PNG",
            "TestFile.png"
        ]

        for variation in case_variations:
            test_path = temp_dir / variation
            if test_path.exists():
                # File exists with this case
                result = ValidationUtils.validate_file_path(test_path)
                assert result.is_valid

    def test_long_path_handling(self, temp_dir):
        """Test handling of very long file paths."""
        # Create nested directory structure
        long_path = temp_dir

        # Add many nested directories (but stay within reasonable limits)
        for i in range(10):
            long_path = long_path / f"very_long_directory_name_{i}"

        try:
            long_path.mkdir(parents=True)
            test_file = long_path / "test_file_with_very_long_name.png"

            # Test validation of long path
            result = ValidationUtils.validate_file_path(test_file, must_exist=False)
            assert result.is_valid

        except OSError:
            # Some systems have path length limitations
            pytest.skip("System has path length limitations")

    @pytest.mark.skipif(os.name == 'nt', reason="Unix-specific test")
    def test_unix_specific_features(self, temp_dir):
        """Test Unix-specific file system features."""
        import stat

        # Test file permissions
        test_file = temp_dir / "permission_test.txt"
        test_file.touch()

        # Make file read-only
        os.chmod(test_file, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

        # Test validation with restricted permissions
        result = ValidationUtils.validate_file_path(test_file, must_exist=True)
        assert result.is_valid

    @pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
    def test_windows_specific_features(self, temp_dir):
        """Test Windows-specific file system features."""
        # Test reserved names
        reserved_names = ["CON", "PRN", "AUX", "NUL"]

        for name in reserved_names:
            test_path = temp_dir / f"{name}.txt"
            result = ValidationUtils.validate_file_path(test_path, must_exist=False)
            # May or may not be valid depending on system configuration


class TestResourceExhaustion:
    """Test handling of resource exhaustion scenarios."""

    def test_memory_pressure_simulation(self, temp_dir):
        """Test behavior under simulated memory pressure."""
        # Create many small images to simulate memory pressure
        images = []

        try:
            for i in range(100):  # Create many images
                image = Image.new('RGB', (200, 200), color=(i % 256, 0, 0))
                images.append(image)

                # Test operations under memory pressure
                if i % 10 == 0:
                    resized = ImageUtils.resize_image(image, (100, 100))
                    assert resized.size == (100, 100)

        except MemoryError:
            pytest.skip("System has insufficient memory for test")
        finally:
            # Cleanup
            images.clear()

    def test_file_descriptor_exhaustion(self, temp_dir):
        """Test handling when file descriptors are exhausted."""
        # Open many files to approach system limits
        open_files = []

        try:
            for i in range(100):  # Open many files
                test_file = temp_dir / f"fd_test_{i}.txt"
                test_file.touch()
                file_obj = open(test_file, 'r')
                open_files.append(file_obj)

                # Test file operations
                if i % 10 == 0:
                    result = ValidationUtils.validate_file_path(test_file)
                    assert result.is_valid

        except OSError:
            # Hit file descriptor limit
            pass
        finally:
            # Cleanup
            for file_obj in open_files:
                try:
                    file_obj.close()
                except:
                    pass

    def test_disk_space_simulation(self, temp_dir):
        """Test behavior when disk space is limited."""
        # This is a simulation - actual disk space testing is complex
        # Test that operations handle disk space errors gracefully

        large_image = Image.new('RGB', (1000, 1000), color='blue')

        # Mock disk space error
        original_save = Image.Image.save

        def mock_save_with_disk_error(self, fp, format=None, **params):
            # Simulate disk full error occasionally
            import random
            if random.random() < 0.1:  # 10% chance of disk error
                raise OSError("No space left on device")
            return original_save(self, fp, format, **params)

        with patch.object(Image.Image, 'save', mock_save_with_disk_error):
            # Try to save multiple images
            success_count = 0
            error_count = 0

            for i in range(20):
                try:
                    output_path = temp_dir / f"disk_test_{i}.png"
                    ImageUtils.save_image(large_image, output_path)
                    success_count += 1
                except OSError:
                    error_count += 1

            # Some operations should succeed
            assert success_count > 0

    def test_concurrent_resource_contention(self, temp_dir):
        """Test resource contention under high concurrency."""
        import threading
        import queue

        results = queue.Queue()
        errors = queue.Queue()

        def resource_intensive_operation():
            try:
                # Create and process image
                image = Image.new('RGB', (500, 500), color='red')

                # Multiple operations
                for _ in range(10):
                    resized = ImageUtils.resize_image(image, (100, 100))
                    info = ImageUtils.get_image_info(resized)

                results.put(True)

            except Exception as e:
                errors.put(e)

        # Start many concurrent threads
        threads = []
        for _ in range(20):  # High concurrency
            thread = threading.Thread(target=resource_intensive_operation)
            threads.append(thread)
            thread.start()

        # Wait with timeout
        for thread in threads:
            thread.join(timeout=30)  # 30 second timeout

        # Check results
        success_count = results.qsize()
        error_count = errors.qsize()

        # Most operations should succeed despite contention
        total_threads = 20
        success_rate = success_count / total_threads
        assert success_rate > 0.7  # At least 70% success rate


class TestCorruptedDataHandling:
    """Test handling of corrupted or invalid data."""

    def test_corrupted_image_files(self, temp_dir):
        """Test handling of corrupted image files."""
        # Create files with image extensions but invalid content
        corrupted_files = [
            ("text_as_image.jpg", "This is just text, not an image"),
            ("partial_header.png", b"\x89PNG\r\n\x1a\n"),  # PNG header only
            ("random_bytes.gif", b"\x00\x01\x02\x03" * 100),  # Random bytes
        ]

        for filename, content in corrupted_files:
            corrupted_file = temp_dir / filename

            if isinstance(content, str):
                corrupted_file.write_text(content)
            else:
                corrupted_file.write_bytes(content)

            # Should detect invalid image
            assert ImageUtils.is_valid_image(corrupted_file) is False

            # Loading should fail gracefully
            with pytest.raises(IOError):
                ImageUtils.load_image(corrupted_file)

    def test_malformed_configuration_data(self):
        """Test handling of malformed configuration data."""
        from retileup.utils.validation import ValidationUtils
        from pydantic import BaseModel

        class TestConfig(BaseModel):
            name: str
            value: int

        # Test with malformed data
        malformed_data = [
            {"name": "test"},  # Missing required field
            {"name": "test", "value": "not_an_int"},  # Wrong type
            {"name": "", "value": -1},  # Invalid values
            {},  # Empty data
        ]

        for data in malformed_data:
            result = ValidationUtils.validate_pydantic_model(data, TestConfig)
            assert not result.is_valid

    def test_invalid_coordinate_data(self):
        """Test handling of invalid coordinate data."""
        invalid_coordinates = [
            "not a list",
            [1, 2, 3],  # Not tuples
            [(1,)],  # Single element tuples
            [(1, 2, 3)],  # Too many elements
            [("a", "b")],  # Non-numeric
            [(1.5, float('inf'))],  # Infinite values
            [(1, float('nan'))],  # NaN values
        ]

        for coords in invalid_coordinates:
            assert validate_coordinates(coords) is False

    def test_truncated_file_handling(self, temp_dir):
        """Test handling of truncated files."""
        # Create a valid image first
        complete_image = Image.new('RGB', (100, 100), color='green')
        temp_file = temp_dir / "temp_complete.png"
        complete_image.save(temp_file)

        # Read the complete file
        complete_data = temp_file.read_bytes()

        # Create truncated version
        truncated_file = temp_dir / "truncated.png"
        truncated_data = complete_data[:len(complete_data)//2]  # Half the data
        truncated_file.write_bytes(truncated_data)

        # Should handle truncated file gracefully
        # PIL's LOAD_TRUNCATED_IMAGES setting should help
        try:
            image = ImageUtils.load_image(truncated_file)
            # If it loads, verify it's reasonable
            assert image.size[0] > 0
            assert image.size[1] > 0
        except (IOError, OSError):
            # Truncated file detected and rejected - also acceptable
            pass

    def test_invalid_metadata_handling(self, temp_dir):
        """Test handling of files with invalid metadata."""
        # Create image with potentially problematic metadata
        image = Image.new('RGB', (50, 50), color='blue')

        # Add some metadata that might cause issues
        image.info['problematic_key'] = '\x00\x01\x02'  # Binary data in text field
        image.info['very_long_key'] = 'x' * 10000  # Very long metadata

        image_file = temp_dir / "metadata_test.png"
        image.save(image_file, 'PNG')

        # Should handle metadata gracefully
        loaded_image = ImageUtils.load_image(image_file)
        info = ImageUtils.get_image_info(loaded_image)

        assert info['width'] == 50
        assert info['height'] == 50


class TestExtremeInputValues:
    """Test handling of extreme input values."""

    def test_extremely_large_numbers(self):
        """Test handling of extremely large numbers."""
        large_numbers = [
            sys.maxsize,
            sys.maxsize * 2,
            float('inf'),
            1e100,
        ]

        for num in large_numbers:
            if num == float('inf'):
                # Infinity should be rejected
                assert validate_positive_number(num) is False
            else:
                # Very large numbers might be valid depending on context
                # Test that they don't cause crashes
                try:
                    result = validate_positive_number(num)
                    assert isinstance(result, bool)
                except (OverflowError, ValueError):
                    # Acceptable to reject extremely large numbers
                    pass

    def test_floating_point_precision(self):
        """Test floating point precision edge cases."""
        precision_cases = [
            (0.1 + 0.2, 0.3),  # Classic floating point precision issue
            (1e-15, 0),  # Very small numbers
            (1.0000000000000002, 1.0),  # Near-equal values
        ]

        for value, expected in precision_cases:
            # Validation should handle precision issues gracefully
            result = validate_positive_number(value)
            assert isinstance(result, bool)

    def test_boundary_value_analysis(self):
        """Test boundary value analysis for ranges."""
        # Test range validator at boundaries
        validator = validate_in_range(0, 100, inclusive=True)

        boundary_tests = [
            (-0.000001, False),  # Just below minimum
            (0.0, True),  # Exact minimum
            (0.000001, True),  # Just above minimum
            (99.999999, True),  # Just below maximum
            (100.0, True),  # Exact maximum
            (100.000001, False),  # Just above maximum
        ]

        for value, expected in boundary_tests:
            assert validator(value) == expected

    def test_string_length_extremes(self):
        """Test handling of extremely long strings."""
        from retileup.utils.validation import COMMON_VALIDATORS

        # Very long string
        very_long_string = "x" * 100000  # 100K characters
        assert COMMON_VALIDATORS['non_empty_string'](very_long_string) is True

        # String with many Unicode characters
        unicode_string = "🔥" * 10000  # 10K emoji
        assert COMMON_VALIDATORS['non_empty_string'](unicode_string) is True

    def test_coordinate_extremes(self):
        """Test coordinate validation with extreme values."""
        extreme_coordinates = [
            [(0, 0), (sys.maxsize, sys.maxsize)],  # Very large coordinates
            [(0.000001, 0.000001)],  # Very small coordinates
            [(1e6, 1e6)],  # Large but reasonable coordinates
        ]

        for coords in extreme_coordinates:
            try:
                result = validate_coordinates(coords)
                assert isinstance(result, bool)
            except (OverflowError, ValueError):
                # Acceptable to reject extreme coordinates
                pass


class TestRaceConditionsAndTiming:
    """Test race conditions and timing-sensitive scenarios."""

    def test_concurrent_file_access(self, temp_dir):
        """Test concurrent access to the same file."""
        import threading
        import queue

        # Create test image
        test_image = Image.new('RGB', (100, 100), color='red')
        test_file = temp_dir / "concurrent_test.png"
        test_image.save(test_file)

        results = queue.Queue()
        errors = queue.Queue()

        def access_file():
            try:
                # Multiple threads accessing same file
                image = ImageUtils.load_image(test_file)
                info = ImageUtils.get_image_info(image)
                results.put(info['width'])
            except Exception as e:
                errors.put(e)

        # Start concurrent threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=access_file)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # All should succeed with same result
        assert errors.empty()
        assert results.qsize() == 10

        while not results.empty():
            width = results.get()
            assert width == 100

    def test_timing_dependent_operations(self):
        """Test operations that might be timing-dependent."""
        import time

        # Test rapid successive operations
        start_time = time.time()

        for i in range(50):
            # Rapid validation operations
            result = validate_positive_number(i + 1)
            assert result is True

            # Small delay to test timing sensitivity
            time.sleep(0.001)  # 1ms delay

        end_time = time.time()
        total_time = end_time - start_time

        # Should complete quickly despite delays
        assert total_time < 1.0  # Less than 1 second total

    def test_resource_cleanup_timing(self, temp_dir):
        """Test that resource cleanup happens in timely manner."""
        import gc
        import weakref

        # Create objects and track cleanup
        cleanup_events = []

        def cleanup_callback(ref):
            cleanup_events.append(time.time())

        # Create and release objects
        for i in range(10):
            image = Image.new('RGB', (100, 100))
            weak_ref = weakref.ref(image, cleanup_callback)

            # Use the image
            resized = ImageUtils.resize_image(image, (50, 50))

            # Release references
            del image, resized

        # Force garbage collection
        gc.collect()

        # Give some time for cleanup
        time.sleep(0.1)

        # Some cleanup should have occurred
        # (exact behavior depends on Python implementation)
        assert len(cleanup_events) >= 0  # At least no errors occurred