"""Validation utilities and decorators for ReTileUp.

This module provides comprehensive validation decorators, custom validators, and utility
functions for structured input validation throughout the ReTileUp framework.
It includes both the original validation utilities and enhanced decorators for
comprehensive parameter validation.
"""

import functools
import inspect
import logging
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel, ValidationError as PydanticValidationError

from ..core.exceptions import ValidationError, ErrorCode, validation_error

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


# Original ValidationResult class (preserved for compatibility)
class ValidationResult:
    """Result of a validation operation."""

    def __init__(self, is_valid: bool, errors: Optional[List[str]] = None) -> None:
        """Initialize validation result.

        Args:
            is_valid: Whether the validation passed
            errors: List of validation error messages
        """
        self.is_valid = is_valid
        self.errors = errors or []

    def __bool__(self) -> bool:
        """Return True if validation passed."""
        return self.is_valid

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        self.is_valid = False

    def merge(self, other: "ValidationResult") -> None:
        """Merge another validation result into this one."""
        if not other.is_valid:
            self.is_valid = False
            self.errors.extend(other.errors)


# Enhanced validation decorators and utilities
def validate_input(**validators: Callable[[Any], bool]) -> Callable[[F], F]:
    """Decorator for validating function input parameters.

    This decorator applies validation functions to specified parameters
    before the decorated function is called. If validation fails, a
    ValidationError is raised with detailed information.

    Args:
        **validators: Mapping of parameter names to validation functions

    Returns:
        Decorated function with input validation

    Example:
        @validate_input(
            width=lambda x: x > 0,
            height=lambda x: x > 0,
            path=lambda x: Path(x).exists()
        )
        def process_image(width: int, height: int, path: Path) -> bool:
            # Function implementation
            return True
    """
    def decorator(func: F) -> F:
        sig = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Bind arguments to parameter names
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Validate each specified parameter
            for param_name, validator in validators.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    try:
                        if not validator(value):
                            raise validation_error(
                                f"Validation failed for parameter '{param_name}'",
                                field_name=param_name,
                                invalid_value=value,
                            )
                    except Exception as e:
                        if isinstance(e, ValidationError):
                            raise
                        raise validation_error(
                            f"Validation error for parameter '{param_name}': {str(e)}",
                            field_name=param_name,
                            invalid_value=value,
                            cause=e,
                        ) from e

            return func(*args, **kwargs)

        return wrapper
    return decorator


def validate_config(config_class: Type[BaseModel]) -> Callable[[F], F]:
    """Decorator for validating configuration objects using Pydantic.

    This decorator validates that the first argument of the decorated function
    is a valid instance of the specified Pydantic model class.

    Args:
        config_class: Pydantic model class for validation

    Returns:
        Decorated function with configuration validation

    Example:
        @validate_config(MyToolConfig)
        def execute_tool(config: MyToolConfig) -> ToolResult:
            # Function implementation
            return ToolResult(success=True, message="Done")
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if args:
                config = args[0]
                if not isinstance(config, config_class):
                    # Try to validate/convert if it's a dict
                    if isinstance(config, dict):
                        try:
                            config = config_class(**config)
                            args = (config,) + args[1:]
                        except PydanticValidationError as e:
                            raise validation_error(
                                f"Configuration validation failed: {str(e)}",
                                cause=e,
                            ) from e
                    else:
                        raise validation_error(
                            f"Expected {config_class.__name__} instance, got {type(config).__name__}",
                            invalid_value=type(config).__name__,
                        )

            return func(*args, **kwargs)

        return wrapper
    return decorator


def validate_file_path(
    must_exist: bool = True,
    must_be_file: bool = True,
    readable: bool = True,
    writable: bool = False,
) -> Callable[[Path], bool]:
    """Create a file path validator with specific requirements.

    Args:
        must_exist: Whether the path must exist
        must_be_file: Whether the path must be a file (not directory)
        readable: Whether the file must be readable
        writable: Whether the file must be writable

    Returns:
        Validation function for file paths
    """
    def validator(path: Union[str, Path]) -> bool:
        try:
            path = Path(path)

            if must_exist and not path.exists():
                return False

            if path.exists():
                if must_be_file and not path.is_file():
                    return False

                # Check permissions on existing files
                if readable and not path.readable():
                    return False

                if writable and not path.writable():
                    return False

            return True

        except (OSError, ValueError):
            return False

    return validator


def validate_image_file(
    supported_formats: Optional[List[str]] = None,
    max_size_mb: Optional[float] = None,
) -> Callable[[Path], bool]:
    """Create an image file validator with format and size constraints.

    Args:
        supported_formats: List of supported image formats (e.g., ['PNG', 'JPEG'])
        max_size_mb: Maximum file size in megabytes

    Returns:
        Validation function for image files
    """
    def validator(path: Union[str, Path]) -> bool:
        try:
            from PIL import Image

            path = Path(path)

            # Basic file validation
            if not path.exists() or not path.is_file():
                return False

            # Size validation
            if max_size_mb is not None:
                file_size_mb = path.stat().st_size / (1024 * 1024)
                if file_size_mb > max_size_mb:
                    return False

            # Format validation
            if supported_formats is not None:
                try:
                    with Image.open(path) as img:
                        img_format = img.format
                        if img_format not in supported_formats:
                            return False
                except Exception:
                    return False

            return True

        except Exception:
            return False

    return validator


def validate_positive_number(value: Union[int, float]) -> bool:
    """Validate that a number is positive.

    Args:
        value: Number to validate

    Returns:
        True if the number is positive, False otherwise
    """
    try:
        return isinstance(value, (int, float)) and value > 0
    except (TypeError, ValueError):
        return False


def validate_non_negative_number(value: Union[int, float]) -> bool:
    """Validate that a number is non-negative.

    Args:
        value: Number to validate

    Returns:
        True if the number is non-negative, False otherwise
    """
    try:
        return isinstance(value, (int, float)) and value >= 0
    except (TypeError, ValueError):
        return False


def validate_in_range(
    min_value: Union[int, float],
    max_value: Union[int, float],
    inclusive: bool = True,
) -> Callable[[Union[int, float]], bool]:
    """Create a range validator for numeric values.

    Args:
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        inclusive: Whether the range is inclusive of endpoints

    Returns:
        Validation function for range checking
    """
    def validator(value: Union[int, float]) -> bool:
        try:
            if not isinstance(value, (int, float)):
                return False

            if inclusive:
                return min_value <= value <= max_value
            else:
                return min_value < value < max_value

        except (TypeError, ValueError):
            return False

    return validator


def validate_coordinates(coordinates: List[tuple]) -> bool:
    """Validate a list of coordinate tuples.

    Args:
        coordinates: List of (x, y) coordinate tuples

    Returns:
        True if all coordinates are valid, False otherwise
    """
    try:
        if not isinstance(coordinates, list) or not coordinates:
            return False

        for coord in coordinates:
            if (
                not isinstance(coord, (tuple, list)) or
                len(coord) != 2 or
                not all(isinstance(x, (int, float)) for x in coord) or
                any(x < 0 for x in coord)
            ):
                return False

        return True

    except (TypeError, ValueError):
        return False


class ValidationContext:
    """Context manager for collecting validation errors."""

    def __init__(self) -> None:
        """Initialize validation context."""
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def add_error(self, message: str, field_name: Optional[str] = None) -> None:
        """Add a validation error.

        Args:
            message: Error message
            field_name: Optional field name that failed validation
        """
        if field_name:
            self.errors.append(f"{field_name}: {message}")
        else:
            self.errors.append(message)

    def add_warning(self, message: str, field_name: Optional[str] = None) -> None:
        """Add a validation warning.

        Args:
            message: Warning message
            field_name: Optional field name for the warning
        """
        if field_name:
            self.warnings.append(f"{field_name}: {message}")
        else:
            self.warnings.append(message)

    def has_errors(self) -> bool:
        """Check if there are any validation errors.

        Returns:
            True if there are errors, False otherwise
        """
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any validation warnings.

        Returns:
            True if there are warnings, False otherwise
        """
        return len(self.warnings) > 0

    def get_error_summary(self) -> str:
        """Get a summary of all validation errors.

        Returns:
            Formatted error summary string
        """
        if not self.errors:
            return "No validation errors"

        return f"Validation failed with {len(self.errors)} error(s):\n" + "\n".join(
            f"  - {error}" for error in self.errors
        )

    def raise_if_errors(self) -> None:
        """Raise ValidationError if there are any errors.

        Raises:
            ValidationError: If validation errors exist
        """
        if self.has_errors():
            raise validation_error(
                self.get_error_summary(),
                field_name="validation_context",
            )

    def __enter__(self) -> 'ValidationContext':
        """Enter the validation context."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the validation context."""
        if exc_type is None and self.has_errors():
            # If no exception occurred but we have errors, raise them
            self.raise_if_errors()


# Original ValidationUtils class (preserved and enhanced)
class ValidationUtils:
    """Utility class for validation operations."""

    @staticmethod
    def validate_file_path(
        path: Union[str, Path],
        must_exist: bool = True,
        extensions: Optional[List[str]] = None
    ) -> ValidationResult:
        """Validate a file path.

        Args:
            path: Path to validate
            must_exist: Whether the file must exist
            extensions: Allowed file extensions (with or without dots)

        Returns:
            ValidationResult
        """
        result = ValidationResult(True)
        path = Path(path)

        # Check if file exists
        if must_exist and not path.exists():
            result.add_error(f"File does not exist: {path}")
            return result

        # Check if it's a file (not directory)
        if path.exists() and not path.is_file():
            result.add_error(f"Path is not a file: {path}")

        # Check file extension
        if extensions:
            # Normalize extensions (ensure they start with dots)
            normalized_extensions = []
            for ext in extensions:
                if not ext.startswith('.'):
                    ext = '.' + ext
                normalized_extensions.append(ext.lower())

            if path.suffix.lower() not in normalized_extensions:
                result.add_error(
                    f"Invalid file extension: {path.suffix}. "
                    f"Allowed: {', '.join(normalized_extensions)}"
                )

        return result

    @staticmethod
    def validate_directory_path(
        path: Union[str, Path],
        must_exist: bool = True,
        create_if_missing: bool = False
    ) -> ValidationResult:
        """Validate a directory path.

        Args:
            path: Path to validate
            must_exist: Whether the directory must exist
            create_if_missing: Whether to create the directory if it doesn't exist

        Returns:
            ValidationResult
        """
        result = ValidationResult(True)
        path = Path(path)

        if not path.exists():
            if must_exist and not create_if_missing:
                result.add_error(f"Directory does not exist: {path}")
            elif create_if_missing:
                try:
                    path.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    result.add_error(f"Cannot create directory {path}: {e}")
        elif not path.is_dir():
            result.add_error(f"Path is not a directory: {path}")

        return result

    @staticmethod
    def validate_image_size(
        width: int,
        height: int,
        min_width: int = 1,
        min_height: int = 1,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None
    ) -> ValidationResult:
        """Validate image dimensions.

        Args:
            width: Image width
            height: Image height
            min_width: Minimum allowed width
            min_height: Minimum allowed height
            max_width: Maximum allowed width (None for no limit)
            max_height: Maximum allowed height (None for no limit)

        Returns:
            ValidationResult
        """
        result = ValidationResult(True)

        if width < min_width:
            result.add_error(f"Width {width} is less than minimum {min_width}")

        if height < min_height:
            result.add_error(f"Height {height} is less than minimum {min_height}")

        if max_width is not None and width > max_width:
            result.add_error(f"Width {width} exceeds maximum {max_width}")

        if max_height is not None and height > max_height:
            result.add_error(f"Height {height} exceeds maximum {max_height}")

        return result

    @staticmethod
    def validate_numeric_range(
        value: Union[int, float],
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        value_name: str = "value"
    ) -> ValidationResult:
        """Validate that a numeric value is within a specified range.

        Args:
            value: Value to validate
            min_value: Minimum allowed value (None for no minimum)
            max_value: Maximum allowed value (None for no maximum)
            value_name: Name of the value for error messages

        Returns:
            ValidationResult
        """
        result = ValidationResult(True)

        if min_value is not None and value < min_value:
            result.add_error(f"{value_name} {value} is less than minimum {min_value}")

        if max_value is not None and value > max_value:
            result.add_error(f"{value_name} {value} exceeds maximum {max_value}")

        return result

    @staticmethod
    def validate_percentage(value: Union[int, float], value_name: str = "percentage") -> ValidationResult:
        """Validate a percentage value (0-100).

        Args:
            value: Percentage value to validate
            value_name: Name of the value for error messages

        Returns:
            ValidationResult
        """
        return ValidationUtils.validate_numeric_range(
            value, 0, 100, value_name
        )

    @staticmethod
    def validate_string_pattern(
        value: str,
        pattern: str,
        value_name: str = "value"
    ) -> ValidationResult:
        """Validate that a string matches a regular expression pattern.

        Args:
            value: String to validate
            pattern: Regular expression pattern
            value_name: Name of the value for error messages

        Returns:
            ValidationResult
        """
        result = ValidationResult(True)

        try:
            if not re.match(pattern, value):
                result.add_error(f"{value_name} '{value}' does not match required pattern")
        except re.error as e:
            result.add_error(f"Invalid pattern '{pattern}': {e}")

        return result

    @staticmethod
    def validate_choice(
        value: Any,
        choices: List[Any],
        value_name: str = "value"
    ) -> ValidationResult:
        """Validate that a value is one of the allowed choices.

        Args:
            value: Value to validate
            choices: List of allowed values
            value_name: Name of the value for error messages

        Returns:
            ValidationResult
        """
        result = ValidationResult(True)

        if value not in choices:
            result.add_error(
                f"{value_name} '{value}' is not valid. "
                f"Allowed values: {', '.join(str(c) for c in choices)}"
            )

        return result

    @staticmethod
    def validate_pydantic_model(
        data: Dict[str, Any],
        model_class: Type[BaseModel]
    ) -> ValidationResult:
        """Validate data against a Pydantic model.

        Args:
            data: Data to validate
            model_class: Pydantic model class

        Returns:
            ValidationResult
        """
        result = ValidationResult(True)

        try:
            model_class(**data)
        except PydanticValidationError as e:
            for error in e.errors():
                field_path = " -> ".join(str(loc) for loc in error["loc"])
                result.add_error(f"{field_path}: {error['msg']}")

        return result

    @staticmethod
    def validate_workflow_parameters(
        parameters: Dict[str, Any],
        required_params: Optional[List[str]] = None,
        optional_params: Optional[List[str]] = None
    ) -> ValidationResult:
        """Validate workflow parameters.

        Args:
            parameters: Parameters dictionary
            required_params: List of required parameter names
            optional_params: List of optional parameter names

        Returns:
            ValidationResult
        """
        result = ValidationResult(True)
        required_params = required_params or []
        optional_params = optional_params or []

        # Check required parameters
        for param in required_params:
            if param not in parameters:
                result.add_error(f"Required parameter missing: {param}")

        # Check for unknown parameters
        if required_params or optional_params:
            allowed_params = set(required_params + optional_params)
            for param in parameters:
                if param not in allowed_params:
                    result.add_error(f"Unknown parameter: {param}")

        return result

    @staticmethod
    def validate_image_format(format_name: str, supported_formats: List[str]) -> ValidationResult:
        """Validate an image format.

        Args:
            format_name: Image format to validate
            supported_formats: List of supported formats

        Returns:
            ValidationResult
        """
        result = ValidationResult(True)

        # Normalize format names to uppercase
        format_upper = format_name.upper()
        supported_upper = [fmt.upper() for fmt in supported_formats]

        if format_upper not in supported_upper:
            result.add_error(
                f"Unsupported image format: {format_name}. "
                f"Supported formats: {', '.join(supported_formats)}"
            )

        return result

    @staticmethod
    def validate_color_value(
        color: Union[str, tuple, int],
        allow_transparency: bool = False
    ) -> ValidationResult:
        """Validate a color value.

        Args:
            color: Color value (hex string, RGB tuple, or int)
            allow_transparency: Whether to allow RGBA values

        Returns:
            ValidationResult
        """
        result = ValidationResult(True)

        if isinstance(color, str):
            # Hex color validation
            if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
                if allow_transparency and re.match(r'^#[0-9A-Fa-f]{8}$', color):
                    pass  # Valid RGBA hex
                else:
                    result.add_error(f"Invalid hex color: {color}")

        elif isinstance(color, tuple):
            # RGB/RGBA tuple validation
            if len(color) == 3:
                # RGB
                for i, component in enumerate(color):
                    if not isinstance(component, int) or not 0 <= component <= 255:
                        result.add_error(f"Invalid RGB component {i}: {component}")
            elif len(color) == 4 and allow_transparency:
                # RGBA
                for i, component in enumerate(color):
                    if not isinstance(component, int) or not 0 <= component <= 255:
                        result.add_error(f"Invalid RGBA component {i}: {component}")
            else:
                expected = "RGB or RGBA" if allow_transparency else "RGB"
                result.add_error(f"Invalid color tuple length. Expected {expected}")

        elif isinstance(color, int):
            # Single int (grayscale)
            if not 0 <= color <= 255:
                result.add_error(f"Invalid grayscale value: {color}")

        else:
            result.add_error(f"Invalid color type: {type(color)}")

        return result


# Pre-defined common validators for use with decorators
COMMON_VALIDATORS = {
    'positive_int': lambda x: isinstance(x, int) and x > 0,
    'non_negative_int': lambda x: isinstance(x, int) and x >= 0,
    'positive_float': lambda x: isinstance(x, (int, float)) and x > 0,
    'non_negative_float': lambda x: isinstance(x, (int, float)) and x >= 0,
    'non_empty_string': lambda x: isinstance(x, str) and len(x.strip()) > 0,
    'valid_path': validate_file_path(must_exist=False),
    'existing_file': validate_file_path(must_exist=True, must_be_file=True),
    'existing_dir': lambda x: Path(x).exists() and Path(x).is_dir(),
    'image_file': validate_image_file(),
    'coordinates': validate_coordinates,
}


def batch_validate(
    validators: Dict[str, Callable[[Any], bool]],
    data: Dict[str, Any],
    raise_on_error: bool = True,
) -> ValidationContext:
    """Perform batch validation on a data dictionary.

    Args:
        validators: Mapping of field names to validation functions
        data: Data dictionary to validate
        raise_on_error: Whether to raise exception on validation errors

    Returns:
        ValidationContext with results

    Raises:
        ValidationError: If validation fails and raise_on_error is True
    """
    context = ValidationContext()

    for field_name, validator in validators.items():
        if field_name in data:
            value = data[field_name]
            try:
                if not validator(value):
                    context.add_error(f"Validation failed for value: {value}", field_name)
            except Exception as e:
                context.add_error(f"Validator error: {str(e)}", field_name)
        else:
            context.add_warning(f"Field not present in data", field_name)

    if raise_on_error:
        context.raise_if_errors()

    return context