# ReTileUp Examples

Comprehensive examples demonstrating ReTileUp's capabilities and usage patterns.

## Table of Contents

- [Basic Tiling Operations](#basic-tiling-operations)
- [Advanced Tiling Patterns](#advanced-tiling-patterns)
- [Workflow Automation](#workflow-automation)
- [Performance Optimization](#performance-optimization)
- [Integration Examples](#integration-examples)
- [Error Handling](#error-handling)
- [Custom Tool Development](#custom-tool-development)

## Basic Tiling Operations

### Single Tile Extraction

Extract a single tile from a specific location:

```bash
# Extract 256x256 tile from top-left corner
retileup tile --width 256 --height 256 --coords "0,0" photo.jpg

# Extract tile from center of 1920x1080 image
retileup tile --width 512 --height 512 --coords "704,284" image.jpg

# High-quality PNG output
retileup tile \
  --width 300 --height 300 \
  --coords "100,100" \
  --format PNG \
  --output-pattern "tile_{x}_{y}_hq.{ext}" \
  photo.jpg
```

### Multiple Tile Extraction

Extract multiple tiles from specified coordinates:

```bash
# Extract four corner tiles
retileup tile \
  --width 200 --height 200 \
  --coords "0,0;1720,0;0,880;1720,880" \
  landscape.jpg

# Extract tiles along top edge
retileup tile \
  --width 256 --height 256 \
  --coords "0,0;256,0;512,0;768,0;1024,0" \
  banner.jpg

# Custom output directory and pattern
retileup tile \
  --width 128 --height 128 \
  --coords "0,0;128,0;256,0" \
  --output-dir ./tiles \
  --output-pattern "thumb_{index:03d}.jpg" \
  --quality 85 \
  photo.jpg
```

### Grid-Based Tiling

Create regular grids of tiles:

```bash
# Simple 3x3 grid
retileup tile --width 200 --height 200 --grid 3x3 image.jpg

# 4x2 grid with custom naming
retileup tile \
  --width 256 --height 256 \
  --grid 4x2 \
  --output-pattern "grid_r{row}_c{col}.png" \
  --format PNG \
  photo.jpg

# Large grid for detailed analysis
retileup tile \
  --width 128 --height 128 \
  --grid 10x8 \
  --output-dir ./analysis \
  --validate-bounds \
  high_res_image.tiff
```

## Advanced Tiling Patterns

### Overlapping Tiles

Create tiles with overlapping regions:

```bash
# Tiles with 32-pixel overlap
retileup tile \
  --width 256 --height 256 \
  --coords "0,0;224,0;448,0" \
  --overlap 32 \
  image.jpg

# Grid with overlap for seamless processing
retileup tile \
  --width 512 --height 512 \
  --grid 4x4 \
  --overlap 64 \
  --output-pattern "overlap_{row}_{col}.jpg" \
  large_image.jpg
```

### Aspect Ratio Preservation

Maintain specific aspect ratios:

```bash
# Square tiles (1:1 aspect ratio)
retileup tile \
  --width 300 --height 300 \
  --aspect-ratio 1.0 \
  --grid 3x3 \
  portrait.jpg

# Widescreen tiles (16:9 aspect ratio)
retileup tile \
  --width 480 --height 270 \
  --aspect-ratio 1.777 \
  --coords "0,0;480,0;960,0" \
  --validate-bounds \
  video_frame.jpg
```

### Custom Output Patterns

Use advanced output naming patterns:

```bash
# Include original filename and dimensions
retileup tile \
  --width 256 --height 256 \
  --grid 2x2 \
  --output-pattern "{base}_{width}x{height}_r{row}c{col}.{ext}" \
  photo.jpg
# Output: photo_256x256_r0c0.jpg, photo_256x256_r0c1.jpg, etc.

# Sequential numbering with padding
retileup tile \
  --width 200 --height 200 \
  --coords "0,0;200,0;400,0;600,0" \
  --output-pattern "tile_{index:04d}.png" \
  --format PNG \
  image.jpg
# Output: tile_0001.png, tile_0002.png, tile_0003.png, tile_0004.png

# Include coordinates and metadata
retileup tile \
  --width 128 --height 128 \
  --grid 4x4 \
  --output-pattern "{base}_x{x}_y{y}_{width}x{height}.jpg" \
  test_image.png
```

## Workflow Automation

### Basic Workflow Creation

Create a simple workflow configuration:

```yaml
# simple_workflow.yaml
name: "thumbnail-generator"
description: "Generate thumbnails from input images"
version: "1.0"

settings:
  parallel: true
  max_workers: 4

steps:
  - name: "validate"
    tool: "validate_tool"
    config:
      check_format: true
      min_resolution: [200, 200]

  - name: "create_thumbnails"
    tool: "tiling_tool"
    config:
      tile_width: 150
      tile_height: 150
      coordinates: [[0, 0]]
      output_pattern: "thumb_{base}.{ext}"
      format: "JPEG"
      quality: 85

output:
  directory: "./thumbnails"
  overwrite: false
```

Execute the workflow:

```bash
retileup workflow thumbnail-generator \
  --config-file simple_workflow.yaml \
  --input ./photos \
  --output ./thumbnails
```

### Multi-Step Processing Workflow

Create a complex multi-step workflow:

```yaml
# web_optimization.yaml
name: "web-optimization"
description: "Optimize images for web deployment"
version: "2.0"

settings:
  parallel: true
  max_workers: 6
  continue_on_error: false

steps:
  - name: "validate_inputs"
    tool: "validate_tool"
    config:
      check_format: true
      supported_formats: ["JPEG", "PNG", "TIFF"]
      max_file_size: 50000000  # 50MB

  - name: "resize_large"
    tool: "resize_tool"
    config:
      max_width: 1920
      max_height: 1080
      maintain_aspect: true
      upscale: false

  - name: "create_multiple_sizes"
    tool: "tiling_tool"
    config:
      tile_width: 800
      tile_height: 600
      coordinates: [[0, 0]]
      output_pattern: "medium_{base}.{ext}"
      format: "JPEG"
      quality: 85

  - name: "create_thumbnails"
    tool: "tiling_tool"
    config:
      tile_width: 200
      tile_height: 200
      coordinates: [[0, 0]]
      output_pattern: "thumb_{base}.{ext}"
      format: "JPEG"
      quality: 75

  - name: "create_webp_versions"
    tool: "convert_tool"
    config:
      output_format: "WebP"
      quality: 80
      output_pattern: "{base}.webp"

output:
  directory: "./web_optimized"
  create_subdirectories: true
  preserve_structure: true
```

### Batch Processing Script

Automate processing with shell scripts:

```bash
#!/bin/bash
# batch_process.sh

set -e  # Exit on any error

# Configuration
INPUT_DIR="./raw_photos"
OUTPUT_DIR="./processed"
CONFIG_FILE="./workflows/web_optimization.yaml"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "Starting batch processing..."
echo "Input directory: $INPUT_DIR"
echo "Output directory: $OUTPUT_DIR"
echo "Configuration: $CONFIG_FILE"

# Process all images
for format in jpg jpeg png tiff; do
    if ls "$INPUT_DIR"/*.$format 1> /dev/null 2>&1; then
        echo "Processing $format files..."
        retileup workflow web-optimization \
          --config-file "$CONFIG_FILE" \
          --input "$INPUT_DIR/*.$format" \
          --output "$OUTPUT_DIR" \
          --verbose
    fi
done

echo "Batch processing completed!"

# Generate summary report
echo "Processing Summary:" > "$OUTPUT_DIR/summary.txt"
echo "Processed at: $(date)" >> "$OUTPUT_DIR/summary.txt"
echo "Input files: $(find "$INPUT_DIR" -name "*.jpg" -o -name "*.png" -o -name "*.tiff" | wc -l)" >> "$OUTPUT_DIR/summary.txt"
echo "Output files: $(find "$OUTPUT_DIR" -name "*.jpg" -o -name "*.png" -o -name "*.webp" | wc -l)" >> "$OUTPUT_DIR/summary.txt"
```

Make it executable and run:

```bash
chmod +x batch_process.sh
./batch_process.sh
```

### Makefile Integration

Integrate with Make for build automation:

```makefile
# Makefile
.PHONY: thumbnails web-optimize clean process-all

# Default target
all: thumbnails web-optimize

# Generate thumbnails
thumbnails:
	@echo "Generating thumbnails..."
	@mkdir -p output/thumbnails
	retileup tile \
		--width 150 --height 150 \
		--grid 1x1 \
		--output-dir output/thumbnails \
		--output-pattern "thumb_{base}.jpg" \
		--quality 85 \
		input/*.jpg

# Web optimization
web-optimize:
	@echo "Optimizing for web..."
	@mkdir -p output/web
	retileup workflow web-optimization \
		--input input/ \
		--output output/web \
		--config-file configs/web.yaml

# Create tile grids
tile-grids:
	@echo "Creating tile grids..."
	@mkdir -p output/grids
	retileup tile \
		--width 200 --height 200 \
		--grid 4x4 \
		--output-dir output/grids \
		--output-pattern "grid_{base}_r{row}_c{col}.png" \
		--format PNG \
		input/*.jpg

# Performance testing
perf-test:
	@echo "Running performance tests..."
	time retileup tile \
		--width 256 --height 256 \
		--grid 8x8 \
		--validate-bounds \
		test/large_image.tiff

# Clean output directories
clean:
	rm -rf output/

# Process everything
process-all: clean thumbnails web-optimize tile-grids
	@echo "All processing complete!"
```

Usage:

```bash
make thumbnails          # Generate thumbnails only
make web-optimize        # Web optimization only
make process-all         # Run all processing steps
make clean              # Clean output directories
```

## Performance Optimization

### High-Performance Configuration

Optimize for maximum processing speed:

```yaml
# performance_config.yaml
debug: false
log_level: "ERROR"
max_workers: 8  # Use all CPU cores

tools:
  tiling:
    validate_bounds: false  # Skip validation for speed
    default_quality: 85     # Slightly lower quality for speed
    memory_optimization: true

performance:
  batch_size: 10
  cache_enabled: true
  parallel_io: true
```

Use with commands:

```bash
# High-performance processing
export RETILEUP_MAX_WORKERS=8
retileup --config performance_config.yaml tile \
  --width 256 --height 256 \
  --grid 4x4 \
  large_dataset/*.jpg
```

### Memory-Efficient Processing

Handle large images with limited memory:

```bash
# Process large images with reduced memory usage
export RETILEUP_MAX_WORKERS=2  # Reduce workers
retileup tile \
  --width 512 --height 512 \
  --coords "0,0;512,0;1024,0" \
  --validate-bounds \
  very_large_image.tiff

# Process in smaller chunks
retileup tile \
  --width 256 --height 256 \
  --grid 8x8 \
  --output-dir ./chunks \
  huge_image.tiff
```

### Parallel Processing

Process multiple images in parallel:

```bash
#!/bin/bash
# parallel_process.sh

# Process multiple images in parallel using GNU parallel
find input/ -name "*.jpg" | \
parallel -j 4 retileup tile \
  --width 200 --height 200 \
  --grid 3x3 \
  --output-dir output/{/.} \
  {}
```

Or using xargs:

```bash
# Using xargs for parallel processing
find input/ -name "*.jpg" -print0 | \
xargs -0 -n 1 -P 4 -I {} \
retileup tile --width 256 --height 256 --grid 2x2 {}
```

## Integration Examples

### Python Script Integration

Use ReTileUp in your Python applications:

```python
#!/usr/bin/env python3
"""Example Python script using ReTileUp programmatically."""

import sys
from pathlib import Path
from typing import List

from retileup import Config, ToolRegistry, WorkflowOrchestrator
from retileup.tools.tiling import TilingTool, TilingConfig
from retileup.core.exceptions import RetileupError

def process_image_batch(
    image_paths: List[str],
    tile_width: int = 256,
    tile_height: int = 256,
    grid_size: str = "3x3",
    output_dir: str = "./output"
) -> None:
    """Process a batch of images with tiling.

    Args:
        image_paths: List of image file paths
        tile_width: Width of tiles in pixels
        tile_height: Height of tiles in pixels
        grid_size: Grid pattern (e.g., "3x3")
        output_dir: Output directory path
    """
    # Initialize ReTileUp components
    config = Config()
    registry = ToolRegistry()
    tiling_tool = TilingTool()

    # Parse grid size
    rows, cols = map(int, grid_size.split('x'))

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results = []

    for image_path in image_paths:
        try:
            print(f"Processing: {image_path}")

            # Create tiling configuration
            tile_config = TilingConfig(
                tile_width=tile_width,
                tile_height=tile_height,
                grid_pattern=f"{rows}x{cols}",
                output_pattern=f"{output_path}/{{base}}_{{row}}_{{col}}.jpg",
                format="JPEG",
                quality=90
            )

            # Process image
            result = tiling_tool.process(image_path, tile_config)

            if result.success:
                print(f"  ✓ Created {len(result.outputs)} tiles")
                results.append(result)
            else:
                print(f"  ✗ Error: {result.error}")

        except RetileupError as e:
            print(f"  ✗ ReTileUp error: {e}")
        except Exception as e:
            print(f"  ✗ Unexpected error: {e}")

    print(f"\nProcessing complete! Processed {len(results)} images successfully.")

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python process_batch.py <image1> [image2] ...")
        sys.exit(1)

    image_paths = sys.argv[1:]

    # Validate input files
    valid_paths = []
    for path in image_paths:
        if Path(path).exists():
            valid_paths.append(path)
        else:
            print(f"Warning: File not found: {path}")

    if not valid_paths:
        print("Error: No valid image files found.")
        sys.exit(1)

    # Process images
    process_image_batch(
        image_paths=valid_paths,
        tile_width=256,
        tile_height=256,
        grid_size="4x4",
        output_dir="./processed_tiles"
    )

if __name__ == "__main__":
    main()
```

Run the script:

```bash
python process_batch.py photo1.jpg photo2.jpg photo3.jpg
```

### Django Integration

Integrate with Django web applications:

```python
# views.py
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.conf import settings
import json

from retileup.tools.tiling import TilingTool, TilingConfig

@csrf_exempt
@require_http_methods(["POST"])
def process_image_tiles(request):
    """API endpoint for image tiling."""
    try:
        # Parse request
        data = json.loads(request.body)
        image_url = data.get('image_url')
        tile_width = data.get('tile_width', 256)
        tile_height = data.get('tile_height', 256)
        grid_size = data.get('grid_size', '3x3')

        if not image_url:
            return HttpResponseBadRequest("image_url is required")

        # Download/locate image file
        image_path = default_storage.path(image_url)

        # Configure tiling
        tile_config = TilingConfig(
            tile_width=tile_width,
            tile_height=tile_height,
            grid_pattern=grid_size,
            output_pattern=f"{settings.MEDIA_ROOT}/tiles/{{base}}_{{row}}_{{col}}.jpg",
            format="JPEG",
            quality=85
        )

        # Process image
        tiling_tool = TilingTool()
        result = tiling_tool.process(image_path, tile_config)

        if result.success:
            # Return URLs for generated tiles
            tile_urls = [
                request.build_absolute_uri(f"/media/tiles/{Path(output).name}")
                for output in result.outputs
            ]

            return JsonResponse({
                'success': True,
                'tiles': tile_urls,
                'metadata': result.metadata
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.error
            }, status=500)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
```

### Flask Integration

Simple Flask API for image processing:

```python
# app.py
from flask import Flask, request, jsonify, send_file
import tempfile
import os
from pathlib import Path

from retileup.tools.tiling import TilingTool, TilingConfig

app = Flask(__name__)

@app.route('/api/tile', methods=['POST'])
def tile_image():
    """API endpoint for image tiling."""
    try:
        # Check if file was uploaded
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Get parameters
        tile_width = int(request.form.get('tile_width', 256))
        tile_height = int(request.form.get('tile_height', 256))
        grid_size = request.form.get('grid_size', '2x2')

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            file.save(tmp_file.name)
            input_path = tmp_file.name

        # Create output directory
        output_dir = tempfile.mkdtemp()

        try:
            # Configure and run tiling
            tile_config = TilingConfig(
                tile_width=tile_width,
                tile_height=tile_height,
                grid_pattern=grid_size,
                output_pattern=f"{output_dir}/tile_{{row}}_{{col}}.jpg",
                format="JPEG",
                quality=85
            )

            tiling_tool = TilingTool()
            result = tiling_tool.process(input_path, tile_config)

            if result.success:
                # Return first tile as example (in real app, you'd return all)
                if result.outputs:
                    return send_file(
                        result.outputs[0],
                        as_attachment=True,
                        download_name="tile.jpg"
                    )
                else:
                    return jsonify({'error': 'No tiles generated'}), 500
            else:
                return jsonify({'error': result.error}), 500

        finally:
            # Cleanup
            os.unlink(input_path)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
```

Test the API:

```bash
curl -X POST \
  -F "image=@photo.jpg" \
  -F "tile_width=200" \
  -F "tile_height=200" \
  -F "grid_size=3x3" \
  http://localhost:5000/api/tile \
  --output tile.jpg
```

## Error Handling

### Robust CLI Usage

Handle errors gracefully in scripts:

```bash
#!/bin/bash
# robust_processing.sh

set -euo pipefail  # Exit on error, undefined variables, pipe failures

# Configuration
INPUT_DIR="./input"
OUTPUT_DIR="./output"
LOG_FILE="./processing.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling function
handle_error() {
    log "ERROR: $1"
    exit 1
}

# Validation
if [[ ! -d "$INPUT_DIR" ]]; then
    handle_error "Input directory does not exist: $INPUT_DIR"
fi

mkdir -p "$OUTPUT_DIR"

log "Starting image processing..."

# Process each image with error handling
for image in "$INPUT_DIR"/*.{jpg,jpeg,png}; do
    # Skip if no files match pattern
    [[ -f "$image" ]] || continue

    basename=$(basename "$image")
    log "Processing: $basename"

    # Run with timeout and error handling
    if timeout 60 retileup tile \
        --width 256 --height 256 \
        --grid 2x2 \
        --output-dir "$OUTPUT_DIR" \
        --validate-bounds \
        "$image" 2>>"$LOG_FILE"; then
        log "SUCCESS: $basename processed"
    else
        log "ERROR: Failed to process $basename (exit code: $?)"
        # Continue with other files instead of exiting
        continue
    fi
done

log "Processing completed!"
```

### Python Error Handling

Comprehensive error handling in Python:

```python
#!/usr/bin/env python3
"""Example with comprehensive error handling."""

import logging
import sys
from pathlib import Path
from typing import List, Optional

from retileup.tools.tiling import TilingTool, TilingConfig
from retileup.core.exceptions import ValidationError, ProcessingError, RetileupError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('processing.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ImageProcessor:
    """Robust image processor with comprehensive error handling."""

    def __init__(self):
        self.tool = TilingTool()
        self.processed_count = 0
        self.error_count = 0

    def process_single_image(
        self,
        image_path: str,
        config: TilingConfig
    ) -> Optional[str]:
        """Process a single image with error handling.

        Returns:
            Success message or None if processing failed
        """
        try:
            # Validate input file
            path = Path(image_path)
            if not path.exists():
                raise FileNotFoundError(f"Image file not found: {image_path}")

            if not path.is_file():
                raise ValueError(f"Path is not a file: {image_path}")

            # Check file size (optional - prevent processing huge files)
            file_size = path.stat().st_size
            max_size = 100 * 1024 * 1024  # 100MB
            if file_size > max_size:
                raise ValueError(f"File too large: {file_size} bytes (max: {max_size})")

            logger.info(f"Processing: {image_path}")

            # Process image
            result = self.tool.process(image_path, config)

            if result.success:
                self.processed_count += 1
                message = f"Success: Created {len(result.outputs)} tiles"
                logger.info(message)
                return message
            else:
                self.error_count += 1
                logger.error(f"Processing failed: {result.error}")
                return None

        except ValidationError as e:
            self.error_count += 1
            logger.error(f"Configuration error for {image_path}: {e}")
            return None

        except ProcessingError as e:
            self.error_count += 1
            logger.error(f"Processing error for {image_path}: {e}")
            return None

        except RetileupError as e:
            self.error_count += 1
            logger.error(f"ReTileUp error for {image_path}: {e}")
            return None

        except FileNotFoundError as e:
            self.error_count += 1
            logger.error(f"File error: {e}")
            return None

        except PermissionError as e:
            self.error_count += 1
            logger.error(f"Permission error for {image_path}: {e}")
            return None

        except Exception as e:
            self.error_count += 1
            logger.exception(f"Unexpected error processing {image_path}: {e}")
            return None

    def process_batch(
        self,
        image_paths: List[str],
        tile_width: int = 256,
        tile_height: int = 256,
        grid_size: str = "2x2"
    ) -> dict:
        """Process a batch of images.

        Returns:
            Dictionary with processing statistics
        """
        logger.info(f"Starting batch processing of {len(image_paths)} images")

        try:
            # Create configuration
            config = TilingConfig(
                tile_width=tile_width,
                tile_height=tile_height,
                grid_pattern=grid_size,
                output_pattern="tiles/{base}_r{row}_c{col}.jpg",
                format="JPEG",
                quality=85,
                validate_bounds=True
            )

        except ValidationError as e:
            logger.error(f"Invalid configuration: {e}")
            return {
                'success': False,
                'error': f"Configuration error: {e}",
                'processed': 0,
                'errors': 0
            }

        # Process each image
        for image_path in image_paths:
            self.process_single_image(image_path, config)

        # Return statistics
        total = len(image_paths)
        success_rate = (self.processed_count / total * 100) if total > 0 else 0

        result = {
            'success': self.error_count == 0,
            'total': total,
            'processed': self.processed_count,
            'errors': self.error_count,
            'success_rate': f"{success_rate:.1f}%"
        }

        logger.info(f"Batch processing complete: {result}")
        return result

def main():
    """Main function with argument handling."""
    if len(sys.argv) < 2:
        print("Usage: python robust_processor.py <image1> [image2] ...")
        sys.exit(1)

    processor = ImageProcessor()

    try:
        result = processor.process_batch(sys.argv[1:])

        if result['success']:
            print(f"✓ All {result['total']} images processed successfully!")
            sys.exit(0)
        else:
            print(f"⚠ Processed {result['processed']}/{result['total']} images "
                  f"({result['success_rate']} success rate)")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        print("\nProcessing interrupted.")
        sys.exit(130)

    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## Custom Tool Development

### Simple Custom Tool

Create a basic custom tool:

```python
# custom_tools/watermark_tool.py
"""Custom watermark tool example."""

from typing import Optional
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from retileup.tools.base import BaseTool, ToolConfig, ToolResult
from retileup.core.exceptions import ProcessingError, ValidationError

class WatermarkConfig(ToolConfig):
    """Configuration for watermark tool."""

    text: str = "© ReTileUp"
    position: str = "bottom-right"  # top-left, top-right, bottom-left, bottom-right
    font_size: int = 24
    opacity: int = 128  # 0-255
    color: str = "white"

    def validate_position(self):
        valid_positions = ["top-left", "top-right", "bottom-left", "bottom-right"]
        if self.position not in valid_positions:
            raise ValidationError(f"Invalid position. Must be one of: {valid_positions}")

class WatermarkTool(BaseTool):
    """Tool for adding text watermarks to images."""

    name = "watermark"
    description = "Add text watermarks to images"
    version = "1.0.0"
    config_class = WatermarkConfig

    def process(self, image_path: str, config: WatermarkConfig) -> ToolResult:
        """Add watermark to image."""
        try:
            # Validate configuration
            config.validate_position()

            # Load image
            image = Image.open(image_path).convert("RGBA")

            # Create transparent overlay
            overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)

            # Try to load font (fallback to default if not available)
            try:
                font = ImageFont.truetype("arial.ttf", config.font_size)
            except OSError:
                font = ImageFont.load_default()

            # Calculate text position
            text_bbox = draw.textbbox((0, 0), config.text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            margin = 20
            if config.position == "top-left":
                x, y = margin, margin
            elif config.position == "top-right":
                x, y = image.width - text_width - margin, margin
            elif config.position == "bottom-left":
                x, y = margin, image.height - text_height - margin
            else:  # bottom-right
                x, y = image.width - text_width - margin, image.height - text_height - margin

            # Draw text with opacity
            text_color = (*self._parse_color(config.color), config.opacity)
            draw.text((x, y), config.text, font=font, fill=text_color)

            # Composite images
            watermarked = Image.alpha_composite(image, overlay)
            watermarked = watermarked.convert("RGB")  # Remove alpha for JPEG

            # Generate output path
            input_path = Path(image_path)
            output_path = input_path.parent / f"{input_path.stem}_watermarked{input_path.suffix}"

            # Save result
            watermarked.save(output_path, quality=95)

            return ToolResult(
                success=True,
                outputs=[str(output_path)],
                metadata={
                    "text": config.text,
                    "position": config.position,
                    "original_size": image.size,
                    "font_size": config.font_size
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                outputs=[]
            )

    def _parse_color(self, color_name: str) -> tuple:
        """Parse color name to RGB tuple."""
        colors = {
            "white": (255, 255, 255),
            "black": (0, 0, 0),
            "red": (255, 0, 0),
            "green": (0, 255, 0),
            "blue": (0, 0, 255),
            "yellow": (255, 255, 0),
            "cyan": (0, 255, 255),
            "magenta": (255, 0, 255),
        }
        return colors.get(color_name.lower(), (255, 255, 255))
```

### Using Custom Tools

```python
# Use the custom watermark tool
from custom_tools.watermark_tool import WatermarkTool, WatermarkConfig

# Create tool instance
watermark_tool = WatermarkTool()

# Create configuration
config = WatermarkConfig(
    text="© My Company 2024",
    position="bottom-right",
    font_size=32,
    opacity=128,
    color="white"
)

# Process image
result = watermark_tool.process("photo.jpg", config)

if result.success:
    print(f"Watermarked image saved: {result.outputs[0]}")
else:
    print(f"Error: {result.error}")
```

### CLI Integration for Custom Tools

```python
# Add CLI command for custom tool
# custom_commands/watermark.py

import typer
from rich.console import Console

from custom_tools.watermark_tool import WatermarkTool, WatermarkConfig

def watermark_command(
    text: str = typer.Option("© ReTileUp", help="Watermark text"),
    position: str = typer.Option("bottom-right", help="Position of watermark"),
    font_size: int = typer.Option(24, help="Font size"),
    opacity: int = typer.Option(128, help="Opacity (0-255)"),
    color: str = typer.Option("white", help="Text color"),
    input_file: str = typer.Argument(..., help="Input image file"),
) -> None:
    """Add watermark to image."""

    console = Console()

    try:
        # Create configuration
        config = WatermarkConfig(
            text=text,
            position=position,
            font_size=font_size,
            opacity=opacity,
            color=color
        )

        # Process image
        tool = WatermarkTool()
        result = tool.process(input_file, config)

        if result.success:
            console.print(f"[green]Success![/green] Watermarked image: {result.outputs[0]}")
        else:
            console.print(f"[red]Error:[/red] {result.error}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

# Register with main CLI app
if __name__ == "__main__":
    app = typer.Typer()
    app.command(name="watermark")(watermark_command)
    app()
```

Use the custom command:

```bash
python custom_commands/watermark.py \
  --text "© My Company 2024" \
  --position "bottom-right" \
  --font-size 32 \
  --opacity 200 \
  --color "yellow" \
  photo.jpg
```

---

## Additional Resources

### Sample Data

Create test images for examples:

```python
# create_sample_data.py
"""Create sample images for testing ReTileUp."""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def create_sample_images():
    """Create various sample images."""

    # Create samples directory
    samples_dir = Path("samples")
    samples_dir.mkdir(exist_ok=True)

    # Large landscape image
    large_img = Image.new("RGB", (1920, 1080), color="skyblue")
    draw = ImageDraw.Draw(large_img)
    draw.rectangle([100, 100, 1820, 980], fill="green")
    draw.text((960, 540), "Large Sample Image", anchor="mm", fill="white")
    large_img.save(samples_dir / "large_landscape.jpg", quality=95)

    # Square image
    square_img = Image.new("RGB", (800, 800), color="lightcoral")
    draw = ImageDraw.Draw(square_img)
    for i in range(0, 800, 100):
        draw.line([(i, 0), (i, 800)], fill="white", width=2)
        draw.line([(0, i), (800, i)], fill="white", width=2)
    square_img.save(samples_dir / "square_grid.png")

    # Small portrait
    portrait_img = Image.new("RGB", (600, 800), color="mediumpurple")
    draw = ImageDraw.Draw(portrait_img)
    draw.ellipse([50, 50, 550, 750], fill="lavender")
    portrait_img.save(samples_dir / "portrait.jpg")

    print(f"Sample images created in {samples_dir}/")

if __name__ == "__main__":
    create_sample_images()
```

### Performance Testing

```bash
#!/bin/bash
# performance_test.sh

echo "ReTileUp Performance Test"
echo "========================"

# Create large test image
python3 -c "
from PIL import Image
img = Image.new('RGB', (4000, 3000), color='red')
img.save('large_test.jpg', quality=95)
print('Created large test image: 4000x3000')
"

# Test different tile sizes
for size in 128 256 512; do
    echo "Testing ${size}x${size} tiles..."
    time retileup tile \
        --width $size --height $size \
        --grid 4x4 \
        --output-dir "test_${size}" \
        large_test.jpg
done

# Cleanup
rm large_test.jpg
rm -rf test_*

echo "Performance test complete!"
```

Run the performance test:

```bash
chmod +x performance_test.sh
./performance_test.sh
```

These examples demonstrate the full range of ReTileUp's capabilities, from basic tiling operations to advanced workflow automation and custom tool development. Use them as starting points for your own image processing workflows.