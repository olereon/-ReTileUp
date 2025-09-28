"""Utility commands implementation for ReTileUp CLI."""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any

import typer
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from retileup.core.registry import get_global_registry
from retileup.core.exceptions import ValidationError


def complete_output_formats(incomplete: str) -> List[str]:
    """Auto-complete output format options."""
    formats = ["table", "json", "yaml"]
    return [fmt for fmt in formats if fmt.startswith(incomplete)]


def complete_human_json_formats(incomplete: str) -> List[str]:
    """Auto-complete human/json format options."""
    formats = ["human", "json"]
    return [fmt for fmt in formats if fmt.startswith(incomplete)]


def format_tool_info_table(tools_info: List[Dict[str, Any]], detailed: bool = False) -> Table:
    """Format tool information as a Rich table.

    Args:
        tools_info: List of tool information dictionaries
        detailed: Whether to show detailed information

    Returns:
        Rich Table object
    """
    if detailed:
        table = Table(title="Available Tools (Detailed)")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Version", style="magenta")
        table.add_column("Description", style="yellow")
        table.add_column("Module", style="dim")
        table.add_column("Usage", style="green")

        for tool in tools_info:
            table.add_row(
                tool["name"],
                tool["version"],
                tool["description"][:60] + "..." if len(tool["description"]) > 60 else tool["description"],
                tool.get("module", "N/A"),
                str(tool.get("usage_count", 0))
            )
    else:
        table = Table(title="Available Tools")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Version", style="magenta")
        table.add_column("Description", style="yellow")

        for tool in tools_info:
            table.add_row(
                tool["name"],
                tool["version"],
                tool["description"][:80] + "..." if len(tool["description"]) > 80 else tool["description"]
            )

    return table


def format_tool_info_json(tools_info: List[Dict[str, Any]], detailed: bool = False) -> str:
    """Format tool information as JSON.

    Args:
        tools_info: List of tool information dictionaries
        detailed: Whether to include detailed information

    Returns:
        JSON formatted string
    """
    if detailed:
        return json.dumps(tools_info, indent=2, default=str)
    else:
        # Simplified format for non-detailed output
        simplified = []
        for tool in tools_info:
            simplified.append({
                "name": tool["name"],
                "version": tool["version"],
                "description": tool["description"]
            })
        return json.dumps(simplified, indent=2)


def format_tool_info_yaml(tools_info: List[Dict[str, Any]], detailed: bool = False) -> str:
    """Format tool information as YAML.

    Args:
        tools_info: List of tool information dictionaries
        detailed: Whether to include detailed information

    Returns:
        YAML formatted string
    """
    if detailed:
        return yaml.dump({"tools": tools_info}, default_flow_style=False, indent=2)
    else:
        # Simplified format for non-detailed output
        simplified = []
        for tool in tools_info:
            simplified.append({
                "name": tool["name"],
                "version": tool["version"],
                "description": tool["description"]
            })
        return yaml.dump({"tools": simplified}, default_flow_style=False, indent=2)


def list_tools_command(
    ctx: typer.Context,
    detailed: bool = typer.Option(
        False,
        "--detailed",
        "-d",
        help="Show detailed tool information",
    ),
    format_type: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, json, yaml",
        metavar="FORMAT",
        autocompletion=complete_output_formats,
    ),
) -> None:
    """Display available tools and their descriptions.

    [bold]Examples:[/bold]
        # List all tools
        retileup list-tools

        # Detailed information
        retileup list-tools --detailed

        # JSON output for scripting
        retileup list-tools --format json

        # YAML output with details
        retileup list-tools --detailed --format yaml

    [bold]Output Formats:[/bold]
        • [cyan]table[/cyan] - Human-readable table (default)
        • [cyan]json[/cyan] - JSON format for scripting
        • [cyan]yaml[/cyan] - YAML format for configuration
    """
    # Get CLI context
    cli_context = ctx.obj or {}
    console: Console = cli_context.get("console", Console())
    verbose: bool = cli_context.get("verbose", False)
    quiet: bool = cli_context.get("quiet", False)

    # Validate format
    if format_type not in ["table", "json", "yaml"]:
        console.print(f"[red]Error:[/red] Invalid format '{format_type}'. Must be one of: table, json, yaml")
        raise typer.Exit(1)

    try:
        # Get registry and tool information
        registry = get_global_registry()
        tools_info = registry.list_tools(include_metadata=True)  # Always get metadata for CLI display

        if not tools_info:
            if format_type == "table":
                console.print("[yellow]No tools available[/yellow]")
                console.print("Try running tool discovery or check your installation.")
            elif format_type == "json":
                console.print(json.dumps({"tools": [], "message": "No tools available"}))
            elif format_type == "yaml":
                console.print(yaml.dump({"tools": [], "message": "No tools available"}))
            return

        # Display registry statistics if verbose and table format
        if verbose and format_type == "table" and not quiet:
            stats = registry.get_tool_statistics()
            stats_text = Text()
            stats_text.append("Registry Statistics", style="bold")
            stats_text.append(f"\\nTotal tools: ", style="dim")
            stats_text.append(str(stats["total_tools"]), style="cyan")
            stats_text.append(f"\\nTotal usage: ", style="dim")
            stats_text.append(str(stats["total_usage"]), style="green")

            if stats["most_used_tool"]:
                stats_text.append(f"\\nMost used: ", style="dim")
                stats_text.append(f"{stats['most_used_tool']['name']} ", style="magenta")
                stats_text.append(f"({stats['most_used_tool']['usage_count']} times)", style="dim")

            console.print(Panel(stats_text, title="Registry Info", border_style="dim"))
            console.print()

        # Format and display output
        if format_type == "table":
            table = format_tool_info_table(tools_info, detailed)
            console.print(table)

            # Show tool health status if detailed and verbose
            if detailed and verbose and not quiet:
                console.print()
                console.print("[bold]Tool Health Status[/bold]")

                for tool in tools_info:
                    tool_name = tool["name"]
                    health = registry.validate_tool_health(tool_name)

                    if health["healthy"]:
                        console.print(f"  [green]✓[/green] {tool_name}")
                    else:
                        console.print(f"  [red]✗[/red] {tool_name}: {health.get('error', 'Unknown error')}")

        elif format_type == "json":
            output = format_tool_info_json(tools_info, detailed)
            console.print(output)

        elif format_type == "yaml":
            output = format_tool_info_yaml(tools_info, detailed)
            console.print(output)

        return

    except typer.Exit:
        # Re-raise typer.Exit exceptions without handling them
        raise
    except Exception as e:
        if verbose:
            console.print_exception()
        else:
            console.print(f"[red]Error listing tools:[/red] {e}")
        raise typer.Exit(1)


def validate_yaml_config(config_file: Path) -> tuple[dict, List[str]]:
    """Validate YAML configuration file.

    Args:
        config_file: Path to configuration file

    Returns:
        Tuple of (config_dict, errors_list)
    """
    errors = []

    # Check file exists and is readable
    if not config_file.exists():
        errors.append(f"Configuration file not found: {config_file}")
        return {}, errors

    if not config_file.is_file():
        errors.append(f"Path is not a file: {config_file}")
        return {}, errors

    # Try to load YAML
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        errors.append(f"Invalid YAML syntax: {e}")
        return {}, errors
    except Exception as e:
        errors.append(f"Failed to read file: {e}")
        return {}, errors

    if config is None:
        errors.append("Configuration file is empty")
        return {}, errors

    if not isinstance(config, dict):
        errors.append("Configuration must be a YAML object (dictionary)")
        return {}, errors

    return config, errors


def validate_workflow_schema(config: dict) -> List[str]:
    """Validate workflow schema in configuration.

    Args:
        config: Configuration dictionary

    Returns:
        List of validation errors
    """
    errors = []

    # Check for workflows section
    if "workflows" not in config:
        return ["No 'workflows' section found in configuration"]

    workflows = config["workflows"]
    if not isinstance(workflows, dict):
        return ["'workflows' section must be a dictionary"]

    if not workflows:
        return ["No workflows defined in 'workflows' section"]

    # Validate each workflow
    for workflow_name, workflow_config in workflows.items():
        if not isinstance(workflow_config, dict):
            errors.append(f"Workflow '{workflow_name}' must be a dictionary")
            continue

        # Check required fields
        if "steps" not in workflow_config:
            errors.append(f"Workflow '{workflow_name}' missing required 'steps' field")
            continue

        steps = workflow_config["steps"]
        if not isinstance(steps, list):
            errors.append(f"Workflow '{workflow_name}' steps must be a list")
            continue

        if not steps:
            errors.append(f"Workflow '{workflow_name}' must have at least one step")
            continue

        # Validate each step
        for i, step in enumerate(steps):
            step_name = f"{workflow_name}.steps[{i}]"

            if not isinstance(step, dict):
                errors.append(f"Step {step_name} must be a dictionary")
                continue

            if "tool" not in step:
                errors.append(f"Step {step_name} missing required 'tool' field")

            if "config" not in step:
                errors.append(f"Step {step_name} missing required 'config' field")

    return errors


def validate_command(
    ctx: typer.Context,
    config_file: Path = typer.Argument(
        ...,
        help="Configuration file to validate",
        exists=True,
        file_okay=True,
        dir_okay=False,
        metavar="CONFIG_FILE",
    ),
    strict: bool = typer.Option(
        False,
        "--strict",
        "-s",
        help="Enable strict validation",
    ),
    format_type: str = typer.Option(
        "human",
        "--format",
        "-f",
        help="Output format: human, json",
        metavar="FORMAT",
        autocompletion=complete_human_json_formats,
    ),
) -> None:
    """Validate configuration files and workflows.

    [bold]Examples:[/bold]
        # Validate configuration file
        retileup validate config.yaml

        # Strict validation with detailed output
        retileup validate --strict config.yaml

        # JSON output for automation
        retileup validate --format json workflows.yaml

    [bold]Validation Checks:[/bold]
        • YAML syntax and structure
        • Required configuration sections
        • Workflow definitions and steps
        • Tool references and availability
        • Configuration schema compliance

    [bold]Strict Mode:[/bold]
        Enables additional validation checks:
        • Tool configuration schemas
        • Cross-reference validation
        • Performance estimates
    """
    # Get CLI context
    cli_context = ctx.obj or {}
    console: Console = cli_context.get("console", Console())
    verbose: bool = cli_context.get("verbose", False)
    quiet: bool = cli_context.get("quiet", False)

    # Validate format
    if format_type not in ["human", "json"]:
        console.print(f"[red]Error:[/red] Invalid format '{format_type}'. Must be one of: human, json")
        raise typer.Exit(1)

    try:
        # Load and validate YAML
        config, yaml_errors = validate_yaml_config(config_file)
        all_errors = yaml_errors.copy()

        # If YAML is valid, perform schema validation
        if not yaml_errors:
            # Validate workflow schema
            workflow_errors = validate_workflow_schema(config)
            all_errors.extend(workflow_errors)

            # Strict validation
            if strict and not workflow_errors:
                registry = get_global_registry()

                # Check tool availability
                workflows = config.get("workflows", {})
                for workflow_name, workflow_config in workflows.items():
                    steps = workflow_config.get("steps", [])
                    for i, step in enumerate(steps):
                        tool_name = step.get("tool")
                        if tool_name:
                            if tool_name not in registry:
                                all_errors.append(
                                    f"Workflow '{workflow_name}' step {i}: tool '{tool_name}' not available"
                                )
                            else:
                                # Validate tool health
                                health = registry.validate_tool_health(tool_name)
                                if not health["healthy"]:
                                    all_errors.append(
                                        f"Workflow '{workflow_name}' step {i}: tool '{tool_name}' is unhealthy: {health.get('error', 'Unknown error')}"
                                    )

        # Prepare validation results
        validation_result = {
            "file": str(config_file),
            "valid": len(all_errors) == 0,
            "errors": all_errors,
            "error_count": len(all_errors),
            "strict_mode": strict,
        }

        # Add config summary if valid
        if validation_result["valid"] and config:
            workflows = config.get("workflows", {})
            validation_result["summary"] = {
                "workflows_count": len(workflows),
                "workflow_names": list(workflows.keys()),
                "total_steps": sum(len(wf.get("steps", [])) for wf in workflows.values()),
            }

        # Output results
        if format_type == "json":
            console.print(json.dumps(validation_result, indent=2))
        else:
            # Human-readable format
            if validation_result["valid"]:
                console.print(f"[green]✓[/green] Configuration file [cyan]{config_file}[/cyan] is valid")

                if verbose and "summary" in validation_result:
                    summary = validation_result["summary"]
                    console.print(f"  Workflows: [yellow]{summary['workflows_count']}[/yellow]")
                    console.print(f"  Total steps: [yellow]{summary['total_steps']}[/yellow]")

                    if summary["workflow_names"]:
                        console.print("  Available workflows:")
                        for workflow_name in summary["workflow_names"]:
                            console.print(f"    • [cyan]{workflow_name}[/cyan]")

                if strict:
                    console.print("  [green]Strict validation passed[/green]")

            else:
                console.print(f"[red]✗[/red] Configuration file [cyan]{config_file}[/cyan] has errors")
                console.print(f"  Found [red]{validation_result['error_count']}[/red] errors:")

                for i, error in enumerate(all_errors, 1):
                    console.print(f"    {i}. {error}")

        # Exit with appropriate code
        if validation_result["valid"]:
            return
        else:
            raise typer.Exit(2)

    except typer.Exit:
        # Re-raise typer.Exit exceptions without handling them
        raise
    except Exception as e:
        if verbose:
            console.print_exception()
        else:
            console.print(f"[red]Validation error:[/red] {e}")
        raise typer.Exit(1)