"""Test data generator for ReTileUp tests.

This module provides utilities to generate test images, configurations,
and other test data needed for comprehensive testing.
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from PIL import Image, ImageDraw, ImageFont


class TestImageGenerator:
    """Generator for test images with various characteristics."""

    @staticmethod
    def create_solid_color_image(
        size: Tuple[int, int],
        color: Tuple[int, int, int] = (255, 0, 0),
        mode: str = 'RGB'
    ) -> Image.Image:
        """Create a solid color image.

        Args:
            size: Image size (width, height)
            color: RGB color tuple
            mode: Image mode ('RGB', 'RGBA', 'L', etc.)

        Returns:
            PIL Image object
        """
        if mode == 'L':
            # Convert RGB to grayscale
            gray_value = int(0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2])
            return Image.new(mode, size, gray_value)
        elif mode == 'RGBA':
            # Add alpha channel
            rgba_color = color + (255,) if len(color) == 3 else color
            return Image.new(mode, size, rgba_color)
        else:
            return Image.new(mode, size, color)

    @staticmethod
    def create_gradient_image(
        size: Tuple[int, int],
        start_color: Tuple[int, int, int] = (0, 0, 0),
        end_color: Tuple[int, int, int] = (255, 255, 255),
        direction: str = 'horizontal'
    ) -> Image.Image:
        """Create a gradient image.

        Args:
            size: Image size (width, height)
            start_color: Starting color
            end_color: Ending color
            direction: Gradient direction ('horizontal', 'vertical', 'diagonal')

        Returns:
            PIL Image object
        """
        width, height = size
        image = Image.new('RGB', size)
        draw = ImageDraw.Draw(image)

        if direction == 'horizontal':
            for x in range(width):
                ratio = x / width
                color = tuple(
                    int(start_color[i] + (end_color[i] - start_color[i]) * ratio)
                    for i in range(3)
                )
                draw.line([(x, 0), (x, height)], fill=color)
        elif direction == 'vertical':
            for y in range(height):
                ratio = y / height
                color = tuple(
                    int(start_color[i] + (end_color[i] - start_color[i]) * ratio)
                    for i in range(3)
                )
                draw.line([(0, y), (width, y)], fill=color)
        elif direction == 'diagonal':
            for x in range(width):
                for y in range(height):
                    ratio = (x + y) / (width + height)
                    color = tuple(
                        int(start_color[i] + (end_color[i] - start_color[i]) * ratio)
                        for i in range(3)
                    )
                    draw.point((x, y), fill=color)

        return image

    @staticmethod
    def create_pattern_image(
        size: Tuple[int, int],
        pattern: str = 'checkerboard',
        colors: Tuple[Tuple[int, int, int], Tuple[int, int, int]] = ((255, 255, 255), (0, 0, 0)),
        scale: int = 10
    ) -> Image.Image:
        """Create a patterned image.

        Args:
            size: Image size (width, height)
            pattern: Pattern type ('checkerboard', 'stripes', 'dots')
            colors: Two colors for the pattern
            scale: Pattern scale factor

        Returns:
            PIL Image object
        """
        width, height = size
        image = Image.new('RGB', size, colors[0])
        draw = ImageDraw.Draw(image)

        if pattern == 'checkerboard':
            for x in range(0, width, scale * 2):
                for y in range(0, height, scale * 2):
                    # Alternate pattern
                    if (x // scale + y // scale) % 2:
                        draw.rectangle([x, y, x + scale, y + scale], fill=colors[1])
                    if (x // scale + y // scale + 1) % 2:
                        draw.rectangle([x + scale, y + scale, x + scale * 2, y + scale * 2], fill=colors[1])

        elif pattern == 'stripes':
            for x in range(0, width, scale * 2):
                draw.rectangle([x, 0, x + scale, height], fill=colors[1])

        elif pattern == 'dots':
            for x in range(scale, width, scale * 2):
                for y in range(scale, height, scale * 2):
                    draw.ellipse([x - scale//2, y - scale//2, x + scale//2, y + scale//2], fill=colors[1])

        return image

    @staticmethod
    def create_text_image(
        size: Tuple[int, int],
        text: str = "TEST IMAGE",
        font_size: int = 24,
        text_color: Tuple[int, int, int] = (0, 0, 0),
        background_color: Tuple[int, int, int] = (255, 255, 255)
    ) -> Image.Image:
        """Create an image with text.

        Args:
            size: Image size (width, height)
            text: Text to render
            font_size: Font size
            text_color: Text color
            background_color: Background color

        Returns:
            PIL Image object
        """
        image = Image.new('RGB', size, background_color)
        draw = ImageDraw.Draw(image)

        # Try to use a default font, fall back to built-in if not available
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except (OSError, IOError):
            try:
                font = ImageFont.load_default()
            except (OSError, IOError):
                font = None

        # Get text bounding box
        if font:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            # Rough estimation if no font available
            text_width = len(text) * font_size // 2
            text_height = font_size

        # Center the text
        x = (size[0] - text_width) // 2
        y = (size[1] - text_height) // 2

        draw.text((x, y), text, fill=text_color, font=font)
        return image

    @staticmethod
    def create_noise_image(
        size: Tuple[int, int],
        noise_type: str = 'random',
        intensity: float = 1.0
    ) -> Image.Image:
        """Create an image with noise.

        Args:
            size: Image size (width, height)
            noise_type: Type of noise ('random', 'gaussian', 'salt_pepper')
            intensity: Noise intensity (0.0 to 1.0)

        Returns:
            PIL Image object
        """
        width, height = size
        image = Image.new('RGB', size)
        pixels = image.load()

        if noise_type == 'random':
            # Random noise using Python's random module
            for y in range(height):
                for x in range(width):
                    r = int(random.randint(0, 255) * intensity)
                    g = int(random.randint(0, 255) * intensity)
                    b = int(random.randint(0, 255) * intensity)
                    pixels[x, y] = (r, g, b)

        elif noise_type == 'gaussian':
            # Approximate gaussian noise
            for y in range(height):
                for x in range(width):
                    base = 128
                    noise = random.gauss(0, 64 * intensity)
                    value = max(0, min(255, int(base + noise)))
                    pixels[x, y] = (value, value, value)

        elif noise_type == 'salt_pepper':
            # Salt and pepper noise
            for y in range(height):
                for x in range(width):
                    if random.random() < intensity * 0.05:
                        # Salt (white)
                        pixels[x, y] = (255, 255, 255)
                    elif random.random() < intensity * 0.05:
                        # Pepper (black)
                        pixels[x, y] = (0, 0, 0)
                    else:
                        # Gray background
                        pixels[x, y] = (128, 128, 128)

        else:
            raise ValueError(f"Unknown noise type: {noise_type}")

        return image

    @staticmethod
    def create_complex_image(
        size: Tuple[int, int],
        elements: List[str] = None
    ) -> Image.Image:
        """Create a complex image with multiple elements.

        Args:
            size: Image size (width, height)
            elements: List of elements to include

        Returns:
            PIL Image object
        """
        if elements is None:
            elements = ['gradient', 'text', 'shapes', 'noise']

        width, height = size
        image = Image.new('RGB', size, (255, 255, 255))
        draw = ImageDraw.Draw(image)

        if 'gradient' in elements:
            # Add gradient background
            gradient = TestImageGenerator.create_gradient_image(
                (width // 2, height), (255, 200, 200), (200, 200, 255)
            )
            image.paste(gradient, (0, 0))

        if 'shapes' in elements:
            # Add some shapes
            draw.ellipse([width//4, height//4, 3*width//4, 3*height//4],
                        outline=(255, 0, 0), width=3)
            draw.rectangle([width//8, height//8, width//4, height//4],
                          fill=(0, 255, 0))
            draw.polygon([(3*width//4, height//8), (7*width//8, height//4),
                         (5*width//8, height//4)], fill=(0, 0, 255))

        if 'text' in elements:
            # Add text
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except (OSError, IOError):
                font = None

            draw.text((width//2 - 50, height//2), "Complex Test Image",
                     fill=(0, 0, 0), font=font)

        if 'noise' in elements:
            # Add some noise
            noise_overlay = TestImageGenerator.create_noise_image(
                (width//3, height//3), intensity=0.3
            )
            image.paste(noise_overlay, (2*width//3, 2*height//3))

        return image


class TestDataGenerator:
    """Generator for various test data types."""

    @staticmethod
    def create_test_images(output_dir: Path, image_specs: List[Dict[str, Any]]) -> Dict[str, Path]:
        """Create a set of test images.

        Args:
            output_dir: Directory to save images
            image_specs: List of image specifications

        Returns:
            Dictionary mapping image names to file paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        created_images = {}

        for spec in image_specs:
            name = spec.get('name', 'test_image')
            size = spec.get('size', (100, 100))
            image_type = spec.get('type', 'solid')
            format_name = spec.get('format', 'PNG')

            # Generate image based on type
            if image_type == 'solid':
                color = spec.get('color', (255, 0, 0))
                mode = spec.get('mode', 'RGB')
                image = TestImageGenerator.create_solid_color_image(size, color, mode)

            elif image_type == 'gradient':
                start_color = spec.get('start_color', (0, 0, 0))
                end_color = spec.get('end_color', (255, 255, 255))
                direction = spec.get('direction', 'horizontal')
                image = TestImageGenerator.create_gradient_image(size, start_color, end_color, direction)

            elif image_type == 'pattern':
                pattern = spec.get('pattern', 'checkerboard')
                colors = spec.get('colors', ((255, 255, 255), (0, 0, 0)))
                scale = spec.get('scale', 10)
                image = TestImageGenerator.create_pattern_image(size, pattern, colors, scale)

            elif image_type == 'text':
                text = spec.get('text', 'TEST')
                font_size = spec.get('font_size', 24)
                text_color = spec.get('text_color', (0, 0, 0))
                bg_color = spec.get('background_color', (255, 255, 255))
                image = TestImageGenerator.create_text_image(size, text, font_size, text_color, bg_color)

            elif image_type == 'noise':
                noise_type = spec.get('noise_type', 'random')
                intensity = spec.get('intensity', 1.0)
                image = TestImageGenerator.create_noise_image(size, noise_type, intensity)

            elif image_type == 'complex':
                elements = spec.get('elements', None)
                image = TestImageGenerator.create_complex_image(size, elements)

            else:
                # Default to solid color
                image = TestImageGenerator.create_solid_color_image(size)

            # Save image
            file_path = output_dir / f"{name}.{format_name.lower()}"

            # Handle format-specific options
            save_kwargs = {}
            if format_name.upper() == 'JPEG':
                save_kwargs['quality'] = spec.get('quality', 95)
                # Convert to RGB if necessary
                if image.mode in ('RGBA', 'P'):
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    if image.mode == 'P':
                        image = image.convert('RGBA')
                    background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                    image = background

            image.save(file_path, format=format_name.upper(), **save_kwargs)
            created_images[name] = file_path

        return created_images

    @staticmethod
    def create_test_configs(output_dir: Path) -> Dict[str, Path]:
        """Create test configuration files.

        Args:
            output_dir: Directory to save configs

        Returns:
            Dictionary mapping config names to file paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        created_configs = {}

        # Valid configuration
        valid_config = {
            "app_name": "ReTileUp",
            "version": "1.0.0",
            "defaults": {
                "format": "PNG",
                "quality": 95,
                "optimize": True
            },
            "tiling": {
                "default_size": 256,
                "overlap": 10,
                "parallel": True
            }
        }

        valid_config_path = output_dir / "valid_config.yaml"
        with open(valid_config_path, 'w') as f:
            import yaml
            yaml.dump(valid_config, f, default_flow_style=False)
        created_configs['valid'] = valid_config_path

        # Minimal configuration
        minimal_config = {
            "app_name": "ReTileUp"
        }

        minimal_config_path = output_dir / "minimal_config.yaml"
        with open(minimal_config_path, 'w') as f:
            yaml.dump(minimal_config, f, default_flow_style=False)
        created_configs['minimal'] = minimal_config_path

        # Complex configuration
        complex_config = {
            "app_name": "ReTileUp",
            "version": "1.0.0",
            "debug": False,
            "defaults": {
                "format": "PNG",
                "quality": 95,
                "optimize": True,
                "preserve_metadata": True
            },
            "tiling": {
                "default_size": 512,
                "overlap": 20,
                "max_tiles": 1000,
                "parallel": True,
                "workers": 4
            },
            "tools": {
                "tiling_tool": {
                    "enabled": True,
                    "priority": 1,
                    "config": {
                        "algorithm": "grid",
                        "edge_handling": "clip"
                    }
                }
            },
            "output": {
                "create_directories": True,
                "overwrite_existing": False,
                "naming_pattern": "{basename}_{index:03d}.{ext}"
            }
        }

        complex_config_path = output_dir / "complex_config.yaml"
        with open(complex_config_path, 'w') as f:
            yaml.dump(complex_config, f, default_flow_style=False)
        created_configs['complex'] = complex_config_path

        # JSON configuration
        json_config_path = output_dir / "config.json"
        with open(json_config_path, 'w') as f:
            json.dump(valid_config, f, indent=2)
        created_configs['json'] = json_config_path

        return created_configs

    @staticmethod
    def create_test_coordinates() -> Dict[str, List[Tuple[int, int]]]:
        """Create test coordinate sets.

        Returns:
            Dictionary mapping coordinate set names to coordinate lists
        """
        coordinate_sets = {}

        # Simple grid
        coordinate_sets['simple_grid'] = [
            (0, 0), (100, 0), (200, 0),
            (0, 100), (100, 100), (200, 100)
        ]

        # Single tile
        coordinate_sets['single'] = [(0, 0)]

        # Large grid
        coordinates = []
        for x in range(0, 1000, 100):
            for y in range(0, 800, 100):
                coordinates.append((x, y))
        coordinate_sets['large_grid'] = coordinates

        # Irregular spacing
        coordinate_sets['irregular'] = [
            (0, 0), (50, 30), (150, 25), (300, 100),
            (25, 200), (175, 180), (275, 250)
        ]

        # Overlapping coordinates
        coordinate_sets['overlapping'] = [
            (0, 0), (50, 0), (25, 25), (75, 25),
            (0, 50), (50, 50)
        ]

        return coordinate_sets

    @staticmethod
    def create_performance_test_data(output_dir: Path) -> Dict[str, Any]:
        """Create test data for performance testing.

        Args:
            output_dir: Directory to save test data

        Returns:
            Dictionary with test data information
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        performance_data = {
            'images': {},
            'coordinates': {},
            'configs': {}
        }

        # Create images of various sizes for performance testing
        image_sizes = [
            (100, 100, 'small'),
            (500, 500, 'medium'),
            (1000, 1000, 'large'),
            (2000, 2000, 'very_large')
        ]

        for width, height, size_name in image_sizes:
            image = TestImageGenerator.create_complex_image((width, height))
            image_path = output_dir / f"perf_test_{size_name}.png"
            image.save(image_path, 'PNG')
            performance_data['images'][size_name] = {
                'path': image_path,
                'size': (width, height),
                'estimated_memory_mb': (width * height * 3) / (1024 * 1024)
            }

        # Create coordinate sets for different tile counts
        tile_counts = [1, 4, 16, 64, 256]
        for tile_count in tile_counts:
            grid_size = int(tile_count ** 0.5)
            if grid_size * grid_size != tile_count:
                grid_size = int(tile_count ** 0.5) + 1

            coordinates = []
            tile_size = 100
            for i in range(tile_count):
                x = (i % grid_size) * tile_size
                y = (i // grid_size) * tile_size
                coordinates.append((x, y))

            performance_data['coordinates'][f'tiles_{tile_count}'] = coordinates

        return performance_data


def generate_all_test_fixtures(fixtures_dir: Path):
    """Generate all test fixtures.

    Args:
        fixtures_dir: Directory to create fixtures in
    """
    print("Generating test fixtures...")

    # Create standard test images
    image_specs = [
        {'name': 'rgb_100x100', 'size': (100, 100), 'type': 'solid', 'color': (255, 0, 0), 'format': 'PNG'},
        {'name': 'rgba_100x100', 'size': (100, 100), 'type': 'solid', 'color': (0, 255, 0, 128), 'mode': 'RGBA', 'format': 'PNG'},
        {'name': 'grayscale_100x100', 'size': (100, 100), 'type': 'solid', 'color': (128, 128, 128), 'mode': 'L', 'format': 'PNG'},
        {'name': 'gradient_200x150', 'size': (200, 150), 'type': 'gradient', 'direction': 'horizontal', 'format': 'JPEG', 'quality': 90},
        {'name': 'checkerboard_150x150', 'size': (150, 150), 'type': 'pattern', 'pattern': 'checkerboard', 'scale': 20, 'format': 'PNG'},
        {'name': 'text_300x100', 'size': (300, 100), 'type': 'text', 'text': 'ReTileUp Test', 'font_size': 20, 'format': 'PNG'},
        {'name': 'noise_200x200', 'size': (200, 200), 'type': 'noise', 'noise_type': 'gaussian', 'intensity': 0.5, 'format': 'PNG'},
        {'name': 'complex_400x300', 'size': (400, 300), 'type': 'complex', 'elements': ['gradient', 'text', 'shapes'], 'format': 'PNG'},
        {'name': 'large_1000x800', 'size': (1000, 800), 'type': 'pattern', 'pattern': 'stripes', 'scale': 40, 'format': 'JPEG'},
    ]

    images_dir = fixtures_dir / "images"
    created_images = TestDataGenerator.create_test_images(images_dir, image_specs)
    print(f"Created {len(created_images)} test images in {images_dir}")

    # Create test configurations
    configs_dir = fixtures_dir / "configs"
    created_configs = TestDataGenerator.create_test_configs(configs_dir)
    print(f"Created {len(created_configs)} test configurations in {configs_dir}")

    # Create coordinate test data
    coordinates = TestDataGenerator.create_test_coordinates()
    coords_file = fixtures_dir / "test_coordinates.json"
    with open(coords_file, 'w') as f:
        json.dump(coordinates, f, indent=2)
    print(f"Created coordinate test data in {coords_file}")

    # Create performance test data
    perf_dir = fixtures_dir / "performance"
    perf_data = TestDataGenerator.create_performance_test_data(perf_dir)
    perf_info_file = fixtures_dir / "performance_test_info.json"

    # Convert Path objects to strings for JSON serialization
    perf_data_serializable = {}
    for key, value in perf_data.items():
        if isinstance(value, dict):
            perf_data_serializable[key] = {}
            for subkey, subvalue in value.items():
                if isinstance(subvalue, dict) and 'path' in subvalue:
                    perf_data_serializable[key][subkey] = {
                        **subvalue,
                        'path': str(subvalue['path'])
                    }
                else:
                    perf_data_serializable[key][subkey] = subvalue
        else:
            perf_data_serializable[key] = value

    with open(perf_info_file, 'w') as f:
        json.dump(perf_data_serializable, f, indent=2)
    print(f"Created performance test data in {perf_dir}")

    print("Test fixture generation complete!")


if __name__ == "__main__":
    # Generate fixtures when run directly
    fixtures_dir = Path(__file__).parent
    generate_all_test_fixtures(fixtures_dir)