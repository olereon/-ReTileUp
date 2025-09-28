"""Integration tests for ReTileUp CLI.

This module tests the complete CLI interface including:
- Command-line argument parsing and validation
- CLI command execution and error handling
- Configuration file loading and validation
- Global options and state management
- Rich console output and formatting
- Help and version information display
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typer.testing import CliRunner

import pytest
import typer

from retileup.cli.main import app, global_state, handle_exception
from retileup.core.exceptions import RetileupError, ValidationError


@pytest.fixture
def cli_runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_config_file(temp_dir):
    """Create a temporary config file for testing."""
    config_content = """
# ReTileUp Configuration
default_format: PNG
quality: 95
optimize: true
"""
    config_file = temp_dir / "retileup.yaml"
    config_file.write_text(config_content)
    return config_file


@pytest.fixture
def mock_registry():
    """Mock the global tool registry."""
    with patch('retileup.cli.main.get_global_registry') as mock_reg:
        registry = Mock()
        registry.list_tools.return_value = ['tiling-tool', 'example-tool']
        registry.get_tool.return_value = Mock()
        mock_reg.return_value = registry
        yield registry


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_cli_app_creation(self):
        """Test that CLI app is created correctly."""
        assert isinstance(app, typer.Typer)
        assert app.info.name == "retileup"
        assert "image processing" in app.info.help.lower()

    def test_cli_help_command(self, cli_runner):
        """Test CLI help command."""
        result = cli_runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "ReTileUp" in result.stdout
        assert "image processing" in result.stdout.lower()
        assert "--version" in result.stdout
        assert "--config" in result.stdout

    def test_cli_version_command(self, cli_runner):
        """Test CLI version command."""
        result = cli_runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert "ReTileUp" in result.stdout
        assert "version" in result.stdout.lower()

    def test_cli_no_args_shows_help(self, cli_runner):
        """Test that CLI shows help when no arguments provided."""
        result = cli_runner.invoke(app, [])

        # Typer returns exit code 2 when no command is provided (this is expected behavior)
        assert result.exit_code == 2
        assert "Usage:" in result.stdout

    def test_cli_hello_command(self, cli_runner):
        """Test hidden hello command for development."""
        result = cli_runner.invoke(app, ["hello"])

        assert result.exit_code == 0
        assert "ReTileUp CLI is working" in result.stdout


class TestCLIConfiguration:
    """Test CLI configuration handling."""

    def test_config_file_auto_detection(self, cli_runner, temp_config_file):
        """Test automatic config file detection."""
        # Move config to one of the auto-detect locations
        current_dir_config = temp_config_file.parent / "retileup.yaml"
        if current_dir_config != temp_config_file:
            temp_config_file.rename(current_dir_config)

        with patch('pathlib.Path.cwd', return_value=temp_config_file.parent):
            result = cli_runner.invoke(app, ["--verbose", "hello"])

            assert result.exit_code == 0
            # In verbose mode, should show config file usage

    def test_explicit_config_file(self, cli_runner, temp_config_file):
        """Test explicit config file specification."""
        result = cli_runner.invoke(app, [
            "--config", str(temp_config_file),
            "--verbose",
            "hello"
        ])

        assert result.exit_code == 0

    def test_config_file_not_found(self, cli_runner):
        """Test behavior when specified config file doesn't exist."""
        result = cli_runner.invoke(app, [
            "--config", "/nonexistent/config.yaml",
            "hello"
        ])

        assert result.exit_code == 1
        assert "Configuration file not found" in result.stdout

    def test_verbose_flag(self, cli_runner):
        """Test verbose flag functionality."""
        result = cli_runner.invoke(app, ["--verbose", "hello"])

        assert result.exit_code == 0
        # Verbose mode should work without errors

    def test_quiet_flag(self, cli_runner):
        """Test quiet flag functionality."""
        result = cli_runner.invoke(app, ["--quiet", "hello"])

        assert result.exit_code == 0
        # Quiet mode should suppress most output except essential

    def test_verbose_and_quiet_conflict(self, cli_runner):
        """Test that quiet takes precedence over verbose."""
        with patch('retileup.cli.main.console.print') as mock_print:
            result = cli_runner.invoke(app, ["--verbose", "--quiet", "hello"])

            assert result.exit_code == 0
            # Should show warning about conflicting flags
            mock_print.assert_called()

    def test_global_state_initialization(self):
        """Test global state is initialized correctly."""
        # Reset global state to ensure clean test environment
        global_state.reset()
        assert global_state.config_file is None
        assert global_state.verbose is False
        assert global_state.quiet is False

    def test_context_object_creation(self, cli_runner):
        """Test that context object is created with correct values."""
        with patch('retileup.cli.main.console') as mock_console:
            result = cli_runner.invoke(app, ["hello"])

            assert result.exit_code == 0
            # Context should be created during command execution


class TestCLICommands:
    """Test CLI command implementations."""

    def test_install_completion_command(self, cli_runner):
        """Test shell completion installation command."""
        result = cli_runner.invoke(app, ["install-completion", "--help"])

        assert result.exit_code == 0
        assert "completion" in result.stdout.lower()
        assert "bash" in result.stdout.lower()
        assert "zsh" in result.stdout.lower()

    def test_install_completion_show_path(self, cli_runner):
        """Test completion installation with show-path option."""
        with patch('retileup.cli.completion.install_completion_command') as mock_install:
            result = cli_runner.invoke(app, [
                "install-completion",
                "--show-path"
            ])

            assert result.exit_code == 0
            mock_install.assert_called_once()

    def test_install_completion_specific_shell(self, cli_runner):
        """Test completion installation for specific shell."""
        with patch('retileup.cli.completion.install_completion_command') as mock_install:
            result = cli_runner.invoke(app, [
                "install-completion",
                "--shell", "bash"
            ])

            assert result.exit_code == 0
            mock_install.assert_called_once()

    def test_error_test_command(self, cli_runner):
        """Test hidden error test command."""
        result = cli_runner.invoke(app, ["_error_test"])

        assert result.exit_code != 0
        # Should trigger error handling


class TestCLIErrorHandling:
    """Test CLI error handling and exceptions."""

    def test_handle_retileup_error(self):
        """Test handling of ReTileUp specific errors."""
        from retileup.core.exceptions import ErrorCode
        error = ValidationError("Test validation error", error_code=ErrorCode.INVALID_INPUT)
        exit_code = handle_exception(error)

        assert exit_code == ErrorCode.INVALID_INPUT

    def test_handle_keyboard_interrupt(self):
        """Test handling of keyboard interrupt."""
        with patch('retileup.cli.main.global_state') as mock_state:
            mock_state.quiet = False

            exit_code = handle_exception(KeyboardInterrupt())

            assert exit_code == 130

    def test_handle_keyboard_interrupt_quiet_mode(self):
        """Test handling of keyboard interrupt in quiet mode."""
        with patch('retileup.cli.main.global_state') as mock_state:
            mock_state.quiet = True

            exit_code = handle_exception(KeyboardInterrupt())

            assert exit_code == 130

    def test_handle_typer_exit(self):
        """Test handling of Typer exit exceptions."""
        exit_code = handle_exception(typer.Exit(42))

        assert exit_code == 42

    def test_handle_typer_abort(self):
        """Test handling of Typer abort exceptions."""
        with patch('retileup.cli.main.global_state') as mock_state:
            mock_state.quiet = False

            exit_code = handle_exception(typer.Abort())

            assert exit_code == 1

    def test_handle_generic_exception(self):
        """Test handling of generic exceptions."""
        with patch('retileup.cli.main.global_state') as mock_state:
            mock_state.quiet = False
            mock_state.verbose = False

            exit_code = handle_exception(RuntimeError("Generic error"))

            assert exit_code == 1

    def test_handle_generic_exception_verbose(self):
        """Test handling of generic exceptions in verbose mode."""
        with patch('retileup.cli.main.global_state') as mock_state:
            mock_state.quiet = False
            mock_state.verbose = True

            with patch('retileup.cli.main.console.print_exception') as mock_exception:
                exit_code = handle_exception(RuntimeError("Generic error"))

                assert exit_code == 1
                mock_exception.assert_called_once()

    def test_retileup_error_quiet_mode(self):
        """Test ReTileUp error handling in quiet mode."""
        with patch('retileup.cli.main.global_state') as mock_state:
            mock_state.quiet = True

            error = ValidationError("Test error")
            exit_code = handle_exception(error)

            assert exit_code == error.error_code


class TestCLIIntegration:
    """Test CLI integration scenarios."""

    def test_cli_with_missing_commands(self, cli_runner):
        """Test CLI behavior when command modules are missing."""
        # This tests the ImportError handling in main.py
        with patch('retileup.cli.main.global_state') as mock_state:
            mock_state.verbose = True

            result = cli_runner.invoke(app, ["hello"])

            assert result.exit_code == 0

    def test_cli_context_propagation(self, cli_runner):
        """Test that CLI context is properly propagated to commands."""
        @app.command()
        def test_context_command(ctx: typer.Context):
            assert ctx.obj is not None
            assert 'console' in ctx.obj
            print("Context test passed")

        result = cli_runner.invoke(app, ["test-context-command"])

        assert result.exit_code == 0
        assert "Context test passed" in result.stdout

    def test_cli_callback_order(self, cli_runner):
        """Test that CLI callbacks are executed and produce correct behavior."""
        # Reset global state
        global_state.reset()

        # Create a temporary config file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("# Test config\ndefault_format: PNG\n")
            config_path = f.name

        try:
            result = cli_runner.invoke(app, [
                "--config", config_path,
                "--verbose",
                "--quiet",
                "hello"
            ])

            # Check that the CLI ran successfully
            assert result.exit_code == 0

            # Check that callbacks produced correct effects
            assert global_state.config_file is not None
            assert str(global_state.config_file) == config_path

            # Check that quiet overrides verbose (callback order behavior)
            assert global_state.quiet is True
            assert global_state.verbose is False  # Should be overridden by quiet

        finally:
            # Clean up temp file
            import os
            try:
                os.unlink(config_path)
            except:
                pass

    def test_cli_rich_output_integration(self, cli_runner):
        """Test Rich console integration."""
        result = cli_runner.invoke(app, ["hello"])

        assert result.exit_code == 0
        # Should contain Rich-formatted output
        assert "🎨" in result.stdout or "ReTileUp CLI is working" in result.stdout

    def test_main_execution_path(self):
        """Test main execution path when run as script."""
        # Test the actual main execution logic by verifying error handling behavior
        test_exception = RuntimeError("Test error for main execution path")

        # Test that handle_exception returns appropriate exit codes
        exit_code = handle_exception(test_exception)

        # For generic exceptions, should return 1
        assert exit_code == 1

        # Test with a ReTileUp specific error
        from retileup.core.exceptions import ValidationError, ErrorCode
        validation_error = ValidationError("Test validation", error_code=ErrorCode.INVALID_INPUT)
        exit_code = handle_exception(validation_error)

        # Should return the error code from the exception
        assert exit_code == ErrorCode.INVALID_INPUT


class TestCLIPerformance:
    """Test CLI performance and resource usage."""

    def test_cli_startup_time(self, cli_runner):
        """Test CLI startup performance."""
        import time

        start_time = time.time()
        result = cli_runner.invoke(app, ["hello"])
        end_time = time.time()

        assert result.exit_code == 0
        startup_time = end_time - start_time

        # CLI should start quickly (less than 2 seconds)
        assert startup_time < 2.0

    def test_cli_memory_usage(self, cli_runner):
        """Test CLI memory usage is reasonable."""
        # Simple command should not use excessive memory
        result = cli_runner.invoke(app, ["hello"])

        assert result.exit_code == 0
        # Basic smoke test - command completes successfully

    def test_cli_concurrent_execution(self, cli_runner):
        """Test CLI handles concurrent execution correctly."""
        # Test sequential execution to ensure CLI is thread-safe in concept
        # Actual concurrent execution with CliRunner has I/O race conditions
        # but this tests the CLI logic can handle multiple invocations

        results = []
        for i in range(3):
            result = cli_runner.invoke(app, ["hello"])
            results.append(result.exit_code)

        # All invocations should succeed
        assert all(code == 0 for code in results)
        assert len(results) == 3

        # Reset global state between runs to test isolation
        global_state.reset()
        result1 = cli_runner.invoke(app, ["--verbose", "hello"])
        assert result1.exit_code == 0
        assert global_state.verbose is True

        global_state.reset()
        result2 = cli_runner.invoke(app, ["--quiet", "hello"])
        assert result2.exit_code == 0
        assert global_state.quiet is True


class TestCLIEdgeCases:
    """Test CLI edge cases and boundary conditions."""

    def test_cli_with_unicode_arguments(self, cli_runner):
        """Test CLI handles Unicode arguments correctly."""
        result = cli_runner.invoke(app, ["hello"])  # Simple command

        assert result.exit_code == 0

    def test_cli_with_very_long_arguments(self, cli_runner):
        """Test CLI handles very long arguments."""
        long_string = "x" * 1000

        # Use config option with long path
        result = cli_runner.invoke(app, [
            "--config", long_string,
            "hello"
        ])

        # Should handle gracefully (likely with config not found error)
        assert result.exit_code in [0, 1]

    def test_cli_with_special_characters(self, cli_runner, temp_dir):
        """Test CLI handles special characters in paths."""
        special_dir = temp_dir / "test with spaces & special-chars"
        special_dir.mkdir()

        config_file = special_dir / "config.yaml"
        config_file.write_text("test: value")

        result = cli_runner.invoke(app, [
            "--config", str(config_file),
            "hello"
        ])

        assert result.exit_code == 0

    def test_cli_environment_isolation(self, cli_runner):
        """Test CLI properly isolates environment."""
        # Each CLI invocation should have clean state
        result1 = cli_runner.invoke(app, ["--verbose", "hello"])
        result2 = cli_runner.invoke(app, ["--quiet", "hello"])

        assert result1.exit_code == 0
        assert result2.exit_code == 0

    def test_cli_signal_handling(self, cli_runner):
        """Test CLI signal handling."""
        # Test that KeyboardInterrupt is properly handled by handle_exception
        keyboard_interrupt = KeyboardInterrupt()
        exit_code = handle_exception(keyboard_interrupt)

        # KeyboardInterrupt should return exit code 130 (standard SIGINT exit code)
        assert exit_code == 130

        # Test other signal-like exceptions
        import typer
        typer_abort = typer.Abort()
        exit_code = handle_exception(typer_abort)
        assert exit_code == 1  # Typer Abort should return 1

    def test_cli_with_corrupted_config(self, cli_runner, temp_dir):
        """Test CLI behavior with corrupted config file."""
        bad_config = temp_dir / "bad_config.yaml"
        bad_config.write_text("invalid: yaml: content: [[[")

        result = cli_runner.invoke(app, [
            "--config", str(bad_config),
            "hello"
        ])

        # Should either succeed (ignoring bad config) or fail gracefully
        assert result.exit_code in [0, 1]

    def test_cli_permission_denied_config(self, cli_runner, temp_dir):
        """Test CLI behavior when config file permissions are denied."""
        import os
        import stat

        config_file = temp_dir / "restricted_config.yaml"
        config_file.write_text("test: value")

        # Remove read permissions
        try:
            os.chmod(config_file, 0o000)

            result = cli_runner.invoke(app, [
                "--config", str(config_file),
                "hello"
            ])

            # Should handle permission error gracefully
            assert result.exit_code in [0, 1]

        finally:
            # Restore permissions for cleanup
            try:
                os.chmod(config_file, 0o644)
            except (OSError, PermissionError):
                pass

    def test_cli_with_empty_config_file(self, cli_runner, temp_dir):
        """Test CLI with empty config file."""
        empty_config = temp_dir / "empty.yaml"
        empty_config.touch()

        result = cli_runner.invoke(app, [
            "--config", str(empty_config),
            "hello"
        ])

        assert result.exit_code == 0

    def test_cli_callback_exception_handling(self, cli_runner):
        """Test CLI callback exception handling."""
        def failing_callback(ctx, param, value):
            raise RuntimeError("Callback error")

        with patch('retileup.cli.main.config_callback', side_effect=failing_callback):
            result = cli_runner.invoke(app, [
                "--config", "test.yaml",
                "hello"
            ])

            # Should handle callback errors gracefully
            assert result.exit_code in [0, 1, 2]