"""Main CLI entry point for ReTileUp."""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.traceback import install

from retileup import __version__
from retileup.core.exceptions import RetileupError

# Install rich traceback handler for better error formatting
install()

# Create console for rich output
console = Console()

# Create main Typer app with global options
app = typer.Typer(
    name="retileup",
    help="A modular CLI toolkit for advanced image processing and transformation workflows",
    add_completion=True,
    rich_markup_mode="rich",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)

# Global state for CLI options
class GlobalState:
    """Global state for CLI options."""
    def __init__(self):
        self.config_file: Optional[Path] = None
        self.verbose: bool = False
        self.quiet: bool = False

    def reset(self):
        """Reset global state to initial values."""
        self.config_file = None
        self.verbose = False
        self.quiet = False

global_state = GlobalState()


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"[bold green]ReTileUp[/bold green] version [cyan]{__version__}[/cyan]")
        raise typer.Exit()


def config_callback(ctx: typer.Context, param: typer.CallbackParam, value: Optional[str]) -> Optional[Path]:
    """Handle config file option with auto-detection."""
    if value is None:
        # Auto-detect configuration file
        config_locations = [
            Path("./retileup.yaml"),
            Path.home() / ".retileup.yaml",
            Path.home() / ".config" / "retileup" / "config.yaml",
        ]

        for config_path in config_locations:
            if config_path.exists():
                global_state.config_file = config_path
                if global_state.verbose:
                    console.print(f"[dim]Using config file: {config_path}[/dim]")
                return config_path
        return None

    config_path = Path(value)
    if not config_path.exists():
        console.print(f"[red]Error:[/red] Configuration file not found: {config_path}")
        raise typer.Exit(1)

    global_state.config_file = config_path
    if global_state.verbose:
        console.print(f"[dim]Using config file: {config_path}[/dim]")
    return config_path


def verbose_callback(ctx: typer.Context, param: typer.CallbackParam, value: bool) -> bool:
    """Handle verbose option."""
    global_state.verbose = value
    return value


def quiet_callback(ctx: typer.Context, param: typer.CallbackParam, value: bool) -> bool:
    """Handle quiet option."""
    global_state.quiet = value
    if value and global_state.verbose:
        console.print("[yellow]Warning:[/yellow] Both --verbose and --quiet specified. Quiet mode takes precedence.")
        global_state.verbose = False
    return value


@app.callback()
def main(
    ctx: typer.Context,
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        callback=config_callback,
        help="Configuration file path (auto-detected if not specified)",
        metavar="PATH",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        callback=verbose_callback,
        help="Enable verbose output",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        callback=quiet_callback,
        help="Suppress non-error output",
    ),
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """ReTileUp: A modular CLI toolkit for advanced image processing and transformation workflows.

    [bold]Examples:[/bold]
        retileup tile --width 256 --height 256 --coords "0,0;256,0" image.jpg
        retileup workflow web-optimize --input ./photos --output ./web
        retileup list-tools --detailed
        retileup validate config.yaml

    [bold]Global Options:[/bold]
        Use [cyan]--config[/cyan] to specify a configuration file
        Use [cyan]--verbose[/cyan] for detailed output
        Use [cyan]--quiet[/cyan] to suppress non-error messages
    """
    # Store the context for use in commands
    ctx.obj = {
        "config_file": global_state.config_file,
        "verbose": global_state.verbose,
        "quiet": global_state.quiet,
        "console": console,
    }


# Import and register command modules
# Note: Commands are registered as individual commands, not sub-apps
# This allows for the flat command structure specified in the API

try:
    from .commands.tile import tile_command
    from .commands.workflow import workflow_command
    from .commands.utils import list_tools_command, validate_command
    from .commands.batch_rename import batch_rename_command

    # Register commands directly
    app.command(name="tile")(tile_command)
    app.command(name="workflow")(workflow_command)
    app.command(name="list-tools")(list_tools_command)
    app.command(name="validate")(validate_command)
    app.command(name="batch-rename")(batch_rename_command)

except ImportError as e:
    # Commands not yet implemented - will be created
    if global_state.verbose:
        console.print(f"[dim]Command modules not yet available: {e}[/dim]")
    pass


# Shell completion installation
@app.command()
def install_completion(
    ctx: typer.Context,
    shell: str = typer.Option(
        "auto",
        "--shell",
        help="Shell type: bash, zsh, fish, or auto-detect",
        metavar="SHELL",
    ),
    show_path: bool = typer.Option(
        False,
        "--show-path",
        help="Show the completion script path instead of installing",
    ),
) -> None:
    """Install shell completion for ReTileUp.

    [bold]Examples:[/bold]
        # Auto-detect shell and install
        retileup install-completion

        # Install for specific shell
        retileup install-completion --shell bash

        # Show completion script path
        retileup install-completion --show-path

    [bold]Supported Shells:[/bold]
        • [cyan]bash[/cyan] - Bash shell completion
        • [cyan]zsh[/cyan] - Zsh shell completion
        • [cyan]fish[/cyan] - Fish shell completion
        • [cyan]auto[/cyan] - Auto-detect current shell
    """
    from .completion import install_completion_command
    install_completion_command(ctx, shell, show_path)


# Test command for development
@app.command(hidden=True)
def hello() -> None:
    """Test command to verify CLI is working."""
    console.print("🎨 [bold green]ReTileUp CLI is working![/bold green]")
    console.print(f"Version: [cyan]{__version__}[/cyan]")
    console.print("Ready for image processing workflows!")


# Error handling
@app.command(hidden=True)
def _error_test() -> None:
    """Test error handling (hidden command for development)."""
    raise RuntimeError("This is a test error to verify error handling works.")


def handle_exception(e: Exception) -> int:
    """Handle exceptions and return appropriate exit codes."""
    if isinstance(e, RetileupError):
        if not global_state.quiet:
            console.print(f"[red]Error:[/red] {e}")
        return e.error_code
    elif isinstance(e, KeyboardInterrupt):
        if not global_state.quiet:
            console.print("\n[yellow]Operation cancelled by user[/yellow]")
        return 130  # Standard exit code for SIGINT
    elif isinstance(e, typer.Exit):
        return e.exit_code
    elif isinstance(e, typer.Abort):
        if not global_state.quiet:
            console.print("[yellow]Operation aborted[/yellow]")
        return 1
    else:
        if not global_state.quiet:
            console.print(f"[red]Unexpected error:[/red] {e}")
            if global_state.verbose:
                console.print_exception()
        return 1


if __name__ == "__main__":
    try:
        app()
    except Exception as e:
        exit_code = handle_exception(e)
        sys.exit(exit_code)