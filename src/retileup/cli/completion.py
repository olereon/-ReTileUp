"""Shell completion support for ReTileUp CLI."""

from pathlib import Path
from typing import List

import typer
from rich.console import Console

from retileup.core.registry import get_global_registry


def complete_tool_names(incomplete: str) -> List[str]:
    """Complete tool names from registry.

    Args:
        incomplete: Incomplete tool name

    Returns:
        List of matching tool names
    """
    try:
        registry = get_global_registry()
        tool_names = registry.list_tools()
        return [name for name in tool_names if name.startswith(incomplete)]
    except Exception:
        return []


def complete_workflow_names(ctx: typer.Context, incomplete: str) -> List[str]:
    """Complete workflow names from configuration.

    Args:
        ctx: Typer context
        incomplete: Incomplete workflow name

    Returns:
        List of matching workflow names
    """
    try:
        import yaml

        # Try to find and load configuration file
        config_locations = [
            Path("./retileup.yaml"),
            Path("./workflows.yaml"),
            Path.home() / ".retileup.yaml",
            Path.home() / ".config" / "retileup" / "config.yaml",
        ]

        config = None
        for config_path in config_locations:
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                    break
                except Exception:
                    continue

        if not config or "workflows" not in config:
            return []

        workflow_names = list(config["workflows"].keys())
        return [name for name in workflow_names if name.startswith(incomplete)]

    except Exception:
        return []


def complete_output_formats(incomplete: str) -> List[str]:
    """Complete output format options.

    Args:
        incomplete: Incomplete format name

    Returns:
        List of matching format names
    """
    formats = ["table", "json", "yaml"]
    return [fmt for fmt in formats if fmt.startswith(incomplete)]


def complete_coordinate_examples(incomplete: str) -> List[str]:
    """Provide coordinate format examples.

    Args:
        incomplete: Incomplete coordinate string

    Returns:
        List of coordinate examples
    """
    examples = [
        "0,0",
        "0,0;256,0",
        "0,0;256,0;0,256",
        "0,0;256,0;0,256;256,256",
    ]
    return [ex for ex in examples if ex.startswith(incomplete)]


def install_completion_command(
    ctx: typer.Context,
    shell: str = typer.Option(
        "auto",
        "--shell",
        help="Shell type: bash, zsh, fish, or auto-detect",
        metavar="SHELL",
    ),
    path: bool = typer.Option(
        False,
        "--show-path",
        help="Show the completion script path instead of installing",
    ),
) -> None:
    """Install shell completion for ReTileUp.

    [bold]Examples:[/bold]
        # Auto-detect shell and install
        retileup --install-completion

        # Install for specific shell
        retileup --install-completion --shell bash

        # Show completion script path
        retileup --install-completion --show-path

    [bold]Supported Shells:[/bold]
        • [cyan]bash[/cyan] - Bash shell completion
        • [cyan]zsh[/cyan] - Zsh shell completion
        • [cyan]fish[/cyan] - Fish shell completion
        • [cyan]auto[/cyan] - Auto-detect current shell

    [bold]Manual Installation:[/bold]
        For bash: Add to ~/.bashrc
        For zsh: Add to ~/.zshrc
        For fish: Add to ~/.config/fish/config.fish
    """
    console: Console = ctx.obj.get("console", Console()) if ctx.obj else Console()

    try:
        # Get the main typer app from the context
        from retileup.cli.main import app

        if path:
            # Show completion script path
            console.print("[bold]Completion script installation paths:[/bold]")
            console.print("• Bash: ~/.bashrc or ~/.bash_completion")
            console.print("• Zsh: ~/.zshrc or ~/.zsh_completion")
            console.print("• Fish: ~/.config/fish/completions/retileup.fish")
            console.print()
            console.print("[bold]To install manually, add this line to your shell config:[/bold]")

            if shell == "bash" or (shell == "auto" and "bash" in str(Path.cwd())):
                console.print("eval \"$(_RETILEUP_COMPLETE=bash_source retileup)\"")
            elif shell == "zsh" or (shell == "auto" and "zsh" in str(Path.cwd())):
                console.print("eval \"$(_RETILEUP_COMPLETE=zsh_source retileup)\"")
            elif shell == "fish" or (shell == "auto" and "fish" in str(Path.cwd())):
                console.print("eval (env _RETILEUP_COMPLETE=fish_source retileup)")
            else:
                console.print("eval \"$(_RETILEUP_COMPLETE=bash_source retileup)\"  # For bash")
                console.print("eval \"$(_RETILEUP_COMPLETE=zsh_source retileup)\"   # For zsh")
                console.print("eval (env _RETILEUP_COMPLETE=fish_source retileup)    # For fish")

            raise typer.Exit(0)

        # Auto-detect shell if needed
        if shell == "auto":
            import os
            shell_env = os.environ.get("SHELL", "")
            if "bash" in shell_env:
                shell = "bash"
            elif "zsh" in shell_env:
                shell = "zsh"
            elif "fish" in shell_env:
                shell = "fish"
            else:
                shell = "bash"  # Default to bash

        # Install completion
        console.print(f"[bold]Installing completion for {shell}...[/bold]")

        try:
            # Try to use typer's built-in completion installation
            import subprocess
            import os

            # Set up environment for completion
            env = os.environ.copy()
            env[f"_RETILEUP_COMPLETE"] = f"{shell}_source"

            # Get completion script
            result = subprocess.run(
                ["python", "-m", "retileup.cli.main"],
                env=env,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                completion_script = result.stdout

                # Install to appropriate location
                if shell == "bash":
                    completion_dir = Path.home() / ".bashrc"
                    completion_line = 'eval "$(_RETILEUP_COMPLETE=bash_source retileup)"'
                elif shell == "zsh":
                    completion_dir = Path.home() / ".zshrc"
                    completion_line = 'eval "$(_RETILEUP_COMPLETE=zsh_source retileup)"'
                elif shell == "fish":
                    completion_dir = Path.home() / ".config" / "fish" / "config.fish"
                    completion_line = 'eval (env _RETILEUP_COMPLETE=fish_source retileup)'
                else:
                    raise ValueError(f"Unsupported shell: {shell}")

                # Check if already installed
                if completion_dir.exists():
                    with open(completion_dir, 'r', encoding='utf-8') as f:
                        content = f.read()

                    if "_RETILEUP_COMPLETE" in content:
                        console.print("[yellow]Completion already installed[/yellow]")
                        raise typer.Exit(0)

                # Add completion line to shell config
                with open(completion_dir, 'a', encoding='utf-8') as f:
                    f.write(f"\\n# ReTileUp completion\\n{completion_line}\\n")

                console.print(f"[green]✓[/green] Completion installed for {shell}")
                console.print(f"[dim]Added to: {completion_dir}[/dim]")
                console.print("\\n[yellow]Note:[/yellow] Restart your shell or run:")
                console.print(f"[cyan]source {completion_dir}[/cyan]")

            else:
                raise Exception("Failed to generate completion script")

        except Exception as e:
            console.print(f"[red]Failed to install completion:[/red] {e}")
            console.print("\\n[bold]Manual installation:[/bold]")
            console.print(f"Add this line to your {shell} configuration file:")

            if shell == "bash":
                console.print('eval "$(_RETILEUP_COMPLETE=bash_source retileup)"')
            elif shell == "zsh":
                console.print('eval "$(_RETILEUP_COMPLETE=zsh_source retileup)"')
            elif shell == "fish":
                console.print('eval (env _RETILEUP_COMPLETE=fish_source retileup)')

            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)