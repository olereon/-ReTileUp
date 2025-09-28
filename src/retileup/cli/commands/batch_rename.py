"""CLI command for batch file renaming."""

from pathlib import Path
from typing import Optional, Set

import typer
from rich.console import Console

from ...core.registry import ToolRegistry
from ...tools.batch_renamer import BatchRenamerConfig
from ..main import global_state

console = Console()


def batch_rename_command(
    input_dir: Path = typer.Argument(
        ...,
        help="Input directory containing image files to rename",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    output_dir: Path = typer.Option(
        Path("output/renamed"),
        "--output",
        "-o",
        help="Output directory for renamed files",
        file_okay=False,
        dir_okay=True,
    ),
    processed_file: Path = typer.Option(
        Path("processed.txt"),
        "--processed-file",
        "-p",
        help="File to track processed filenames",
    ),
    naming_pattern: str = typer.Option(
        "{date}_{index:09d}",
        "--pattern",
        help="Naming pattern with {date} and {index} placeholders",
    ),
    date_format: str = typer.Option(
        "%Y-%m-%d",
        "--date-format",
        help="Date format for the naming schema (strftime format)",
    ),
    use_current_date: bool = typer.Option(
        True,
        "--current-date/--parse-date",
        help="Use current date instead of parsing from processed file",
    ),
    preserve_extension: bool = typer.Option(
        True,
        "--preserve-ext/--no-preserve-ext",
        help="Keep the original file extension",
    ),
    delete_originals: bool = typer.Option(
        False,
        "--delete-originals",
        help="Delete original files after successful renaming",
    ),
    force_overwrite: bool = typer.Option(
        False,
        "--force-overwrite",
        help="Overwrite existing files in output directory",
    ),
    extensions: Optional[str] = typer.Option(
        None,
        "--extensions",
        help="Comma-separated list of file extensions to process (e.g., '.jpg,.png,.tiff')",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be done without executing",
    ),
    timeout: Optional[float] = typer.Option(
        None,
        "--timeout",
        help="Maximum execution time in seconds",
        min=0.1,
    ),
) -> None:
    """Rename image files using a systematic date-based naming scheme.

    This command systematically renames image files using a date-based incrementing schema.
    The naming format is: {date}_{index} where date follows the specified format and index
    is a 9-digit zero-padded number (000000001-999999999).

    [bold]Examples:[/bold]
        # Basic batch rename with default pattern (YYYY-MM-DD_000000001.jpg)
        retileup batch-rename ./photos

        # Specify custom output directory
        retileup batch-rename ./photos --output ./renamed_photos

        # Use custom naming pattern and date format
        retileup batch-rename ./photos --pattern "{date}_{index:06d}" --date-format "%Y%m%d"

        # Preview changes without executing
        retileup batch-rename ./photos --dry-run

        # Process only specific file types
        retileup batch-rename ./photos --extensions ".jpg,.png,.tiff"

        # Delete originals after successful renaming (use with caution!)
        retileup batch-rename ./photos --delete-originals

    [bold]Naming Schema:[/bold]
        • Files are renamed using format: {date}_{index}.{ext}
        • Date component uses configurable format (default: YYYY-MM-DD)
        • Index is 9-digit zero-padded (000000001, 000000002, etc.)
        • Original file extensions are preserved by default
        • Processed filenames are tracked in processed.txt

    [bold]Safety Features:[/bold]
        • Creates output directory automatically
        • Tracks all processed files to prevent duplicates
        • Validates naming patterns before processing
        • Supports dry-run mode for preview
        • Optional original file deletion with validation
        • Comprehensive error handling and recovery

    [bold]Supported Formats:[/bold]
        JPG, JPEG, PNG, GIF, BMP, TIFF, TIF, WEBP, SVG, RAW, CR2, NEF, ARW, DNG
    """
    try:
        # Configure logging based on global verbosity
        if global_state.verbose:
            console.print("[dim]Starting batch rename operation...[/dim]")

        # Parse file extensions if provided
        supported_extensions = None
        if extensions:
            ext_list = [ext.strip() for ext in extensions.split(",")]
            supported_extensions = set()
            for ext in ext_list:
                if not ext.startswith("."):
                    ext = "." + ext
                supported_extensions.add(ext.lower())

        # Create configuration
        config = BatchRenamerConfig(
            input_path=input_dir,
            output_dir=output_dir,
            processed_file=processed_file,
            naming_pattern=naming_pattern,
            date_format=date_format,
            use_current_date=use_current_date,
            preserve_original_extension=preserve_extension,
            delete_originals=delete_originals,
            force_overwrite=force_overwrite,
            dry_run=dry_run,
            verbose=global_state.verbose,
            timeout=timeout,
            supported_extensions=supported_extensions
            or {
                ".jpg",
                ".jpeg",
                ".png",
                ".gif",
                ".bmp",
                ".tiff",
                ".tif",
                ".webp",
                ".svg",
                ".raw",
                ".cr2",
                ".nef",
                ".arw",
                ".dng",
            },
        )

        # Get the batch renaming tool from registry
        from ...core.registry import get_global_registry

        registry = get_global_registry()

        # Ensure auto-discovery has run
        registry.auto_discover_tools(force_refresh=True)

        tool = registry.get_tool("batch-rename")

        if not tool:
            console.print("[red]Error:[/red] Batch rename tool not found in registry")
            raise typer.Exit(1)

        # Validate configuration
        validation_errors = tool.validate_config(config)
        if validation_errors:
            console.print("[red]Configuration validation failed:[/red]")
            for error in validation_errors:
                console.print(f"  • {error}")
            raise typer.Exit(1)

        # Execute the tool
        if not global_state.quiet:
            if config.dry_run:
                console.print(
                    "[yellow]Dry run mode - no files will be modified[/yellow]"
                )
            else:
                console.print(f"Processing files from [cyan]{input_dir}[/cyan]")
                console.print(f"Output directory: [cyan]{output_dir}[/cyan]")
                console.print(f"Naming pattern: [cyan]{naming_pattern}[/cyan]")

        result = tool.execute_with_timing(config)

        # Display results
        if result.success:
            if not global_state.quiet:
                console.print(f"[green]✓[/green] {result.message}")

                # Show detailed statistics
                metadata = result.metadata
                if metadata:
                    console.print("\n[bold]Operation Summary:[/bold]")
                    console.print(
                        f"  Files renamed: {metadata.get('files_renamed', 0)}"
                    )
                    console.print(f"  Files failed: {metadata.get('files_failed', 0)}")
                    console.print(f"  Date used: {metadata.get('date_used', 'N/A')}")
                    console.print(
                        f"  Index range: {metadata.get('starting_index', 0):09d} - {metadata.get('ending_index', 0):09d}"
                    )

                    if config.dry_run:
                        console.print(f"  [yellow]Dry run - no changes made[/yellow]")
                    elif metadata.get("deleted_originals"):
                        console.print(f"  [yellow]Original files deleted[/yellow]")

                    if metadata.get("failed_files"):
                        console.print("\n[bold yellow]Failed files:[/bold yellow]")
                        for fail_info in metadata["failed_files"][:5]:  # Show first 5
                            console.print(
                                f"  • {fail_info['file'].name}: {fail_info['error']}"
                            )
                        if len(metadata["failed_files"]) > 5:
                            console.print(
                                f"  ... and {len(metadata['failed_files']) - 5} more"
                            )

                # Show output files in verbose mode
                if global_state.verbose and result.output_files:
                    console.print(
                        f"\n[bold]Output files:[/bold] ({len(result.output_files)} total)"
                    )
                    for output_file in result.output_files[:10]:  # Show first 10
                        console.print(f"  • {output_file.name}")
                    if len(result.output_files) > 10:
                        console.print(f"  ... and {len(result.output_files) - 10} more")

        else:
            console.print(f"[red]✗[/red] {result.message}")
            if result.error_code:
                console.print(f"[dim]Error code: {result.error_code}[/dim]")

            # Show partial results if any
            if result.output_files:
                console.print(
                    f"\n[yellow]Partial results:[/yellow] {len(result.output_files)} files processed"
                )

            raise typer.Exit(1)

    except typer.Exit:
        raise  # Re-raise typer exits
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        if global_state.verbose:
            console.print_exception()
        raise typer.Exit(1)
