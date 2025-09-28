"""Pytest configuration and fixtures for ReTileUp tests."""

import asyncio
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Dict, Generator, List, Optional, Any
from unittest.mock import MagicMock, Mock

import pytest
import pytest_mock
from PIL import Image, ImageDraw

from retileup.core.config import Config
from retileup.core.registry import ToolRegistry, reset_global_registry
from retileup.core.workflow import Workflow
from retileup.core.exceptions import RetileupError, ValidationError
from retileup.tools.base import BaseTool, ToolConfig, ToolResult
from retileup.tools.tiling import TilingTool, TilingConfig
from retileup.utils.image import ImageUtils
from retileup.utils.validation import ValidationUtils


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_image() -> Image.Image:
    """Create a sample image for testing."""
    return Image.new('RGB', (100, 100), color='red')


@pytest.fixture
def sample_rgba_image() -> Image.Image:
    """Create a sample RGBA image for testing."""
    return Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))


@pytest.fixture
def sample_grayscale_image() -> Image.Image:
    """Create a sample grayscale image for testing."""
    return Image.new('L', (100, 100), color=128)


@pytest.fixture
def sample_image_file(temp_dir: Path, sample_image: Image.Image) -> Path:
    """Create a sample image file for testing."""
    image_path = temp_dir / "sample.png"
    sample_image.save(image_path)
    return image_path


@pytest.fixture
def sample_jpeg_file(temp_dir: Path, sample_image: Image.Image) -> Path:
    """Create a sample JPEG image file for testing."""
    image_path = temp_dir / "sample.jpg"
    sample_image.save(image_path, "JPEG")
    return image_path


@pytest.fixture
def multiple_image_files(temp_dir: Path) -> list[Path]:
    """Create multiple sample image files for testing."""
    files = []
    for i, color in enumerate(['red', 'green', 'blue']):
        image = Image.new('RGB', (50, 50), color=color)
        image_path = temp_dir / f"image_{i}.png"
        image.save(image_path)
        files.append(image_path)
    return files


@pytest.fixture
def config() -> Config:
    """Create a test configuration."""
    return Config()


@pytest.fixture
def tool_registry() -> ToolRegistry:
    """Create a test tool registry."""
    return ToolRegistry()


@pytest.fixture
def sample_workflow() -> Workflow:
    """Create a sample workflow for testing."""
    workflow = Workflow(
        name="test_workflow",
        description="A test workflow"
    )

    workflow.add_step(
        name="step1",
        tool_name="test_tool",
        parameters={"param1": "value1"}
    )

    workflow.add_step(
        name="step2",
        tool_name="test_tool2",
        parameters={"param2": "value2"}
    )

    return workflow


@pytest.fixture
def config_file(temp_dir: Path) -> Path:
    """Create a sample configuration file."""
    config_content = """
version: "1.0.0"
debug: false

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

performance:
  max_workers: 2
  chunk_size: 512

output:
  directory: "test_outputs"
  format: "PNG"
  quality: 90
  overwrite: true

tool_configs:
  test_tool:
    param1: "default_value"
    param2: 42
"""

    config_path = temp_dir / "config.yaml"
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def workflow_file(temp_dir: Path) -> Path:
    """Create a sample workflow file."""
    workflow_content = """
name: "test_workflow"
version: "1.0.0"
description: "A test workflow for unit tests"

steps:
  - name: "resize"
    tool_name: "resize_tool"
    description: "Resize the image"
    parameters:
      width: 200
      height: 200
    enabled: true

  - name: "convert"
    tool_name: "format_converter"
    description: "Convert image format"
    parameters:
      format: "JPEG"
      quality: 85
    enabled: true

global_parameters:
  output_dir: "/tmp/test_output"

parallel_execution: false
stop_on_error: true
"""

    workflow_path = temp_dir / "workflow.yaml"
    workflow_path.write_text(workflow_content)
    return workflow_path


@pytest.fixture
def invalid_image_file(temp_dir: Path) -> Path:
    """Create an invalid image file for testing error handling."""
    invalid_path = temp_dir / "invalid.png"
    invalid_path.write_text("This is not an image file")
    return invalid_path


@pytest.fixture
def empty_directory(temp_dir: Path) -> Path:
    """Create an empty directory for testing."""
    empty_dir = temp_dir / "empty"
    empty_dir.mkdir()
    return empty_dir


# Markers for different test categories
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (may take longer to run)"
    )
    config.addinivalue_line(
        "markers", "requires_network: marks tests that require network access"
    )


# Test data
@pytest.fixture
def sample_tool_metadata():
    """Sample tool metadata for testing."""
    return {
        "name": "test_tool",
        "version": "1.0.0",
        "description": "A test tool",
        "author": "Test Author",
        "tags": ["test", "sample"],
        "input_formats": ["PNG", "JPEG"],
        "output_formats": ["PNG", "JPEG", "BMP"]
    }


@pytest.fixture
def sample_step_data():
    """Sample step data for testing."""
    return {
        "name": "test_step",
        "tool_name": "test_tool",
        "description": "A test step",
        "parameters": {
            "width": 100,
            "height": 100,
            "quality": 95
        },
        "enabled": True,
        "tags": ["resize", "test"]
    }


@pytest.fixture
def sample_workflow_data():
    """Sample workflow data for testing."""
    return {
        "name": "test_workflow",
        "version": "1.0.0",
        "description": "A comprehensive test workflow",
        "steps": [
            {
                "name": "resize",
                "tool_name": "resize_tool",
                "parameters": {"width": 200, "height": 200}
            },
            {
                "name": "convert",
                "tool_name": "convert_tool",
                "parameters": {"format": "JPEG"}
            }
        ],
        "parallel_execution": False,
        "stop_on_error": True,
        "global_parameters": {
            "quality": 90,
            "output_dir": "/tmp/test"
        }
    }


# Environment setup
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment variables."""
    # Set test-specific environment variables
    monkeypatch.setenv("RETILEUP_DEBUG", "true")
    monkeypatch.setenv("RETILEUP_LOG_LEVEL", "DEBUG")

    # Clear any existing configuration that might interfere
    monkeypatch.delenv("RETILEUP_CONFIG_FILE", raising=False)


# Database/Storage fixtures (for future use)
@pytest.fixture
def mock_storage(temp_dir: Path):
    """Mock storage backend for testing."""
    storage_dir = temp_dir / "storage"
    storage_dir.mkdir()
    return storage_dir


# Performance testing fixtures
@pytest.fixture
def large_image() -> Image.Image:
    """Create a large image for performance testing."""
    return Image.new('RGB', (2000, 2000), color='blue')


@pytest.fixture
def very_large_image() -> Image.Image:
    """Create a very large image for stress testing."""
    return Image.new('RGB', (4000, 4000), color='cyan')


@pytest.fixture
def benchmark_images() -> List[Image.Image]:
    """Create a set of images for benchmarking."""
    images = []
    sizes = [(100, 100), (500, 500), (1000, 1000), (2000, 2000)]
    colors = ['red', 'green', 'blue', 'yellow']

    for size, color in zip(sizes, colors):
        images.append(Image.new('RGB', size, color=color))

    return images


@pytest.fixture
def complex_image() -> Image.Image:
    """Create a complex image with patterns for testing."""
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)

    # Draw some patterns
    for i in range(0, 800, 50):
        draw.line([(i, 0), (i, 600)], fill='lightgray', width=1)
    for i in range(0, 600, 50):
        draw.line([(0, i), (800, i)], fill='lightgray', width=1)

    # Add some shapes
    draw.rectangle([100, 100, 200, 200], fill='red', outline='black')
    draw.ellipse([300, 150, 450, 300], fill='blue', outline='black')
    draw.polygon([(600, 100), (700, 100), (650, 200)], fill='green', outline='black')

    return img


@pytest.fixture
def sample_image_with_alpha() -> Image.Image:
    """Create a sample image with alpha channel."""
    img = Image.new('RGBA', (200, 200), color=(255, 0, 0, 128))
    draw = ImageDraw.Draw(img)
    draw.ellipse([50, 50, 150, 150], fill=(0, 255, 0, 200), outline=(0, 0, 255, 255))
    return img


# Test data and mock fixtures
@pytest.fixture
def sample_coordinates() -> List[tuple]:
    """Sample coordinates for tiling tests."""
    return [(0, 0), (100, 100), (200, 200), (50, 50)]


@pytest.fixture
def invalid_coordinates() -> List:
    """Invalid coordinates for error testing."""
    return [
        (-1, 0),  # Negative x
        (0, -1),  # Negative y
        ("a", 0),  # Non-numeric x
        (0, "b"),  # Non-numeric y
        (0,),     # Incomplete tuple
        (0, 1, 2) # Too many values
    ]


@pytest.fixture
def sample_tiling_config(temp_dir: Path, sample_image_file: Path) -> TilingConfig:
    """Create a sample tiling configuration."""
    return TilingConfig(
        input_path=sample_image_file,
        output_dir=temp_dir,
        tile_width=50,
        tile_height=50,
        coordinates=[(0, 0), (25, 25)],
        output_pattern="{base}_{x}_{y}.{ext}"
    )


@pytest.fixture
def mock_tool() -> BaseTool:
    """Create a mock tool for testing."""
    class MockTool(BaseTool):
        @property
        def name(self) -> str:
            return "mock_tool"

        @property
        def description(self) -> str:
            return "A mock tool for testing"

        @property
        def version(self) -> str:
            return "1.0.0"

        def get_config_schema(self):
            return ToolConfig

        def validate_config(self, config: ToolConfig) -> List[str]:
            return []

        def execute(self, config: ToolConfig) -> ToolResult:
            return ToolResult(
                success=True,
                message="Mock execution successful",
                output_files=[],
                metadata={"mock": True}
            )

    return MockTool()


@pytest.fixture
def failing_mock_tool() -> BaseTool:
    """Create a mock tool that fails for error testing."""
    class FailingMockTool(BaseTool):
        @property
        def name(self) -> str:
            return "failing_tool"

        @property
        def description(self) -> str:
            return "A tool that always fails"

        @property
        def version(self) -> str:
            return "1.0.0"

        def get_config_schema(self):
            return ToolConfig

        def validate_config(self, config: ToolConfig) -> List[str]:
            return ["This tool always fails validation"]

        def execute(self, config: ToolConfig) -> ToolResult:
            raise RuntimeError("This tool always fails")

    return FailingMockTool()


@pytest.fixture
def memory_monitor():
    """Monitor memory usage during tests."""
    import psutil
    import threading

    class MemoryMonitor:
        def __init__(self):
            self.peak_memory = 0
            self.current_memory = 0
            self.monitoring = False
            self.process = psutil.Process()

        def start(self):
            self.monitoring = True
            self.peak_memory = 0
            threading.Thread(target=self._monitor_loop, daemon=True).start()

        def stop(self):
            self.monitoring = False
            return self.peak_memory

        def _monitor_loop(self):
            while self.monitoring:
                self.current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
                self.peak_memory = max(self.peak_memory, self.current_memory)
                time.sleep(0.1)

    return MemoryMonitor()


@pytest.fixture
def performance_timer():
    """Timer for performance testing."""
    class PerformanceTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.perf_counter()

        def stop(self):
            self.end_time = time.perf_counter()
            return self.end_time - self.start_time

        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

    return PerformanceTimer()


# File system and data fixtures
@pytest.fixture
def corrupted_image_file(temp_dir: Path) -> Path:
    """Create a corrupted image file for error testing."""
    corrupted_path = temp_dir / "corrupted.jpg"
    # Write invalid JPEG data
    with open(corrupted_path, 'wb') as f:
        f.write(b'\xff\xd8\xff\xe0' + b'\x00' * 100)  # Invalid JPEG header + garbage
    return corrupted_path


@pytest.fixture
def huge_image_files(temp_dir: Path) -> List[Path]:
    """Create several large image files for stress testing."""
    files = []
    sizes = [(1000, 1000), (2000, 1500), (1500, 2000)]

    for i, (width, height) in enumerate(sizes):
        img = Image.new('RGB', (width, height), color=f'C{i}')
        path = temp_dir / f"huge_{i}.png"
        img.save(path)
        files.append(path)

    return files


@pytest.fixture
def mixed_format_images(temp_dir: Path) -> Dict[str, Path]:
    """Create images in different formats."""
    base_img = Image.new('RGB', (100, 100), color='purple')
    formats = {
        'png': (base_img, 'PNG'),
        'jpg': (base_img, 'JPEG'),
        'bmp': (base_img, 'BMP'),
        'tiff': (base_img.convert('RGB'), 'TIFF'),
        'webp': (base_img, 'WEBP')
    }

    files = {}
    for ext, (img, format_name) in formats.items():
        path = temp_dir / f"test.{ext}"
        try:
            img.save(path, format=format_name)
            files[ext] = path
        except Exception:
            # Skip formats that aren't supported
            pass

    return files


@pytest.fixture
def temp_output_dir(temp_dir: Path) -> Path:
    """Create a temporary output directory with proper cleanup."""
    output_dir = temp_dir / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir


# CLI and integration test fixtures
@pytest.fixture
def cli_runner():
    """Create a Typer CLI test runner."""
    from typer.testing import CliRunner
    return CliRunner()


@pytest.fixture
def isolated_filesystem(temp_dir: Path):
    """Provide an isolated filesystem for tests."""
    original_cwd = os.getcwd()
    try:
        os.chdir(temp_dir)
        yield temp_dir
    finally:
        os.chdir(original_cwd)


# Registry and tool management fixtures
@pytest.fixture(autouse=True)
def clean_registry():
    """Clean the global registry before and after each test."""
    reset_global_registry()
    yield
    reset_global_registry()


@pytest.fixture
def populated_registry() -> ToolRegistry:
    """Create a registry with sample tools."""
    registry = ToolRegistry()

    # Register the tiling tool
    registry.register_tool(TilingTool)

    return registry


# Configuration test fixtures
@pytest.fixture
def minimal_config() -> Dict[str, Any]:
    """Minimal valid configuration."""
    return {
        "version": "1.0.0",
        "debug": False
    }


@pytest.fixture
def complex_config() -> Dict[str, Any]:
    """Complex configuration for testing."""
    return {
        "version": "1.0.0",
        "debug": True,
        "logging": {
            "level": "DEBUG",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": "retileup.log"
        },
        "performance": {
            "max_workers": 4,
            "chunk_size": 1024,
            "memory_limit": "1GB"
        },
        "output": {
            "directory": "output",
            "format": "PNG",
            "quality": 95,
            "overwrite": False,
            "compression": "lossless"
        },
        "tool_configs": {
            "tiling": {
                "default_tile_size": [256, 256],
                "overlap": 10,
                "maintain_aspect": True
            }
        }
    }


# Error simulation fixtures
@pytest.fixture
def error_scenarios():
    """Common error scenarios for testing."""
    return {
        "file_not_found": FileNotFoundError("Test file not found"),
        "permission_denied": PermissionError("Permission denied"),
        "invalid_image": IOError("Invalid image format"),
        "memory_error": MemoryError("Out of memory"),
        "validation_error": ValidationError("Validation failed"),
        "processing_error": RetileupError("Processing failed")
    }


# Network and resource simulation fixtures
@pytest.fixture
def mock_network_conditions():
    """Mock different network conditions for testing."""
    return {
        "normal": {"delay": 0.1, "success_rate": 1.0},
        "slow": {"delay": 2.0, "success_rate": 1.0},
        "unreliable": {"delay": 0.5, "success_rate": 0.7},
        "offline": {"delay": 0, "success_rate": 0.0}
    }


# Cross-platform compatibility fixtures
@pytest.fixture
def platform_paths():
    """Platform-specific path scenarios."""
    return {
        "windows": r"C:\Users\test\images\file.jpg",
        "unix": "/home/test/images/file.jpg",
        "relative": "./images/file.jpg",
        "with_spaces": "path with spaces/file name.jpg",
        "unicode": "测试/файл.jpg",
        "long_path": "/" + "/".join(["very_long_directory_name"] * 20) + "/file.jpg"
    }


# Database/storage mocking
@pytest.fixture
def mock_database(temp_dir: Path):
    """Mock database for testing workflow persistence."""
    db_file = temp_dir / "test.db"

    class MockDatabase:
        def __init__(self, path):
            self.path = path
            self.data = {}

        def save(self, key, value):
            self.data[key] = value

        def load(self, key, default=None):
            return self.data.get(key, default)

        def delete(self, key):
            return self.data.pop(key, None)

        def list_keys(self):
            return list(self.data.keys())

        def clear(self):
            self.data.clear()

    return MockDatabase(db_file)