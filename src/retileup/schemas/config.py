"""Configuration schema definitions for ReTileUp.

This module provides comprehensive configuration schemas for the ReTileUp
framework, including tool configuration, workflow definitions, and
validation decorators for structured configuration management.
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LoggingConfigSchema(BaseModel):
    """Schema for logging configuration."""

    level: str = Field("INFO", description="Logging level")
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    file: Optional[str] = Field(None, description="Log file path")

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid logging level. Must be one of: {valid_levels}")
        return v.upper()


class PerformanceConfigSchema(BaseModel):
    """Schema for performance configuration."""

    max_workers: int = Field(4, description="Maximum number of worker threads", ge=1, le=32)
    chunk_size: int = Field(1024, description="Processing chunk size in KB", ge=1)
    memory_limit: Optional[int] = Field(
        None,
        description="Memory limit in MB",
        ge=1
    )


class OutputConfigSchema(BaseModel):
    """Schema for output configuration."""

    directory: str = Field("outputs", description="Default output directory")
    format: str = Field("PNG", description="Default output format")
    quality: int = Field(95, description="Default output quality (for JPEG)", ge=1, le=100)
    overwrite: bool = Field(False, description="Overwrite existing files")

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate output format."""
        valid_formats = ["PNG", "JPEG", "JPG", "BMP", "TIFF", "WEBP"]
        if v.upper() not in valid_formats:
            raise ValueError(f"Invalid format. Must be one of: {valid_formats}")
        return v.upper()


class ToolConfigSchema(BaseModel):
    """Schema for tool-specific configuration."""

    enabled: bool = Field(True, description="Whether the tool is enabled")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Default parameters for the tool"
    )
    timeout: Optional[float] = Field(
        None,
        description="Tool execution timeout in seconds",
        ge=0
    )
    priority: int = Field(0, description="Tool priority for automatic selection")


class PluginConfigSchema(BaseModel):
    """Schema for plugin configuration."""

    directories: List[str] = Field(
        default_factory=list,
        description="Additional directories to search for plugins"
    )
    auto_load: bool = Field(True, description="Automatically load plugins on startup")
    blacklist: List[str] = Field(
        default_factory=list,
        description="Plugin names to exclude from loading"
    )
    whitelist: Optional[List[str]] = Field(
        None,
        description="Only load plugins in this list (if specified)"
    )


class ConfigSchema(BaseModel):
    """Main configuration schema for ReTileUp."""

    version: str = Field("1.0.0", description="Configuration version")
    debug: bool = Field(False, description="Enable debug mode")

    # Component configurations
    logging: LoggingConfigSchema = Field(
        default_factory=LoggingConfigSchema,
        description="Logging configuration"
    )
    performance: PerformanceConfigSchema = Field(
        default_factory=PerformanceConfigSchema,
        description="Performance configuration"
    )
    output: OutputConfigSchema = Field(
        default_factory=OutputConfigSchema,
        description="Output configuration"
    )

    # Tool configurations
    tools: Dict[str, ToolConfigSchema] = Field(
        default_factory=dict,
        description="Tool-specific configurations"
    )

    # Plugin configuration
    plugins: PluginConfigSchema = Field(
        default_factory=PluginConfigSchema,
        description="Plugin configuration"
    )

    # Environment-specific settings
    environment: Dict[str, Any] = Field(
        default_factory=dict,
        description="Environment-specific settings"
    )

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate version format."""
        import re
        if not re.match(r'^\d+\.\d+\.\d+$', v):
            raise ValueError("Version must be in format 'x.y.z'")
        return v

    def get_tool_config(self, tool_name: str) -> ToolConfigSchema:
        """Get configuration for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool configuration schema
        """
        return self.tools.get(tool_name, ToolConfigSchema())

    def set_tool_config(self, tool_name: str, config: ToolConfigSchema) -> None:
        """Set configuration for a specific tool.

        Args:
            tool_name: Name of the tool
            config: Tool configuration schema
        """
        self.tools[tool_name] = config


class WorkflowConfigSchema(BaseModel):
    """Schema for workflow-specific configuration."""

    parallel_execution: bool = Field(False, description="Enable parallel step execution")
    stop_on_error: bool = Field(True, description="Stop workflow on first error")
    retry_failed_steps: bool = Field(False, description="Retry failed steps")
    max_retries: int = Field(3, description="Maximum number of retries", ge=0, le=10)
    step_timeout: Optional[float] = Field(
        None,
        description="Default step timeout in seconds",
        ge=0
    )

    # Progress tracking
    show_progress: bool = Field(True, description="Show progress bars")
    progress_format: str = Field("detailed", description="Progress bar format")

    # Output settings
    save_intermediate: bool = Field(False, description="Save intermediate results")
    intermediate_format: str = Field("PNG", description="Format for intermediate files")

    @field_validator("progress_format")
    @classmethod
    def validate_progress_format(cls, v: str) -> str:
        """Validate progress format."""
        valid_formats = ["simple", "detailed", "minimal"]
        if v not in valid_formats:
            raise ValueError(f"Invalid progress format. Must be one of: {valid_formats}")
        return v


class ValidationConfigSchema(BaseModel):
    """Schema for validation configuration."""

    strict_mode: bool = Field(False, description="Enable strict validation")
    check_file_permissions: bool = Field(True, description="Check file permissions")
    validate_image_integrity: bool = Field(True, description="Validate image file integrity")
    max_file_size_mb: Optional[int] = Field(
        None,
        description="Maximum allowed file size in MB",
        ge=1
    )
    allowed_formats: Optional[List[str]] = Field(
        None,
        description="List of allowed image formats"
    )

    @field_validator("allowed_formats", mode="before")
    @classmethod
    def validate_formats(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate and normalize format names."""
        if v is None:
            return v
        return [fmt.upper() for fmt in v]


class SecurityConfigSchema(BaseModel):
    """Schema for security configuration."""

    sandbox_mode: bool = Field(False, description="Enable sandbox mode")
    allowed_paths: List[str] = Field(
        default_factory=list,
        description="List of allowed file paths"
    )
    blocked_paths: List[str] = Field(
        default_factory=list,
        description="List of blocked file paths"
    )
    max_memory_usage_mb: Optional[int] = Field(
        None,
        description="Maximum memory usage in MB",
        ge=1
    )
    max_execution_time_s: Optional[float] = Field(
        None,
        description="Maximum execution time in seconds",
        ge=0
    )


class ExtendedConfigSchema(ConfigSchema):
    """Extended configuration schema with additional settings."""

    workflow: WorkflowConfigSchema = Field(
        default_factory=WorkflowConfigSchema,
        description="Workflow configuration"
    )
    validation: ValidationConfigSchema = Field(
        default_factory=ValidationConfigSchema,
        description="Validation configuration"
    )
    security: SecurityConfigSchema = Field(
        default_factory=SecurityConfigSchema,
        description="Security configuration"
    )

    # Experimental features
    experimental: Dict[str, Any] = Field(
        default_factory=dict,
        description="Experimental feature flags"
    )

    model_config = ConfigDict(extra="allow")