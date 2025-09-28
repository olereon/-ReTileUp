"""Comprehensive unit tests for BaseTool framework.

This module tests the core tool infrastructure including:
- BaseTool abstract interface
- ToolConfig validation
- ToolResult data models
- Tool lifecycle management
- Error handling and edge cases
"""

import time
from pathlib import Path
from typing import List, Type
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError as PydanticValidationError

from retileup.tools.base import BaseTool, ToolConfig, ToolResult
from retileup.core.exceptions import RetileupError, ValidationError


class TestToolResult:
    """Test ToolResult data model."""

    def test_tool_result_creation_minimal(self):
        """Test creating ToolResult with minimal required fields."""
        result = ToolResult(success=True, message="Test successful")

        assert result.success is True
        assert result.message == "Test successful"
        assert result.output_files == []
        assert result.metadata == {}
        assert result.execution_time is None
        assert result.error_code is None

    def test_tool_result_creation_complete(self, temp_dir):
        """Test creating ToolResult with all fields."""
        output_files = [temp_dir / "output1.png", temp_dir / "output2.jpg"]
        metadata = {"processed_tiles": 5, "total_size": "2MB"}

        result = ToolResult(
            success=True,
            message="Processing completed successfully",
            output_files=output_files,
            metadata=metadata,
            execution_time=1.5,
            error_code="0000"
        )

        assert result.success is True
        assert result.message == "Processing completed successfully"
        assert result.output_files == output_files
        assert result.metadata == metadata
        assert result.execution_time == 1.5
        assert result.error_code == "0000"

    def test_tool_result_path_validation(self, temp_dir):
        """Test that output file paths are properly validated."""
        # Test string paths are converted to Path objects
        result = ToolResult(
            success=True,
            message="Test",
            output_files=[str(temp_dir / "test.png")]
        )

        assert all(isinstance(p, Path) for p in result.output_files)
        assert result.output_files[0] == temp_dir / "test.png"

    def test_tool_result_negative_execution_time(self):
        """Test that negative execution time is rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ToolResult(
                success=True,
                message="Test",
                execution_time=-1.0
            )

        assert "greater than or equal to 0" in str(exc_info.value)

    def test_tool_result_immutable_after_creation(self):
        """Test that ToolResult validates on assignment."""
        result = ToolResult(success=True, message="Test")

        # This should work
        result.execution_time = 2.5
        assert result.execution_time == 2.5

        # This should fail validation
        with pytest.raises(PydanticValidationError):
            result.execution_time = -1.0

    def test_tool_result_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ToolResult(
                success=True,
                message="Test",
                extra_field="not allowed"
            )

        assert "Extra inputs are not permitted" in str(exc_info.value)


class TestToolConfig:
    """Test ToolConfig base class."""

    def test_tool_config_creation_minimal(self, temp_dir):
        """Test creating ToolConfig with minimal fields."""
        input_path = temp_dir / "input.jpg"
        input_path.touch()  # Create empty file

        config = ToolConfig(input_path=input_path)

        assert config.input_path == input_path
        assert config.output_dir is None
        assert config.dry_run is False
        assert config.verbose is False
        assert config.preserve_metadata is True
        assert config.timeout is None

    def test_tool_config_creation_complete(self, temp_dir):
        """Test creating ToolConfig with all fields."""
        input_path = temp_dir / "input.jpg"
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        config = ToolConfig(
            input_path=input_path,
            output_dir=output_dir,
            dry_run=True,
            verbose=True,
            preserve_metadata=False,
            timeout=30.0
        )

        assert config.input_path == input_path
        assert config.output_dir == output_dir
        assert config.dry_run is True
        assert config.verbose is True
        assert config.preserve_metadata is False
        assert config.timeout == 30.0

    def test_tool_config_path_validation(self, temp_dir):
        """Test path validation and conversion."""
        # Test string path conversion
        config = ToolConfig(input_path=str(temp_dir / "test.jpg"))
        assert isinstance(config.input_path, Path)

        # Test output dir string conversion
        config = ToolConfig(
            input_path=temp_dir / "test.jpg",
            output_dir=str(temp_dir / "output")
        )
        assert isinstance(config.output_dir, Path)

    def test_tool_config_invalid_timeout(self, temp_dir):
        """Test that invalid timeout values are rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ToolConfig(
                input_path=temp_dir / "test.jpg",
                timeout=0.05  # Too small
            )

        assert "greater than or equal to 0.1" in str(exc_info.value)

    def test_tool_config_extra_fields_forbidden(self, temp_dir):
        """Test that extra fields are not allowed."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ToolConfig(
                input_path=temp_dir / "test.jpg",
                extra_param="not allowed"
            )

        assert "Extra inputs are not permitted" in str(exc_info.value)


class ConcreteTestTool(BaseTool):
    """Concrete implementation of BaseTool for testing."""

    def __init__(self, should_fail: bool = False):
        super().__init__()
        self._should_fail = should_fail
        self._execution_count = 0

    @property
    def name(self) -> str:
        return "test-tool"

    @property
    def description(self) -> str:
        return "A concrete test tool"

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_config_schema(self) -> Type[ToolConfig]:
        return ToolConfig

    def validate_config(self, config: ToolConfig) -> List[str]:
        errors = []
        if config.timeout and config.timeout > 60:
            errors.append("Timeout cannot exceed 60 seconds")
        return errors

    def execute(self, config: ToolConfig) -> ToolResult:
        self._execution_count += 1

        if self._should_fail:
            raise RuntimeError("Tool execution failed as requested")

        # Simulate some processing time
        time.sleep(0.01)

        return ToolResult(
            success=True,
            message=f"Tool executed successfully (count: {self._execution_count})",
            metadata={"execution_count": self._execution_count}
        )


class TestBaseTool:
    """Test BaseTool abstract base class."""

    def test_base_tool_cannot_be_instantiated(self):
        """Test that abstract BaseTool cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseTool()

    def test_concrete_tool_instantiation(self):
        """Test that concrete tool can be instantiated."""
        tool = ConcreteTestTool()
        assert tool.name == "test-tool"
        assert tool.description == "A concrete test tool"
        assert tool.version == "1.0.0"

    def test_tool_basic_execution(self, temp_dir):
        """Test basic tool execution."""
        tool = ConcreteTestTool()
        config = ToolConfig(input_path=temp_dir / "test.jpg")

        result = tool.execute(config)

        assert result.success is True
        assert "executed successfully" in result.message
        assert result.metadata["execution_count"] == 1

    def test_tool_execution_with_timing(self, temp_dir):
        """Test tool execution with automatic timing."""
        tool = ConcreteTestTool()
        config = ToolConfig(input_path=temp_dir / "test.jpg")

        start_time = time.time()
        result = tool.execute_with_timing(config)
        end_time = time.time()

        assert result.success is True
        assert result.execution_time is not None
        assert result.execution_time > 0
        assert result.execution_time <= (end_time - start_time)
        assert "execution_time_ms" in result.metadata

    def test_tool_lifecycle_management(self, temp_dir):
        """Test tool setup and cleanup lifecycle."""
        tool = ConcreteTestTool()
        config = ToolConfig(input_path=temp_dir / "test.jpg")

        # Initially, setup and cleanup should not be called
        assert not tool._setup_called
        assert not tool._cleanup_called

        # Execute with timing to trigger lifecycle
        result = tool.execute_with_timing(config)

        # After execution, both should be called
        assert tool._setup_called
        assert tool._cleanup_called
        assert result.success is True

    def test_tool_manual_lifecycle(self, temp_dir):
        """Test manual setup and cleanup calls."""
        tool = ConcreteTestTool()

        # Manual setup
        tool.setup()
        assert tool._setup_called
        assert not tool._cleanup_called

        # Manual cleanup
        tool.cleanup()
        assert tool._setup_called
        assert tool._cleanup_called

    def test_tool_config_validation_success(self, temp_dir):
        """Test successful config validation."""
        tool = ConcreteTestTool()
        config = ToolConfig(
            input_path=temp_dir / "test.jpg",
            timeout=30.0
        )

        errors = tool.validate_config(config)
        assert errors == []

    def test_tool_config_validation_failure(self, temp_dir):
        """Test config validation with errors."""
        tool = ConcreteTestTool()
        config = ToolConfig(
            input_path=temp_dir / "test.jpg",
            timeout=120.0  # Too long
        )

        errors = tool.validate_config(config)
        assert len(errors) == 1
        assert "cannot exceed 60 seconds" in errors[0]

    def test_tool_execution_failure(self, temp_dir):
        """Test tool execution failure handling."""
        tool = ConcreteTestTool(should_fail=True)
        config = ToolConfig(input_path=temp_dir / "test.jpg")

        with pytest.raises(RuntimeError) as exc_info:
            tool.execute(config)

        assert "execution failed as requested" in str(exc_info.value)

    def test_tool_execution_failure_with_timing(self, temp_dir):
        """Test that cleanup is called even when execution fails."""
        tool = ConcreteTestTool(should_fail=True)
        config = ToolConfig(input_path=temp_dir / "test.jpg")

        with pytest.raises(RuntimeError):
            tool.execute_with_timing(config)

        # Cleanup should still be called
        assert tool._setup_called
        assert tool._cleanup_called

    def test_tool_string_representations(self):
        """Test tool string representations."""
        tool = ConcreteTestTool()

        str_repr = str(tool)
        assert "test-tool v1.0.0" == str_repr

        repr_str = repr(tool)
        assert "ConcreteTestTool" in repr_str
        assert "name='test-tool'" in repr_str
        assert "version='1.0.0'" in repr_str

    def test_tool_get_config_schema(self):
        """Test getting tool configuration schema."""
        tool = ConcreteTestTool()
        schema = tool.get_config_schema()

        assert schema == ToolConfig
        assert issubclass(schema, ToolConfig)

    def test_tool_execution_timing_precision(self, temp_dir):
        """Test that execution timing is reasonably precise."""
        tool = ConcreteTestTool()
        config = ToolConfig(input_path=temp_dir / "test.jpg")

        # Execute multiple times to check timing consistency
        times = []
        for _ in range(5):
            result = tool.execute_with_timing(config)
            times.append(result.execution_time)

        # All times should be positive and reasonably consistent
        assert all(t > 0 for t in times)
        assert all(t < 1.0 for t in times)  # Should be fast

        # Times should be roughly similar (within 100ms)
        avg_time = sum(times) / len(times)
        assert all(abs(t - avg_time) < 0.1 for t in times)

    @pytest.mark.parametrize("dry_run,verbose", [
        (True, False),
        (False, True),
        (True, True),
        (False, False)
    ])
    def test_tool_config_combinations(self, temp_dir, dry_run, verbose):
        """Test various configuration combinations."""
        tool = ConcreteTestTool()
        config = ToolConfig(
            input_path=temp_dir / "test.jpg",
            dry_run=dry_run,
            verbose=verbose
        )

        errors = tool.validate_config(config)
        assert errors == []

        # Execution should work regardless of flags
        result = tool.execute(config)
        assert result.success is True

    def test_tool_metadata_preservation(self, temp_dir):
        """Test that tool execution preserves and adds metadata."""
        tool = ConcreteTestTool()
        config = ToolConfig(input_path=temp_dir / "test.jpg")

        result = tool.execute_with_timing(config)

        # Should have both tool-generated and timing metadata
        assert "execution_count" in result.metadata
        assert "execution_time_ms" in result.metadata
        assert result.metadata["execution_count"] == 1
        assert result.metadata["execution_time_ms"] > 0

    def test_tool_exception_propagation(self, temp_dir):
        """Test that tool exceptions are properly propagated."""

        class ExceptionTestTool(ConcreteTestTool):
            def execute(self, config: ToolConfig) -> ToolResult:
                raise ValueError("Custom exception for testing")

        tool = ExceptionTestTool()
        config = ToolConfig(input_path=temp_dir / "test.jpg")

        # Exception should propagate through execute_with_timing
        with pytest.raises(ValueError) as exc_info:
            tool.execute_with_timing(config)

        assert "Custom exception for testing" in str(exc_info.value)

        # Cleanup should still be called
        assert tool._setup_called
        assert tool._cleanup_called

    def test_tool_concurrent_execution(self, temp_dir):
        """Test that tools can handle concurrent execution safely."""
        import threading
        import queue

        tool = ConcreteTestTool()
        config = ToolConfig(input_path=temp_dir / "test.jpg")
        results_queue = queue.Queue()
        errors_queue = queue.Queue()

        def execute_tool():
            try:
                result = tool.execute_with_timing(config)
                results_queue.put(result)
            except Exception as e:
                errors_queue.put(e)

        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=execute_tool)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        assert errors_queue.empty(), f"Unexpected errors: {list(errors_queue.queue)}"
        assert results_queue.qsize() == 5

        # All results should be successful
        while not results_queue.empty():
            result = results_queue.get()
            assert result.success is True
            assert result.execution_time is not None


class TestToolEdgeCases:
    """Test edge cases and error conditions for tools."""

    def test_tool_with_empty_name(self):
        """Test tool with empty name."""
        class EmptyNameTool(ConcreteTestTool):
            @property
            def name(self) -> str:
                return ""

        tool = EmptyNameTool()
        assert tool.name == ""  # Should be allowed, validation happens elsewhere

    def test_tool_with_unicode_properties(self):
        """Test tool with Unicode characters in properties."""
        class UnicodeTool(ConcreteTestTool):
            @property
            def name(self) -> str:
                return "测试工具"

            @property
            def description(self) -> str:
                return "Инструмент для тестирования"

        tool = UnicodeTool()
        assert tool.name == "测试工具"
        assert tool.description == "Инструмент для тестирования"

    def test_tool_with_very_long_properties(self):
        """Test tool with very long property values."""
        long_string = "x" * 10000

        class LongPropertyTool(ConcreteTestTool):
            @property
            def description(self) -> str:
                return long_string

        tool = LongPropertyTool()
        assert len(tool.description) == 10000

    def test_tool_setup_cleanup_idempotency(self):
        """Test that setup and cleanup can be called multiple times safely."""
        tool = ConcreteTestTool()

        # Call setup multiple times
        tool.setup()
        tool.setup()
        tool.setup()
        assert tool._setup_called

        # Call cleanup multiple times
        tool.cleanup()
        tool.cleanup()
        tool.cleanup()
        assert tool._cleanup_called

    def test_tool_execution_with_none_config(self):
        """Test tool behavior with None configuration."""
        tool = ConcreteTestTool()

        # This should raise an appropriate error
        with pytest.raises((TypeError, AttributeError)):
            tool.execute(None)

    def test_tool_memory_efficiency(self, temp_dir, memory_monitor):
        """Test that tool execution doesn't leak memory."""
        tool = ConcreteTestTool()
        config = ToolConfig(input_path=temp_dir / "test.jpg")

        memory_monitor.start()

        # Execute tool many times
        for _ in range(100):
            result = tool.execute_with_timing(config)
            assert result.success

        peak_memory = memory_monitor.stop()

        # Memory usage should be reasonable (less than 100MB for this simple test)
        assert peak_memory < 100, f"Memory usage too high: {peak_memory}MB"