#!/usr/bin/env python3
"""
Basic usage example for ReTileUp.

This script demonstrates how to use ReTileUp programmatically
for basic image processing tasks.
"""

from pathlib import Path

from PIL import Image

from retileup import Config, ToolRegistry, Workflow, WorkflowOrchestrator
from retileup.utils.image import ImageUtils


def main():
    """Main function demonstrating basic ReTileUp usage."""
    print("🎨 ReTileUp Basic Usage Example")
    print("=" * 40)

    # 1. Create a sample image for testing
    print("\n1. Creating sample image...")
    sample_image = Image.new('RGB', (800, 600), color='lightblue')
    sample_path = Path("sample_input.png")
    sample_image.save(sample_path)
    print(f"   Created: {sample_path}")

    # 2. Initialize ReTileUp components
    print("\n2. Initializing ReTileUp components...")
    config = Config()
    registry = ToolRegistry()
    orchestrator = WorkflowOrchestrator(registry, config)
    print("   ✓ Configuration loaded")
    print("   ✓ Tool registry created")
    print("   ✓ Workflow orchestrator ready")

    # 3. Load and inspect the image
    print("\n3. Loading and inspecting image...")
    loaded_image = ImageUtils.load_image(sample_path)
    image_info = ImageUtils.get_image_info(loaded_image)
    print(f"   Image size: {image_info['width']}x{image_info['height']}")
    print(f"   Image mode: {image_info['mode']}")
    print(f"   Image format: {image_info['format']}")

    # 4. Create a simple workflow
    print("\n4. Creating workflow...")
    workflow = Workflow(
        name="basic_example",
        description="Basic image processing example"
    )

    # Add a hypothetical resize step (would need actual tools registered)
    workflow.add_step(
        name="resize",
        tool_name="resize_tool",
        description="Resize image to 400x300",
        parameters={
            "width": 400,
            "height": 300,
            "method": "lanczos"
        }
    )

    print(f"   Created workflow: {workflow.name}")
    print(f"   Steps: {len(workflow.steps)}")

    # 5. Validate workflow (will show validation errors since we don't have tools)
    print("\n5. Validating workflow...")
    validation_errors = workflow.validate_workflow(registry)
    if validation_errors:
        print(f"   ⚠️  Validation errors (expected): {len(validation_errors)}")
        for error in validation_errors[:3]:  # Show first 3 errors
            print(f"      - {error}")
    else:
        print("   ✓ Workflow validation passed")

    # 6. Demonstrate configuration
    print("\n6. Configuration example...")
    print(f"   Debug mode: {config.debug}")
    print(f"   Max workers: {config.performance.max_workers}")
    print(f"   Output format: {config.output.format}")
    print(f"   Output quality: {config.output.quality}")

    # 7. Show supported image formats
    print("\n7. Supported image formats...")
    supported_formats = ImageUtils.get_supported_formats()
    print(f"   Total formats: {len(supported_formats)}")
    print(f"   Common formats: {', '.join(supported_formats[:10])}")

    # 8. Demonstrate image utilities
    print("\n8. Image utilities demonstration...")

    # Resize the image using utilities
    resized_image = ImageUtils.resize_image(
        loaded_image,
        (400, 300),
        method='lanczos',
        maintain_aspect=True
    )
    print(f"   Resized to: {resized_image.size}")

    # Save the result
    output_path = Path("sample_output.png")
    ImageUtils.save_image(resized_image, output_path)
    print(f"   Saved result: {output_path}")

    # 9. Cleanup
    print("\n9. Cleaning up...")
    orchestrator.cleanup()
    print("   ✓ Resources cleaned up")

    # Clean up sample files
    sample_path.unlink(missing_ok=True)
    output_path.unlink(missing_ok=True)
    print("   ✓ Sample files removed")

    print("\n🎉 Basic usage example completed successfully!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Example interrupted by user")
    except Exception as e:
        print(f"\n❌ Error running example: {e}")
        import traceback
        traceback.print_exc()