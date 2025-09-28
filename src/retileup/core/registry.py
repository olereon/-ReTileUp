"""Tool registry for managing ReTileUp tools.

This module provides a comprehensive tool registry system with auto-discovery,
version compatibility checking, and advanced tool management capabilities.
It serves as the central hub for tool registration and coordination within
the ReTileUp framework.
"""

import importlib
import importlib.util
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type, Union

from ..tools.base import BaseTool, ToolConfig, ToolResult
from .exceptions import RegistryError, ErrorCode, registry_error

logger = logging.getLogger(__name__)


class ToolMetadata(object):
    """Extended metadata for registered tools."""

    def __init__(
        self,
        tool_class: Type[BaseTool],
        name: str,
        version: str,
        description: str,
        registration_time: float,
        source_module: Optional[str] = None,
        plugin_path: Optional[Path] = None,
    ) -> None:
        """Initialize tool metadata.

        Args:
            tool_class: The tool class
            name: Tool name
            version: Tool version
            description: Tool description
            registration_time: When the tool was registered
            source_module: Module name where tool was loaded from
            plugin_path: Path to plugin file if loaded from plugin
        """
        self.tool_class = tool_class
        self.name = name
        self.version = version
        self.description = description
        self.registration_time = registration_time
        self.source_module = source_module
        self.plugin_path = plugin_path
        self.usage_count = 0
        self.last_used = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "class_name": self.tool_class.__name__,
            "module": self.source_module,
            "plugin_path": str(self.plugin_path) if self.plugin_path else None,
            "registration_time": self.registration_time,
            "usage_count": self.usage_count,
            "last_used": self.last_used,
        }


class ToolRegistry:
    """Registry for managing ReTileUp tools with advanced capabilities.

    This class provides a thread-safe registry for managing image processing
    tools. It supports automatic tool discovery, plugin loading, version
    compatibility checking, and comprehensive tool management.

    Features:
    - Thread-safe operations for concurrent access
    - Auto-discovery of built-in and plugin tools
    - Version compatibility validation
    - Usage tracking and statistics
    - Plugin lifecycle management
    - Tool validation and health checking

    Example:
        registry = ToolRegistry()
        registry.auto_discover_tools()
        registry.load_plugins_from_directory(Path("./plugins"))

        tool = registry.create_tool("image-resize")
        if tool:
            config = ResizeConfig(input_path=Path("image.jpg"))
            result = tool.execute(config)
    """

    def __init__(self) -> None:
        """Initialize the tool registry.

        Creates an empty registry with thread-safe access patterns
        and prepares for tool discovery and registration.
        """
        self._tools: Dict[str, ToolMetadata] = {}
        self._plugin_directories: List[Path] = []
        self._lock = threading.RLock()
        self._discovery_cache: Dict[str, float] = {}
        self._auto_discovery_enabled = True

        # Initialize with default plugin directories
        self._setup_default_plugin_directories()

    def _setup_default_plugin_directories(self) -> None:
        """Setup default plugin directories for auto-discovery."""
        # Built-in tools directory
        builtin_dir = Path(__file__).parent.parent / "tools"
        if builtin_dir.exists():
            self._plugin_directories.append(builtin_dir)

        # User plugin directories
        user_dirs = [
            Path.home() / ".retileup" / "plugins",
            Path.cwd() / "plugins",
            Path("/usr/local/share/retileup/plugins"),
        ]

        for directory in user_dirs:
            if directory.exists() and directory.is_dir():
                self._plugin_directories.append(directory)

    def register_tool(
        self,
        tool_class: Type[BaseTool],
        name: Optional[str] = None,
        force: bool = False,
    ) -> None:
        """Register a tool class with enhanced validation.

        Args:
            tool_class: The tool class to register (can be class or instance)
            name: Optional custom name for the tool
            force: Whether to force registration even if tool exists

        Raises:
            RegistryError: If registration fails or tool validation fails
        """
        with self._lock:
            try:
                # Handle case where an instance is passed instead of a class
                if not isinstance(tool_class, type):
                    # If it's an instance, get its class
                    actual_tool_class = type(tool_class)
                else:
                    actual_tool_class = tool_class

                # Validate the tool class
                self._validate_tool_class(actual_tool_class)

                # Create instance to get metadata (handle instantiation failures)
                try:
                    if isinstance(tool_class, type):
                        # It's a class, create an instance
                        tool_instance = tool_class()
                    else:
                        # It's already an instance
                        tool_instance = tool_class

                    tool_name = name or tool_instance.name
                    tool_version = tool_instance.version
                    tool_description = tool_instance.description
                except Exception as inst_error:
                    # If instantiation fails, use class name and defaults
                    logger.warning(f"Failed to instantiate {actual_tool_class.__name__} for metadata - using defaults: {inst_error}")
                    tool_name = name or actual_tool_class.__name__.lower().replace('tool', '')
                    tool_version = "unknown"
                    tool_description = f"Tool class {actual_tool_class.__name__} (instantiation may fail)"

                # Check for existing registration
                if tool_name in self._tools and not force:
                    existing_metadata = self._tools[tool_name]
                    logger.warning(
                        f"Tool '{tool_name}' already registered "
                        f"(existing: v{existing_metadata.version}, "
                        f"new: v{tool_version}). Use force=True to override."
                    )
                    return

                # Create metadata
                metadata = ToolMetadata(
                    tool_class=actual_tool_class,
                    name=tool_name,
                    version=tool_version,
                    description=tool_description,
                    registration_time=time.time(),
                    source_module=actual_tool_class.__module__,
                )

                # Register the tool
                self._tools[tool_name] = metadata

                logger.info(
                    f"Registered tool: {tool_name} v{tool_version} "
                    f"from {actual_tool_class.__module__}"
                )

            except Exception as e:
                raise registry_error(
                    f"Failed to register tool {actual_tool_class.__name__}: {str(e)}",
                    tool_name=getattr(tool_instance if 'tool_instance' in locals() else actual_tool_class, "name", actual_tool_class.__name__),
                    operation="register",
                    cause=e,
                ) from e

    def _validate_tool_class(self, tool_class: Type[BaseTool]) -> None:
        """Validate that a tool class meets requirements.

        Args:
            tool_class: Tool class to validate

        Raises:
            RegistryError: If validation fails
        """
        # Check if it's a subclass of BaseTool
        if not issubclass(tool_class, BaseTool):
            raise RegistryError(
                f"Tool class {tool_class.__name__} must inherit from BaseTool",
                error_code=ErrorCode.TOOL_REGISTRATION_ERROR,
            )

        # Check if it's not the abstract base class
        if tool_class is BaseTool:
            raise RegistryError(
                "Cannot register abstract BaseTool class",
                error_code=ErrorCode.TOOL_REGISTRATION_ERROR,
            )

        # Check required methods exist at class level (don't instantiate yet)
        required_methods = ["get_config_schema", "validate_config", "execute"]
        for method in required_methods:
            if not hasattr(tool_class, method):
                raise RegistryError(
                    f"Tool {tool_class.__name__} must implement {method} method",
                    error_code=ErrorCode.TOOL_REGISTRATION_ERROR,
                )

        # Try to instantiate only to check properties (optional validation)
        try:
            instance = tool_class()

            # Check required properties
            required_props = ["name", "description", "version"]
            for prop in required_props:
                value = getattr(instance, prop)
                if not value or not isinstance(value, str):
                    raise RegistryError(
                        f"Tool {tool_class.__name__} must have valid {prop} property",
                        error_code=ErrorCode.TOOL_REGISTRATION_ERROR,
                    )

        except RegistryError:
            # Re-raise registry errors as-is
            raise
        except Exception:
            # For other exceptions during instantiation, we'll allow registration
            # but warn that instantiation might fail later
            logger.warning(f"Tool {tool_class.__name__} failed instantiation during validation - "
                         "registration allowed but creation may fail")

    def unregister_tool(self, name: str) -> bool:
        """Unregister a tool with logging and cleanup.

        Args:
            name: Name of the tool to unregister

        Returns:
            True if tool was unregistered, False if tool was not found
        """
        with self._lock:
            if name in self._tools:
                metadata = self._tools[name]
                del self._tools[name]
                logger.info(
                    f"Unregistered tool: {name} v{metadata.version} "
                    f"(used {metadata.usage_count} times)"
                )
                return True
            return False

    def get_tool_class(self, name: str) -> Optional[Type[BaseTool]]:
        """Get a tool class by name with usage tracking.

        Args:
            name: Name of the tool

        Returns:
            Tool class or None if not found
        """
        with self._lock:
            metadata = self._tools.get(name)
            if metadata:
                metadata.usage_count += 1
                metadata.last_used = time.time()
                return metadata.tool_class
            return None

    def create_tool(self, name: str) -> Optional[BaseTool]:
        """Create an instance of a tool with error handling.

        Args:
            name: Name of the tool

        Returns:
            Tool instance or None if tool not found

        Raises:
            RegistryError: If tool creation fails
        """
        tool_class = self.get_tool_class(name)
        if tool_class:
            try:
                return tool_class()
            except Exception as e:
                raise registry_error(
                    f"Failed to create tool instance: {str(e)}",
                    tool_name=name,
                    operation="create",
                    cause=e,
                ) from e
        return None

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool instance by name (alias for create_tool).

        Args:
            name: Name of the tool

        Returns:
            Tool instance or None if tool not found
        """
        return self.create_tool(name)

    def get_tool_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive metadata for a tool.

        Args:
            name: Name of the tool

        Returns:
            Tool metadata dictionary or None if not found
        """
        with self._lock:
            metadata = self._tools.get(name)
            return metadata.to_dict() if metadata else None

    def list_tools(self, include_metadata: bool = False) -> Union[List[str], List[Dict[str, Any]]]:
        """Get list of all registered tools.

        Args:
            include_metadata: Whether to include full metadata

        Returns:
            List of tool names or metadata dictionaries
        """
        with self._lock:
            if include_metadata:
                return [metadata.to_dict() for metadata in self._tools.values()]
            return list(self._tools.keys())

    def list_tools_by_pattern(self, pattern: str) -> List[str]:
        """Get list of tools matching a name pattern.

        Args:
            pattern: Pattern to match against tool names (supports wildcards)

        Returns:
            List of tool names matching the pattern
        """
        import fnmatch

        with self._lock:
            return [
                name for name in self._tools.keys()
                if fnmatch.fnmatch(name, pattern)
            ]

    def get_tool_statistics(self) -> Dict[str, Any]:
        """Get registry statistics.

        Returns:
            Dictionary with registry statistics
        """
        with self._lock:
            total_tools = len(self._tools)
            total_usage = sum(metadata.usage_count for metadata in self._tools.values())

            most_used = None
            if self._tools:
                most_used_metadata = max(
                    self._tools.values(),
                    key=lambda m: m.usage_count
                )
                most_used = {
                    "name": most_used_metadata.name,
                    "usage_count": most_used_metadata.usage_count,
                }

            return {
                "total_tools": total_tools,
                "total_usage": total_usage,
                "most_used_tool": most_used,
                "plugin_directories": [str(p) for p in self._plugin_directories],
                "discovery_cache_size": len(self._discovery_cache),
            }

    def add_plugin_directory(self, directory: Path, auto_load: bool = True) -> None:
        """Add a directory to search for plugins.

        Args:
            directory: Path to plugin directory
            auto_load: Whether to immediately load plugins from directory
        """
        directory = Path(directory)
        if not directory.exists():
            logger.warning(f"Plugin directory does not exist: {directory}")
            return

        if not directory.is_dir():
            logger.warning(f"Plugin path is not a directory: {directory}")
            return

        with self._lock:
            if directory not in self._plugin_directories:
                self._plugin_directories.append(directory)
                logger.info(f"Added plugin directory: {directory}")

                if auto_load:
                    self.load_plugins_from_directory(directory)

    def load_plugins_from_directory(self, directory: Path) -> int:
        """Load plugins from a directory with enhanced error handling.

        Args:
            directory: Directory to scan for plugins

        Returns:
            Number of plugins loaded successfully
        """
        directory = Path(directory)
        if not directory.exists() or not directory.is_dir():
            logger.warning(f"Plugin directory does not exist: {directory}")
            return 0

        loaded_count = 0
        failed_count = 0

        # Look for Python files in the directory
        for plugin_file in directory.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue  # Skip private files

            try:
                loaded = self._load_plugin_file(plugin_file)
                loaded_count += loaded
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to load plugin {plugin_file}: {e}")

        logger.info(
            f"Plugin loading complete: {loaded_count} loaded, "
            f"{failed_count} failed from {directory}"
        )
        return loaded_count

    def _load_plugin_file(self, plugin_file: Path) -> int:
        """Load a single plugin file.

        Args:
            plugin_file: Path to plugin file

        Returns:
            Number of tools loaded from the file
        """
        # Check if this is a built-in tool (in retileup package structure)
        retileup_root = Path(__file__).parent.parent
        try:
            relative_path = plugin_file.relative_to(retileup_root)
            is_builtin = True
        except ValueError:
            is_builtin = False

        if is_builtin:
            # Handle built-in tools using proper package imports
            return self._load_builtin_tool(plugin_file, relative_path)
        else:
            # Handle external plugins using isolated loading
            return self._load_external_plugin(plugin_file)

    def _load_builtin_tool(self, plugin_file: Path, relative_path: Path) -> int:
        """Load a built-in tool using proper package imports.

        Args:
            plugin_file: Path to the tool file
            relative_path: Relative path from retileup root

        Returns:
            Number of tools loaded from the file
        """
        try:
            # Convert file path to module name
            module_parts = relative_path.parts[:-1] + (relative_path.stem,)
            module_name = f"retileup.{'.'.join(module_parts)}"

            # Import using standard Python import mechanism
            module = importlib.import_module(module_name)

            tools_loaded = 0

            # Look for tool classes in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type) and
                    issubclass(attr, BaseTool) and
                    attr is not BaseTool
                ):
                    try:
                        self.register_tool(attr)

                        # Add plugin path to metadata
                        tool_instance = attr()
                        metadata = self._tools.get(tool_instance.name)
                        if metadata:
                            metadata.plugin_path = plugin_file

                        tools_loaded += 1
                        logger.debug(f"Loaded built-in tool {attr_name} from {module_name}")
                    except Exception as e:
                        logger.error(f"Failed to register built-in tool {attr_name} from {module_name}: {e}")

            return tools_loaded

        except Exception as e:
            logger.error(f"Failed to load built-in tool {plugin_file}: {e}")
            return 0

    def _load_external_plugin(self, plugin_file: Path) -> int:
        """Load an external plugin file using isolated loading.

        Args:
            plugin_file: Path to the plugin file

        Returns:
            Number of tools loaded from the file
        """
        try:
            spec = importlib.util.spec_from_file_location(
                plugin_file.stem, plugin_file
            )
            if not spec or not spec.loader:
                logger.warning(f"Could not create module spec for {plugin_file}")
                return 0

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            tools_loaded = 0

            # Look for tool classes in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type) and
                    issubclass(attr, BaseTool) and
                    attr is not BaseTool
                ):
                    try:
                        self.register_tool(attr)

                        # Add plugin path to metadata
                        tool_instance = attr()
                        metadata = self._tools.get(tool_instance.name)
                        if metadata:
                            metadata.plugin_path = plugin_file

                        tools_loaded += 1
                        logger.debug(f"Loaded external plugin {attr_name} from {plugin_file}")
                    except Exception as e:
                        logger.error(f"Failed to register external plugin {attr_name} from {plugin_file}: {e}")

            return tools_loaded

        except Exception as e:
            logger.error(f"Failed to load external plugin {plugin_file}: {e}")
            return 0

    def auto_discover_tools(self, force_refresh: bool = False) -> int:
        """Automatically discover and load tools from all directories.

        Args:
            force_refresh: Whether to force refresh of discovery cache

        Returns:
            Total number of tools discovered and loaded
        """
        if not self._auto_discovery_enabled:
            logger.debug("Auto-discovery is disabled")
            return 0

        total_loaded = 0

        with self._lock:
            for directory in self._plugin_directories:
                # Check cache to avoid unnecessary rescanning
                cache_key = str(directory)
                last_scan = self._discovery_cache.get(cache_key, 0)
                current_time = time.time()

                # Rescan if forced or if it's been more than 5 minutes
                if force_refresh or (current_time - last_scan) > 300:
                    loaded = self.load_plugins_from_directory(directory)
                    total_loaded += loaded
                    self._discovery_cache[cache_key] = current_time

        logger.info(f"Auto-discovery completed: {total_loaded} tools loaded")
        return total_loaded

    def enable_auto_discovery(self, enabled: bool = True) -> None:
        """Enable or disable auto-discovery.

        Args:
            enabled: Whether to enable auto-discovery
        """
        self._auto_discovery_enabled = enabled
        logger.info(f"Auto-discovery {'enabled' if enabled else 'disabled'}")

    def validate_tool_health(self, name: str) -> Dict[str, Any]:
        """Validate that a tool is healthy and functional.

        Args:
            name: Name of the tool to validate

        Returns:
            Health check results
        """
        tool_class = self.get_tool_class(name)
        if not tool_class:
            return {
                "healthy": False,
                "error": f"Tool '{name}' not found",
                "error_code": ErrorCode.TOOL_NOT_FOUND.value,
            }

        try:
            # Try to instantiate the tool
            tool_instance = tool_class()

            # Check basic properties
            checks = {
                "name": bool(tool_instance.name),
                "description": bool(tool_instance.description),
                "version": bool(tool_instance.version),
                "config_schema": callable(tool_instance.get_config_schema),
                "validate_config": callable(tool_instance.validate_config),
                "execute": callable(tool_instance.execute),
            }

            all_healthy = all(checks.values())

            return {
                "healthy": all_healthy,
                "checks": checks,
                "tool_name": tool_instance.name,
                "tool_version": tool_instance.version,
            }

        except Exception as e:
            return {
                "healthy": False,
                "error": f"Health check failed: {str(e)}",
                "error_code": ErrorCode.TOOL_EXECUTION_ERROR.value,
            }

    def clear_registry(self, confirm: bool = False) -> None:
        """Clear all registered tools with confirmation.

        Args:
            confirm: Confirmation flag to prevent accidental clearing
        """
        if not confirm:
            logger.warning("Clear registry called without confirmation")
            return

        with self._lock:
            tool_count = len(self._tools)
            self._tools.clear()
            self._discovery_cache.clear()
            logger.info(f"Cleared tool registry ({tool_count} tools removed)")

    def export_registry_state(self) -> Dict[str, Any]:
        """Export the current registry state for backup/restore.

        Returns:
            Registry state dictionary
        """
        with self._lock:
            return {
                "tools": {name: metadata.to_dict() for name, metadata in self._tools.items()},
                "plugin_directories": [str(p) for p in self._plugin_directories],
                "discovery_cache": dict(self._discovery_cache),
                "auto_discovery_enabled": self._auto_discovery_enabled,
                "export_time": time.time(),
            }

    def __len__(self) -> int:
        """Get number of registered tools."""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    def __iter__(self):
        """Iterate over tool names."""
        return iter(self._tools.keys())

    def __repr__(self) -> str:
        """String representation of the registry."""
        return f"<ToolRegistry(tools={len(self._tools)}, directories={len(self._plugin_directories)})>"


# Global registry instance
_global_registry: Optional[ToolRegistry] = None
_registry_lock = threading.Lock()


def get_global_registry() -> ToolRegistry:
    """Get the global tool registry instance.

    Returns:
        Global ToolRegistry instance (thread-safe singleton)
    """
    global _global_registry

    if _global_registry is None:
        with _registry_lock:
            if _global_registry is None:
                _global_registry = ToolRegistry()
                # Perform initial auto-discovery
                _global_registry.auto_discover_tools()

    return _global_registry


def reset_global_registry() -> None:
    """Reset the global registry (mainly for testing)."""
    global _global_registry

    with _registry_lock:
        _global_registry = None