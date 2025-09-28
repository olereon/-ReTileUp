# ReTileUp User Guide

Complete guide for using ReTileUp for image processing and workflow automation.

## Table of Contents

- [Installation](#installation)
- [Getting Started](#getting-started)
- [Command Reference](#command-reference)
- [Configuration](#configuration)
- [Workflows](#workflows)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [FAQ](#faq)

## Installation

### System Requirements

- **Operating System**: Linux, macOS, or Windows
- **Python**: Version 3.8 or higher
- **Memory**: 256MB+ RAM recommended
- **Storage**: Varies based on image processing needs

### Installation Methods

#### Method 1: From Source (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/retileup.git
cd retileup

# Install the package
pip install -e .

# Verify installation
retileup --version
```

#### Method 2: Development Installation

For development or if you want the latest features:

```bash
# Clone and install with development dependencies
git clone https://github.com/yourusername/retileup.git
cd retileup
pip install -e ".[dev]"

# Install additional development tools
pip install -e ".[test,docs]"
```

#### Method 3: Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv retileup-env
source retileup-env/bin/activate  # On Windows: retileup-env\Scripts\activate

# Install ReTileUp
pip install -e .
```

### Verification

After installation, verify everything works:

```bash
# Check version
retileup --version

# Test basic functionality
retileup hello

# List available commands
retileup --help
```

### Installation Troubleshooting

**Issue**: `ModuleNotFoundError: No module named 'retileup'`
**Solution**: Ensure you installed with `-e .` flag and are in the correct directory.

**Issue**: Permission errors during installation
**Solution**: Use virtual environment or add `--user` flag: `pip install --user -e .`

**Issue**: Pillow installation fails
**Solution**: Install system dependencies:
```bash
# Ubuntu/Debian
sudo apt-get install python3-dev libjpeg-dev libpng-dev

# macOS (with Homebrew)
brew install jpeg libpng

# Windows
# Usually works out of the box
```

## Getting Started

### First Steps

1. **Test Installation**
   ```bash
   retileup hello
   ```

2. **Create Sample Images** (optional)
   ```bash
   # Use provided script to create test images
   python examples/scripts/create_samples.py
   ```

3. **Basic Tiling Operation**
   ```bash
   # Extract a single tile
   retileup tile --width 256 --height 256 --coords "0,0" sample.jpg
   ```

### Understanding the Basics

ReTileUp operates on three main concepts:

1. **Tools**: Individual processing operations (e.g., tiling, resizing)
2. **Workflows**: Sequences of tool operations
3. **Configuration**: Settings that control tool behavior

### Your First Command

```bash
# Extract four corner tiles from an image
retileup tile \
  --width 200 \
  --height 200 \
  --coords "0,0;1720,0;0,880;1720,880" \
  photo.jpg
```

This command:
- Creates 200x200 pixel tiles
- Extracts from four corner coordinates
- Saves tiles with default naming pattern

## Command Reference

### Global Options

These options work with all commands:

```bash
retileup [GLOBAL_OPTIONS] <command> [COMMAND_OPTIONS]
```

**Global Options:**
- `--config, -c PATH`: Specify configuration file
- `--verbose, -v`: Enable detailed output
- `--quiet, -q`: Suppress non-error messages
- `--version`: Show version and exit
- `--help`: Show help message

### retileup tile

Extract rectangular tiles from images at specified coordinates.

#### Basic Usage

```bash
retileup tile --width WIDTH --height HEIGHT --coords COORDINATES INPUT_FILE
```

#### Parameters

**Required:**
- `--width, -w INTEGER`: Tile width in pixels (1-8192)
- `--height, -h INTEGER`: Tile height in pixels (1-8192)
- One of:
  - `--coords TEXT`: Coordinates as "x1,y1;x2,y2;..." format
  - `--grid TEXT`: Grid pattern like "3x3" or "4x2"

**Optional:**
- `--output-pattern TEXT`: Output filename pattern (default: `{base}_{x}_{y}.{ext}`)
- `--format TEXT`: Output format (JPEG, PNG, BMP, etc.)
- `--quality INTEGER`: JPEG quality 1-100 (default: 95)
- `--overlap INTEGER`: Overlap pixels between tiles (default: 0)
- `--aspect-ratio FLOAT`: Maintain aspect ratio (width/height)
- `--validate-bounds`: Validate tiles fit within image bounds
- `--output-dir PATH`: Output directory (default: current directory)

#### Examples

**Basic Tiling:**
```bash
# Extract single tile
retileup tile --width 256 --height 256 --coords "0,0" image.jpg

# Extract multiple tiles
retileup tile --width 200 --height 200 --coords "0,0;200,0;400,0" image.jpg
```

**Grid Tiling:**
```bash
# 3x3 grid
retileup tile --width 200 --height 200 --grid 3x3 image.jpg

# 4x2 grid with custom pattern
retileup tile \
  --width 256 --height 256 \
  --grid 4x2 \
  --output-pattern "grid_{row}_{col}.png" \
  --format PNG \
  image.jpg
```

**Advanced Options:**
```bash
# High-quality tiles with overlap
retileup tile \
  --width 512 --height 512 \
  --coords "0,0;256,0;512,0" \
  --overlap 64 \
  --format PNG \
  --validate-bounds \
  image.jpg

# Custom output pattern and directory
retileup tile \
  --width 300 --height 300 \
  --grid 2x2 \
  --output-pattern "tile_row{row}_col{col}.jpg" \
  --quality 90 \
  --output-dir ./tiles \
  photo.jpg
```

#### Output Patterns

The `--output-pattern` option supports these placeholders:

- `{base}`: Input filename without extension
- `{ext}`: Output file extension
- `{x}`, `{y}`: Tile coordinates
- `{row}`, `{col}`: Grid position (for grid mode)
- `{width}`, `{height}`: Tile dimensions
- `{index}`: Sequential tile number

Examples:
- `{base}_{x}_{y}.{ext}` → `photo_0_0.jpg`
- `tile_{index:03d}.png` → `tile_001.png`
- `{base}_r{row}_c{col}.{ext}` → `image_r0_c0.jpg`

### retileup workflow

Execute predefined workflows for batch processing.

#### Basic Usage

```bash
retileup workflow WORKFLOW_NAME [OPTIONS]
```

#### Parameters

**Required:**
- `WORKFLOW_NAME`: Name of the workflow to execute

**Optional:**
- `--input, -i PATH`: Input directory or file
- `--output, -o PATH`: Output directory
- `--config-file PATH`: Workflow configuration file
- `--dry-run`: Show what would be done without executing
- `--parallel INTEGER`: Number of parallel workers

#### Examples

```bash
# Run web optimization workflow
retileup workflow web-optimize --input ./photos --output ./web

# Dry run to see what would happen
retileup workflow resize-batch --input ./images --dry-run

# Custom configuration
retileup workflow custom --config-file my-workflow.yaml
```

### retileup list-tools

Display available processing tools and their capabilities.

#### Usage

```bash
retileup list-tools [OPTIONS]
```

#### Parameters

- `--detailed`: Show detailed tool information
- `--category TEXT`: Filter by tool category
- `--format TEXT`: Output format (table, json, yaml)

#### Examples

```bash
# Simple list
retileup list-tools

# Detailed information
retileup list-tools --detailed

# Filter by category
retileup list-tools --category processing --detailed

# JSON output
retileup list-tools --format json
```

### retileup validate

Validate configuration and workflow files.

#### Usage

```bash
retileup validate FILE [OPTIONS]
```

#### Parameters

- `--type TEXT`: File type (config, workflow, auto)
- `--strict`: Enable strict validation mode

#### Examples

```bash
# Validate configuration
retileup validate config.yaml

# Validate workflow with strict mode
retileup validate --type workflow --strict workflow.yaml

# Auto-detect file type
retileup validate my-settings.yaml
```

## Configuration

ReTileUp supports flexible configuration through multiple sources.

### Configuration Sources (Priority Order)

1. Command-line options (highest priority)
2. Configuration files
3. Environment variables
4. Default values (lowest priority)

### Configuration Files

#### Auto-Detection

ReTileUp automatically looks for configuration files in these locations:

1. `./retileup.yaml` (current directory)
2. `~/.retileup.yaml` (home directory)
3. `~/.config/retileup/config.yaml` (user config directory)

#### Manual Configuration

```bash
# Use specific configuration file
retileup --config /path/to/config.yaml tile --width 256 --height 256 --coords "0,0" image.jpg
```

#### Configuration File Format

```yaml
# retileup.yaml
# Global settings
debug: false
log_level: "INFO"
max_workers: 4
output_dir: "./output"

# Tool-specific settings
tools:
  tiling:
    default_width: 256
    default_height: 256
    default_format: "JPEG"
    default_quality: 95
    validate_bounds: true

# Workflow settings
workflows:
  web_optimize:
    max_dimension: 1920
    quality: 85
    format: "JPEG"

# Output settings
output:
  create_directories: true
  overwrite_existing: false
  preserve_metadata: false
```

### Environment Variables

```bash
# Set environment variables
export RETILEUP_DEBUG=true
export RETILEUP_LOG_LEVEL=DEBUG
export RETILEUP_MAX_WORKERS=8
export RETILEUP_OUTPUT_DIR=/tmp/retileup

# Use in commands
retileup tile --width 256 --height 256 --coords "0,0" image.jpg
```

**Available Environment Variables:**

- `RETILEUP_DEBUG`: Enable debug mode (true/false)
- `RETILEUP_LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)
- `RETILEUP_MAX_WORKERS`: Maximum worker threads (1-16)
- `RETILEUP_OUTPUT_DIR`: Default output directory
- `RETILEUP_CONFIG_FILE`: Default configuration file path
- `RETILEUP_CACHE_DIR`: Cache directory for temporary files

### Programmatic Configuration

```python
from retileup import Config

# Create configuration
config = Config(
    debug=True,
    log_level="DEBUG",
    max_workers=4,
    output_dir="./output"
)

# Load from file
config = Config.from_file("config.yaml")

# Load from environment
config = Config.from_env()
```

## Workflows

Workflows allow you to define complex, multi-step image processing operations.

### Workflow Structure

```yaml
# workflow.yaml
name: "my-workflow"
description: "Custom image processing workflow"
version: "1.0"

# Global settings
settings:
  parallel: true
  max_workers: 4
  continue_on_error: false

# Processing steps
steps:
  - name: "validate"
    tool: "validate_tool"
    config:
      check_format: true
      min_resolution: [800, 600]

  - name: "resize"
    tool: "resize_tool"
    config:
      max_width: 1920
      max_height: 1080
      maintain_aspect: true

  - name: "tile"
    tool: "tiling_tool"
    config:
      tile_width: 256
      tile_height: 256
      grid: "4x4"
      overlap: 32

# Output configuration
output:
  directory: "./processed"
  pattern: "{step}_{base}_{index}.{ext}"
  overwrite: false
```

### Built-in Workflows

#### Web Optimization

```bash
retileup workflow web-optimize --input ./photos --output ./web
```

Optimizes images for web use:
- Resizes to maximum 1920x1080
- Compresses with 85% quality
- Converts to JPEG format

#### Thumbnail Generation

```bash
retileup workflow thumbnails --input ./images --output ./thumbs
```

Creates thumbnails:
- Resizes to 200x200 pixels
- Maintains aspect ratio
- High-quality compression

### Custom Workflows

Create your own workflow file:

```yaml
# my-workflow.yaml
name: "social-media-prep"
description: "Prepare images for social media"

steps:
  - name: "resize-square"
    tool: "resize_tool"
    config:
      width: 1080
      height: 1080
      crop_mode: "center"

  - name: "enhance"
    tool: "enhance_tool"
    config:
      brightness: 1.1
      contrast: 1.05
      saturation: 1.1

  - name: "compress"
    tool: "compress_tool"
    config:
      quality: 90
      format: "JPEG"
```

Execute your workflow:

```bash
retileup workflow social-media-prep --config-file my-workflow.yaml --input ./photos
```

## Troubleshooting

### Common Issues

#### 1. Installation Problems

**Problem**: `pip install -e .` fails
**Solution**:
```bash
# Update pip first
pip install --upgrade pip setuptools wheel

# Try installation again
pip install -e .
```

**Problem**: Permission denied errors
**Solution**:
```bash
# Use virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .

# Or install to user directory
pip install --user -e .
```

#### 2. Command Execution Issues

**Problem**: `retileup: command not found`
**Solution**:
```bash
# Check if installed correctly
pip list | grep retileup

# Add to PATH if needed (with --user install)
export PATH=$PATH:~/.local/bin

# Or use python module execution
python -m retileup --help
```

**Problem**: Import errors when running commands
**Solution**:
```bash
# Reinstall with dependencies
pip install -e ".[dev]"

# Check Python version
python --version  # Should be 3.8+
```

#### 3. Image Processing Issues

**Problem**: "Image not found" error
**Solution**:
```bash
# Use absolute paths
retileup tile --width 256 --height 256 --coords "0,0" /full/path/to/image.jpg

# Check file exists
ls -la image.jpg

# Check file permissions
chmod 644 image.jpg
```

**Problem**: "Unsupported image format"
**Solution**:
```bash
# Check format support
retileup list-tools --detailed

# Convert format first
convert image.tiff image.jpg  # Using ImageMagick
```

**Problem**: "Coordinates out of bounds"
**Solution**:
```bash
# Check image dimensions first
identify image.jpg  # Using ImageMagick

# Or use Python
python -c "from PIL import Image; img=Image.open('image.jpg'); print(img.size)"

# Use --validate-bounds to check
retileup tile --width 256 --height 256 --coords "0,0" --validate-bounds image.jpg
```

#### 4. Performance Issues

**Problem**: Slow processing
**Solution**:
```bash
# Increase worker threads
export RETILEUP_MAX_WORKERS=8

# Use configuration file
echo "max_workers: 8" > retileup.yaml

# Monitor with verbose output
retileup --verbose tile ...
```

**Problem**: High memory usage
**Solution**:
```bash
# Reduce worker count
export RETILEUP_MAX_WORKERS=2

# Process smaller batches
# Split large operations into smaller chunks
```

### Debug Mode

Enable debug mode for detailed troubleshooting:

```bash
# Via environment variable
export RETILEUP_DEBUG=true
retileup tile ...

# Via command line
retileup --verbose tile ...

# Via configuration file
echo "debug: true" > retileup.yaml
```

### Log Files

Check log files for detailed error information:

```bash
# Set log level
export RETILEUP_LOG_LEVEL=DEBUG

# View logs
tail -f ~/.local/share/retileup/logs/retileup.log

# Or specify log file
retileup --config config.yaml tile ...
```

### Getting Help

1. **Check Documentation**:
   - `retileup --help`
   - `retileup <command> --help`
   - Read this user guide

2. **Enable Verbose Mode**:
   ```bash
   retileup --verbose <command>
   ```

3. **Check Issues**:
   - [GitHub Issues](https://github.com/yourusername/retileup/issues)

4. **Ask for Help**:
   - [GitHub Discussions](https://github.com/yourusername/retileup/discussions)

## Best Practices

### File Organization

```bash
# Organize your projects
project/
├── config/
│   ├── retileup.yaml
│   └── workflows/
├── input/
│   ├── raw/
│   └── processed/
├── output/
│   ├── tiles/
│   ├── thumbnails/
│   └── web/
└── scripts/
    └── batch_process.sh
```

### Configuration Management

1. **Use Configuration Files**:
   ```yaml
   # retileup.yaml
   tools:
     tiling:
       default_width: 256
       default_height: 256
       validate_bounds: true
   ```

2. **Environment-Specific Configs**:
   ```bash
   # Development
   retileup --config dev-config.yaml

   # Production
   retileup --config prod-config.yaml
   ```

3. **Version Control**:
   ```bash
   # Track configuration
   git add retileup.yaml workflows/
   git commit -m "Add processing configuration"
   ```

### Performance Optimization

1. **Batch Processing**:
   ```bash
   # Process multiple files
   for file in *.jpg; do
     retileup tile --width 256 --height 256 --grid 3x3 "$file"
   done
   ```

2. **Parallel Processing**:
   ```bash
   # Set optimal worker count
   export RETILEUP_MAX_WORKERS=$(nproc)
   ```

3. **Memory Management**:
   ```bash
   # For large images, reduce workers
   export RETILEUP_MAX_WORKERS=2
   ```

### Quality Control

1. **Validate Inputs**:
   ```bash
   # Always validate configurations
   retileup validate config.yaml

   # Use bounds checking
   retileup tile --validate-bounds ...
   ```

2. **Test First**:
   ```bash
   # Use dry-run mode
   retileup workflow test --dry-run

   # Test with small images first
   retileup tile --width 128 --height 128 test-image.jpg
   ```

3. **Monitor Output**:
   ```bash
   # Use verbose mode
   retileup --verbose tile ...

   # Check output quality
   identify output/*.jpg
   ```

### Automation

1. **Shell Scripts**:
   ```bash
   #!/bin/bash
   # process_batch.sh
   for image in input/*.jpg; do
     retileup tile --width 256 --height 256 --grid 4x4 "$image"
   done
   ```

2. **Makefile**:
   ```makefile
   # Makefile
   .PHONY: tiles thumbnails web

   tiles:
   	retileup tile --width 256 --height 256 --grid 4x4 input/*.jpg

   thumbnails:
   	retileup workflow thumbnails --input input/ --output thumbs/

   web:
   	retileup workflow web-optimize --input input/ --output web/
   ```

3. **CI/CD Integration**:
   ```yaml
   # .github/workflows/process-images.yml
   name: Process Images
   on: [push]
   jobs:
     process:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v2
         - name: Setup Python
           uses: actions/setup-python@v2
           with:
             python-version: '3.9'
         - name: Install ReTileUp
           run: pip install -e .
         - name: Process Images
           run: retileup workflow web-optimize --input images/ --output processed/
   ```

## FAQ

### General Questions

**Q: What image formats does ReTileUp support?**
A: ReTileUp supports 67+ formats including JPEG, PNG, GIF, BMP, TIFF, WebP, HEIC, and many RAW formats.

**Q: Can I process images in batch?**
A: Yes, use workflows or shell scripts to process multiple images. ReTileUp supports parallel processing.

**Q: Is ReTileUp suitable for production use?**
A: ReTileUp is designed for production with comprehensive testing, error handling, and performance optimization.

### Technical Questions

**Q: How do I handle large images?**
A: Reduce the number of workers, increase system memory, or process images in chunks.

**Q: Can I extend ReTileUp with custom tools?**
A: Yes, ReTileUp has a plugin architecture. See the Developer Guide for creating custom tools.

**Q: How do I report bugs or request features?**
A: Use [GitHub Issues](https://github.com/yourusername/retileup/issues) for bugs and feature requests.

### Performance Questions

**Q: Why is processing slow?**
A: Check your worker count, system resources, and image sizes. Use `--verbose` mode to identify bottlenecks.

**Q: How much memory does ReTileUp use?**
A: Typically <500MB for most operations. Memory usage scales with image size and worker count.

**Q: Can I process images on a server without a display?**
A: Yes, ReTileUp works in headless environments and doesn't require a display.

### Workflow Questions

**Q: Can I create custom workflows?**
A: Yes, create YAML workflow files defining your processing steps. See the Workflows section for details.

**Q: How do I share workflows with my team?**
A: Workflow files are just YAML files that can be version controlled and shared like any other code.

**Q: Can workflows handle errors gracefully?**
A: Yes, configure `continue_on_error` in your workflow settings to handle failures gracefully.

---

For more information, see the [Developer Guide](DEVELOPER_GUIDE.md) or visit our [GitHub repository](https://github.com/yourusername/retileup).