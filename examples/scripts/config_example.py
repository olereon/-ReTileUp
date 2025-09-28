#!/usr/bin/env python3
"""
Configuration example for ReTileUp.

This script demonstrates how to work with ReTileUp configuration
including loading, modifying, and saving configurations.
"""

import tempfile
from pathlib import Path

import yaml

from retileup.core.config import Config, LoggingConfig, OutputConfig, PerformanceConfig


def demonstrate_basic_config():
    """Demonstrate basic configuration usage."""
    print("\n⚙️  Basic Configuration")
    print("-" * 40)

    # Create default configuration
    print("1. Creating default configuration...")
    config = Config()

    print(f"   Version: {config.version}")
    print(f"   Debug mode: {config.debug}")
    print(f"   Logging level: {config.logging.level}")
    print(f"   Max workers: {config.performance.max_workers}")
    print(f"   Output format: {config.output.format}")

    # Modify configuration
    print("\n2. Modifying configuration...")
    config.debug = True
    config.logging.level = "DEBUG"
    config.performance.max_workers = 8
    config.output.quality = 90

    print(f"   Debug mode: {config.debug}")
    print(f"   Logging level: {config.logging.level}")
    print(f"   Max workers: {config.performance.max_workers}")
    print(f"   Output quality: {config.output.quality}")

    return config


def demonstrate_component_configs():
    """Demonstrate individual component configurations."""
    print("\n🔧 Component Configurations")
    print("-" * 40)

    # Logging configuration
    print("1. Custom logging configuration...")
    logging_config = LoggingConfig(
        level="WARNING",
        format="%(levelname)s: %(message)s",
        file=Path("/tmp/retileup.log")
    )
    print(f"   Level: {logging_config.level}")
    print(f"   Format: {logging_config.format}")
    print(f"   File: {logging_config.file}")

    # Performance configuration
    print("\n2. Custom performance configuration...")
    perf_config = PerformanceConfig(
        max_workers=16,
        chunk_size=2048,
        memory_limit=2048  # 2GB
    )
    print(f"   Max workers: {perf_config.max_workers}")
    print(f"   Chunk size: {perf_config.chunk_size} KB")
    print(f"   Memory limit: {perf_config.memory_limit} MB")

    # Output configuration
    print("\n3. Custom output configuration...")
    output_config = OutputConfig(
        directory=Path("/tmp/retileup_output"),
        format="JPEG",
        quality=85,
        overwrite=True
    )
    print(f"   Directory: {output_config.directory}")
    print(f"   Format: {output_config.format}")
    print(f"   Quality: {output_config.quality}")
    print(f"   Overwrite: {output_config.overwrite}")

    # Create complete configuration
    complete_config = Config(
        debug=True,
        logging=logging_config,
        performance=perf_config,
        output=output_config
    )

    return complete_config


def demonstrate_tool_configs():
    """Demonstrate tool-specific configurations."""
    print("\n🛠️  Tool-Specific Configurations")
    print("-" * 40)

    config = Config()

    # Add tool configurations
    print("1. Adding tool configurations...")

    config.set_tool_config("resize_tool", {
        "default_method": "lanczos",
        "maintain_aspect": True,
        "max_size": 4096
    })

    config.set_tool_config("compression_tool", {
        "algorithm": "deflate",
        "level": 9,
        "optimize": True
    })

    config.set_tool_config("watermark_tool", {
        "default_text": "© ReTileUp",
        "default_position": "bottom_right",
        "default_opacity": 0.7,
        "font_family": "Arial"
    })

    print(f"   Configured tools: {len(config.tool_configs)}")

    # Retrieve tool configurations
    print("\n2. Retrieving tool configurations...")
    for tool_name in config.tool_configs:
        tool_config = config.get_tool_config(tool_name)
        print(f"   {tool_name}:")
        for key, value in tool_config.items():
            print(f"      {key}: {value}")

    # Get configuration for non-existent tool
    print("\n3. Non-existent tool configuration...")
    unknown_config = config.get_tool_config("unknown_tool")
    print(f"   Unknown tool config: {unknown_config}")

    return config


def demonstrate_config_file_operations():
    """Demonstrate saving and loading configuration files."""
    print("\n💾 Configuration File Operations")
    print("-" * 40)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create a comprehensive configuration
        print("1. Creating comprehensive configuration...")
        config = Config(
            debug=True,
            version="2.0.0"
        )

        # Add various configurations
        config.logging.level = "DEBUG"
        config.performance.max_workers = 12
        config.output.format = "PNG"
        config.output.quality = 95

        # Add tool configurations
        config.set_tool_config("test_tool", {
            "param1": "value1",
            "param2": 42,
            "param3": True
        })

        # Save to file
        print("2. Saving configuration to file...")
        config_path = temp_path / "config.yaml"
        config.save_to_file(config_path)
        print(f"   Saved to: {config_path}")

        # Display file contents
        print("\n3. Configuration file contents:")
        with open(config_path, 'r') as f:
            content = f.read()
            # Show first 20 lines
            lines = content.split('\n')[:20]
            for line in lines:
                print(f"   {line}")
            if len(content.split('\n')) > 20:
                print("   ...")

        # Load from file
        print("\n4. Loading configuration from file...")
        loaded_config = Config.load_from_file(config_path)
        print(f"   ✓ Loaded configuration")
        print(f"   Debug: {loaded_config.debug}")
        print(f"   Version: {loaded_config.version}")
        print(f"   Logging level: {loaded_config.logging.level}")

        # Verify integrity
        print("\n5. Verifying configuration integrity...")
        assert loaded_config.debug == config.debug
        assert loaded_config.version == config.version
        assert loaded_config.logging.level == config.logging.level
        assert loaded_config.get_tool_config("test_tool") == config.get_tool_config("test_tool")
        print("   ✓ Configuration integrity verified")

        return loaded_config


def demonstrate_environment_config():
    """Demonstrate environment-based configuration."""
    print("\n🌍 Environment-Based Configuration")
    print("-" * 40)

    import os

    # Set environment variables
    print("1. Setting environment variables...")
    env_vars = {
        "RETILEUP_DEBUG": "true",
        "RETILEUP_LOG_LEVEL": "WARNING",
        "RETILEUP_MAX_WORKERS": "6",
        "RETILEUP_OUTPUT_FORMAT": "JPEG",
        "RETILEUP_OUTPUT_QUALITY": "88"
    }

    # Store original values
    original_values = {}
    for key in env_vars:
        original_values[key] = os.environ.get(key)

    # Set new values
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"   {key} = {value}")

    try:
        # Load configuration from environment
        print("\n2. Loading configuration from environment...")
        env_config = Config.load_from_env()

        print(f"   Debug: {env_config.debug}")
        print(f"   Log level: {env_config.logging.level}")
        print(f"   Max workers: {env_config.performance.max_workers}")
        print(f"   Output format: {env_config.output.format}")
        print(f"   Output quality: {env_config.output.quality}")

        # Verify environment loading
        print("\n3. Verifying environment configuration...")
        assert env_config.debug is True
        assert env_config.logging.level == "WARNING"
        assert env_config.performance.max_workers == 6
        assert env_config.output.format == "JPEG"
        assert env_config.output.quality == 88
        print("   ✓ Environment configuration verified")

    finally:
        # Restore original environment variables
        print("\n4. Restoring environment...")
        for key, original_value in original_values.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value
        print("   ✓ Environment restored")


def demonstrate_config_validation():
    """Demonstrate configuration validation."""
    print("\n✅ Configuration Validation")
    print("-" * 40)

    print("1. Valid configuration...")
    try:
        valid_config = Config(
            debug=True,
            version="1.0.0",
            output=OutputConfig(quality=85)
        )
        print("   ✓ Valid configuration created")
    except Exception as e:
        print(f"   ❌ Validation error: {e}")

    print("\n2. Invalid configuration (bad quality)...")
    try:
        invalid_config = Config(
            output=OutputConfig(quality=150)  # Invalid: > 100
        )
        print("   ❌ Invalid configuration should have failed")
    except Exception as e:
        print(f"   ✓ Validation error caught: {e}")

    print("\n3. Invalid configuration (bad version)...")
    try:
        invalid_config = Config(version="invalid.version")
        print("   ❌ Invalid version should have failed")
    except Exception as e:
        print(f"   ✓ Validation error caught: {e}")


def main():
    """Main function demonstrating configuration usage."""
    print("⚙️  ReTileUp Configuration Example")
    print("=" * 40)

    try:
        # Demonstrate different aspects of configuration
        demonstrate_basic_config()
        demonstrate_component_configs()
        demonstrate_tool_configs()
        demonstrate_config_file_operations()
        demonstrate_environment_config()
        demonstrate_config_validation()

        print("\n🎉 Configuration example completed successfully!")

    except Exception as e:
        print(f"\n❌ Error in configuration example: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Configuration example interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()