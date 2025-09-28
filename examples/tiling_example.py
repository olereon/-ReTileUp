#!/usr/bin/env python3
"""Example script demonstrating the TilingTool functionality.

This script shows various use cases for the TilingTool including:
- Basic tile extraction
- Grid-based tiling
- Custom patterns and overlaps
- Error handling and validation
- Performance monitoring
"""

import sys
import time
from pathlib import Path
from typing import List, Tuple

from PIL import Image

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from retileup.tools.tiling import TilingTool, TilingConfig
from retileup.utils.image import ImageUtils


def create_sample_image(path: Path, width: int = 1200, height: int = 800) -> None:
    """Create a sample image for demonstration purposes.

    Args:
        path: Output path for the sample image
        width: Image width in pixels
        height: Image height in pixels
    """
    print(f"Creating sample image: {width}x{height} at {path}")

    # Create base image with gradient background
    image = Image.new('RGB', (width, height))

    # Create a gradient background
    for y in range(height):
        for x in range(width):
            r = int(255 * x / width)
            g = int(255 * y / height)
            b = int(255 * (x + y) / (width + height))
            image.putpixel((x, y), (r, g, b))

    # Add some geometric patterns
    # Grid pattern
    grid_size = 50
    for x in range(0, width, grid_size):
        for y in range(0, height, grid_size):
            # Draw grid lines
            for i in range(min(5, width - x)):
                if y < height:
                    image.putpixel((x + i, y), (255, 255, 255))
            for j in range(min(5, height - y)):
                if x < width:
                    image.putpixel((x, y + j), (255, 255, 255))

    # Add some colored rectangles
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]
    for i, color in enumerate(colors):
        rect_x = (i * width // len(colors)) + 50
        rect_y = height // 2 - 50
        rect_w = width // len(colors) - 100
        rect_h = 100

        for x in range(rect_x, min(rect_x + rect_w, width)):
            for y in range(rect_y, min(rect_y + rect_h, height)):
                image.putpixel((x, y), color)

    # Save the image
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, quality=95)
    print(f"Sample image created: {path}")


def example_basic_tiling():
    """Demonstrate basic tile extraction."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Tile Extraction")
    print("="*60)

    # Setup paths
    base_dir = Path(__file__).parent
    input_image = base_dir / "data" / "sample_image.jpg"
    output_dir = base_dir / "output" / "basic_tiling"

    # Create sample image if it doesn't exist
    if not input_image.exists():
        create_sample_image(input_image)

    # Initialize tool
    tool = TilingTool()

    # Define tile extraction coordinates
    coordinates = [
        (0, 0),      # Top-left corner
        (200, 0),    # Top-middle
        (400, 0),    # Top-right area
        (0, 200),    # Middle-left
        (200, 200),  # Center
        (400, 200)   # Middle-right
    ]

    # Create configuration
    config = TilingConfig(
        input_path=input_image,
        output_dir=output_dir,
        tile_width=200,
        tile_height=200,
        coordinates=coordinates,
        output_pattern="tile_{base}_{x}_{y}.{ext}",
        verbose=True
    )

    # Validate configuration
    print("Validating configuration...")
    errors = tool.validate_config(config)
    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
        return

    print("Configuration is valid!")

    # Execute tiling
    print("Executing tile extraction...")
    result = tool.execute_with_timing(config)

    # Display results
    if result.success:
        print(f"✓ SUCCESS: {result.message}")
        print(f"  Execution time: {result.execution_time:.2f}s")
        print(f"  Tiles created: {len(result.output_files)}")
        print(f"  Processing rate: {result.metadata['pixels_per_second']/1_000_000:.1f} MP/s")

        print("\nOutput files:")
        for i, output_file in enumerate(result.output_files):
            print(f"  {i+1}. {output_file.name}")
    else:
        print(f"✗ FAILED: {result.message}")


def example_grid_tiling():
    """Demonstrate grid-based tiling."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Grid-Based Tiling")
    print("="*60)

    # Setup paths
    base_dir = Path(__file__).parent
    input_image = base_dir / "data" / "sample_image.jpg"
    output_dir = base_dir / "output" / "grid_tiling"

    # Ensure sample image exists
    if not input_image.exists():
        create_sample_image(input_image)

    tool = TilingTool()

    # Generate grid coordinates
    tile_size = 150
    grid_coordinates = []

    # Load image to get dimensions
    with Image.open(input_image) as img:
        img_width, img_height = img.size

    print(f"Source image: {img_width}x{img_height}")
    print(f"Tile size: {tile_size}x{tile_size}")

    # Generate grid covering the entire image
    for x in range(0, img_width - tile_size + 1, tile_size):
        for y in range(0, img_height - tile_size + 1, tile_size):
            grid_coordinates.append((x, y))

    print(f"Generated {len(grid_coordinates)} tile coordinates")

    # Create configuration with overlap
    config = TilingConfig(
        input_path=input_image,
        output_dir=output_dir,
        tile_width=tile_size,
        tile_height=tile_size,
        coordinates=grid_coordinates,
        output_pattern="grid_{base}_{x:04d}_{y:04d}.{ext}",
        overlap=20,  # 20 pixel overlap between tiles
        preserve_metadata=True
    )

    # Execute
    print("Executing grid tiling...")
    start_time = time.time()
    result = tool.execute(config)
    end_time = time.time()

    if result.success:
        print(f"✓ Grid tiling completed in {end_time - start_time:.2f}s")
        print(f"  Total tiles: {len(result.output_files)}")
        print(f"  Overlap: {config.overlap} pixels")
        print(f"  Average tile processing time: {(end_time - start_time)/len(result.output_files)*1000:.1f}ms")
    else:
        print(f"✗ Grid tiling failed: {result.message}")


def example_custom_patterns():
    """Demonstrate custom tiling patterns and features."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Custom Patterns and Features")
    print("="*60)

    # Setup paths
    base_dir = Path(__file__).parent
    input_image = base_dir / "data" / "sample_image.jpg"
    output_dir = base_dir / "output" / "custom_patterns"

    # Ensure sample image exists
    if not input_image.exists():
        create_sample_image(input_image, 1600, 1200)  # Larger image for this example

    tool = TilingTool()

    # Example 1: Diagonal pattern
    print("\nSubexample 3a: Diagonal Pattern")
    diagonal_coords = [(i * 100, i * 80) for i in range(8)]

    config_diagonal = TilingConfig(
        input_path=input_image,
        output_dir=output_dir / "diagonal",
        tile_width=200,
        tile_height=160,
        coordinates=diagonal_coords,
        output_pattern="diagonal_{base}_{x}_{y}_sample.{ext}",
        maintain_aspect=True
    )

    result_diagonal = tool.execute(config_diagonal)
    print(f"Diagonal pattern: {'✓' if result_diagonal.success else '✗'} "
          f"({len(result_diagonal.output_files)} tiles)")

    # Example 2: Circular pattern (approximation)
    print("\nSubexample 3b: Circular Pattern")
    import math

    center_x, center_y = 400, 300
    radius = 200
    circular_coords = []

    for angle in range(0, 360, 45):  # Every 45 degrees
        x = int(center_x + radius * math.cos(math.radians(angle)))
        y = int(center_y + radius * math.sin(math.radians(angle)))
        if x >= 0 and y >= 0:  # Ensure coordinates are positive
            circular_coords.append((x, y))

    config_circular = TilingConfig(
        input_path=input_image,
        output_dir=output_dir / "circular",
        tile_width=150,
        tile_height=150,
        coordinates=circular_coords,
        output_pattern="circular_{base}_{x:03d}_{y:03d}.{ext}",
        overlap=10
    )

    result_circular = tool.execute(config_circular)
    print(f"Circular pattern: {'✓' if result_circular.success else '✗'} "
          f"({len(result_circular.output_files)} tiles)")

    # Example 3: Different sizes
    print("\nSubexample 3c: Variable Tile Sizes")

    # Large tiles
    large_coords = [(0, 0), (300, 0)]
    config_large = TilingConfig(
        input_path=input_image,
        output_dir=output_dir / "large",
        tile_width=400,
        tile_height=400,
        coordinates=large_coords,
        output_pattern="large_{base}_{x}_{y}.{ext}"
    )

    # Small tiles
    small_coords = [(i * 50, j * 50) for i in range(10) for j in range(5)]
    config_small = TilingConfig(
        input_path=input_image,
        output_dir=output_dir / "small",
        tile_width=50,
        tile_height=50,
        coordinates=small_coords[:20],  # Limit to first 20
        output_pattern="small_{base}_{x:03d}_{y:03d}.{ext}"
    )

    result_large = tool.execute(config_large)
    result_small = tool.execute(config_small)

    print(f"Large tiles: {'✓' if result_large.success else '✗'} "
          f"({len(result_large.output_files)} tiles)")
    print(f"Small tiles: {'✓' if result_small.success else '✗'} "
          f"({len(result_small.output_files)} tiles)")


def example_error_handling():
    """Demonstrate error handling and validation."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Error Handling and Validation")
    print("="*60)

    base_dir = Path(__file__).parent
    output_dir = base_dir / "output" / "error_handling"
    tool = TilingTool()

    # Example 1: Missing input file
    print("\nSubexample 4a: Missing Input File")
    try:
        config_missing = TilingConfig(
            input_path=base_dir / "nonexistent.jpg",
            output_dir=output_dir,
            tile_width=100,
            tile_height=100,
            coordinates=[(0, 0)]
        )

        errors = tool.validate_config(config_missing)
        print(f"Validation errors for missing file: {len(errors)}")
        for error in errors:
            print(f"  - {error}")

    except Exception as e:
        print(f"Exception during validation: {e}")

    # Example 2: Invalid coordinates
    print("\nSubexample 4b: Invalid Configuration")
    input_image = base_dir / "data" / "sample_image.jpg"

    if not input_image.exists():
        create_sample_image(input_image, 400, 300)  # Small image

    try:
        config_invalid = TilingConfig(
            input_path=input_image,
            output_dir=output_dir,
            tile_width=200,
            tile_height=200,
            coordinates=[(500, 500)]  # Way out of bounds
        )

        errors = tool.validate_config(config_invalid)
        print(f"Validation errors for out-of-bounds coordinates: {len(errors)}")
        for error in errors:
            print(f"  - {error}")

    except Exception as e:
        print(f"Exception during validation: {e}")

    # Example 3: Dry run mode
    print("\nSubexample 4c: Dry Run Mode")
    config_dry_run = TilingConfig(
        input_path=input_image,
        output_dir=output_dir / "dry_run",
        tile_width=100,
        tile_height=100,
        coordinates=[(0, 0), (100, 0)],
        dry_run=True
    )

    result_dry_run = tool.execute(config_dry_run)
    print(f"Dry run result: {'✓' if result_dry_run.success else '✗'}")
    print(f"Output files listed: {len(result_dry_run.output_files)}")
    print(f"Files actually created: {sum(1 for f in result_dry_run.output_files if f.exists())}")


def example_performance_monitoring():
    """Demonstrate performance monitoring and optimization."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Performance Monitoring")
    print("="*60)

    base_dir = Path(__file__).parent
    input_image = base_dir / "data" / "large_sample.jpg"
    output_dir = base_dir / "output" / "performance"

    # Create a larger image for performance testing
    if not input_image.exists():
        print("Creating large sample image for performance testing...")
        create_sample_image(input_image, 2400, 1800)

    tool = TilingTool()

    # Test different tile sizes and their performance impact
    test_configs = [
        {"size": 128, "name": "Small tiles"},
        {"size": 256, "name": "Medium tiles"},
        {"size": 512, "name": "Large tiles"}
    ]

    print(f"Performance testing with image: {input_image}")

    for test_config in test_configs:
        tile_size = test_config["size"]
        test_name = test_config["name"]

        print(f"\nTesting {test_name} ({tile_size}x{tile_size}):")

        # Generate coordinates for full coverage
        with Image.open(input_image) as img:
            img_width, img_height = img.size

        coords = []
        for x in range(0, img_width - tile_size + 1, tile_size):
            for y in range(0, img_height - tile_size + 1, tile_size):
                coords.append((x, y))

        config = TilingConfig(
            input_path=input_image,
            output_dir=output_dir / f"tiles_{tile_size}x{tile_size}",
            tile_width=tile_size,
            tile_height=tile_size,
            coordinates=coords,
            output_pattern=f"perf_{tile_size}_{{base}}_{{x}}_{{y}}.{{ext}}"
        )

        # Execute and measure
        start_time = time.time()
        result = tool.execute_with_timing(config)
        total_time = time.time() - start_time

        if result.success:
            metadata = result.metadata
            print(f"  ✓ Processed {len(result.output_files)} tiles")
            print(f"  ✓ Total time: {total_time:.2f}s")
            print(f"  ✓ Avg per tile: {total_time/len(result.output_files)*1000:.1f}ms")
            print(f"  ✓ Throughput: {metadata['pixels_per_second']/1_000_000:.1f} MP/s")
            print(f"  ✓ Peak memory estimate: {metadata.get('peak_memory_mb', 'N/A')} MB")
        else:
            print(f"  ✗ Failed: {result.message}")


def main():
    """Run all examples."""
    print("ReTileUp TilingTool Examples")
    print("="*60)
    print("This script demonstrates various features of the TilingTool.")

    try:
        example_basic_tiling()
        example_grid_tiling()
        example_custom_patterns()
        example_error_handling()
        example_performance_monitoring()

        print("\n" + "="*60)
        print("All examples completed!")
        print("Check the 'examples/output' directory for generated tiles.")
        print("="*60)

    except KeyboardInterrupt:
        print("\n\nExecution interrupted by user.")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()