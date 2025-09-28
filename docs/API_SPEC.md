# ReTileUp - API Specification

## 1. Overview

This document defines the complete API specification for ReTileUp, including CLI commands, Python APIs, configuration schemas, and data models.

## 2. CLI Command Reference

### 2.1 Global Options

All commands support the following global options:

```bash
retileup [GLOBAL_OPTIONS] <command> [COMMAND_OPTIONS] [ARGUMENTS]
```

#### Global Options
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--config` | `-c` | Path | auto-detect | Configuration file path |
| `--verbose` | `-v` | Flag | False | Enable verbose output |
| `--quiet` | `-q` | Flag | False | Suppress non-error output |
| `--help` | `-h` | Flag | - | Show help message |
| `--version` | - | Flag | - | Show version information |

#### Configuration File Discovery
1. `./retileup.yaml` (project config)
2. `~/.retileup.yaml` (user config)
3. `~/.config/retileup/config.yaml` (XDG config)

### 2.2 Command: `tile`

Extract rectangular tiles from images at specified coordinates.

#### Syntax
```bash
retileup tile [OPTIONS] INPUT_FILE
```

#### Arguments
| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `INPUT_FILE` | Path | Yes | Input image file path |

#### Options
| Option | Short | Type | Required | Default | Description |
|--------|-------|------|----------|---------|-------------|
| `--width` | `-w` | Integer | Yes | - | Tile width in pixels |
| `--height` | `-h` | Integer | Yes | - | Tile height in pixels |
| `--coords` | `-c` | String | Yes | - | Coordinates as "x1,y1;x2,y2;..." |
| `--output` | `-o` | Path | No | `./output` | Output directory |
| `--pattern` | `-p` | String | No | `{base}_{x}_{y}.{ext}` | Output filename pattern |
| `--dry-run` | - | Flag | No | False | Show actions without executing |
| `--overlap` | - | Integer | No | 0 | Tile overlap in pixels |
| `--maintain-aspect` | - | Flag | No | False | Maintain aspect ratio |

#### Examples
```bash
# Basic tiling
retileup tile --width 256 --height 256 --coords "0,0;256,0;0,256" image.jpg

# Custom output directory and pattern
retileup tile -w 100 -h 100 -c "0,0;100,100" -o ./tiles -p "tile_{x}_{y}.png" photo.jpg

# Dry run to preview actions
retileup tile --width 200 --height 200 --coords "0,0" --dry-run large_image.png
```

#### Exit Codes
| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | General error (invalid arguments, file not found, etc.) |
| 2 | Validation error (coordinates out of bounds, invalid dimensions) |
| 3 | Processing error (image format unsupported, write permission denied) |

### 2.3 Command: `workflow`

Execute predefined workflows from configuration files.

#### Syntax
```bash
retileup workflow [OPTIONS] WORKFLOW_NAME
```

#### Arguments
| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `WORKFLOW_NAME` | String | Yes | Name of workflow to execute |

#### Options
| Option | Short | Type | Required | Default | Description |
|--------|-------|------|----------|---------|-------------|
| `--input` | `-i` | Path | Yes | - | Input file or directory |
| `--output` | `-o` | Path | No | `./output` | Output directory |
| `--config` | `-c` | Path | No | auto-detect | Workflow configuration file |
| `--dry-run` | - | Flag | No | False | Preview workflow without execution |
| `--parallel` | - | Integer | No | 4 | Maximum parallel jobs |

#### Examples
```bash
# Execute workflow from default config
retileup workflow web-optimize --input ./photos --output ./web

# Use specific config file
retileup workflow thumbnail-gen --input image.jpg --config ./custom-workflows.yaml

# Dry run to preview workflow
retileup workflow batch-process --input ./images --dry-run
```

### 2.4 Command: `list-tools`

Display available tools and their descriptions.

#### Syntax
```bash
retileup list-tools [OPTIONS]
```

#### Options
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--detailed` | `-d` | Flag | False | Show detailed tool information |
| `--format` | `-f` | String | `table` | Output format: table, json, yaml |

#### Examples
```bash
# List all tools
retileup list-tools

# Detailed information
retileup list-tools --detailed

# JSON output for scripting
retileup list-tools --format json
```

### 2.5 Command: `validate`

Validate configuration files and workflows.

#### Syntax
```bash
retileup validate [OPTIONS] CONFIG_FILE
```

#### Arguments
| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `CONFIG_FILE` | Path | Yes | Configuration file to validate |

#### Options
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--strict` | `-s` | Flag | False | Enable strict validation |
| `--format` | `-f` | String | `human` | Output format: human, json |

## 3. Configuration Schema

### 3.1 Main Configuration File

Configuration files use YAML format with the following structure:

```yaml
# Global application settings
global:
  default_output_dir: "./output"
  max_parallel_jobs: 4
  log_level: "INFO"
  preserve_metadata: true

# Default settings for tools
tool_defaults:
  tile:
    output_pattern: "{base}_{x}_{y}.{ext}"
    maintain_aspect: false
    overlap: 0

# Workflow definitions
workflows:
  web-optimize:
    name: "Web Optimization"
    description: "Optimize images for web deployment"
    steps:
      - tool: "tile"
        config:
          tile_width: 1200
          tile_height: 800
          coordinates: [[0, 0]]
          output_pattern: "{base}_web.{ext}"

  thumbnail-batch:
    name: "Thumbnail Generation"
    description: "Generate multiple thumbnail sizes"
    steps:
      - tool: "tile"
        config:
          tile_width: 150
          tile_height: 150
          coordinates: [[0, 0]]
          output_pattern: "{base}_thumb_150.{ext}"
      - tool: "tile"
        config:
          tile_width: 300
          tile_height: 300
          coordinates: [[0, 0]]
          output_pattern: "{base}_thumb_300.{ext}"
```

### 3.2 Schema Validation

#### Global Configuration Schema
```yaml
global:
  type: object
  properties:
    default_output_dir:
      type: string
      format: path
      default: "./output"
    max_parallel_jobs:
      type: integer
      minimum: 1
      maximum: 16
      default: 4
    log_level:
      type: string
      enum: ["DEBUG", "INFO", "WARNING", "ERROR"]
      default: "INFO"
    preserve_metadata:
      type: boolean
      default: true
  additionalProperties: false
```

#### Tool Defaults Schema
```yaml
tool_defaults:
  type: object
  properties:
    tile:
      type: object
      properties:
        output_pattern:
          type: string
          pattern: ".*\\{base\\}.*\\{ext\\}.*"
          default: "{base}_{x}_{y}.{ext}"
        maintain_aspect:
          type: boolean
          default: false
        overlap:
          type: integer
          minimum: 0
          default: 0
      additionalProperties: false
  additionalProperties: true
```

#### Workflow Schema
```yaml
workflow:
  type: object
  required: ["name", "steps"]
  properties:
    name:
      type: string
      minLength: 1
    description:
      type: string
      default: ""
    steps:
      type: array
      minItems: 1
      items:
        type: object
        required: ["tool", "config"]
        properties:
          tool:
            type: string
            enum: ["tile"]  # Will expand with new tools
          config:
            type: object
            # Schema varies by tool
          condition:
            type: string
            description: "Future: conditional execution"
        additionalProperties: false
  additionalProperties: false
```

## 4. Python API Reference

### 4.1 Core Classes

#### Tool Base Class
```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pathlib import Path
from pydantic import BaseModel

class ToolResult(BaseModel):
    """Result of tool execution"""
    success: bool
    message: str
    output_files: List[Path] = []
    metadata: Dict[str, Any] = {}
    execution_time: float = 0.0

class ToolConfig(BaseModel):
    """Base configuration for all tools"""
    input_path: Path
    output_dir: Optional[Path] = None
    dry_run: bool = False
    verbose: bool = False

class BaseTool(ABC):
    """Abstract base class for all image processing tools"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for CLI and registry"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for help text"""
        pass

    @property
    def version(self) -> str:
        """Tool version"""
        return "1.0.0"

    @abstractmethod
    def get_config_schema(self) -> Dict[str, Any]:
        """Return JSON schema for tool configuration"""
        pass

    @abstractmethod
    def validate_config(self, config: ToolConfig) -> List[str]:
        """Validate tool configuration, return list of errors"""
        pass

    @abstractmethod
    def execute(self, config: ToolConfig) -> ToolResult:
        """Execute tool with given configuration"""
        pass

    def setup(self) -> None:
        """Optional setup before execution"""
        pass

    def cleanup(self) -> None:
        """Optional cleanup after execution"""
        pass
```

#### Tiling Tool Implementation
```python
from PIL import Image
from typing import List, Tuple
import time

class TilingConfig(ToolConfig):
    """Configuration for image tiling tool"""
    tile_width: int
    tile_height: int
    coordinates: List[Tuple[int, int]]
    output_pattern: str = "{base}_{x}_{y}.{ext}"
    maintain_aspect: bool = False
    overlap: int = 0

    @validator('tile_width', 'tile_height')
    def positive_dimensions(cls, v):
        if v <= 0:
            raise ValueError('Dimensions must be positive')
        return v

    @validator('coordinates')
    def valid_coordinates(cls, v):
        if not v:
            raise ValueError('At least one coordinate required')
        for x, y in v:
            if x < 0 or y < 0:
                raise ValueError('Coordinates must be non-negative')
        return v

class TilingTool(BaseTool):
    """Image tiling tool implementation"""

    @property
    def name(self) -> str:
        return "tile"

    @property
    def description(self) -> str:
        return "Extract rectangular tiles from images at specified coordinates"

    def get_config_schema(self) -> Dict[str, Any]:
        """Return JSON schema for tiling configuration"""
        return {
            "type": "object",
            "required": ["tile_width", "tile_height", "coordinates"],
            "properties": {
                "tile_width": {"type": "integer", "minimum": 1},
                "tile_height": {"type": "integer", "minimum": 1},
                "coordinates": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 2,
                        "maxItems": 2
                    },
                    "minItems": 1
                },
                "output_pattern": {"type": "string"},
                "maintain_aspect": {"type": "boolean"},
                "overlap": {"type": "integer", "minimum": 0}
            }
        }

    def validate_config(self, config: TilingConfig) -> List[str]:
        """Validate tiling configuration"""
        errors = []

        # Validate input file
        if not config.input_path.exists():
            errors.append(f"Input file not found: {config.input_path}")
            return errors

        # Validate image format and get dimensions
        try:
            with Image.open(config.input_path) as img:
                img_width, img_height = img.size
        except Exception as e:
            errors.append(f"Cannot open image: {e}")
            return errors

        # Validate coordinates within bounds
        for x, y in config.coordinates:
            tile_right = x + config.tile_width - config.overlap
            tile_bottom = y + config.tile_height - config.overlap

            if tile_right > img_width:
                errors.append(f"Tile at ({x}, {y}) exceeds image width")
            if tile_bottom > img_height:
                errors.append(f"Tile at ({x}, {y}) exceeds image height")

        # Validate output pattern
        try:
            test_name = config.output_pattern.format(
                base="test", x=0, y=0, ext="jpg"
            )
        except KeyError as e:
            errors.append(f"Invalid output pattern: missing {e}")

        return errors

    def execute(self, config: TilingConfig) -> ToolResult:
        """Execute tiling operation"""
        start_time = time.time()
        output_files = []

        try:
            with Image.open(config.input_path) as img:
                base_name = config.input_path.stem
                ext = config.input_path.suffix[1:]  # Remove dot

                for x, y in config.coordinates:
                    # Calculate tile bounds with overlap
                    left = max(0, x - config.overlap)
                    top = max(0, y - config.overlap)
                    right = min(img.width, x + config.tile_width + config.overlap)
                    bottom = min(img.height, y + config.tile_height + config.overlap)

                    # Extract tile
                    tile = img.crop((left, top, right, bottom))

                    # Resize if maintain_aspect is enabled
                    if config.maintain_aspect:
                        tile.thumbnail(
                            (config.tile_width, config.tile_height),
                            Image.Resampling.LANCZOS
                        )

                    # Generate output filename
                    filename = config.output_pattern.format(
                        base=base_name, x=x, y=y, ext=ext
                    )

                    output_path = config.output_dir / filename
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    # Save tile
                    if not config.dry_run:
                        tile.save(output_path, quality=95, optimize=True)

                    output_files.append(output_path)

                    if config.verbose:
                        print(f"Created tile: {output_path}")

            execution_time = time.time() - start_time

            return ToolResult(
                success=True,
                message=f"Generated {len(output_files)} tiles in {execution_time:.2f}s",
                output_files=output_files,
                metadata={
                    "tile_count": len(output_files),
                    "tile_size": f"{config.tile_width}x{config.tile_height}",
                    "overlap": config.overlap,
                    "total_pixels_processed": config.tile_width * config.tile_height * len(config.coordinates)
                },
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return ToolResult(
                success=False,
                message=f"Tiling failed: {str(e)}",
                output_files=[],
                metadata={"error": str(e), "error_type": type(e).__name__},
                execution_time=execution_time
            )
```

### 4.2 Registry and Orchestration

#### Tool Registry
```python
from typing import Dict, Type, List
import importlib
import inspect

class ToolRegistry:
    """Registry for available image processing tools"""

    def __init__(self):
        self._tools: Dict[str, Type[BaseTool]] = {}
        self._discover_tools()

    def register_tool(self, tool_class: Type[BaseTool]) -> None:
        """Register a tool class"""
        if not issubclass(tool_class, BaseTool):
            raise ValueError(f"{tool_class} must inherit from BaseTool")

        tool_instance = tool_class()
        self._tools[tool_instance.name] = tool_class

    def get_tool(self, name: str) -> BaseTool:
        """Get tool instance by name"""
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found")
        return self._tools[name]()

    def list_tools(self) -> List[Dict[str, str]]:
        """List all registered tools"""
        tools = []
        for name, tool_class in self._tools.items():
            tool_instance = tool_class()
            tools.append({
                "name": name,
                "description": tool_instance.description,
                "version": tool_instance.version
            })
        return tools

    def _discover_tools(self) -> None:
        """Automatically discover and register tools"""
        # Import and register built-in tools
        from retileup.tools.tiling import TilingTool
        self.register_tool(TilingTool)

        # Future: discover plugins from installed packages
```

#### Workflow Engine
```python
from typing import List, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor

class WorkflowEngine:
    """Executes workflows with multiple tools"""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def validate_workflow(self, workflow: Dict[str, Any]) -> List[str]:
        """Validate workflow definition"""
        errors = []

        if "steps" not in workflow:
            errors.append("Workflow must have 'steps' field")
            return errors

        for i, step in enumerate(workflow["steps"]):
            if "tool" not in step:
                errors.append(f"Step {i} missing 'tool' field")
                continue

            tool_name = step["tool"]
            try:
                tool = self.registry.get_tool(tool_name)
            except ValueError:
                errors.append(f"Step {i}: unknown tool '{tool_name}'")
                continue

            if "config" not in step:
                errors.append(f"Step {i} missing 'config' field")
                continue

            # Validate tool configuration
            try:
                config_class = tool.__class__.__annotations__.get('config', ToolConfig)
                config = config_class(**step["config"])
                tool_errors = tool.validate_config(config)
                errors.extend([f"Step {i}: {err}" for err in tool_errors])
            except Exception as e:
                errors.append(f"Step {i}: invalid config - {e}")

        return errors

    async def execute_workflow(
        self,
        workflow: Dict[str, Any],
        input_files: List[Path],
        output_dir: Path,
        parallel: bool = True
    ) -> List[ToolResult]:
        """Execute workflow on input files"""
        results = []

        if parallel and len(input_files) > 1:
            # Parallel execution for multiple files
            with ThreadPoolExecutor() as executor:
                futures = [
                    executor.submit(self._execute_single_workflow, workflow, file, output_dir)
                    for file in input_files
                ]
                results = [future.result() for future in futures]
        else:
            # Sequential execution
            for file in input_files:
                result = self._execute_single_workflow(workflow, file, output_dir)
                results.append(result)

        return results

    def _execute_single_workflow(
        self,
        workflow: Dict[str, Any],
        input_file: Path,
        output_dir: Path
    ) -> ToolResult:
        """Execute workflow on a single file"""
        overall_result = ToolResult(success=True, message="Workflow completed")
        current_input = input_file

        for step in workflow["steps"]:
            tool = self.registry.get_tool(step["tool"])

            # Prepare config for this step
            config_data = step["config"].copy()
            config_data["input_path"] = current_input
            config_data["output_dir"] = output_dir

            config_class = tool.__class__.__annotations__.get('config', ToolConfig)
            config = config_class(**config_data)

            # Execute tool
            result = tool.execute(config)

            if not result.success:
                return ToolResult(
                    success=False,
                    message=f"Workflow failed at step {step['tool']}: {result.message}",
                    metadata={"failed_step": step["tool"], "error": result.message}
                )

            # Update input for next step (use first output file)
            if result.output_files:
                current_input = result.output_files[0]

            # Accumulate metadata
            overall_result.output_files.extend(result.output_files)
            overall_result.metadata[f"step_{step['tool']}"] = result.metadata

        return overall_result
```

## 5. Data Models

### 5.1 Core Data Structures

#### Image Metadata
```python
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class ImageMetadata(BaseModel):
    """Image file metadata"""
    width: int
    height: int
    format: str
    mode: str  # RGB, RGBA, etc.
    file_size: int
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    exif_data: Optional[Dict[str, Any]] = None

class ProcessingMetadata(BaseModel):
    """Processing operation metadata"""
    tool_name: str
    tool_version: str
    execution_time: float
    input_file: str
    output_files: List[str]
    parameters: Dict[str, Any]
    timestamp: datetime
```

#### Coordinate Systems
```python
from pydantic import BaseModel, validator
from typing import Tuple

class Point(BaseModel):
    """2D point coordinate"""
    x: int
    y: int

    @validator('x', 'y')
    def non_negative(cls, v):
        if v < 0:
            raise ValueError('Coordinates must be non-negative')
        return v

class Rectangle(BaseModel):
    """Rectangle defined by top-left corner and dimensions"""
    x: int
    y: int
    width: int
    height: int

    @validator('x', 'y')
    def non_negative_position(cls, v):
        if v < 0:
            raise ValueError('Position must be non-negative')
        return v

    @validator('width', 'height')
    def positive_dimensions(cls, v):
        if v <= 0:
            raise ValueError('Dimensions must be positive')
        return v

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    def contains_point(self, point: Point) -> bool:
        """Check if point is within rectangle"""
        return (self.x <= point.x < self.right and
                self.y <= point.y < self.bottom)

    def intersects(self, other: 'Rectangle') -> bool:
        """Check if rectangle intersects with another"""
        return not (self.right <= other.x or other.right <= self.x or
                   self.bottom <= other.y or other.bottom <= self.y)
```

## 6. Error Handling

### 6.1 Exception Hierarchy
```python
class RetileupError(Exception):
    """Base exception for all ReTileUp errors"""
    def __init__(self, message: str, error_code: int = 1):
        super().__init__(message)
        self.error_code = error_code

class ValidationError(RetileupError):
    """Input validation errors"""
    def __init__(self, message: str, field: str = None):
        super().__init__(message, error_code=2)
        self.field = field

class ProcessingError(RetileupError):
    """Image processing errors"""
    def __init__(self, message: str, tool: str = None):
        super().__init__(message, error_code=3)
        self.tool = tool

class ConfigurationError(RetileupError):
    """Configuration file errors"""
    def __init__(self, message: str, file_path: str = None):
        super().__init__(message, error_code=4)
        self.file_path = file_path

class WorkflowError(RetileupError):
    """Workflow execution errors"""
    def __init__(self, message: str, step: str = None):
        super().__init__(message, error_code=5)
        self.step = step
```

### 6.2 Error Response Format
```json
{
  "success": false,
  "error": {
    "type": "ValidationError",
    "message": "Tile coordinates exceed image bounds",
    "code": 2,
    "details": {
      "field": "coordinates",
      "value": [1500, 1200],
      "constraint": "max_x: 1024, max_y: 768"
    }
  },
  "context": {
    "tool": "tile",
    "input_file": "/path/to/image.jpg",
    "timestamp": "2025-01-28T10:30:00Z"
  }
}
```

## 7. Performance Specifications

### 7.1 Performance Requirements
- **Startup Time**: < 1 second for tool discovery and CLI initialization
- **Memory Usage**: < 500MB for typical operations (single 10MP image)
- **Processing Speed**: > 10 tiles/second for 256x256 tiles from 4K images
- **Batch Processing**: Support for 1000+ images with progress tracking
- **Concurrent Jobs**: Up to CPU core count parallel operations

### 7.2 Benchmarking API
```python
import time
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class PerformanceMetrics:
    """Performance measurement data"""
    operation: str
    execution_time: float
    memory_peak_mb: float
    files_processed: int
    throughput_files_per_second: float
    metadata: Dict[str, Any]

class PerformanceBenchmark:
    """Performance benchmarking utility"""

    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []

    def benchmark_tool(self, tool: BaseTool, config: ToolConfig) -> PerformanceMetrics:
        """Benchmark tool execution"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        start_time = time.time()
        result = tool.execute(config)
        end_time = time.time()

        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_peak = max(memory_before, memory_after)

        execution_time = end_time - start_time
        files_processed = len(result.output_files) if result.success else 0
        throughput = files_processed / execution_time if execution_time > 0 else 0

        metrics = PerformanceMetrics(
            operation=f"{tool.name}_execute",
            execution_time=execution_time,
            memory_peak_mb=memory_peak,
            files_processed=files_processed,
            throughput_files_per_second=throughput,
            metadata={
                "success": result.success,
                "tool_metadata": result.metadata
            }
        )

        self.metrics.append(metrics)
        return metrics
```

## 8. Versioning and Compatibility

### 8.1 API Versioning
- **Semantic Versioning**: MAJOR.MINOR.PATCH format
- **CLI Compatibility**: Maintain backward compatibility within major versions
- **Configuration Schema**: Support for schema migration
- **Tool Interface**: Versioned tool API for plugin compatibility

### 8.2 Deprecation Policy
- **Warning Period**: 2 minor versions before removal
- **Migration Path**: Clear upgrade instructions and tooling
- **Legacy Support**: Optional legacy mode for critical features

---

**Document Version**: 1.0
**Last Updated**: 2025-01-28
**Status**: Draft - Ready for Implementation