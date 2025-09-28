"""Unit tests for the Config module."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from retileup.core.config import Config, LoggingConfig, OutputConfig, PerformanceConfig


class TestConfig:
    """Test cases for the Config class."""

    def test_default_config(self):
        """Test default configuration creation."""
        config = Config()

        assert config.version == "1.0.0"
        assert config.debug is False
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.performance, PerformanceConfig)
        assert isinstance(config.output, OutputConfig)

    def test_config_with_custom_values(self):
        """Test configuration with custom values."""
        config = Config(
            debug=True,
            version="2.0.0"
        )

        assert config.debug is True
        assert config.version == "2.0.0"

    def test_load_from_file(self, config_file: Path):
        """Test loading configuration from file."""
        config = Config.load_from_file(config_file)

        assert config.debug is False
        assert config.logging.level == "INFO"
        assert config.performance.max_workers == 2
        assert config.output.format == "PNG"

    def test_load_from_nonexistent_file(self):
        """Test loading from non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            Config.load_from_file("nonexistent.yaml")

    def test_save_to_file(self, temp_dir: Path):
        """Test saving configuration to file."""
        config = Config(debug=True)
        config_path = temp_dir / "test_config.yaml"

        config.save_to_file(config_path)

        assert config_path.exists()

        # Load and verify
        with open(config_path) as f:
            data = yaml.safe_load(f)

        assert data["debug"] is True

    def test_load_from_env(self, monkeypatch):
        """Test loading configuration from environment variables."""
        monkeypatch.setenv("RETILEUP_DEBUG", "true")
        monkeypatch.setenv("RETILEUP_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("RETILEUP_MAX_WORKERS", "8")

        config = Config.load_from_env()

        assert config.debug is True
        assert config.logging.level == "DEBUG"
        assert config.performance.max_workers == 8

    def test_get_tool_config(self):
        """Test getting tool-specific configuration."""
        config = Config()
        config.set_tool_config("test_tool", {"param1": "value1"})

        tool_config = config.get_tool_config("test_tool")
        assert tool_config == {"param1": "value1"}

        # Test non-existent tool
        empty_config = config.get_tool_config("nonexistent_tool")
        assert empty_config == {}

    def test_set_tool_config(self):
        """Test setting tool-specific configuration."""
        config = Config()
        tool_config = {"param1": "value1", "param2": 42}

        config.set_tool_config("test_tool", tool_config)

        assert config.tool_configs["test_tool"] == tool_config


class TestLoggingConfig:
    """Test cases for the LoggingConfig class."""

    def test_default_logging_config(self):
        """Test default logging configuration."""
        logging_config = LoggingConfig()

        assert logging_config.level == "INFO"
        assert "%(asctime)s" in logging_config.format
        assert logging_config.file is None

    def test_custom_logging_config(self):
        """Test custom logging configuration."""
        logging_config = LoggingConfig(
            level="DEBUG",
            file=Path("/tmp/test.log")
        )

        assert logging_config.level == "DEBUG"
        assert logging_config.file == Path("/tmp/test.log")


class TestPerformanceConfig:
    """Test cases for the PerformanceConfig class."""

    def test_default_performance_config(self):
        """Test default performance configuration."""
        perf_config = PerformanceConfig()

        assert perf_config.max_workers == 4
        assert perf_config.chunk_size == 1024
        assert perf_config.memory_limit is None

    def test_custom_performance_config(self):
        """Test custom performance configuration."""
        perf_config = PerformanceConfig(
            max_workers=8,
            chunk_size=2048,
            memory_limit=1024
        )

        assert perf_config.max_workers == 8
        assert perf_config.chunk_size == 2048
        assert perf_config.memory_limit == 1024


class TestOutputConfig:
    """Test cases for the OutputConfig class."""

    def test_default_output_config(self):
        """Test default output configuration."""
        output_config = OutputConfig()

        assert output_config.directory == Path("outputs")
        assert output_config.format == "PNG"
        assert output_config.quality == 95
        assert output_config.overwrite is False

    def test_custom_output_config(self):
        """Test custom output configuration."""
        output_config = OutputConfig(
            directory=Path("/tmp/outputs"),
            format="JPEG",
            quality=80,
            overwrite=True
        )

        assert output_config.directory == Path("/tmp/outputs")
        assert output_config.format == "JPEG"
        assert output_config.quality == 80
        assert output_config.overwrite is True

    def test_invalid_quality_value(self):
        """Test that invalid quality values raise validation error."""
        with pytest.raises(ValueError, match="Quality must be between 1 and 100"):
            OutputConfig(quality=0)

        with pytest.raises(ValueError, match="Quality must be between 1 and 100"):
            OutputConfig(quality=101)