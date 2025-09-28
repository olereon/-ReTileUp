"""Tile command implementation for ReTileUp CLI."""

import re
from pathlib import Path
from typing import List, Optional, Tuple

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from retileup.core.registry import get_global_registry
from retileup.core.exceptions import ValidationError, ProcessingError
from retileup.tools.tiling import TilingConfig


def parse_coordinates(coords_str: str) -> List[Tuple[int, int]]:
    """Parse coordinate string into list of (x, y) tuples.

    Args:
        coords_str: Coordinate string in format "x1,y1;x2,y2;..."

    Returns:
        List of (x, y) coordinate tuples

    Raises:
        ValueError: If coordinate format is invalid
    """
    if not coords_str.strip():
        raise ValueError("Coordinates string cannot be empty")

    coordinates = []
    coord_pairs = coords_str.split(';')

    for i, pair in enumerate(coord_pairs):
        pair = pair.strip()
        if not pair:
            continue

        # Match x,y pattern
        if not re.match(r'^\d+,\d+$', pair):
            raise ValueError(f"Invalid coordinate format at position {i}: '{pair}'. Expected format: 'x,y'")

        try:
            x_str, y_str = pair.split(',')
            x, y = int(x_str), int(y_str)
            coordinates.append((x, y))
        except ValueError as e:
            raise ValueError(f"Invalid coordinate values at position {i}: '{pair}'. {e}")

    if not coordinates:
        raise ValueError("No valid coordinates found in string")

    return coordinates


def validate_tile_dimensions(width: int, height: int) -> None:
    """Validate tile dimensions are reasonable.

    Args:
        width: Tile width in pixels
        height: Tile height in pixels

    Raises:
        ValueError: If dimensions are invalid
    """
    if width <= 0 or height <= 0:
        raise ValueError("Tile dimensions must be positive integers")

    if width > 8192 or height > 8192:
        raise ValueError("Tile dimensions cannot exceed 8192x8192 pixels")

    if width < 1 or height < 1:
        raise ValueError("Tile dimensions must be at least 1x1 pixel")


def tile_command(
    ctx: typer.Context,
    input_file: Path = typer.Argument(
        ...,
        help="Input image file path",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        metavar="INPUT_FILE",
    ),
    width: int = typer.Option(
        ...,
        "--width",
        "-w",
        help="Tile width in pixels",
        min=1,
        max=8192,
    ),
    height: int = typer.Option(
        ...,
        "--height",
        "-h",
        help="Tile height in pixels",
        min=1,
        max=8192,
    ),
    coords: str = typer.Option(
        ...,
        "--coords",
        "-c",
        help="Coordinates as 'x1,y1;x2,y2;...' format",
        metavar="COORDS",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory (default: ./output)",
        metavar="DIR",
    ),
    pattern: str = typer.Option(
        "{base}_{x}_{y}.{ext}",
        "--pattern",
        "-p",
        help="Output filename pattern",
        metavar="PATTERN",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show actions without executing",
    ),
    overlap: int = typer.Option(
        0,
        "--overlap",
        help="Tile overlap in pixels",
        min=0,
        max=512,
    ),
    maintain_aspect: bool = typer.Option(
        False,
        "--maintain-aspect",
        help="Maintain aspect ratio when tiling",
    ),
) -> None:
    """Extract rectangular tiles from images at specified coordinates.

    [bold]Examples:[/bold]
        # Basic tiling
        retileup tile --width 256 --height 256 --coords "0,0;256,0;0,256" image.jpg

        # Custom output and pattern
        retileup tile -w 100 -h 100 -c "0,0;100,100" -o ./tiles -p "tile_{x}_{y}.png" photo.jpg

        # Dry run to preview
        retileup tile --width 200 --height 200 --coords "0,0" --dry-run large_image.png

    [bold]Coordinate Format:[/bold]
        Use semicolon-separated x,y pairs: "x1,y1;x2,y2;x3,y3"
        Example: "0,0;256,0;0,256;256,256"

    [bold]Pattern Placeholders:[/bold]
        {base} - Original filename without extension
        {x}, {y} - Tile coordinates
        {ext} - Original file extension
    """
    # Get CLI context
    cli_context = ctx.obj or {}
    console: Console = cli_context.get("console", Console())
    verbose: bool = cli_context.get("verbose", False)
    quiet: bool = cli_context.get("quiet", False)

    try:
        # Validate tile dimensions
        validate_tile_dimensions(width, height)

        # Parse coordinates
        try:
            coordinates = parse_coordinates(coords)
        except ValueError as e:
            console.print(f"[red]Error:[/red] Invalid coordinates format: {e}")
            raise typer.Exit(2)

        # Set default output directory
        if output is None:
            output = Path("./output")

        # Display operation summary if not quiet
        if not quiet:
            console.print(f"[bold]Tiling Operation Summary[/bold]")
            console.print(f"Input file: [cyan]{input_file}[/cyan]")
            console.print(f"Tile size: [yellow]{width}x{height}[/yellow] pixels")
            console.print(f"Coordinates: [magenta]{len(coordinates)}[/magenta] tiles")
            console.print(f"Output directory: [cyan]{output}[/cyan]")
            console.print(f"Pattern: [dim]{pattern}[/dim]")

            if overlap > 0:
                console.print(f"Overlap: [yellow]{overlap}[/yellow] pixels")
            if maintain_aspect:
                console.print("Maintain aspect ratio: [green]enabled[/green]")
            if dry_run:
                console.print("[yellow]Dry run mode - no files will be created[/yellow]")
            console.print()

        # Show coordinate details in verbose mode
        if verbose and not quiet:
            coord_table = Table(title="Tile Coordinates")
            coord_table.add_column("Index", style="cyan")
            coord_table.add_column("X", style="magenta")
            coord_table.add_column("Y", style="magenta")
            coord_table.add_column("Position", style="dim")

            for i, (x, y) in enumerate(coordinates):
                coord_table.add_row(
                    str(i + 1),
                    str(x),
                    str(y),
                    f"({x}, {y})"
                )

            console.print(coord_table)
            console.print()

        # Get tiling tool from registry
        registry = get_global_registry()
        tiling_tool = registry.create_tool("tile")

        if not tiling_tool:
            console.print("[red]Error:[/red] Tiling tool not available")
            raise typer.Exit(3)

        # Create configuration
        config = TilingConfig(
            input_path=input_file,
            output_dir=output,
            dry_run=dry_run,
            verbose=verbose,
            tile_width=width,
            tile_height=height,
            coordinates=coordinates,
            output_pattern=pattern,
            maintain_aspect=maintain_aspect,
            overlap=overlap,
        )

        # Validate configuration
        validation_errors = tiling_tool.validate_config(config)
        if validation_errors:
            console.print("[red]Validation errors:[/red]")
            for error in validation_errors:
                console.print(f"  • {error}")
            raise typer.Exit(2)

        # Execute tiling operation with progress bar
        if not quiet:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(
                    f"Processing {len(coordinates)} tiles...",
                    total=len(coordinates)
                )

                # Execute the tiling operation
                result = tiling_tool.execute(config)
                progress.update(task, completed=len(coordinates))
        else:
            # Execute without progress bar in quiet mode
            result = tiling_tool.execute(config)

        # Handle results
        if result.success:
            if not quiet:
                console.print(f"[green]✓[/green] {result.message}")

                if verbose and result.metadata:
                    metadata_table = Table(title="Operation Details")
                    metadata_table.add_column("Metric", style="cyan")
                    metadata_table.add_column("Value", style="yellow")

                    # Display key metrics
                    metadata_table.add_row("Tiles created", str(result.metadata.get("tile_count", 0)))
                    metadata_table.add_row("Tile size", result.metadata.get("tile_size", "Unknown"))
                    metadata_table.add_row("Processing time", f"{result.execution_time:.2f}s")

                    if "pixels_per_second" in result.metadata:
                        pps = result.metadata["pixels_per_second"]
                        metadata_table.add_row("Performance", f"{pps/1_000_000:.1f} MP/s")

                    console.print()
                    console.print(metadata_table)

                # List output files if verbose
                if verbose and result.output_files:
                    console.print(f"\\n[bold]Output files ([cyan]{len(result.output_files)}[/cyan]):[/bold]")
                    for output_file in result.output_files[:10]:  # Show first 10
                        console.print(f"  [dim]•[/dim] {output_file}")

                    if len(result.output_files) > 10:
                        console.print(f"  [dim]... and {len(result.output_files) - 10} more files[/dim]")

            # Exit with success
            raise typer.Exit(0)
        else:
            console.print(f"[red]✗ Tiling failed:[/red] {result.message}")

            if verbose and result.metadata and "error" in result.metadata:
                console.print(f"[dim]Error details: {result.metadata['error']}[/dim]")

            # Determine exit code based on error type
            if "validation" in result.message.lower():
                raise typer.Exit(2)
            else:
                raise typer.Exit(3)

    except ValidationError as e:
        console.print(f"[red]Validation error:[/red] {e}")
        raise typer.Exit(2)
    except ProcessingError as e:
        console.print(f"[red]Processing error:[/red] {e}")
        raise typer.Exit(3)
    except Exception as e:
        if verbose:
            console.print_exception()
        else:
            console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)