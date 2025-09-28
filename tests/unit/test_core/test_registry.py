"""Comprehensive unit tests for ToolRegistry.

This module tests the tool registry system including:
- Tool registration and management
- Plugin loading and discovery
- Thread safety and concurrent access
- Tool validation and health checking
- Statistics and metadata tracking
- Error handling and recovery
"""

import importlib.util
import tempfile
import threading
import time
from pathlib import Path
from typing import List, Type
from unittest.mock import Mock, patch, MagicMock

import pytest

from retileup.core.registry import ToolRegistry, ToolMetadata, get_global_registry, reset_global_registry
from retileup.core.exceptions import RegistryError, ErrorCode
from retileup.tools.base import BaseTool, ToolConfig, ToolResult


class MockValidTool(BaseTool):
    """Valid mock tool for testing."""

    @property
    def name(self) -> str:
        return "mock-valid-tool"

    @property
    def description(self) -> str:
        return "A valid mock tool for testing"

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_config_schema(self) -> Type[ToolConfig]:
        return ToolConfig

    def validate_config(self, config: ToolConfig) -> List[str]:
        return []

    def execute(self, config: ToolConfig) -> ToolResult:
        return ToolResult(success=True, message="Mock execution successful")


class MockInvalidTool:
    """Invalid mock tool (doesn't inherit from BaseTool)."""

    def __init__(self):
        pass


class MockFailingTool(BaseTool):
    """Mock tool that fails during instantiation."""

    @property
    def name(self) -> str:
        return "failing-tool"

    @property
    def description(self) -> str:
        return ""  # Invalid - empty description

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_config_schema(self) -> Type[ToolConfig]:
        return ToolConfig

    def validate_config(self, config: ToolConfig) -> List[str]:
        return []

    def execute(self, config: ToolConfig) -> ToolResult:
        raise RuntimeError("This tool always fails")


class TestToolMetadata:
    """Test ToolMetadata class."""

    def test_tool_metadata_creation(self):
        """Test creating ToolMetadata with all fields."""
        registration_time = time.time()
        metadata = ToolMetadata(
            tool_class=MockValidTool,
            name="test-tool",
            version="2.0.0",
            description="Test tool description",
            registration_time=registration_time,
            source_module="test.module",
            plugin_path=Path("/test/plugin.py")
        )

        assert metadata.tool_class == MockValidTool
        assert metadata.name == "test-tool"
        assert metadata.version == "2.0.0"
        assert metadata.description == "Test tool description"
        assert metadata.registration_time == registration_time
        assert metadata.source_module == "test.module"
        assert metadata.plugin_path == Path("/test/plugin.py")
        assert metadata.usage_count == 0
        assert metadata.last_used is None

    def test_tool_metadata_to_dict(self):
        """Test converting ToolMetadata to dictionary."""
        registration_time = time.time()
        metadata = ToolMetadata(
            tool_class=MockValidTool,
            name="test-tool",
            version="1.5.0",
            description="Test description",
            registration_time=registration_time
        )

        metadata_dict = metadata.to_dict()

        assert metadata_dict["name"] == "test-tool"
        assert metadata_dict["version"] == "1.5.0"
        assert metadata_dict["description"] == "Test description"
        assert metadata_dict["class_name"] == "MockValidTool"
        assert metadata_dict["registration_time"] == registration_time
        assert metadata_dict["usage_count"] == 0
        assert metadata_dict["last_used"] is None
        assert metadata_dict["plugin_path"] is None


class TestToolRegistry:
    """Test ToolRegistry core functionality."""

    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = ToolRegistry()

        assert len(registry) == 0
        assert len(registry._plugin_directories) > 0  # Should have default directories
        assert registry._auto_discovery_enabled is True

    def test_tool_registration_success(self):
        """Test successful tool registration."""
        registry = ToolRegistry()

        registry.register_tool(MockValidTool)

        assert len(registry) == 1
        assert "mock-valid-tool" in registry
        assert registry.get_tool_class("mock-valid-tool") == MockValidTool

    def test_tool_registration_with_custom_name(self):
        """Test tool registration with custom name."""
        registry = ToolRegistry()

        registry.register_tool(MockValidTool, name="custom-tool-name")

        assert len(registry) == 1
        assert "custom-tool-name" in registry
        assert "mock-valid-tool" not in registry
        assert registry.get_tool_class("custom-tool-name") == MockValidTool

    def test_tool_registration_duplicate_without_force(self):
        """Test duplicate tool registration without force flag."""
        registry = ToolRegistry()

        # Register tool twice
        registry.register_tool(MockValidTool)
        registry.register_tool(MockValidTool)  # Should be ignored

        assert len(registry) == 1

    def test_tool_registration_duplicate_with_force(self):
        """Test duplicate tool registration with force flag."""
        registry = ToolRegistry()

        # Register tool twice with force
        registry.register_tool(MockValidTool)
        registry.register_tool(MockValidTool, force=True)

        assert len(registry) == 1  # Still only one, but replaced

    def test_tool_registration_invalid_class(self):
        """Test registration of invalid tool class."""
        registry = ToolRegistry()

        with pytest.raises(RegistryError) as exc_info:
            registry.register_tool(MockInvalidTool)

        assert "must inherit from BaseTool" in str(exc_info.value)
        assert exc_info.value.error_code == ErrorCode.TOOL_REGISTRATION_ERROR

    def test_tool_registration_abstract_base_class(self):
        """Test registration of abstract BaseTool class."""
        registry = ToolRegistry()

        with pytest.raises(RegistryError) as exc_info:
            registry.register_tool(BaseTool)

        assert "Cannot register abstract BaseTool class" in str(exc_info.value)

    def test_tool_registration_failing_tool(self):
        """Test registration of tool with invalid properties."""
        registry = ToolRegistry()

        with pytest.raises(RegistryError) as exc_info:
            registry.register_tool(MockFailingTool)

        assert "must have valid description property" in str(exc_info.value)

    def test_tool_unregistration(self):
        """Test tool unregistration."""
        registry = ToolRegistry()

        registry.register_tool(MockValidTool)
        assert len(registry) == 1

        success = registry.unregister_tool("mock-valid-tool")
        assert success is True
        assert len(registry) == 0
        assert "mock-valid-tool" not in registry

        # Try to unregister non-existent tool
        success = registry.unregister_tool("nonexistent-tool")
        assert success is False

    def test_get_tool_class_with_usage_tracking(self):
        """Test getting tool class with usage tracking."""
        registry = ToolRegistry()
        registry.register_tool(MockValidTool)

        metadata = registry._tools["mock-valid-tool"]
        assert metadata.usage_count == 0
        assert metadata.last_used is None

        # Get tool class should increment usage
        tool_class = registry.get_tool_class("mock-valid-tool")
        assert tool_class == MockValidTool
        assert metadata.usage_count == 1
        assert metadata.last_used is not None

        # Get again should increment further
        registry.get_tool_class("mock-valid-tool")
        assert metadata.usage_count == 2

    def test_get_tool_class_nonexistent(self):
        """Test getting non-existent tool class."""
        registry = ToolRegistry()

        tool_class = registry.get_tool_class("nonexistent-tool")
        assert tool_class is None

    def test_create_tool_instance(self):
        """Test creating tool instance."""
        registry = ToolRegistry()
        registry.register_tool(MockValidTool)

        tool_instance = registry.create_tool("mock-valid-tool")
        assert isinstance(tool_instance, MockValidTool)
        assert tool_instance.name == "mock-valid-tool"

    def test_create_tool_instance_nonexistent(self):
        """Test creating instance of non-existent tool."""
        registry = ToolRegistry()

        tool_instance = registry.create_tool("nonexistent-tool")
        assert tool_instance is None

    def test_create_tool_instance_failure(self):
        """Test creating tool instance that fails during instantiation."""
        registry = ToolRegistry()

        class FailingInstantiationTool(BaseTool):
            def __init__(self):
                raise RuntimeError("Failed to instantiate")

            @property
            def name(self) -> str:
                return "failing-instantiation"

            @property
            def description(self) -> str:
                return "Fails during instantiation"

            @property
            def version(self) -> str:
                return "1.0.0"

            def get_config_schema(self) -> Type[ToolConfig]:
                return ToolConfig

            def validate_config(self, config: ToolConfig) -> List[str]:
                return []

            def execute(self, config: ToolConfig) -> ToolResult:
                return ToolResult(success=True, message="Should not reach here")

        # Registration should work (we don't instantiate during registration)
        registry.register_tool(FailingInstantiationTool)

        # But creation should fail
        with pytest.raises(RegistryError) as exc_info:
            registry.create_tool("failinginstantiation")

        assert "Failed to create tool instance" in str(exc_info.value)

    def test_get_tool_metadata(self):
        """Test getting tool metadata."""
        registry = ToolRegistry()
        registry.register_tool(MockValidTool)

        metadata = registry.get_tool_metadata("mock-valid-tool")
        assert metadata is not None
        assert metadata["name"] == "mock-valid-tool"
        assert metadata["version"] == "1.0.0"
        assert metadata["class_name"] == "MockValidTool"

        # Non-existent tool
        metadata = registry.get_tool_metadata("nonexistent-tool")
        assert metadata is None

    def test_list_tools(self):
        """Test listing tools."""
        registry = ToolRegistry()
        registry.register_tool(MockValidTool)

        # List names only
        tools = registry.list_tools()
        assert tools == ["mock-valid-tool"]

        # List with metadata
        tools_with_metadata = registry.list_tools(include_metadata=True)
        assert len(tools_with_metadata) == 1
        assert tools_with_metadata[0]["name"] == "mock-valid-tool"

    def test_list_tools_by_pattern(self):
        """Test listing tools by pattern matching."""
        registry = ToolRegistry()

        # Create multiple mock tools
        class MockTool1(MockValidTool):
            @property
            def name(self) -> str:
                return "image-resize"

        class MockTool2(MockValidTool):
            @property
            def name(self) -> str:
                return "image-crop"

        class MockTool3(MockValidTool):
            @property
            def name(self) -> str:
                return "text-tool"

        registry.register_tool(MockTool1)
        registry.register_tool(MockTool2)
        registry.register_tool(MockTool3)

        # Test pattern matching
        image_tools = registry.list_tools_by_pattern("image-*")
        assert set(image_tools) == {"image-resize", "image-crop"}

        all_tools = registry.list_tools_by_pattern("*")
        assert len(all_tools) == 3

        no_match = registry.list_tools_by_pattern("video-*")
        assert no_match == []

    def test_get_tool_statistics(self):
        """Test getting registry statistics."""
        registry = ToolRegistry()

        # Empty registry
        stats = registry.get_tool_statistics()
        assert stats["total_tools"] == 0
        assert stats["total_usage"] == 0
        assert stats["most_used_tool"] is None

        # Add tools and use them
        registry.register_tool(MockValidTool)
        registry.get_tool_class("mock-valid-tool")  # Use once
        registry.get_tool_class("mock-valid-tool")  # Use twice

        stats = registry.get_tool_statistics()
        assert stats["total_tools"] == 1
        assert stats["total_usage"] == 2
        assert stats["most_used_tool"]["name"] == "mock-valid-tool"
        assert stats["most_used_tool"]["usage_count"] == 2

    def test_clear_registry(self):
        """Test clearing registry."""
        registry = ToolRegistry()
        registry.register_tool(MockValidTool)

        assert len(registry) == 1

        # Should not clear without confirmation
        registry.clear_registry(confirm=False)
        assert len(registry) == 1

        # Should clear with confirmation
        registry.clear_registry(confirm=True)
        assert len(registry) == 0

    def test_export_registry_state(self):
        """Test exporting registry state."""
        registry = ToolRegistry()
        registry.register_tool(MockValidTool)

        state = registry.export_registry_state()

        assert "tools" in state
        assert "plugin_directories" in state
        assert "discovery_cache" in state
        assert "auto_discovery_enabled" in state
        assert "export_time" in state

        assert len(state["tools"]) == 1
        assert "mock-valid-tool" in state["tools"]
        assert state["auto_discovery_enabled"] is True

    def test_registry_len_contains_iter(self):
        """Test registry collection interface."""
        registry = ToolRegistry()

        assert len(registry) == 0
        assert "mock-valid-tool" not in registry

        registry.register_tool(MockValidTool)

        assert len(registry) == 1
        assert "mock-valid-tool" in registry
        assert list(registry) == ["mock-valid-tool"]

    def test_registry_string_representation(self):
        """Test registry string representation."""
        registry = ToolRegistry()

        repr_str = repr(registry)
        assert "ToolRegistry" in repr_str
        assert "tools=0" in repr_str
        assert "directories=" in repr_str


class TestToolRegistryPluginLoading:
    """Test plugin loading functionality."""

    def test_add_plugin_directory(self, temp_dir):
        """Test adding plugin directory."""
        registry = ToolRegistry()
        initial_count = len(registry._plugin_directories)

        plugin_dir = temp_dir / "plugins"
        plugin_dir.mkdir()

        registry.add_plugin_directory(plugin_dir, auto_load=False)

        assert len(registry._plugin_directories) == initial_count + 1
        assert plugin_dir in registry._plugin_directories

    def test_add_nonexistent_plugin_directory(self, temp_dir):
        """Test adding non-existent plugin directory."""
        registry = ToolRegistry()
        initial_count = len(registry._plugin_directories)

        nonexistent_dir = temp_dir / "nonexistent"

        registry.add_plugin_directory(nonexistent_dir, auto_load=False)

        # Should not be added
        assert len(registry._plugin_directories) == initial_count

    def test_load_plugins_from_directory(self, temp_dir):
        """Test loading plugins from directory."""
        registry = ToolRegistry()

        # Create plugin directory with a valid plugin
        plugin_dir = temp_dir / "plugins"
        plugin_dir.mkdir()

        plugin_content = '''
from retileup.tools.base import BaseTool, ToolConfig, ToolResult
from typing import List, Type

class TestPlugin(BaseTool):
    @property
    def name(self) -> str:
        return "test-plugin"

    @property
    def description(self) -> str:
        return "A test plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_config_schema(self) -> Type[ToolConfig]:
        return ToolConfig

    def validate_config(self, config: ToolConfig) -> List[str]:
        return []

    def execute(self, config: ToolConfig) -> ToolResult:
        return ToolResult(success=True, message="Plugin executed")
'''

        plugin_file = plugin_dir / "test_plugin.py"
        plugin_file.write_text(plugin_content)

        loaded_count = registry.load_plugins_from_directory(plugin_dir)

        assert loaded_count == 1
        assert "test-plugin" in registry

    def test_load_plugins_from_nonexistent_directory(self, temp_dir):
        """Test loading plugins from non-existent directory."""
        registry = ToolRegistry()

        nonexistent_dir = temp_dir / "nonexistent"
        loaded_count = registry.load_plugins_from_directory(nonexistent_dir)

        assert loaded_count == 0

    def test_load_plugins_skip_private_files(self, temp_dir):
        """Test that private files are skipped during plugin loading."""
        registry = ToolRegistry()

        plugin_dir = temp_dir / "plugins"
        plugin_dir.mkdir()

        # Create private file (starts with underscore)
        private_file = plugin_dir / "_private_plugin.py"
        private_file.write_text("# This should be skipped")

        loaded_count = registry.load_plugins_from_directory(plugin_dir)

        assert loaded_count == 0

    def test_auto_discovery(self, temp_dir):
        """Test auto-discovery functionality."""
        registry = ToolRegistry()

        # Add test plugin directory
        plugin_dir = temp_dir / "test_plugins"
        plugin_dir.mkdir()
        registry.add_plugin_directory(plugin_dir, auto_load=False)

        # Create a valid plugin
        plugin_content = '''
from retileup.tools.base import BaseTool, ToolConfig, ToolResult
from typing import List, Type

class AutoDiscoveredTool(BaseTool):
    @property
    def name(self) -> str:
        return "auto-discovered"

    @property
    def description(self) -> str:
        return "Auto-discovered tool"

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_config_schema(self) -> Type[ToolConfig]:
        return ToolConfig

    def validate_config(self, config: ToolConfig) -> List[str]:
        return []

    def execute(self, config: ToolConfig) -> ToolResult:
        return ToolResult(success=True, message="Auto-discovered execution")
'''

        plugin_file = plugin_dir / "auto_tool.py"
        plugin_file.write_text(plugin_content)

        # Run auto-discovery
        loaded_count = registry.auto_discover_tools(force_refresh=True)

        assert loaded_count >= 1
        assert "auto-discovered" in registry

    def test_auto_discovery_disabled(self, temp_dir):
        """Test auto-discovery when disabled."""
        registry = ToolRegistry()
        registry.enable_auto_discovery(False)

        loaded_count = registry.auto_discover_tools()

        assert loaded_count == 0

    def test_auto_discovery_caching(self, temp_dir):
        """Test auto-discovery caching mechanism."""
        registry = ToolRegistry()

        plugin_dir = temp_dir / "test_plugins"
        plugin_dir.mkdir()
        registry.add_plugin_directory(plugin_dir, auto_load=False)

        # First discovery
        loaded_count1 = registry.auto_discover_tools(force_refresh=True)

        # Second discovery without force should use cache
        loaded_count2 = registry.auto_discover_tools(force_refresh=False)
        assert loaded_count2 == 0  # Should skip due to cache

        # Third discovery with force should run again
        loaded_count3 = registry.auto_discover_tools(force_refresh=True)
        assert loaded_count3 == loaded_count1


class TestToolRegistryHealthAndValidation:
    """Test tool health checking and validation."""

    def test_validate_tool_health_success(self):
        """Test successful tool health validation."""
        registry = ToolRegistry()
        registry.register_tool(MockValidTool)

        health = registry.validate_tool_health("mock-valid-tool")

        assert health["healthy"] is True
        assert health["tool_name"] == "mock-valid-tool"
        assert health["tool_version"] == "1.0.0"
        assert all(health["checks"].values())

    def test_validate_tool_health_nonexistent(self):
        """Test health validation for non-existent tool."""
        registry = ToolRegistry()

        health = registry.validate_tool_health("nonexistent-tool")

        assert health["healthy"] is False
        assert "not found" in health["error"]
        assert health["error_code"] == ErrorCode.TOOL_NOT_FOUND.value

    def test_validate_tool_health_failure(self):
        """Test health validation for failing tool."""
        registry = ToolRegistry()

        class FailingHealthTool(BaseTool):
            def __init__(self):
                raise RuntimeError("Health check failure")

            @property
            def name(self) -> str:
                return "failing-health"

            @property
            def description(self) -> str:
                return "Fails health check"

            @property
            def version(self) -> str:
                return "1.0.0"

            def get_config_schema(self) -> Type[ToolConfig]:
                return ToolConfig

            def validate_config(self, config: ToolConfig) -> List[str]:
                return []

            def execute(self, config: ToolConfig) -> ToolResult:
                return ToolResult(success=True, message="Should not reach here")

        registry.register_tool(FailingHealthTool)

        health = registry.validate_tool_health("failinghealth")

        assert health["healthy"] is False
        assert "Health check failed" in health["error"]


class TestToolRegistryThreadSafety:
    """Test thread safety of ToolRegistry."""

    def test_concurrent_registration(self):
        """Test concurrent tool registration."""
        registry = ToolRegistry()
        results = []
        errors = []

        def register_tool(tool_class, name):
            try:
                registry.register_tool(tool_class, name=name)
                results.append(name)
            except Exception as e:
                errors.append(e)

        # Create multiple tool classes
        tool_classes = []
        for i in range(10):
            class_name = f"ConcurrentTool{i}"
            tool_class = type(class_name, (MockValidTool,), {
                "name": property(lambda self, idx=i: f"concurrent-tool-{idx}")
            })
            tool_classes.append((tool_class, f"concurrent-tool-{i}"))

        # Start multiple threads
        threads = []
        for tool_class, name in tool_classes:
            thread = threading.Thread(target=register_tool, args=(tool_class, name))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        assert len(errors) == 0, f"Unexpected errors: {errors}"
        assert len(results) == 10
        assert len(registry) == 10

    def test_concurrent_access(self):
        """Test concurrent tool access."""
        registry = ToolRegistry()
        registry.register_tool(MockValidTool)

        access_results = []
        access_errors = []

        def access_tool():
            try:
                for _ in range(100):
                    tool_class = registry.get_tool_class("mock-valid-tool")
                    assert tool_class == MockValidTool

                    tool_instance = registry.create_tool("mock-valid-tool")
                    assert isinstance(tool_instance, MockValidTool)

                access_results.append(True)
            except Exception as e:
                access_errors.append(e)

        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=access_tool)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        assert len(access_errors) == 0, f"Unexpected errors: {access_errors}"
        assert len(access_results) == 5

        # Check usage count was updated correctly
        metadata = registry.get_tool_metadata("mock-valid-tool")
        assert metadata["usage_count"] == 5 * 100 * 2  # 5 threads × 100 accesses × 2 calls each (get_tool_class + create_tool->get_tool_class)


class TestGlobalRegistry:
    """Test global registry functionality."""

    def test_get_global_registry(self):
        """Test getting global registry instance."""
        # Reset first
        reset_global_registry()

        registry1 = get_global_registry()
        registry2 = get_global_registry()

        assert registry1 is registry2  # Should be singleton

    def test_reset_global_registry(self):
        """Test resetting global registry."""
        registry1 = get_global_registry()
        reset_global_registry()
        registry2 = get_global_registry()

        assert registry1 is not registry2

    def test_global_registry_thread_safety(self):
        """Test global registry thread safety."""
        reset_global_registry()

        registries = []
        errors = []

        def get_registry():
            try:
                registry = get_global_registry()
                registries.append(registry)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=get_registry)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        assert len(errors) == 0, f"Unexpected errors: {errors}"
        assert len(registries) == 10

        # All should be the same instance
        first_registry = registries[0]
        assert all(registry is first_registry for registry in registries)