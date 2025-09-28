#!/usr/bin/env python3
"""
Workflow example for ReTileUp.

This script demonstrates how to create, load, and execute workflows
programmatically using ReTileUp.
"""

import json
import tempfile
from pathlib import Path

import yaml
from PIL import Image

from retileup.core.config import Config
from retileup.core.registry import ToolRegistry
from retileup.core.workflow import Workflow, WorkflowStep
from retileup.core.orchestrator import WorkflowOrchestrator
from retileup.utils.progress import ProgressTracker


def create_sample_workflow() -> Workflow:
    """Create a sample workflow programmatically."""
    workflow = Workflow(
        name="example_workflow",
        version="1.0.0",
        description="Example workflow created programmatically",
        author="ReTileUp Example"
    )

    # Add global parameters
    workflow.global_parameters = {
        "target_width": 800,
        "target_height": 600,
        "output_format": "JPEG",
        "quality": 90
    }

    # Add steps
    workflow.add_step(
        name="load",
        tool_name="image_loader",
        description="Load the input image",
        parameters={
            "validate": True,
            "auto_orient": True
        },
        tags=["input", "validation"]
    )

    workflow.add_step(
        name="resize",
        tool_name="resize_tool",
        description="Resize image to target dimensions",
        parameters={
            "width": "{{ global_parameters.target_width }}",
            "height": "{{ global_parameters.target_height }}",
            "method": "lanczos",
            "maintain_aspect": True
        },
        tags=["transform", "resize"]
    )

    workflow.add_step(
        name="enhance",
        tool_name="enhancement_tool",
        description="Enhance image quality",
        parameters={
            "brightness": 1.1,
            "contrast": 1.05,
            "saturation": 1.02
        },
        tags=["enhancement", "color"]
    )

    workflow.add_step(
        name="save",
        tool_name="image_saver",
        description="Save the processed image",
        parameters={
            "format": "{{ global_parameters.output_format }}",
            "quality": "{{ global_parameters.quality }}",
            "optimize": True
        },
        tags=["output", "optimization"]
    )

    return workflow


def save_workflow_to_file(workflow: Workflow, filepath: Path) -> None:
    """Save workflow to a YAML file."""
    workflow_dict = workflow.to_dict()

    with open(filepath, 'w') as f:
        yaml.safe_dump(workflow_dict, f, default_flow_style=False, indent=2)

    print(f"   Workflow saved to: {filepath}")


def load_workflow_from_file(filepath: Path) -> Workflow:
    """Load workflow from a YAML file."""
    with open(filepath, 'r') as f:
        workflow_dict = yaml.safe_load(f)

    workflow = Workflow.from_dict(workflow_dict)
    print(f"   Workflow loaded from: {filepath}")
    return workflow


def demonstrate_workflow_manipulation():
    """Demonstrate workflow creation and manipulation."""
    print("\n📋 Workflow Creation and Manipulation")
    print("-" * 40)

    # Create workflow
    print("1. Creating workflow programmatically...")
    workflow = create_sample_workflow()
    print(f"   ✓ Created workflow: {workflow.name}")
    print(f"   ✓ Steps: {len(workflow.steps)}")
    print(f"   ✓ Global parameters: {len(workflow.global_parameters)}")

    # Show workflow summary
    print("\n2. Workflow summary:")
    for i, step in enumerate(workflow.steps, 1):
        print(f"   {i}. {step.name} ({step.tool_name})")
        print(f"      Description: {step.description}")
        print(f"      Parameters: {len(step.parameters)}")
        print(f"      Tags: {', '.join(step.tags)}")

    # Modify workflow
    print("\n3. Modifying workflow...")

    # Add a new step
    workflow.add_step(
        name="watermark",
        tool_name="watermark_tool",
        description="Add watermark to image",
        parameters={
            "text": "© Example",
            "position": "bottom_right",
            "opacity": 0.7
        },
        enabled=False  # Disabled by default
    )
    print(f"   ✓ Added watermark step (disabled)")

    # Enable/disable steps
    watermark_step = workflow.get_step("watermark")
    if watermark_step:
        watermark_step.enabled = True
        print(f"   ✓ Enabled watermark step")

    # Update global parameters
    workflow.global_parameters["watermark_text"] = "© ReTileUp Example"
    print(f"   ✓ Updated global parameters")

    return workflow


def demonstrate_workflow_serialization(workflow: Workflow):
    """Demonstrate workflow serialization and deserialization."""
    print("\n💾 Workflow Serialization")
    print("-" * 40)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Save to YAML
        print("1. Saving workflow to YAML...")
        yaml_path = temp_path / "workflow.yaml"
        save_workflow_to_file(workflow, yaml_path)

        # Save to JSON
        print("2. Saving workflow to JSON...")
        json_path = temp_path / "workflow.json"
        workflow_dict = workflow.to_dict()
        with open(json_path, 'w') as f:
            json.dump(workflow_dict, f, indent=2, default=str)
        print(f"   Workflow saved to: {json_path}")

        # Load from YAML
        print("3. Loading workflow from YAML...")
        loaded_workflow = load_workflow_from_file(yaml_path)
        print(f"   ✓ Loaded workflow: {loaded_workflow.name}")
        print(f"   ✓ Steps: {len(loaded_workflow.steps)}")

        # Verify integrity
        print("4. Verifying workflow integrity...")
        assert loaded_workflow.name == workflow.name
        assert len(loaded_workflow.steps) == len(workflow.steps)
        assert loaded_workflow.global_parameters == workflow.global_parameters
        print("   ✓ Workflow integrity verified")


def demonstrate_workflow_validation():
    """Demonstrate workflow validation."""
    print("\n✅ Workflow Validation")
    print("-" * 40)

    # Create registry and config
    registry = ToolRegistry()
    config = Config()

    # Create a workflow
    workflow = create_sample_workflow()

    print("1. Validating workflow against empty registry...")
    validation_errors = workflow.validate_workflow(registry)
    print(f"   Validation errors: {len(validation_errors)}")

    if validation_errors:
        print("   Error details:")
        for error in validation_errors[:3]:  # Show first 3
            print(f"      - {error}")

    # Demonstrate workflow execution summary
    print("\n2. Execution summary (before execution):")
    summary = workflow.get_execution_summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")


def demonstrate_workflow_step_management():
    """Demonstrate workflow step management."""
    print("\n🔧 Workflow Step Management")
    print("-" * 40)

    workflow = Workflow(
        name="step_management_example",
        description="Example for step management"
    )

    print("1. Adding steps...")
    # Add several steps
    steps_data = [
        ("input", "file_loader", "Load input files"),
        ("preprocess", "preprocessor", "Preprocess images"),
        ("process", "main_processor", "Main processing"),
        ("postprocess", "postprocessor", "Post-processing"),
        ("output", "file_saver", "Save output files")
    ]

    for name, tool, desc in steps_data:
        workflow.add_step(name=name, tool_name=tool, description=desc)
        print(f"   ✓ Added step: {name}")

    print(f"\n2. Current workflow has {len(workflow.steps)} steps")

    # Get steps by status
    print("\n3. Steps by status:")
    pending_steps = workflow.get_steps_by_status("pending")
    print(f"   Pending steps: {len(pending_steps)}")

    # Get enabled steps
    enabled_steps = workflow.get_enabled_steps()
    print(f"   Enabled steps: {len(enabled_steps)}")

    # Disable a step
    print("\n4. Disabling postprocess step...")
    postprocess_step = workflow.get_step("postprocess")
    if postprocess_step:
        postprocess_step.enabled = False
        print("   ✓ Postprocess step disabled")

    enabled_steps = workflow.get_enabled_steps()
    print(f"   Enabled steps now: {len(enabled_steps)}")

    # Remove a step
    print("\n5. Removing preprocess step...")
    removed = workflow.remove_step("preprocess")
    if removed:
        print("   ✓ Preprocess step removed")
    print(f"   Workflow now has {len(workflow.steps)} steps")

    return workflow


def demonstrate_progress_tracking():
    """Demonstrate progress tracking with workflows."""
    print("\n📊 Progress Tracking")
    print("-" * 40)

    # Create sample data
    items = list(range(1, 11))  # 10 items

    print("1. Simple progress tracking...")
    tracker = ProgressTracker()

    with tracker.track_operation("Processing items", total=len(items)) as progress:
        for i, item in enumerate(items):
            # Simulate processing
            import time
            time.sleep(0.1)  # 100ms delay

            progress.advance()

            # Update description every few items
            if (i + 1) % 3 == 0:
                progress.update(description=f"Processing item {i + 1}")

    print("   ✓ Simple progress tracking completed")

    print("\n2. Multi-operation progress tracking...")
    with tracker.track_multiple_operations() as multi_progress:
        # Add multiple tasks
        multi_progress.add_task("load", "Loading images", total=5)
        multi_progress.add_task("process", "Processing images", total=5)
        multi_progress.add_task("save", "Saving results", total=5)

        # Simulate work
        for i in range(5):
            time.sleep(0.05)
            multi_progress.update_task("load", advance=1)

            time.sleep(0.1)
            multi_progress.update_task("process", advance=1)

            time.sleep(0.05)
            multi_progress.update_task("save", advance=1)

    print("   ✓ Multi-operation progress tracking completed")


def main():
    """Main function demonstrating workflow usage."""
    print("🔄 ReTileUp Workflow Example")
    print("=" * 40)

    try:
        # Demonstrate different aspects of workflows
        workflow = demonstrate_workflow_manipulation()
        demonstrate_workflow_serialization(workflow)
        demonstrate_workflow_validation()
        demonstrate_workflow_step_management()
        demonstrate_progress_tracking()

        print("\n🎉 Workflow example completed successfully!")

    except Exception as e:
        print(f"\n❌ Error in workflow example: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Workflow example interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()