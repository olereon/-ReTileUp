"""Workflow command implementation for ReTileUp CLI."""

import asyncio
from pathlib import Path
from typing import Optional, List

import typer
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel

from retileup.core.registry import get_global_registry
from retileup.core.orchestrator import WorkflowOrchestrator
from retileup.core.config import Config
from retileup.core.exceptions import ValidationError, ProcessingError, WorkflowError


def complete_workflow_names(incomplete: str) -> List[str]:
    """Auto-complete workflow names from configuration files."""
    try:
        # Try to find and load configuration file
        config_locations = [
            Path("./retileup.yaml"),
            Path("./workflows.yaml"),
            Path.home() / ".retileup.yaml",
            Path.home() / ".config" / "retileup" / "config.yaml",
        ]

        for config_path in config_locations:
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)

                    if config and "workflows" in config:
                        workflow_names = list(config["workflows"].keys())
                        return [name for name in workflow_names if name.startswith(incomplete)]
                except Exception:
                    continue

        return []
    except Exception:
        return []


def load_workflow_config(config_file: Optional[Path]) -> dict:
    """Load workflow configuration from file.

    Args:
        config_file: Path to configuration file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file not found
        yaml.YAMLError: If config file is invalid YAML
    """
    if config_file is None:
        # Try to auto-detect config files
        config_locations = [
            Path("./retileup.yaml"),
            Path("./workflows.yaml"),
            Path.home() / ".retileup.yaml",
            Path.home() / ".config" / "retileup" / "config.yaml",
        ]

        for config_path in config_locations:
            if config_path.exists():
                config_file = config_path
                break
        else:
            raise FileNotFoundError("No configuration file found. Please specify --config or create retileup.yaml")

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Invalid YAML in config file {config_file}: {e}")


def validate_workflow_exists(config: dict, workflow_name: str) -> dict:
    """Validate that workflow exists in configuration.

    Args:
        config: Configuration dictionary
        workflow_name: Name of workflow to validate

    Returns:
        Workflow configuration dictionary

    Raises:
        ValueError: If workflow not found or invalid
    """
    workflows = config.get("workflows", {})
    if workflow_name not in workflows:
        available = list(workflows.keys())
        if available:
            raise ValueError(f"Workflow '{workflow_name}' not found. Available workflows: {', '.join(available)}")
        else:
            raise ValueError(f"Workflow '{workflow_name}' not found. No workflows defined in configuration.")

    workflow_config = workflows[workflow_name]
    if not isinstance(workflow_config, dict):
        raise ValueError(f"Invalid workflow configuration for '{workflow_name}': must be a dictionary")

    # Validate required fields
    if "steps" not in workflow_config:
        raise ValueError(f"Workflow '{workflow_name}' missing required 'steps' field")

    steps = workflow_config["steps"]
    if not isinstance(steps, list) or not steps:
        raise ValueError(f"Workflow '{workflow_name}' must have at least one step")

    return workflow_config


def collect_input_files(input_path: Path) -> list[Path]:
    """Collect input files from path.

    Args:
        input_path: Input file or directory path

    Returns:
        List of input file paths

    Raises:
        ValueError: If no valid input files found
    """
    if input_path.is_file():
        # Check if it's a supported image format
        supported_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif'}
        if input_path.suffix.lower() in supported_extensions:
            return [input_path]
        else:
            raise ValueError(f"Unsupported file format: {input_path.suffix}")

    elif input_path.is_dir():
        # Collect all supported image files from directory
        supported_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif'}
        image_files = []

        for pattern in ['*.jpg', '*.jpeg', '*.png', '*.webp', '*.bmp', '*.tiff', '*.tif']:
            image_files.extend(input_path.glob(pattern))
            image_files.extend(input_path.glob(pattern.upper()))

        if not image_files:
            raise ValueError(f"No supported image files found in directory: {input_path}")

        return sorted(set(image_files))  # Remove duplicates and sort

    else:
        raise ValueError(f"Input path does not exist: {input_path}")


def workflow_command(
    ctx: typer.Context,
    workflow_name: str = typer.Argument(
        ...,
        help="Name of workflow to execute",
        metavar="WORKFLOW_NAME",
        autocompletion=complete_workflow_names,
    ),
    input_path: Path = typer.Option(
        ...,
        "--input",
        "-i",
        help="Input file or directory",
        exists=True,
        metavar="PATH",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory (default: ./output)",
        metavar="DIR",
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Workflow configuration file (auto-detected if not specified)",
        metavar="PATH",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview workflow without execution",
    ),
    parallel: int = typer.Option(
        4,
        "--parallel",
        help="Maximum parallel jobs",
        min=1,
        max=16,
    ),
) -> None:
    """Execute predefined workflows from configuration files.

    [bold]Examples:[/bold]
        # Execute workflow from default config
        retileup workflow web-optimize --input ./photos --output ./web

        # Use specific config file
        retileup workflow thumbnail-gen --input image.jpg --config ./custom-workflows.yaml

        # Dry run to preview workflow
        retileup workflow batch-process --input ./images --dry-run

    [bold]Configuration File Locations (searched in order):[/bold]
        • ./retileup.yaml
        • ./workflows.yaml
        • ~/.retileup.yaml
        • ~/.config/retileup/config.yaml

    [bold]Workflow Configuration Format:[/bold]
        workflows:
          web-optimize:
            name: "Web Optimization"
            description: "Optimize images for web deployment"
            steps:
              - tool: "tile"
                config:
                  tile_width: 1200
                  tile_height: 800
                  coordinates: [[0, 0]]
    """
    # Get CLI context
    cli_context = ctx.obj or {}
    console: Console = cli_context.get("console", Console())
    verbose: bool = cli_context.get("verbose", False)
    quiet: bool = cli_context.get("quiet", False)

    try:
        # Set default output directory
        if output is None:
            output = Path("./output")

        # Load configuration
        if not quiet:
            with console.status("[bold green]Loading workflow configuration..."):
                config = load_workflow_config(config_file)

        else:
            config = load_workflow_config(config_file)

        # Validate workflow exists
        workflow_config = validate_workflow_exists(config, workflow_name)

        # Collect input files
        input_files = collect_input_files(input_path)

        # Display workflow summary if not quiet
        if not quiet:
            console.print(f"[bold]Workflow Execution Summary[/bold]")
            console.print(f"Workflow: [cyan]{workflow_name}[/cyan]")

            if workflow_config.get("name"):
                console.print(f"Name: [yellow]{workflow_config['name']}[/yellow]")

            if workflow_config.get("description"):
                console.print(f"Description: [dim]{workflow_config['description']}[/dim]")

            console.print(f"Input files: [magenta]{len(input_files)}[/magenta] files")
            console.print(f"Output directory: [cyan]{output}[/cyan]")
            console.print(f"Parallel jobs: [yellow]{parallel}[/yellow]")

            if dry_run:
                console.print("[yellow]Dry run mode - no files will be created[/yellow]")

            console.print()

        # Show workflow steps in verbose mode
        if verbose and not quiet:
            steps_table = Table(title="Workflow Steps")
            steps_table.add_column("Step", style="cyan")
            steps_table.add_column("Tool", style="magenta")
            steps_table.add_column("Description", style="dim")

            for i, step in enumerate(workflow_config["steps"], 1):
                tool_name = step.get("tool", "unknown")
                description = step.get("description", "No description")
                steps_table.add_row(str(i), tool_name, description)

            console.print(steps_table)
            console.print()

        # Show input files in verbose mode
        if verbose and not quiet and len(input_files) <= 20:
            files_panel = Panel(
                "\\n".join([f"• {f}" for f in input_files]),
                title=f"Input Files ({len(input_files)})",
                border_style="dim"
            )
            console.print(files_panel)
            console.print()

        # Create workflow orchestrator
        registry = get_global_registry()
        orchestrator = WorkflowOrchestrator(registry)

        # Validate workflow configuration
        validation_errors = orchestrator.validate_workflow(workflow_config)
        if validation_errors:
            console.print("[red]Workflow validation errors:[/red]")
            for error in validation_errors:
                console.print(f"  • {error}")
            raise typer.Exit(2)

        if dry_run:
            console.print("[green]✓[/green] Workflow validation passed - ready for execution")
            console.print("[yellow]Dry run completed - no files were processed[/yellow]")
            return

        # Execute workflow
        if not quiet:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(
                    f"Executing workflow on {len(input_files)} files...",
                    total=len(input_files)
                )

                # Run workflow (asyncio support for future parallel processing)
                try:
                    results = asyncio.run(
                        orchestrator.execute_workflow(
                            workflow_config,
                            input_files,
                            output,
                            parallel=(parallel > 1)
                        )
                    )
                except Exception as e:
                    # Fallback to synchronous execution if asyncio fails
                    console.print("[yellow]Note:[/yellow] Falling back to synchronous execution")
                    results = []
                    for i, input_file in enumerate(input_files):
                        result = orchestrator._execute_single_workflow(
                            workflow_config, input_file, output
                        )
                        results.append(result)
                        progress.update(task, completed=i + 1)

                progress.update(task, completed=len(input_files))
        else:
            # Execute without progress bar in quiet mode
            try:
                results = asyncio.run(
                    orchestrator.execute_workflow(
                        workflow_config,
                        input_files,
                        output,
                        parallel=(parallel > 1)
                    )
                )
            except Exception:
                # Fallback to synchronous execution
                results = []
                for input_file in input_files:
                    result = orchestrator._execute_single_workflow(
                        workflow_config, input_file, output
                    )
                    results.append(result)

        # Process results
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]

        if not quiet:
            console.print(f"[green]✓[/green] Workflow completed")
            console.print(f"  Successful: [green]{len(successful_results)}[/green] files")

            if failed_results:
                console.print(f"  Failed: [red]{len(failed_results)}[/red] files")

            # Show performance metrics if verbose
            if verbose and successful_results:
                total_time = sum(r.execution_time for r in results)
                avg_time = total_time / len(results) if results else 0

                metrics_table = Table(title="Performance Metrics")
                metrics_table.add_column("Metric", style="cyan")
                metrics_table.add_column("Value", style="yellow")

                metrics_table.add_row("Total files", str(len(results)))
                metrics_table.add_row("Successful", str(len(successful_results)))
                metrics_table.add_row("Failed", str(len(failed_results)))
                metrics_table.add_row("Total time", f"{total_time:.2f}s")
                metrics_table.add_row("Average per file", f"{avg_time:.2f}s")

                console.print()
                console.print(metrics_table)

            # Show failed files if any
            if failed_results and verbose:
                console.print("\\n[red]Failed files:[/red]")
                for result in failed_results[:5]:  # Show first 5 failures
                    console.print(f"  [dim]•[/dim] {result.metadata.get('input_file', 'Unknown')}: {result.message}")

                if len(failed_results) > 5:
                    console.print(f"  [dim]... and {len(failed_results) - 5} more failures[/dim]")

        # Determine exit code
        if failed_results:
            if len(failed_results) == len(results):
                # All files failed
                raise typer.Exit(3)
            else:
                # Partial failure
                raise typer.Exit(1)
        else:
            # All successful
            return

    except FileNotFoundError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(2)
    except yaml.YAMLError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(2)
    except ValidationError as e:
        console.print(f"[red]Validation error:[/red] {e}")
        raise typer.Exit(2)
    except WorkflowError as e:
        console.print(f"[red]Workflow error:[/red] {e}")
        raise typer.Exit(3)
    except ProcessingError as e:
        console.print(f"[red]Processing error:[/red] {e}")
        raise typer.Exit(3)
    except typer.Exit:
        # Re-raise typer.Exit exceptions without handling them
        raise
    except Exception as e:
        if verbose:
            console.print_exception()
        else:
            console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)