"""Configuration management for ReTileUp."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field("INFO", description="Logging level")
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    file: Optional[Path] = Field(None, description="Log file path")


class PerformanceConfig(BaseModel):
    """Performance configuration."""

    max_workers: int = Field(4, description="Maximum number of worker threads")
    chunk_size: int = Field(1024, description="Processing chunk size in KB")
    memory_limit: Optional[int] = Field(None, description="Memory limit in MB")


class OutputConfig(BaseModel):
    """Output configuration."""

    directory: Path = Field(Path("outputs"), description="Default output directory")
    format: str = Field("PNG", description="Default output format")
    quality: int = Field(95, description="Default output quality (for JPEG)")
    overwrite: bool = Field(False, description="Overwrite existing files")

    @field_validator("quality")
    @classmethod
    def validate_quality(cls, v: int) -> int:
        """Validate quality value."""
        if not 1 <= v <= 100:
            raise ValueError("Quality must be between 1 and 100")
        return v


class Config(BaseModel):
    """Main configuration class for ReTileUp."""

    # Core settings
    version: str = Field("1.0.0", description="Configuration version")
    debug: bool = Field(False, description="Enable debug mode")

    # Component configurations
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)

    # Tool-specific configurations
    tool_configs: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Tool-specific configuration overrides"
    )

    # Plugin directories
    plugin_directories: List[Path] = Field(
        default_factory=list,
        description="Additional directories to search for plugins"
    )

    model_config = ConfigDict(extra="allow")  # Allow additional fields for extensibility

    @classmethod
    def load_from_file(cls, config_path: Union[str, Path]) -> "Config":
        """Load configuration from a YAML file."""
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        return cls(**config_data)

    @classmethod
    def load_from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        config_data: Dict[str, Any] = {}

        # Check for debug mode
        if os.getenv("RETILEUP_DEBUG"):
            config_data["debug"] = os.getenv("RETILEUP_DEBUG").lower() in ("true", "1", "yes")

        # Logging configuration
        logging_config: Dict[str, Any] = {}
        if log_level := os.getenv("RETILEUP_LOG_LEVEL"):
            logging_config["level"] = log_level
        if log_file := os.getenv("RETILEUP_LOG_FILE"):
            logging_config["file"] = Path(log_file)
        if logging_config:
            config_data["logging"] = logging_config

        # Performance configuration
        performance_config: Dict[str, Any] = {}
        if max_workers := os.getenv("RETILEUP_MAX_WORKERS"):
            performance_config["max_workers"] = int(max_workers)
        if chunk_size := os.getenv("RETILEUP_CHUNK_SIZE"):
            performance_config["chunk_size"] = int(chunk_size)
        if memory_limit := os.getenv("RETILEUP_MEMORY_LIMIT"):
            performance_config["memory_limit"] = int(memory_limit)
        if performance_config:
            config_data["performance"] = performance_config

        # Output configuration
        output_config: Dict[str, Any] = {}
        if output_dir := os.getenv("RETILEUP_OUTPUT_DIR"):
            output_config["directory"] = Path(output_dir)
        if output_format := os.getenv("RETILEUP_OUTPUT_FORMAT"):
            output_config["format"] = output_format
        if output_quality := os.getenv("RETILEUP_OUTPUT_QUALITY"):
            output_config["quality"] = int(output_quality)
        if overwrite := os.getenv("RETILEUP_OVERWRITE"):
            output_config["overwrite"] = overwrite.lower() in ("true", "1", "yes")
        if output_config:
            config_data["output"] = output_config

        return cls(**config_data)

    @classmethod
    def load_default(cls) -> "Config":
        """Load default configuration."""
        return cls()

    @classmethod
    def load_config(cls, config_path: Optional[Union[str, Path]] = None) -> "Config":
        """Load configuration with fallback chain.

        Priority:
        1. Explicit config file path
        2. Environment variables
        3. Default configuration
        """
        if config_path:
            return cls.load_from_file(config_path)

        # Try environment variables
        env_config = cls.load_from_env()

        # If no environment config was found, use defaults
        if not any([env_config.debug, env_config.logging.file, env_config.tool_configs]):
            return cls.load_default()

        return env_config

    def save_to_file(self, config_path: Union[str, Path]) -> None:
        """Save configuration to a YAML file."""
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict and handle Path objects
        config_dict = self.dict()

        def convert_paths(obj: Any) -> Any:
            if isinstance(obj, Path):
                return str(obj)
            elif isinstance(obj, dict):
                return {k: convert_paths(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_paths(item) for item in obj]
            return obj

        config_dict = convert_paths(config_dict)

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config_dict, f, default_flow_style=False, indent=2)

    def get_tool_config(self, tool_name: str) -> Dict[str, Any]:
        """Get configuration for a specific tool."""
        return self.tool_configs.get(tool_name, {})

    def set_tool_config(self, tool_name: str, config: Dict[str, Any]) -> None:
        """Set configuration for a specific tool."""
        self.tool_configs[tool_name] = config