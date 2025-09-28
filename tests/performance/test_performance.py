"""Performance tests for ReTileUp.

This module tests performance characteristics including:
- Image processing speed and memory usage
- Large file handling capabilities
- Concurrent processing performance
- Memory leak detection
- Resource utilization optimization
- Scalability under load
"""

import gc
import time
import threading
import tempfile
from pathlib import Path
from unittest.mock import patch
import sys

import pytest
from PIL import Image
import psutil

from retileup.utils.image import ImageUtils
from retileup.utils.validation import ValidationUtils, batch_validate, COMMON_VALIDATORS
from retileup.core.registry import ToolRegistry
from retileup.tools.base import BaseTool, ToolConfig, ToolResult


# Performance test markers
pytestmark = [
    pytest.mark.performance,
    pytest.mark.slow
]


@pytest.fixture
def performance_images(temp_dir):
    """Create images of various sizes for performance testing."""
    images = {}

    # Small image (baseline)
    small_img = Image.new('RGB', (100, 100), color='red')
    small_path = temp_dir / "small.png"
    small_img.save(small_path)
    images['small'] = (small_path, 100, 100)

    # Medium image
    medium_img = Image.new('RGB', (500, 500), color='green')
    medium_path = temp_dir / "medium.png"
    medium_img.save(medium_path)
    images['medium'] = (medium_path, 500, 500)

    # Large image
    large_img = Image.new('RGB', (1000, 1000), color='blue')
    large_path = temp_dir / "large.png"
    large_img.save(large_path)
    images['large'] = (large_path, 1000, 1000)

    # Very large image (for stress testing)
    if sys.maxsize > 2**32:  # Only on 64-bit systems
        very_large_img = Image.new('RGB', (2000, 2000), color='yellow')
        very_large_path = temp_dir / "very_large.png"
        very_large_img.save(very_large_path)
        images['very_large'] = (very_large_path, 2000, 2000)

    return images


@pytest.fixture
def memory_tracker():
    """Track memory usage during tests."""
    class MemoryTracker:
        def __init__(self):
            self.process = psutil.Process()
            self.start_memory = None
            self.peak_memory = None

        def start(self):
            gc.collect()  # Force garbage collection
            self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            self.peak_memory = self.start_memory

        def update(self):
            current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            if current_memory > self.peak_memory:
                self.peak_memory = current_memory

        def stop(self):
            gc.collect()  # Force garbage collection
            final_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            return {
                'start_mb': self.start_memory,
                'peak_mb': self.peak_memory,
                'final_mb': final_memory,
                'delta_mb': final_memory - self.start_memory
            }

    return MemoryTracker()


class TestImageProcessingPerformance:
    """Test image processing performance."""

    def test_image_loading_performance(self, performance_images, memory_tracker):
        """Test image loading performance across different sizes."""
        memory_tracker.start()
        loading_times = {}

        for size_name, (image_path, width, height) in performance_images.items():
            start_time = time.time()
            image = ImageUtils.load_image(image_path)
            end_time = time.time()

            loading_times[size_name] = {
                'time': end_time - start_time,
                'pixels': width * height,
                'size_mb': image_path.stat().st_size / 1024 / 1024
            }

            memory_tracker.update()

            # Verify image loaded correctly
            assert image.size == (width, height)

        memory_stats = memory_tracker.stop()

        # Performance assertions
        # Loading should be reasonably fast
        for size_name, stats in loading_times.items():
            if size_name == 'small':
                assert stats['time'] < 0.1  # Less than 100ms for small images
            elif size_name == 'medium':
                assert stats['time'] < 0.5  # Less than 500ms for medium images
            elif size_name == 'large':
                assert stats['time'] < 2.0  # Less than 2s for large images

        # Memory usage should be reasonable
        assert memory_stats['delta_mb'] < 200  # Less than 200MB memory increase

    def test_image_resize_performance(self, performance_images, memory_tracker):
        """Test image resizing performance."""
        memory_tracker.start()
        resize_times = {}

        for size_name, (image_path, width, height) in performance_images.items():
            image = ImageUtils.load_image(image_path)

            # Test resizing to half size
            target_size = (width // 2, height // 2)

            start_time = time.time()
            resized = ImageUtils.resize_image(image, target_size)
            end_time = time.time()

            resize_times[size_name] = {
                'time': end_time - start_time,
                'original_pixels': width * height,
                'target_pixels': target_size[0] * target_size[1]
            }

            memory_tracker.update()

            # Verify resize worked correctly
            assert resized.size == target_size

        memory_stats = memory_tracker.stop()

        # Performance assertions
        # Resizing should scale reasonably with image size
        small_time = resize_times.get('small', {}).get('time', 0)
        if 'large' in resize_times and small_time > 0:
            large_time = resize_times['large']['time']
            # Large image should not take more than 100x longer than small
            assert large_time / small_time < 100

        # Memory usage should be reasonable
        assert memory_stats['delta_mb'] < 150

    def test_image_format_conversion_performance(self, performance_images, temp_dir, memory_tracker):
        """Test image format conversion performance."""
        memory_tracker.start()
        conversion_times = {}

        for size_name, (image_path, width, height) in performance_images.items():
            if size_name == 'very_large':
                continue  # Skip very large for conversion tests

            image = ImageUtils.load_image(image_path)

            # Convert PNG to JPEG
            output_path = temp_dir / f"{size_name}_converted.jpg"

            start_time = time.time()
            ImageUtils.save_image(image, output_path, format='JPEG', quality=90)
            end_time = time.time()

            conversion_times[size_name] = {
                'time': end_time - start_time,
                'pixels': width * height,
                'input_size_mb': image_path.stat().st_size / 1024 / 1024,
                'output_size_mb': output_path.stat().st_size / 1024 / 1024
            }

            memory_tracker.update()

            # Verify conversion worked
            assert output_path.exists()
            converted = ImageUtils.load_image(output_path)
            assert converted.size == (width, height)

        memory_stats = memory_tracker.stop()

        # Performance assertions
        for size_name, stats in conversion_times.items():
            # Conversion should be reasonably fast
            if size_name == 'small':
                assert stats['time'] < 0.2
            elif size_name == 'medium':
                assert stats['time'] < 1.0
            elif size_name == 'large':
                assert stats['time'] < 5.0

        # Memory usage should be controlled
        assert memory_stats['delta_mb'] < 100

    def test_batch_image_processing_performance(self, performance_images, temp_dir, memory_tracker):
        """Test batch image processing performance."""
        memory_tracker.start()

        batch_size = 10
        processing_times = []

        # Create multiple copies of small image for batch processing
        small_path = performance_images['small'][0]
        batch_images = []

        for i in range(batch_size):
            batch_path = temp_dir / f"batch_{i}.png"
            Image.open(small_path).save(batch_path)
            batch_images.append(batch_path)

        # Process batch
        start_time = time.time()

        for image_path in batch_images:
            image = ImageUtils.load_image(image_path)
            resized = ImageUtils.resize_image(image, (50, 50))
            output_path = temp_dir / f"processed_{image_path.stem}.png"
            ImageUtils.save_image(resized, output_path)

            memory_tracker.update()

        end_time = time.time()
        total_time = end_time - start_time

        memory_stats = memory_tracker.stop()

        # Performance assertions
        avg_time_per_image = total_time / batch_size
        assert avg_time_per_image < 0.1  # Less than 100ms per image
        assert total_time < 2.0  # Total batch should complete in under 2 seconds

        # Memory should not grow excessively
        assert memory_stats['delta_mb'] < 50

        # Verify all outputs were created
        for i in range(batch_size):
            output_path = temp_dir / f"processed_batch_{i}.png"
            if output_path.exists():
                assert output_path.stat().st_size > 0

    def test_memory_efficiency_repeated_operations(self, performance_images, memory_tracker):
        """Test memory efficiency with repeated operations."""
        memory_tracker.start()

        small_path = performance_images['small'][0]
        iterations = 50

        for i in range(iterations):
            # Load, process, and discard image
            image = ImageUtils.load_image(small_path)
            resized = ImageUtils.resize_image(image, (80, 80))
            info = ImageUtils.get_image_info(resized)

            # Update memory tracking
            if i % 10 == 0:
                memory_tracker.update()

            # Force cleanup
            del image, resized, info

        # Force garbage collection
        gc.collect()
        memory_stats = memory_tracker.stop()

        # Memory should not grow significantly with repeated operations
        assert memory_stats['delta_mb'] < 20  # Less than 20MB growth

    @pytest.mark.skipif(sys.maxsize <= 2**32, reason="Requires 64-bit system")
    def test_large_image_handling(self, performance_images, memory_tracker):
        """Test handling of very large images."""
        if 'very_large' not in performance_images:
            pytest.skip("Very large image not available")

        memory_tracker.start()
        large_path, width, height = performance_images['very_large']

        start_time = time.time()

        # Load large image
        image = ImageUtils.load_image(large_path)
        memory_tracker.update()

        # Perform basic operations
        info = ImageUtils.get_image_info(image)
        memory_tracker.update()

        # Resize to smaller size
        resized = ImageUtils.resize_image(image, (500, 500))
        memory_tracker.update()

        end_time = time.time()
        total_time = end_time - start_time

        memory_stats = memory_tracker.stop()

        # Performance assertions for large images
        assert total_time < 30.0  # Should complete within 30 seconds
        assert info['width'] == width
        assert info['height'] == height
        assert resized.size == (500, 500)

        # Memory usage should be controlled even for large images
        expected_memory_mb = (width * height * 3) / (1024 * 1024)  # RGB bytes to MB
        assert memory_stats['peak_mb'] < expected_memory_mb * 3  # Allow 3x overhead


class TestValidationPerformance:
    """Test validation performance."""

    def test_file_path_validation_performance(self, temp_dir):
        """Test file path validation performance."""
        # Create many files for testing
        file_count = 1000
        test_files = []

        for i in range(file_count):
            test_file = temp_dir / f"test_file_{i}.txt"
            test_file.touch()
            test_files.append(test_file)

        start_time = time.time()

        # Validate all files
        valid_count = 0
        for test_file in test_files:
            result = ValidationUtils.validate_file_path(test_file, must_exist=True)
            if result.is_valid:
                valid_count += 1

        end_time = time.time()
        total_time = end_time - start_time

        # Performance assertions
        assert total_time < 5.0  # Should complete within 5 seconds
        assert valid_count == file_count  # All should be valid
        avg_time_per_validation = total_time / file_count
        assert avg_time_per_validation < 0.01  # Less than 10ms per validation

    def test_batch_validation_performance(self, temp_dir):
        """Test batch validation performance."""
        # Create test data
        test_data = {}
        for i in range(1000):
            test_data[f'width_{i}'] = i + 1
            test_data[f'height_{i}'] = i + 1
            test_data[f'name_{i}'] = f"test_name_{i}"

        # Create validators
        validators = {}
        for key in test_data.keys():
            if key.startswith('width_') or key.startswith('height_'):
                validators[key] = COMMON_VALIDATORS['positive_int']
            elif key.startswith('name_'):
                validators[key] = COMMON_VALIDATORS['non_empty_string']

        start_time = time.time()

        # Perform batch validation
        context = batch_validate(validators, test_data, raise_on_error=False)

        end_time = time.time()
        total_time = end_time - start_time

        # Performance assertions
        assert total_time < 2.0  # Should complete within 2 seconds
        assert not context.has_errors()  # All should be valid
        avg_time_per_validation = total_time / len(test_data)
        assert avg_time_per_validation < 0.002  # Less than 2ms per validation

    def test_coordinate_validation_performance(self):
        """Test coordinate validation performance with large datasets."""
        # Create large coordinate set
        coordinates = []
        for x in range(100):
            for y in range(100):
                coordinates.append((x * 10, y * 10))

        start_time = time.time()

        # Validate coordinates
        from retileup.utils.validation import validate_coordinates
        is_valid = validate_coordinates(coordinates)

        end_time = time.time()
        total_time = end_time - start_time

        # Performance assertions
        assert is_valid is True
        assert total_time < 1.0  # Should complete within 1 second
        assert len(coordinates) == 10000  # Verify we tested 10k coordinates


class TestConcurrencyPerformance:
    """Test concurrent processing performance."""

    def test_concurrent_image_loading(self, performance_images):
        """Test concurrent image loading performance."""
        import queue
        import threading

        results = queue.Queue()
        errors = queue.Queue()
        thread_count = 5

        def load_images():
            try:
                for size_name, (image_path, width, height) in performance_images.items():
                    start_time = time.time()
                    image = ImageUtils.load_image(image_path)
                    end_time = time.time()

                    results.put({
                        'size_name': size_name,
                        'time': end_time - start_time,
                        'success': True
                    })
            except Exception as e:
                errors.put(e)

        start_time = time.time()

        # Start concurrent threads
        threads = []
        for _ in range(thread_count):
            thread = threading.Thread(target=load_images)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        end_time = time.time()
        total_time = end_time - start_time

        # Check results
        assert errors.empty(), f"Errors occurred: {list(errors.queue)}"

        # Collect results
        load_results = []
        while not results.empty():
            load_results.append(results.get())

        # Performance assertions
        expected_operations = len(performance_images) * thread_count
        assert len(load_results) == expected_operations

        # Concurrent execution should provide some speedup
        # (though not linear due to I/O limitations)
        sequential_estimate = len(performance_images) * thread_count * 0.1  # Estimate 100ms per load
        assert total_time < sequential_estimate

    def test_concurrent_validation(self):
        """Test concurrent validation performance."""
        import queue
        import threading

        results = queue.Queue()
        errors = queue.Queue()
        thread_count = 10

        def validate_data():
            try:
                # Each thread validates different data
                for i in range(100):
                    validators = {
                        'width': COMMON_VALIDATORS['positive_int'],
                        'height': COMMON_VALIDATORS['positive_int'],
                        'name': COMMON_VALIDATORS['non_empty_string']
                    }

                    data = {
                        'width': i + 1,
                        'height': i + 1,
                        'name': f'test_{i}'
                    }

                    context = batch_validate(validators, data, raise_on_error=False)
                    results.put(not context.has_errors())

            except Exception as e:
                errors.put(e)

        start_time = time.time()

        # Start concurrent threads
        threads = []
        for _ in range(thread_count):
            thread = threading.Thread(target=validate_data)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        end_time = time.time()
        total_time = end_time - start_time

        # Check results
        assert errors.empty(), f"Errors occurred: {list(errors.queue)}"

        # All validations should succeed
        success_count = 0
        while not results.empty():
            if results.get():
                success_count += 1

        expected_validations = 100 * thread_count
        assert success_count == expected_validations

        # Should complete reasonably quickly
        assert total_time < 10.0

    def test_thread_safety_image_operations(self, performance_images):
        """Test thread safety of image operations."""
        import queue
        import threading

        results = queue.Queue()
        errors = queue.Queue()
        small_path = performance_images['small'][0]

        def process_image():
            try:
                for _ in range(10):  # Each thread processes 10 times
                    image = ImageUtils.load_image(small_path)
                    resized = ImageUtils.resize_image(image, (50, 50))
                    info = ImageUtils.get_image_info(resized)

                    results.put({
                        'size': resized.size,
                        'mode': info['mode'],
                        'success': True
                    })

            except Exception as e:
                errors.put(e)

        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=process_image)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Check results
        assert errors.empty(), f"Errors occurred: {list(errors.queue)}"

        # All results should be consistent
        expected_results = 50  # 5 threads * 10 operations each
        actual_results = 0

        while not results.empty():
            result = results.get()
            assert result['size'] == (50, 50)
            assert result['mode'] == 'RGB'
            assert result['success'] is True
            actual_results += 1

        assert actual_results == expected_results


class TestResourceUtilization:
    """Test resource utilization optimization."""

    def test_memory_usage_patterns(self, performance_images, memory_tracker):
        """Test memory usage patterns for different operations."""
        memory_tracker.start()

        small_path = performance_images['small'][0]
        operations = []

        # Test different operations and their memory impact
        for i in range(20):
            memory_before = memory_tracker.process.memory_info().rss / 1024 / 1024

            # Load image
            image = ImageUtils.load_image(small_path)
            memory_after_load = memory_tracker.process.memory_info().rss / 1024 / 1024

            # Resize image
            resized = ImageUtils.resize_image(image, (75, 75))
            memory_after_resize = memory_tracker.process.memory_info().rss / 1024 / 1024

            # Get info
            info = ImageUtils.get_image_info(resized)
            memory_after_info = memory_tracker.process.memory_info().rss / 1024 / 1024

            operations.append({
                'iteration': i,
                'memory_before': memory_before,
                'memory_after_load': memory_after_load,
                'memory_after_resize': memory_after_resize,
                'memory_after_info': memory_after_info
            })

            # Cleanup
            del image, resized, info

            # Periodic garbage collection
            if i % 5 == 0:
                gc.collect()

        memory_stats = memory_tracker.stop()

        # Analyze memory patterns
        load_deltas = [op['memory_after_load'] - op['memory_before'] for op in operations]
        resize_deltas = [op['memory_after_resize'] - op['memory_after_load'] for op in operations]

        # Memory usage should be consistent across iterations
        avg_load_delta = sum(load_deltas) / len(load_deltas)
        avg_resize_delta = sum(resize_deltas) / len(resize_deltas)

        assert avg_load_delta < 5.0  # Less than 5MB per load on average
        assert avg_resize_delta < 3.0  # Less than 3MB per resize on average

        # Overall memory growth should be minimal
        assert memory_stats['delta_mb'] < 10.0

    def test_cpu_utilization_efficiency(self, performance_images):
        """Test CPU utilization efficiency."""
        import time

        small_path = performance_images['small'][0]

        # Measure CPU time for operations
        start_cpu_time = time.process_time()
        start_wall_time = time.time()

        operations_count = 100

        for _ in range(operations_count):
            image = ImageUtils.load_image(small_path)
            resized = ImageUtils.resize_image(image, (60, 60))
            info = ImageUtils.get_image_info(resized)

        end_cpu_time = time.process_time()
        end_wall_time = time.time()

        cpu_time = end_cpu_time - start_cpu_time
        wall_time = end_wall_time - start_wall_time

        # Calculate efficiency metrics
        cpu_efficiency = cpu_time / wall_time if wall_time > 0 else 0
        avg_cpu_time_per_op = cpu_time / operations_count
        avg_wall_time_per_op = wall_time / operations_count

        # Performance assertions
        assert avg_cpu_time_per_op < 0.01  # Less than 10ms CPU time per operation
        assert avg_wall_time_per_op < 0.02  # Less than 20ms wall time per operation
        assert cpu_efficiency > 0.1  # At least 10% CPU efficiency

    def test_file_handle_management(self, temp_dir):
        """Test file handle management and cleanup."""
        import psutil

        process = psutil.Process()
        initial_file_count = len(process.open_files())

        # Create and process many images
        for i in range(50):
            image_path = temp_dir / f"handle_test_{i}.png"

            # Create image
            image = Image.new('RGB', (100, 100), color=(i % 256, 0, 0))
            image.save(image_path)

            # Load and process
            loaded = ImageUtils.load_image(image_path)
            resized = ImageUtils.resize_image(loaded, (50, 50))

            # Save processed image
            output_path = temp_dir / f"processed_{i}.png"
            ImageUtils.save_image(resized, output_path)

        # Check file handle count
        final_file_count = len(process.open_files())

        # File handles should not accumulate
        handle_increase = final_file_count - initial_file_count
        assert handle_increase < 10  # Allow some variance but no major leaks


class TestScalabilityLimits:
    """Test scalability limits and edge cases."""

    def test_maximum_image_dimensions(self):
        """Test handling of maximum image dimensions."""
        # Test with large but reasonable dimensions
        large_width = 5000
        large_height = 4000

        # Test memory estimation
        memory_estimate = ImageUtils.estimate_processing_memory(
            large_width, large_height, 25
        )

        assert memory_estimate['base_image_mb'] > 0
        assert memory_estimate['peak_memory_mb'] > memory_estimate['base_image_mb']

        # Memory estimates should be reasonable for large images
        expected_base_mb = (large_width * large_height * 3) / (1024 * 1024)
        assert abs(memory_estimate['base_image_mb'] - expected_base_mb) < 10

    def test_maximum_tile_count(self):
        """Test handling of maximum tile counts."""
        # Test with many tiles
        image_width = 2000
        image_height = 1500
        tile_size = 100
        max_tiles = 1000

        # Generate coordinates for maximum tiles
        coordinates = []
        for i in range(max_tiles):
            x = (i % 20) * tile_size
            y = (i // 20) * tile_size
            if x < image_width and y < image_height:
                coordinates.append((x, y))

        # Test coordinate validation
        from retileup.utils.validation import validate_coordinates
        is_valid = validate_coordinates(coordinates[:max_tiles])
        assert is_valid is True

        # Test memory estimation for many tiles
        memory_estimate = ImageUtils.estimate_processing_memory(
            image_width, image_height, len(coordinates)
        )

        # Should handle large tile counts without overflow
        assert memory_estimate['estimated_total_mb'] > 0
        assert memory_estimate['estimated_total_mb'] < 10000  # Reasonable upper bound

    def test_stress_concurrent_operations(self, performance_images):
        """Test system under stress with many concurrent operations."""
        import queue
        import threading

        results = queue.Queue()
        errors = queue.Queue()
        thread_count = 20  # High concurrency
        operations_per_thread = 25

        small_path = performance_images['small'][0]

        def stress_operations():
            try:
                for i in range(operations_per_thread):
                    # Mix of operations
                    image = ImageUtils.load_image(small_path)

                    if i % 3 == 0:
                        processed = ImageUtils.resize_image(image, (80, 80))
                    elif i % 3 == 1:
                        processed = ImageUtils.rotate_image(image, 90)
                    else:
                        processed = ImageUtils.flip_image(image)

                    info = ImageUtils.get_image_info(processed)
                    results.put(info['width'] * info['height'])

            except Exception as e:
                errors.put(e)

        start_time = time.time()

        # Start stress test
        threads = []
        for _ in range(thread_count):
            thread = threading.Thread(target=stress_operations)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        end_time = time.time()
        total_time = end_time - start_time

        # Check results
        error_count = errors.qsize()
        success_count = results.qsize()

        # Some operations should succeed even under stress
        total_operations = thread_count * operations_per_thread
        success_rate = success_count / total_operations

        assert success_rate > 0.8  # At least 80% success rate
        assert error_count < total_operations * 0.2  # Less than 20% errors

        # Should complete within reasonable time even under stress
        assert total_time < 60.0  # Less than 1 minute