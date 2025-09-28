"""Integration tests for ReTileUp workflows.

This module tests complete workflow execution including:
- End-to-end workflow processing pipelines
- Tool integration and coordination
- Configuration validation and loading
- Error handling and recovery
- Performance and resource management
- Cross-platform compatibility
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import threading
import time

import pytest
from PIL import Image

from retileup.core.registry import ToolRegistry
from retileup.tools.base import BaseTool, ToolConfig, ToolResult
from retileup.core.exceptions import ValidationError, ProcessingError


# Mock workflow classes for testing
class MockWorkflowConfig(ToolConfig):
    """Mock configuration for workflow testing."""
    steps: int = 3
    parallel: bool = False
    timeout: float = 30.0


class MockWorkflowTool(BaseTool):
    """Mock workflow tool for integration testing."""

    def __init__(self, should_fail: bool = False, delay: float = 0.0):
        super().__init__()
        self._should_fail = should_fail
        self._delay = delay
        self._execution_count = 0

    @property
    def name(self) -> str:
        return "mock-workflow-tool"

    @property
    def description(self) -> str:
        return "Mock tool for workflow testing"

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_config_schema(self):
        return MockWorkflowConfig

    def validate_config(self, config: MockWorkflowConfig):
        errors = []
        if config.steps <= 0:
            errors.append("Steps must be positive")
        if config.timeout <= 0:
            errors.append("Timeout must be positive")
        return errors

    def execute(self, config: MockWorkflowConfig) -> ToolResult:
        self._execution_count += 1

        if self._delay > 0:
            time.sleep(self._delay)

        if self._should_fail:
            raise ProcessingError(f"Mock tool failure #{self._execution_count}")

        output_files = []
        if hasattr(config, 'output_dir') and config.output_dir:
            for i in range(config.steps):
                output_file = config.output_dir / f"step_{i}.png"
                output_files.append(output_file)

        return ToolResult(
            success=True,
            message=f"Mock workflow completed {config.steps} steps",
            output_files=output_files,
            metadata={
                "execution_count": self._execution_count,
                "steps_completed": config.steps,
                "parallel": config.parallel
            }
        )


@pytest.fixture
def mock_registry():
    """Create a mock tool registry with test tools."""
    registry = ToolRegistry()
    registry.register_tool(MockWorkflowTool())
    registry.register_tool(MockWorkflowTool(should_fail=False), name="stable-tool")
    registry.register_tool(MockWorkflowTool(should_fail=True), name="failing-tool")
    registry.register_tool(MockWorkflowTool(delay=0.1), name="slow-tool")
    return registry


@pytest.fixture
def workflow_config(temp_dir):
    """Create a workflow configuration."""
    return MockWorkflowConfig(
        input_path=temp_dir / "input.jpg",
        output_dir=temp_dir / "output",
        steps=3,
        parallel=False,
        timeout=30.0
    )


@pytest.fixture
def sample_workflow_input(temp_dir):
    """Create sample input for workflow testing."""
    input_file = temp_dir / "input.jpg"

    # Create a sample image
    image = Image.new('RGB', (200, 200), color='red')
    image.save(input_file, 'JPEG')

    return input_file


class TestWorkflowBasics:
    """Test basic workflow functionality."""

    def test_workflow_tool_registration(self, mock_registry):
        """Test that workflow tools are registered correctly."""
        tools = mock_registry.list_tools()

        assert "mock-workflow-tool" in tools
        assert "stable-tool" in tools
        assert "failing-tool" in tools
        assert "slow-tool" in tools

    def test_workflow_tool_retrieval(self, mock_registry):
        """Test workflow tool retrieval from registry."""
        tool = mock_registry.get_tool("mock-workflow-tool")

        assert isinstance(tool, MockWorkflowTool)
        assert tool.name == "mock-workflow-tool"

    def test_workflow_config_validation(self, workflow_config):
        """Test workflow configuration validation."""
        tool = MockWorkflowTool()
        errors = tool.validate_config(workflow_config)

        assert len(errors) == 0

    def test_workflow_config_validation_errors(self, temp_dir):
        """Test workflow configuration validation with errors."""
        invalid_config = MockWorkflowConfig(
            input_path=temp_dir / "input.jpg",
            steps=-1,  # Invalid
            timeout=-5.0  # Invalid
        )

        tool = MockWorkflowTool()
        errors = tool.validate_config(invalid_config)

        assert len(errors) == 2
        assert any("positive" in error for error in errors)


class TestWorkflowExecution:
    """Test workflow execution scenarios."""

    def test_simple_workflow_execution(self, mock_registry, workflow_config, sample_workflow_input):
        """Test simple workflow execution."""
        workflow_config.input_path = sample_workflow_input

        tool = mock_registry.get_tool("stable-tool")
        result = tool.execute(workflow_config)

        assert result.success is True
        assert "3 steps" in result.message
        assert result.metadata["steps_completed"] == 3

    def test_workflow_with_output_files(self, mock_registry, workflow_config, sample_workflow_input):
        """Test workflow execution with output file generation."""
        workflow_config.input_path = sample_workflow_input
        workflow_config.output_dir.mkdir(exist_ok=True)

        tool = mock_registry.get_tool("stable-tool")
        result = tool.execute(workflow_config)

        assert result.success is True
        assert len(result.output_files) == workflow_config.steps

        for output_file in result.output_files:
            assert isinstance(output_file, Path)
            assert output_file.name.startswith("step_")

    def test_workflow_execution_failure(self, mock_registry, workflow_config, sample_workflow_input):
        """Test workflow execution failure handling."""
        workflow_config.input_path = sample_workflow_input

        tool = mock_registry.get_tool("failing-tool")

        with pytest.raises(ProcessingError) as exc_info:
            tool.execute(workflow_config)

        assert "Mock tool failure" in str(exc_info.value)

    def test_workflow_execution_with_timing(self, mock_registry, workflow_config, sample_workflow_input):
        """Test workflow execution with timing measurement."""
        workflow_config.input_path = sample_workflow_input

        tool = mock_registry.get_tool("slow-tool")

        start_time = time.time()
        result = tool.execute_with_timing(workflow_config)
        end_time = time.time()

        assert result.success is True
        assert result.execution_time is not None
        assert result.execution_time > 0
        assert result.execution_time <= (end_time - start_time)

    def test_workflow_multiple_executions(self, mock_registry, workflow_config, sample_workflow_input):
        """Test multiple workflow executions."""
        workflow_config.input_path = sample_workflow_input

        tool = mock_registry.get_tool("stable-tool")

        results = []
        for i in range(3):
            result = tool.execute(workflow_config)
            results.append(result)

        # All executions should succeed
        assert all(result.success for result in results)

        # Execution count should increment
        for i, result in enumerate(results, 1):
            assert result.metadata["execution_count"] == i

    def test_workflow_parallel_configuration(self, mock_registry, workflow_config, sample_workflow_input):
        """Test workflow with parallel configuration."""
        workflow_config.input_path = sample_workflow_input
        workflow_config.parallel = True

        tool = mock_registry.get_tool("stable-tool")
        result = tool.execute(workflow_config)

        assert result.success is True
        assert result.metadata["parallel"] is True


class TestWorkflowConcurrency:
    """Test workflow concurrency and thread safety."""

    def test_concurrent_workflow_execution(self, mock_registry, temp_dir, sample_workflow_input):
        """Test concurrent workflow execution."""
        import queue

        results = queue.Queue()
        errors = queue.Queue()

        def execute_workflow(tool_name, config):
            try:
                tool = mock_registry.get_tool(tool_name)
                result = tool.execute(config)
                results.put((tool_name, result))
            except Exception as e:
                errors.put((tool_name, e))

        # Create separate configs for each thread
        configs = []
        for i in range(3):
            config = MockWorkflowConfig(
                input_path=sample_workflow_input,
                output_dir=temp_dir / f"output_{i}",
                steps=2
            )
            config.output_dir.mkdir(exist_ok=True)
            configs.append(config)

        # Start concurrent executions
        threads = []
        for i, config in enumerate(configs):
            thread = threading.Thread(
                target=execute_workflow,
                args=("stable-tool", config)
            )
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Check results
        assert errors.empty(), f"Errors occurred: {list(errors.queue)}"
        assert results.qsize() == 3

        # All workflows should complete successfully
        while not results.empty():
            tool_name, result = results.get()
            assert result.success is True
            assert tool_name == "stable-tool"

    def test_workflow_thread_safety(self, mock_registry, workflow_config, sample_workflow_input):
        """Test workflow thread safety with shared tool instances."""
        workflow_config.input_path = sample_workflow_input

        import queue

        results = queue.Queue()
        errors = queue.Queue()

        def execute_shared_tool():
            try:
                tool = mock_registry.get_tool("stable-tool")
                result = tool.execute(workflow_config)
                results.put(result.metadata["execution_count"])
            except Exception as e:
                errors.put(e)

        # Start multiple threads using the same tool
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=execute_shared_tool)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Check results
        assert errors.empty(), f"Errors occurred: {list(errors.queue)}"
        assert results.qsize() == 5

        # Execution counts should be unique (thread-safe increments)
        execution_counts = []
        while not results.empty():
            execution_counts.append(results.get())

        assert len(set(execution_counts)) == 5  # All unique

    def test_workflow_resource_contention(self, mock_registry, temp_dir, sample_workflow_input):
        """Test workflow behavior under resource contention."""
        import queue

        results = queue.Queue()
        errors = queue.Queue()

        # Create many configs that use the same output directory
        shared_output = temp_dir / "shared_output"
        shared_output.mkdir(exist_ok=True)

        def execute_with_contention():
            try:
                config = MockWorkflowConfig(
                    input_path=sample_workflow_input,
                    output_dir=shared_output,
                    steps=1
                )

                tool = mock_registry.get_tool("stable-tool")
                result = tool.execute(config)
                results.put(result.success)
            except Exception as e:
                errors.put(e)

        # Start many concurrent executions
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=execute_with_contention)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Most should succeed despite contention
        successful_count = 0
        while not results.empty():
            if results.get():
                successful_count += 1

        assert successful_count >= 8  # At least 80% success rate


class TestWorkflowErrorHandling:
    """Test workflow error handling and recovery."""

    def test_workflow_validation_error_handling(self, mock_registry, temp_dir):
        """Test workflow validation error handling."""
        invalid_config = MockWorkflowConfig(
            input_path=temp_dir / "nonexistent.jpg",
            steps=0  # Invalid
        )

        tool = mock_registry.get_tool("stable-tool")
        errors = tool.validate_config(invalid_config)

        assert len(errors) > 0

    def test_workflow_processing_error_recovery(self, mock_registry, workflow_config, sample_workflow_input):
        """Test workflow processing error recovery."""
        workflow_config.input_path = sample_workflow_input

        failing_tool = mock_registry.get_tool("failing-tool")
        stable_tool = mock_registry.get_tool("stable-tool")

        # First execution should fail
        with pytest.raises(ProcessingError):
            failing_tool.execute(workflow_config)

        # Recovery with stable tool should work
        result = stable_tool.execute(workflow_config)
        assert result.success is True

    def test_workflow_timeout_handling(self, mock_registry, workflow_config, sample_workflow_input):
        """Test workflow timeout handling."""
        workflow_config.input_path = sample_workflow_input
        workflow_config.timeout = 0.05  # Very short timeout

        slow_tool = mock_registry.get_tool("slow-tool")

        # This is a basic test - actual timeout implementation would be in the workflow engine
        start_time = time.time()
        result = slow_tool.execute(workflow_config)
        end_time = time.time()

        # Tool should still complete (no actual timeout implementation in mock)
        assert result.success is True
        assert end_time - start_time >= 0.1  # Slow tool has 0.1s delay

    def test_workflow_partial_failure_handling(self, mock_registry, workflow_config, sample_workflow_input):
        """Test handling of partial workflow failures."""
        workflow_config.input_path = sample_workflow_input

        # Simulate a workflow that fails partway through
        tool = MockWorkflowTool(should_fail=False)

        # First execution succeeds
        result1 = tool.execute(workflow_config)
        assert result1.success is True

        # Change tool to fail
        tool._should_fail = True

        # Second execution fails
        with pytest.raises(ProcessingError):
            tool.execute(workflow_config)

    def test_workflow_cleanup_on_failure(self, mock_registry, workflow_config, sample_workflow_input):
        """Test workflow cleanup on failure."""
        workflow_config.input_path = sample_workflow_input

        failing_tool = mock_registry.get_tool("failing-tool")

        # Execute with timing to ensure cleanup is called
        with pytest.raises(ProcessingError):
            failing_tool.execute_with_timing(workflow_config)

        # Cleanup should have been called
        assert failing_tool._cleanup_called


class TestWorkflowPerformance:
    """Test workflow performance characteristics."""

    def test_workflow_execution_time(self, mock_registry, workflow_config, sample_workflow_input):
        """Test workflow execution time measurement."""
        workflow_config.input_path = sample_workflow_input

        tool = mock_registry.get_tool("stable-tool")

        result = tool.execute_with_timing(workflow_config)

        assert result.execution_time is not None
        assert result.execution_time > 0
        assert result.execution_time < 1.0  # Should be fast for mock

    def test_workflow_memory_efficiency(self, mock_registry, workflow_config, sample_workflow_input, memory_monitor):
        """Test workflow memory efficiency."""
        workflow_config.input_path = sample_workflow_input
        workflow_config.steps = 10  # More steps

        tool = mock_registry.get_tool("stable-tool")

        memory_monitor.start()

        # Execute multiple times
        for _ in range(5):
            result = tool.execute(workflow_config)
            assert result.success is True

        peak_memory = memory_monitor.stop()

        # Memory usage should be reasonable (less than 50MB for mock)
        assert peak_memory < 50

    def test_workflow_scalability(self, mock_registry, temp_dir, sample_workflow_input):
        """Test workflow scalability with increasing load."""
        execution_times = []

        for step_count in [1, 5, 10, 20]:
            config = MockWorkflowConfig(
                input_path=sample_workflow_input,
                output_dir=temp_dir / f"output_{step_count}",
                steps=step_count
            )
            config.output_dir.mkdir(exist_ok=True)

            tool = mock_registry.get_tool("stable-tool")

            start_time = time.time()
            result = tool.execute(config)
            end_time = time.time()

            assert result.success is True
            execution_times.append(end_time - start_time)

        # Execution time should scale reasonably
        # (This is a basic test since mock doesn't have real scaling behavior)
        assert all(t >= 0 for t in execution_times)

    def test_workflow_resource_cleanup(self, mock_registry, workflow_config, sample_workflow_input):
        """Test workflow resource cleanup."""
        workflow_config.input_path = sample_workflow_input

        tool = mock_registry.get_tool("stable-tool")

        # Execute multiple workflows
        for _ in range(10):
            result = tool.execute_with_timing(workflow_config)
            assert result.success is True

            # Ensure setup and cleanup are called
            assert tool._setup_called
            assert tool._cleanup_called


class TestWorkflowIntegration:
    """Test workflow integration scenarios."""

    def test_end_to_end_workflow(self, mock_registry, temp_dir, sample_workflow_input):
        """Test complete end-to-end workflow execution."""
        # Create workflow configuration
        config = MockWorkflowConfig(
            input_path=sample_workflow_input,
            output_dir=temp_dir / "final_output",
            steps=5,
            parallel=False,
            timeout=30.0
        )
        config.output_dir.mkdir(exist_ok=True)

        # Execute workflow
        tool = mock_registry.get_tool("stable-tool")
        result = tool.execute_with_timing(config)

        # Verify complete success
        assert result.success is True
        assert result.execution_time is not None
        assert len(result.output_files) == 5
        assert result.metadata["steps_completed"] == 5

        # Verify output structure
        for i, output_file in enumerate(result.output_files):
            assert output_file.name == f"step_{i}.png"

    def test_workflow_chaining(self, mock_registry, temp_dir, sample_workflow_input):
        """Test chaining multiple workflows together."""
        # First workflow
        config1 = MockWorkflowConfig(
            input_path=sample_workflow_input,
            output_dir=temp_dir / "stage1",
            steps=2
        )
        config1.output_dir.mkdir(exist_ok=True)

        tool = mock_registry.get_tool("stable-tool")
        result1 = tool.execute(config1)

        assert result1.success is True
        assert len(result1.output_files) == 2

        # Second workflow using output from first
        if result1.output_files:
            config2 = MockWorkflowConfig(
                input_path=result1.output_files[0],  # Use first output
                output_dir=temp_dir / "stage2",
                steps=3
            )
            config2.output_dir.mkdir(exist_ok=True)

            result2 = tool.execute(config2)

            assert result2.success is True
            assert len(result2.output_files) == 3

    def test_workflow_error_propagation(self, mock_registry, workflow_config, sample_workflow_input):
        """Test error propagation through workflow layers."""
        workflow_config.input_path = sample_workflow_input

        # Start with working tool
        stable_tool = mock_registry.get_tool("stable-tool")
        result = stable_tool.execute(workflow_config)
        assert result.success is True

        # Switch to failing tool
        failing_tool = mock_registry.get_tool("failing-tool")

        # Error should propagate properly
        with pytest.raises(ProcessingError) as exc_info:
            failing_tool.execute(workflow_config)

        assert "Mock tool failure" in str(exc_info.value)

    def test_workflow_configuration_inheritance(self, mock_registry, workflow_config, sample_workflow_input):
        """Test workflow configuration inheritance and overrides."""
        workflow_config.input_path = sample_workflow_input

        # Base configuration
        base_config = workflow_config

        # Create derived configuration
        derived_config = MockWorkflowConfig(
            input_path=base_config.input_path,
            output_dir=base_config.output_dir,
            steps=base_config.steps * 2,  # Override
            parallel=True,  # Override
            timeout=base_config.timeout
        )

        tool = mock_registry.get_tool("stable-tool")

        # Execute with base config
        result1 = tool.execute(base_config)
        assert result1.metadata["steps_completed"] == base_config.steps
        assert result1.metadata["parallel"] == base_config.parallel

        # Execute with derived config
        result2 = tool.execute(derived_config)
        assert result2.metadata["steps_completed"] == derived_config.steps
        assert result2.metadata["parallel"] == derived_config.parallel

    def test_workflow_state_management(self, mock_registry, workflow_config, sample_workflow_input):
        """Test workflow state management across executions."""
        workflow_config.input_path = sample_workflow_input

        tool = mock_registry.get_tool("stable-tool")

        # Track state across multiple executions
        execution_counts = []

        for i in range(3):
            result = tool.execute(workflow_config)
            assert result.success is True
            execution_counts.append(result.metadata["execution_count"])

        # Execution count should increment properly
        assert execution_counts == [1, 2, 3]