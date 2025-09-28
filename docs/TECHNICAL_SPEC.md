# ReTileUp - Technical Specification

## 1. System Architecture Overview

### 1.1 High-Level Architecture
ReTileUp follows a modular plugin-based architecture with clear separation of concerns:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Interface │────│  Core Engine     │────│  Plugin System  │
│   (Typer)       │    │  (Orchestrator)  │    │  (Tools)        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Config Mgmt   │    │  Workflow Engine │    │  Image Utils    │
│   (YAML/JSON)   │    │  (Pipeline)      │    │  (Pillow)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 1.2 Core Components

#### 1.2.1 CLI Interface Layer
- **Entry Point**: Single `retileup` command with subcommands
- **Framework**: Typer for modern Python CLI with type hints
- **Features**: Auto-completion, rich help, progress bars
- **Configuration**: Global flags and per-command options

#### 1.2.2 Core Engine
- **Registry**: Plugin discovery and registration
- **Orchestrator**: Command routing and execution
- **Validation**: Input/parameter validation pipeline
- **Error Handling**: Centralized error management

#### 1.2.3 Plugin System
- **Base Interface**: Abstract tool interface for consistency
- **Discovery**: Automatic tool detection and registration
- **Isolation**: Each tool operates independently
- **Extensibility**: Easy addition of new processing tools

#### 1.2.4 Workflow Engine
- **Parser**: YAML/JSON workflow definition parsing
- **Executor**: Sequential and parallel execution
- **State Management**: Intermediate result handling
- **Error Recovery**: Graceful failure and rollback

## 2. Technology Stack

### 2.1 Core Dependencies
```yaml
dependencies:
  runtime:
    - python: ">=3.8"
    - pillow: ">=10.0.0"      # Core image processing
    - typer: ">=0.9.0"        # CLI framework
    - rich: ">=13.0.0"        # Terminal output formatting
    - pyyaml: ">=6.0"         # Configuration parsing
    - pydantic: ">=2.0.0"     # Data validation

  development:
    - pytest: ">=7.0.0"       # Testing framework
    - pytest-cov: ">=4.0.0"   # Coverage reporting
    - black: ">=23.0.0"       # Code formatting
    - mypy: ">=1.0.0"         # Type checking
    - ruff: ">=0.1.0"         # Linting
```

### 2.2 Rationale for Technology Choices

#### Python 3.8+
- **Advantages**: Excellent image processing ecosystem, readable code, rapid development
- **Considerations**: Cross-platform compatibility, good package management
- **Alternatives Rejected**: Go (less image processing libraries), Rust (steeper learning curve)

#### Pillow
- **Advantages**: Lightweight, excellent format support, pure Python, stable API
- **Considerations**: Sufficient for image tiling and basic operations
- **Alternatives Rejected**: OpenCV (too heavy), scikit-image (overkill for requirements)

#### Typer
- **Advantages**: Type-safe CLI, auto-completion, rich output, modern Python patterns
- **Considerations**: Good documentation, FastAPI ecosystem compatibility
- **Alternatives Rejected**: Click (less modern), argparse (too verbose)

## 3. System Design

### 3.1 Project Structure
```
ReTileUp/
├── pyproject.toml              # Modern Python packaging
├── README.md                   # User-facing documentation
├── TODO.md                     # Project tracking
├── docs/                       # Documentation
│   ├── PRD.md
│   ├── TECHNICAL_SPEC.md
│   └── API_SPEC.md
├── src/
│   └── retileup/              # Main package
│       ├── __init__.py
│       ├── __main__.py        # Entry point (python -m retileup)
│       ├── cli/               # CLI interface
│       │   ├── __init__.py
│       │   ├── main.py        # Main CLI app
│       │   └── commands/      # Individual commands
│       │       ├── __init__.py
│       │       ├── tile.py
│       │       └── workflow.py
│       ├── core/              # Core engine
│       │   ├── __init__.py
│       │   ├── registry.py    # Plugin registry
│       │   ├── orchestrator.py # Command orchestration
│       │   ├── workflow.py    # Workflow engine
│       │   └── config.py      # Configuration management
│       ├── tools/             # Processing tools
│       │   ├── __init__.py
│       │   ├── base.py        # Abstract base tool
│       │   └── tiling.py      # Image tiling tool
│       ├── utils/             # Utilities
│       │   ├── __init__.py
│       │   ├── image.py       # Image utilities
│       │   ├── validation.py  # Input validation
│       │   └── progress.py    # Progress reporting
│       └── schemas/           # Data models
│           ├── __init__.py
│           ├── config.py      # Configuration schemas
│           └── workflow.py    # Workflow schemas
├── tests/                     # Test suite
│   ├── __init__.py
│   ├── conftest.py           # Pytest configuration
│   ├── unit/                 # Unit tests
│   │   ├── test_tools/
│   │   ├── test_core/
│   │   └── test_utils/
│   ├── integration/          # Integration tests
│   │   ├── test_cli/
│   │   └── test_workflows/
│   └── fixtures/             # Test data
│       ├── images/
│       └── configs/
└── examples/                 # Usage examples
    ├── workflows/
    └── scripts/
```

### 3.2 Core Interface Definitions

#### 3.2.1 Base Tool Interface
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

#### 3.2.2 Tiling Tool Specification
```python
from pydantic import BaseModel, validator
from typing import List, Tuple, Optional

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

    def validate_config(self, config: TilingConfig) -> List[str]:
        errors = []

        # Validate input file
        if not config.input_path.exists():
            errors.append(f"Input file not found: {config.input_path}")

        # Validate image format
        try:
            with Image.open(config.input_path) as img:
                img_width, img_height = img.size
        except Exception as e:
            errors.append(f"Cannot open image: {e}")
            return errors

        # Validate coordinates within bounds
        for x, y in config.coordinates:
            if x + config.tile_width > img_width:
                errors.append(f"Tile at ({x}, {y}) exceeds image width")
            if y + config.tile_height > img_height:
                errors.append(f"Tile at ({x}, {y}) exceeds image height")

        return errors

    def execute(self, config: TilingConfig) -> ToolResult:
        output_files = []

        try:
            with Image.open(config.input_path) as img:
                for x, y in config.coordinates:
                    # Extract tile
                    tile = img.crop((x, y, x + config.tile_width, y + config.tile_height))

                    # Generate output filename
                    base_name = config.input_path.stem
                    ext = config.input_path.suffix[1:]  # Remove dot
                    filename = config.output_pattern.format(
                        base=base_name, x=x, y=y, ext=ext
                    )

                    output_path = config.output_dir / filename
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    # Save tile
                    if not config.dry_run:
                        tile.save(output_path)

                    output_files.append(output_path)

                    if config.verbose:
                        print(f"Created tile: {output_path}")

            return ToolResult(
                success=True,
                message=f"Generated {len(output_files)} tiles",
                output_files=output_files,
                metadata={
                    "tile_count": len(output_files),
                    "tile_size": f"{config.tile_width}x{config.tile_height}"
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                message=f"Tiling failed: {str(e)}",
                output_files=[],
                metadata={"error": str(e)}
            )
```

### 3.3 Configuration System

#### 3.3.1 Configuration Schema
```python
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from pathlib import Path

class GlobalConfig(BaseModel):
    """Global application configuration"""
    default_output_dir: Path = Path("./output")
    max_parallel_jobs: int = 4
    log_level: str = "INFO"
    preserve_metadata: bool = True

class ToolDefaults(BaseModel):
    """Default settings for tools"""
    tile: Dict[str, Any] = {
        "output_pattern": "{base}_{x}_{y}.{ext}",
        "maintain_aspect": False
    }

class WorkflowStep(BaseModel):
    """Single step in a workflow"""
    tool: str
    config: Dict[str, Any]
    condition: Optional[str] = None  # Future: conditional execution

class Workflow(BaseModel):
    """Complete workflow definition"""
    name: str
    description: str = ""
    steps: List[WorkflowStep]
    global_config: Optional[Dict[str, Any]] = None

class AppConfig(BaseModel):
    """Complete application configuration"""
    global_settings: GlobalConfig = GlobalConfig()
    tool_defaults: ToolDefaults = ToolDefaults()
    workflows: Dict[str, Workflow] = {}
```

#### 3.3.2 Configuration Loading Strategy
```python
from pathlib import Path
import yaml
from typing import Optional

class ConfigManager:
    """Manages application configuration with precedence"""

    CONFIG_LOCATIONS = [
        Path.cwd() / "retileup.yaml",      # Project config
        Path.home() / ".retileup.yaml",   # User config
        Path.home() / ".config" / "retileup" / "config.yaml",  # XDG config
    ]

    def __init__(self):
        self.config = AppConfig()
        self.load_config()

    def load_config(self) -> None:
        """Load configuration with precedence order"""
        for config_path in reversed(self.CONFIG_LOCATIONS):
            if config_path.exists():
                self._merge_config(config_path)

    def _merge_config(self, config_path: Path) -> None:
        """Merge configuration from file"""
        try:
            with open(config_path) as f:
                data = yaml.safe_load(f)
                # Deep merge configuration
                self._deep_merge(self.config.dict(), data)
        except Exception as e:
            print(f"Warning: Could not load config from {config_path}: {e}")
```

### 3.4 CLI Interface Design

#### 3.4.1 Main CLI Application
```python
import typer
from rich.console import Console
from rich.progress import Progress
from pathlib import Path
from typing import Optional

app = typer.Typer(
    name="retileup",
    help="ReTileUp - CLI Image Processing Toolkit",
    add_completion=True,
    rich_markup_mode="rich"
)

console = Console()

@app.callback()
def main(
    config: Optional[Path] = typer.Option(
        None, "--config", "-c",
        help="Configuration file path"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q",
        help="Suppress non-error output"
    )
):
    """ReTileUp - Image Processing Toolkit"""
    # Initialize global state
    pass

@app.command()
def tile(
    input_file: Path = typer.Argument(..., help="Input image file"),
    tile_width: int = typer.Option(..., "--width", "-w", help="Tile width in pixels"),
    tile_height: int = typer.Option(..., "--height", "-h", help="Tile height in pixels"),
    coordinates: str = typer.Option(
        ..., "--coords", "-c",
        help="Comma-separated coordinates: x1,y1;x2,y2;..."
    ),
    output_dir: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Output directory (default: ./output)"
    ),
    pattern: str = typer.Option(
        "{base}_{x}_{y}.{ext}", "--pattern", "-p",
        help="Output filename pattern"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Show what would be done without executing"
    )
):
    """Extract tiles from an image at specified coordinates"""
    # Parse coordinates
    coord_pairs = []
    for coord in coordinates.split(';'):
        x, y = map(int, coord.split(','))
        coord_pairs.append((x, y))

    # Execute tiling
    config = TilingConfig(
        input_path=input_file,
        tile_width=tile_width,
        tile_height=tile_height,
        coordinates=coord_pairs,
        output_dir=output_dir or Path("./output"),
        output_pattern=pattern,
        dry_run=dry_run
    )

    tool = TilingTool()
    errors = tool.validate_config(config)

    if errors:
        console.print("[red]Validation errors:[/red]")
        for error in errors:
            console.print(f"  • {error}")
        raise typer.Exit(1)

    with Progress() as progress:
        task = progress.add_task("Processing...", total=len(coord_pairs))
        result = tool.execute(config)
        progress.update(task, completed=len(coord_pairs))

    if result.success:
        console.print(f"[green]Success:[/green] {result.message}")
        if config.verbose:
            for file in result.output_files:
                console.print(f"  Created: {file}")
    else:
        console.print(f"[red]Error:[/red] {result.message}")
        raise typer.Exit(1)

@app.command()
def workflow(
    name: str = typer.Argument(..., help="Workflow name"),
    input_path: Path = typer.Option(..., "--input", "-i", help="Input file or directory"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory")
):
    """Execute a predefined workflow"""
    # Workflow execution logic
    pass

@app.command()
def list_tools():
    """List all available tools"""
    # Tool listing logic
    pass

if __name__ == "__main__":
    app()
```

## 4. Performance Considerations

### 4.1 Memory Management
- **Lazy Loading**: Load images only when needed
- **Streaming**: Process large images in chunks when possible
- **Resource Cleanup**: Proper resource disposal with context managers
- **Memory Limits**: Configurable memory usage limits

### 4.2 Parallel Processing
- **Batch Operations**: Parallel processing for multiple files
- **Thread Safety**: Thread-safe image operations
- **Resource Pooling**: Efficient resource utilization
- **Progress Tracking**: Real-time progress updates

### 4.3 Optimization Strategies
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Callable

class BatchProcessor:
    """Handles batch processing with parallelization"""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers

    async def process_batch(
        self,
        items: List[Any],
        processor: Callable,
        progress_callback: Optional[Callable] = None
    ) -> List[ToolResult]:
        """Process items in parallel with progress tracking"""

        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = [executor.submit(processor, item) for item in items]

            # Collect results with progress updates
            for i, future in enumerate(asyncio.as_completed(futures)):
                result = await future
                results.append(result)

                if progress_callback:
                    progress_callback(i + 1, len(items))

        return results
```

## 5. Error Handling Strategy

### 5.1 Error Classification
```python
class RetileupError(Exception):
    """Base exception for all ReTileUp errors"""
    pass

class ValidationError(RetileupError):
    """Raised when input validation fails"""
    pass

class ProcessingError(RetileupError):
    """Raised when image processing fails"""
    pass

class ConfigurationError(RetileupError):
    """Raised when configuration is invalid"""
    pass

class WorkflowError(RetileupError):
    """Raised when workflow execution fails"""
    pass
```

### 5.2 Error Recovery
- **Graceful Degradation**: Continue processing other files when one fails
- **Rollback Support**: Undo partial operations on failure
- **Clear Messaging**: Provide actionable error messages
- **Logging**: Comprehensive error logging for debugging

## 6. Testing Strategy

### 6.1 Test Architecture
```python
# tests/conftest.py
import pytest
from pathlib import Path
from PIL import Image
import tempfile

@pytest.fixture
def sample_image():
    """Create a test image"""
    img = Image.new('RGB', (800, 600), color='red')
    return img

@pytest.fixture
def temp_dir():
    """Temporary directory for test outputs"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def tiling_config(sample_image, temp_dir):
    """Standard tiling configuration for tests"""
    input_path = temp_dir / "test.jpg"
    sample_image.save(input_path)

    return TilingConfig(
        input_path=input_path,
        tile_width=100,
        tile_height=100,
        coordinates=[(0, 0), (100, 100)],
        output_dir=temp_dir
    )
```

### 6.2 Test Coverage Requirements
- **Unit Tests**: > 90% coverage for all modules
- **Integration Tests**: CLI command testing
- **Performance Tests**: Memory and speed benchmarks
- **Edge Case Tests**: Error conditions and boundary cases

## 7. Deployment and Distribution

### 7.1 Package Configuration
```toml
# pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "retileup"
version = "1.0.0"
description = "CLI Image Processing Toolkit"
readme = "README.md"
license = {file = "LICENSE"}
authors = [{name = "Author", email = "author@example.com"}]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Topic :: Multimedia :: Graphics",
]
requires-python = ">=3.8"
dependencies = [
    "pillow>=10.0.0",
    "typer>=0.9.0",
    "rich>=13.0.0",
    "pyyaml>=6.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "mypy>=1.0.0",
    "ruff>=0.1.0",
]

[project.scripts]
retileup = "retileup.cli.main:app"

[project.urls]
Homepage = "https://github.com/user/retileup"
Documentation = "https://retileup.readthedocs.io"
Repository = "https://github.com/user/retileup"
```

### 7.2 Installation Methods
- **PyPI**: `pip install retileup`
- **Development**: `pip install -e .`
- **From Source**: `git clone && pip install .`

## 8. Security Considerations

### 8.1 Input Validation
- **File Path Validation**: Prevent path traversal attacks
- **Image Format Validation**: Validate image headers before processing
- **Memory Limits**: Prevent memory exhaustion attacks
- **File Size Limits**: Configurable maximum file sizes

### 8.2 Safe Processing
- **Temporary Files**: Secure temporary file handling
- **Resource Limits**: CPU and memory usage limits
- **Error Information**: Avoid leaking sensitive information in errors

## 9. Future Extensibility

### 9.1 Plugin Architecture
- **Standard Interface**: Well-defined plugin API
- **Discovery Mechanism**: Automatic plugin detection
- **Versioning**: Plugin version compatibility checking
- **Documentation**: Plugin development guidelines

### 9.2 Potential Extensions
- **Additional Tools**: Resize, crop, filter, format conversion
- **Advanced Workflows**: Conditional execution, loops, variables
- **Performance Optimizations**: GPU acceleration, advanced algorithms
- **Integration Features**: Cloud storage, external APIs

---

**Document Version**: 1.0
**Last Updated**: 2025-01-28
**Status**: Draft - Ready for Implementation