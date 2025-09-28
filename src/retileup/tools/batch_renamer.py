"""Batch file renaming tool for ReTileUp.

This module provides the BatchRenamerTool class for systematically renaming image files
using a date-based incrementing schema. It tracks processed files and ensures
unique naming across multiple batches.
"""

import logging
import os
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Type

from pydantic import BaseModel, Field, field_validator, model_validator

from .base import BaseTool, ToolConfig, ToolResult
from ..core.exceptions import ProcessingError, ValidationError
from ..utils.image import ImageUtils

logger = logging.getLogger(__name__)


class BatchRenamerConfig(ToolConfig):
    """Configuration for batch renaming tool.

    This class defines all parameters needed for batch renaming operations,
    including naming schema, tracking file, and safety options.
    """

    # Override output_dir to be required for batch renaming
    output_dir: Path = Field(
        ..., description="Directory for renamed files (required for batch renaming)"
    )

    processed_file: Path = Field(
        Path("processed.txt"), description="File to track processed filenames"
    )

    naming_pattern: str = Field(
        "{date}_{index:09d}",
        description="Naming pattern with {date} and {index} placeholders",
    )

    date_format: str = Field(
        "%Y-%m-%d", description="Date format for the naming schema"
    )

    use_current_date: bool = Field(
        True, description="Use current date instead of parsing from processed file"
    )

    supported_extensions: Set[str] = Field(
        default_factory=lambda: {
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
        description="Set of supported image file extensions",
    )

    preserve_original_extension: bool = Field(
        True, description="Keep the original file extension"
    )

    delete_originals: bool = Field(
        False, description="Delete original files after successful renaming"
    )

    force_overwrite: bool = Field(
        False, description="Overwrite existing files in output directory"
    )

    @field_validator("naming_pattern")
    @classmethod
    def validate_naming_pattern(cls, v: str) -> str:
        """Validate naming pattern contains required placeholders."""
        required_placeholders = ["{date}", "{index"]
        for placeholder in required_placeholders:
            if placeholder not in v:
                raise ValueError(
                    f"Naming pattern must contain {placeholder} placeholder"
                )

        # Test pattern with sample values
        try:
            test_date = "2024-01-01"
            test_index = 1
            test_result = v.format(date=test_date, index=test_index)
            if not test_result:
                raise ValueError("Naming pattern produces empty filename")
        except KeyError as e:
            raise ValueError(f"Naming pattern contains invalid placeholder: {e}")
        except Exception as e:
            raise ValueError(f"Invalid naming pattern: {e}")

        return v

    @field_validator("date_format")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate date format string."""
        try:
            # Test if the format string is valid
            test_date = datetime.now()
            test_result = test_date.strftime(v)
            # Try to parse it back
            datetime.strptime(test_result, v)
        except ValueError as e:
            raise ValueError(f"Invalid date format: {e}")

        return v

    @field_validator("supported_extensions")
    @classmethod
    def validate_extensions(cls, v: Set[str]) -> Set[str]:
        """Validate and normalize file extensions."""
        normalized = set()
        for ext in v:
            if not ext.startswith("."):
                ext = "." + ext
            normalized.add(ext.lower())
        return normalized


class BatchRenamerTool(BaseTool):
    """Batch renaming tool for systematic file organization.

    This tool renames image files using a date-based incrementing schema,
    tracks processed files, and ensures unique naming across batches.
    Format: {date}_{index:09d}.{ext} (e.g., 2024-01-15_000000001.jpg)
    """

    def __init__(self) -> None:
        """Initialize the batch renaming tool."""
        super().__init__()
        self._processed_entries: List[str] = []
        self._last_index: int = 0
        self._current_date: str = ""

    @property
    def name(self) -> str:
        """Tool name for CLI and registry identification."""
        return "batch-rename"

    @property
    def description(self) -> str:
        """Tool description for help text and documentation."""
        return "Systematically rename image files using date-based incrementing schema"

    @property
    def version(self) -> str:
        """Tool version for compatibility checking."""
        return "1.0.0"

    def get_config_schema(self) -> Type[ToolConfig]:
        """Get the configuration schema class for this tool."""
        return BatchRenamerConfig

    def validate_config(self, config: ToolConfig) -> List[str]:
        """Validate tool configuration and return any errors."""
        if not isinstance(config, BatchRenamerConfig):
            return [
                f"Invalid config type: expected BatchRenamerConfig, got {type(config)}"
            ]

        errors = []

        # Validate input directory exists
        if not config.input_path.exists():
            errors.append(f"Input directory not found: {config.input_path}")
            return errors

        if not config.input_path.is_dir():
            errors.append(f"Input path is not a directory: {config.input_path}")
            return errors

        # Check for image files in input directory
        image_files = self._find_image_files(
            config.input_path, config.supported_extensions
        )
        if not image_files:
            errors.append(f"No supported image files found in: {config.input_path}")

        # Validate output directory can be created
        try:
            config.output_dir.mkdir(parents=True, exist_ok=True)
            if not config.output_dir.is_dir():
                errors.append(
                    f"Output directory exists but is not a directory: {config.output_dir}"
                )
        except PermissionError:
            errors.append(
                f"Permission denied creating output directory: {config.output_dir}"
            )
        except Exception as e:
            errors.append(f"Cannot create output directory {config.output_dir}: {e}")

        # Validate processed file is accessible
        if config.processed_file.exists():
            if not config.processed_file.is_file():
                errors.append(
                    f"Processed file exists but is not a file: {config.processed_file}"
                )
            else:
                try:
                    with open(config.processed_file, "r", encoding="utf-8") as f:
                        f.read(1)  # Test read access
                except PermissionError:
                    errors.append(
                        f"Permission denied reading processed file: {config.processed_file}"
                    )
                except Exception as e:
                    errors.append(
                        f"Cannot read processed file {config.processed_file}: {e}"
                    )

        # Check if output directory is not the same as input
        if config.output_dir.resolve() == config.input_path.resolve():
            errors.append("Output directory cannot be the same as input directory")

        # Warn about potential file overwrites
        if not config.force_overwrite and config.output_dir.exists():
            existing_files = list(config.output_dir.glob("*"))
            if existing_files:
                errors.append(
                    f"Output directory contains {len(existing_files)} files. "
                    "Use --force-overwrite to proceed anyway."
                )

        return errors

    def execute(self, config: ToolConfig) -> ToolResult:
        """Execute the batch renaming operation."""
        if not isinstance(config, BatchRenamerConfig):
            return ToolResult(
                success=False,
                message=f"Invalid config type: expected BatchRenamerConfig, got {type(config)}",
                error_code="INVALID_CONFIG",
            )

        start_time = time.time()
        renamed_files = []
        failed_files = []

        try:
            logger.info(f"Starting batch rename operation on {config.input_path}")

            # Load processed file history
            self._load_processed_file(config)

            # Find and sort image files
            image_files = self._find_image_files(
                config.input_path, config.supported_extensions
            )
            if not image_files:
                return ToolResult(
                    success=False,
                    message="No supported image files found in input directory",
                    error_code="NO_FILES_FOUND",
                )

            # Sort files alphanumerically for consistent ordering
            image_files.sort(key=lambda x: x.name.lower())

            logger.info(f"Found {len(image_files)} image files to process")

            # Determine starting date and index
            current_date = self._get_current_date(config)
            starting_index = self._get_next_index(current_date)

            logger.info(
                f"Using date: {current_date}, starting index: {starting_index:09d}"
            )

            # Ensure output directory exists (only if not dry run)
            if not config.dry_run:
                config.output_dir.mkdir(parents=True, exist_ok=True)

            # Process each file
            for i, image_file in enumerate(image_files):
                try:
                    new_filename = self._generate_filename(
                        config, current_date, starting_index + i, image_file
                    )

                    output_path = config.output_dir / new_filename

                    # Check for overwrites
                    if output_path.exists() and not config.force_overwrite:
                        failed_files.append(
                            {
                                "file": image_file,
                                "error": f"Output file exists: {output_path}",
                                "new_name": new_filename,
                            }
                        )
                        continue

                    # Copy/move file to new location
                    if config.verbose:
                        logger.info(f"Renaming {image_file.name} -> {new_filename}")

                    if not config.dry_run:
                        # Copy file to output directory
                        shutil.copy2(image_file, output_path)

                        # Update processed file
                        self._add_processed_entry(new_filename, config.processed_file)

                    renamed_files.append(
                        {
                            "original": image_file,
                            "new_path": output_path,
                            "new_name": new_filename,
                        }
                    )

                except Exception as e:
                    error_msg = f"Failed to rename {image_file.name}: {e}"
                    logger.error(error_msg)
                    failed_files.append(
                        {"file": image_file, "error": str(e), "new_name": None}
                    )

            # Delete original files if requested and all operations were successful
            if (
                config.delete_originals
                and not config.dry_run
                and not failed_files
                and len(renamed_files) == len(image_files)
            ):

                logger.info("Deleting original files...")
                for file_info in renamed_files:
                    try:
                        file_info["original"].unlink()
                        if config.verbose:
                            logger.info(
                                f"Deleted original: {file_info['original'].name}"
                            )
                    except Exception as e:
                        logger.warning(f"Failed to delete {file_info['original']}: {e}")

            execution_time = time.time() - start_time

            # Generate result summary
            success_count = len(renamed_files)
            failure_count = len(failed_files)

            if failure_count == 0:
                success_message = (
                    f"Successfully renamed {success_count} files "
                    f"in {execution_time:.2f}s"
                )
            else:
                success_message = (
                    f"Renamed {success_count} files, {failure_count} failed "
                    f"in {execution_time:.2f}s"
                )

            logger.info(success_message)

            return ToolResult(
                success=failure_count == 0,
                message=success_message,
                output_files=[info["new_path"] for info in renamed_files],
                metadata={
                    "files_renamed": success_count,
                    "files_failed": failure_count,
                    "date_used": current_date,
                    "starting_index": starting_index,
                    "ending_index": (
                        starting_index + success_count - 1
                        if success_count > 0
                        else starting_index
                    ),
                    "dry_run": config.dry_run,
                    "deleted_originals": config.delete_originals and not config.dry_run,
                    "failed_files": failed_files,
                    "processing_time_ms": execution_time * 1000,
                    "naming_pattern": config.naming_pattern,
                    "processed_file_updated": not config.dry_run,
                },
                execution_time=execution_time,
                error_code="PARTIAL_FAILURE" if failure_count > 0 else None,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Batch rename operation failed: {e}"
            logger.error(error_msg, exc_info=True)

            return ToolResult(
                success=False,
                message=error_msg,
                output_files=[info["new_path"] for info in renamed_files],
                metadata={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "files_completed": len(renamed_files),
                    "files_failed": len(failed_files),
                    "partial_results": len(renamed_files),
                },
                execution_time=execution_time,
                error_code="PROCESSING_ERROR",
            )

    def _find_image_files(
        self, directory: Path, supported_extensions: Set[str]
    ) -> List[Path]:
        """Find all supported image files in the directory."""
        image_files = []

        for file_path in directory.iterdir():
            if file_path.is_file():
                file_ext = file_path.suffix.lower()
                if file_ext in supported_extensions:
                    image_files.append(file_path)

        return image_files

    def _load_processed_file(self, config: BatchRenamerConfig) -> None:
        """Load the processed file history."""
        self._processed_entries = []

        if not config.processed_file.exists():
            logger.info(
                f"Processed file not found, starting fresh: {config.processed_file}"
            )
            return

        try:
            with open(config.processed_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Clean and store entries
            self._processed_entries = [line.strip() for line in lines if line.strip()]

            logger.info(
                f"Loaded {len(self._processed_entries)} entries from processed file"
            )

        except Exception as e:
            logger.warning(
                f"Failed to load processed file {config.processed_file}: {e}"
            )
            self._processed_entries = []

    def _get_current_date(self, config: BatchRenamerConfig) -> str:
        """Get the current date for naming."""
        if config.use_current_date:
            return datetime.now().strftime(config.date_format)

        # Try to parse date from the last processed entry
        if self._processed_entries:
            last_entry = self._processed_entries[-1]
            date_match = self._extract_date_from_filename(
                last_entry, config.date_format
            )
            if date_match:
                return date_match

        # Fallback to current date
        return datetime.now().strftime(config.date_format)

    def _extract_date_from_filename(
        self, filename: str, date_format: str
    ) -> Optional[str]:
        """Extract date from a filename using the date format."""
        # Simple approach for common date formats
        if date_format == "%Y-%m-%d":
            # Look for YYYY-MM-DD pattern
            match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
            if match:
                try:
                    date_str = match.group(1)
                    # Validate the date
                    parsed_date = datetime.strptime(date_str, date_format)
                    return parsed_date.strftime(date_format)
                except ValueError:
                    pass
        elif date_format == "%Y%m%d":
            # Look for YYYYMMDD pattern
            match = re.search(r"(\d{8})", filename)
            if match:
                try:
                    date_str = match.group(1)
                    # Validate the date
                    parsed_date = datetime.strptime(date_str, date_format)
                    return parsed_date.strftime(date_format)
                except ValueError:
                    pass

        # Generic approach for other formats
        try:
            # Create a regex pattern from the date format
            date_pattern_map = {
                "%Y": r"(\d{4})",
                "%m": r"(\d{2})",
                "%d": r"(\d{2})",
                "%H": r"(\d{2})",
                "%M": r"(\d{2})",
                "%S": r"(\d{2})",
            }

            # Convert strftime format to regex
            regex_pattern = date_format
            for fmt_code, regex_part in date_pattern_map.items():
                regex_pattern = regex_pattern.replace(fmt_code, regex_part)

            # Look for the pattern in the filename
            match = re.search(regex_pattern, filename)
            if match:
                matched_text = match.group(0)
                parsed_date = datetime.strptime(matched_text, date_format)
                return parsed_date.strftime(date_format)
        except (ValueError, AttributeError):
            pass

        return None

    def _get_next_index(self, current_date: str) -> int:
        """Get the next available index for the given date."""
        if not self._processed_entries:
            return 1

        max_index = 0
        pattern = f"{current_date}_"

        for entry in self._processed_entries:
            if entry.startswith(pattern):
                # Extract index from filename
                match = re.search(f"{re.escape(pattern)}(\\d+)", entry)
                if match:
                    index = int(match.group(1))
                    max_index = max(max_index, index)

        return max_index + 1

    def _generate_filename(
        self, config: BatchRenamerConfig, date: str, index: int, original_file: Path
    ) -> str:
        """Generate new filename based on the naming pattern."""
        # Get file extension
        if config.preserve_original_extension:
            extension = original_file.suffix
        else:
            extension = ".jpg"  # Default extension

        # Generate base filename without extension
        base_name = config.naming_pattern.format(date=date, index=index)

        return f"{base_name}{extension}"

    def _add_processed_entry(self, filename: str, processed_file: Path) -> None:
        """Add a new entry to the processed file."""
        try:
            with open(processed_file, "a", encoding="utf-8") as f:
                f.write(f"{filename}\n")

            # Also add to in-memory list
            self._processed_entries.append(filename)

        except Exception as e:
            logger.error(f"Failed to update processed file {processed_file}: {e}")
            raise ProcessingError(f"Cannot update processed file: {e}")

    def setup(self) -> None:
        """Setup the batch renaming tool."""
        super().setup()
        logger.debug("BatchRenamerTool setup completed")

    def cleanup(self) -> None:
        """Cleanup resources after execution."""
        # Clear cached data
        self._processed_entries = []
        self._last_index = 0
        self._current_date = ""
        super().cleanup()
        logger.debug("BatchRenamerTool cleanup completed")
