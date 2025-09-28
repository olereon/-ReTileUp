# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ReTileUp is a modular CLI toolkit for advanced image processing and transformation workflows. It's built with Python 3.8+ and follows a plugin-based architecture with comprehensive testing (489 tests, >95% coverage).

## Development Commands

### Environment Setup
```bash
# Install in development mode with all dependencies
pip install -e ".[dev]"

# Verify installation
python3.11 -m retileup.cli.main --version
python3.11 -m retileup.cli.main hello
```

### Testing
```bash
# Run all tests with coverage (489 tests)
pytest

# Run specific test categories
pytest -m unit          # Unit tests (275 tests)
pytest -m integration   # Integration tests (156 tests)
pytest -m performance   # Performance tests (60 tests)

# Run tests with detailed coverage report
pytest --cov=src/retileup --cov-report=html:htmlcov --cov-report=term-missing

# Run single test file
pytest tests/unit/test_config.py -v

# Use the comprehensive test runner script
python3.11 scripts/run_tests.py --help
python3.11 scripts/run_tests.py --quick        # Smoke tests
python3.11 scripts/run_tests.py --performance  # Performance tests only
```

### Code Quality
```bash
# Format code
black src tests

# Lint code
ruff check src tests

# Type checking
mypy src

# Run all quality checks together
black src tests && ruff check src tests && mypy src
```

### CLI Usage
```bash
# Main CLI entry point
python3.11 -m retileup.cli.main --help

# Using the installed command (after pip install -e .)
retileup --help

# Example commands
retileup tile --width 256 --height 256 --coords "0,0;256,0" image.jpg
retileup workflow web-optimize --input ./photos --output ./web
retileup list-tools --detailed
retileup validate config.yaml
```

## Architecture Overview

ReTileUp follows a modular, plugin-based architecture designed for extensibility:

### Core Components

1. **CLI Layer** (`src/retileup/cli/`):
   - `main.py`: Main CLI entry point using Typer with rich output
   - `commands/`: Individual command implementations (tile, workflow, utils)
   - Global options: --config, --verbose, --quiet, --version

2. **Core Framework** (`src/retileup/core/`):
   - `config.py`: Configuration management with Pydantic models
   - `registry.py`: Tool registry system for plugin management
   - `workflow.py`: Workflow definitions and orchestration
   - `orchestrator.py`: Execution engine for workflows
   - `exceptions.py`: Custom exception hierarchy

3. **Tool Framework** (`src/retileup/tools/`):
   - `base.py`: Abstract base class for all processing tools
   - `tiling.py`: Reference implementation for tile extraction
   - Plugin architecture allows easy extension

4. **Utilities** (`src/retileup/utils/`):
   - `image.py`: Image processing utilities
   - `validation.py`: Input validation framework
   - `progress.py`: Progress tracking for CLI

5. **Schemas** (`src/retileup/schemas/`):
   - Pydantic models for configuration and workflow validation

### Key Design Patterns

- **Plugin Architecture**: Tools are plugins that implement the base Tool interface
- **Workflow Engine**: YAML-based workflow definitions with step orchestration
- **Configuration Management**: Hierarchical config with auto-detection
- **Type Safety**: Comprehensive type hints with Pydantic validation
- **Error Handling**: Custom exception hierarchy with graceful degradation

## Development Guidelines

### Code Organization
- All source code is in `src/retileup/` following Python packaging best practices
- Tests mirror the source structure in `tests/` with categories: unit, integration, performance, edge_cases
- Use absolute imports from the retileup package root
- Follow the existing modular structure when adding new features

### Adding New Tools
1. Create new tool class inheriting from `ToolBase` in `src/retileup/tools/`
2. Implement required abstract methods: `process()`, `validate_input()`, `get_config_schema()`
3. Register the tool in the tool registry
4. Add corresponding CLI command in `src/retileup/cli/commands/`
5. Write comprehensive tests in appropriate test categories

### Configuration System
- Configuration uses Pydantic models for validation
- Auto-detects config files: `./retileup.yaml`, `~/.retileup.yaml`, `~/.config/retileup/config.yaml`
- Environment variables override config file settings
- All config classes are in `src/retileup/schemas/config.py`

### Testing Philosophy
- >95% test coverage is maintained
- Tests are categorized with pytest markers (unit, integration, performance, etc.)
- Use `pytest-mock` for mocking external dependencies
- Performance tests validate memory usage <500MB and processing speed >20MP/s
- Edge case tests cover boundary conditions and error scenarios

### Performance Considerations
- Target: 20-60 megapixels/second processing speed
- Memory limit: <500MB for large images
- Supports 67+ image formats including RAW
- Parallel processing with configurable worker threads
- Efficient memory usage with chunked processing

## Important Implementation Details

### CLI Framework
- Uses Typer for CLI with Rich for beautiful terminal output
- Global state management through `GlobalState` class
- Automatic shell completion support
- Comprehensive error handling with appropriate exit codes

### Image Processing
- Built on Pillow (PIL) for core image operations
- Supports RGB, RGBA, L, LA, CMYK, YCbCr color modes
- Handles 1, 8, 16, 32 bits per channel
- Validation framework ensures image bounds and format compatibility

### Workflow System
- YAML-based workflow definitions
- Step orchestration with dependency management
- Conditional execution and error recovery
- Status tracking: PENDING, RUNNING, COMPLETED, FAILED, SKIPPED

### Error Handling
- Custom exception hierarchy in `core/exceptions.py`
- Graceful failure and recovery mechanisms
- Structured error codes for programmatic handling
- Rich error formatting in CLI

## Testing Infrastructure

The project has comprehensive testing with 489 tests across multiple categories:

- **Unit Tests** (275): Test individual components in isolation
- **Integration Tests** (156): Test component interactions
- **Performance Tests** (60): Validate speed and memory usage
- **Edge Case Tests**: Boundary conditions and error scenarios

Test markers help organize test execution:
- `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.performance`
- `@pytest.mark.cli`, `@pytest.mark.core`, `@pytest.mark.tools`
- `@pytest.mark.slow`, `@pytest.mark.memory`, `@pytest.mark.security`

Use `python3.11 scripts/run_tests.py` for comprehensive test execution with performance validation.