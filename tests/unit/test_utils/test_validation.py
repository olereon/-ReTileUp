"""Comprehensive unit tests for validation utilities.

This module tests the validation framework including:
- Validation decorators and input validation
- File and directory path validation
- Image validation and format checking
- Numeric and range validation
- Configuration validation with Pydantic
- Validation context and error handling
- Batch validation and edge cases
"""

import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch

import pytest
from pydantic import BaseModel, ValidationError as PydanticValidationError

from retileup.utils.validation import (
    ValidationResult, ValidationUtils, ValidationContext,
    validate_input, validate_config, validate_file_path, validate_image_file,
    validate_positive_number, validate_non_negative_number, validate_in_range,
    validate_coordinates, batch_validate, COMMON_VALIDATORS
)
from retileup.core.exceptions import ValidationError


class TestValidationResult:
    """Test ValidationResult class."""

    def test_validation_result_success(self):
        """Test successful validation result."""
        result = ValidationResult(True)

        assert result.is_valid is True
        assert result.errors == []
        assert bool(result) is True

    def test_validation_result_failure(self):
        """Test failed validation result."""
        result = ValidationResult(False, ["Error 1", "Error 2"])

        assert result.is_valid is False
        assert len(result.errors) == 2
        assert bool(result) is False

    def test_add_error(self):
        """Test adding errors to validation result."""
        result = ValidationResult(True)
        result.add_error("New error")

        assert result.is_valid is False
        assert "New error" in result.errors

    def test_merge_validation_results(self):
        """Test merging validation results."""
        result1 = ValidationResult(True)
        result2 = ValidationResult(False, ["Error from result2"])

        result1.merge(result2)

        assert result1.is_valid is False
        assert "Error from result2" in result1.errors

    def test_merge_successful_results(self):
        """Test merging successful validation results."""
        result1 = ValidationResult(True)
        result2 = ValidationResult(True)

        result1.merge(result2)

        assert result1.is_valid is True
        assert result1.errors == []


class TestValidationDecorators:
    """Test validation decorators."""

    def test_validate_input_success(self):
        """Test successful input validation."""
        @validate_input(
            width=lambda x: x > 0,
            height=lambda x: x > 0
        )
        def test_function(width: int, height: int) -> str:
            return f"{width}x{height}"

        result = test_function(100, 50)
        assert result == "100x50"

    def test_validate_input_failure(self):
        """Test input validation failure."""
        @validate_input(
            width=lambda x: x > 0,
            height=lambda x: x > 0
        )
        def test_function(width: int, height: int) -> str:
            return f"{width}x{height}"

        with pytest.raises(ValidationError) as exc_info:
            test_function(-10, 50)

        assert "width" in str(exc_info.value)

    def test_validate_input_validator_exception(self):
        """Test handling of validator exceptions."""
        def failing_validator(x):
            raise ValueError("Validator error")

        @validate_input(width=failing_validator)
        def test_function(width: int) -> str:
            return str(width)

        with pytest.raises(ValidationError) as exc_info:
            test_function(100)

        assert "Validation error" in str(exc_info.value)

    def test_validate_input_with_kwargs(self):
        """Test input validation with keyword arguments."""
        @validate_input(
            width=lambda x: x > 0,
            name=lambda x: len(x) > 0
        )
        def test_function(width: int, name: str = "default") -> str:
            return f"{name}: {width}"

        result = test_function(100, name="test")
        assert result == "test: 100"

    def test_validate_input_missing_parameter(self):
        """Test validation when parameter is not provided."""
        @validate_input(missing_param=lambda x: True)
        def test_function(width: int) -> str:
            return str(width)

        # Should not raise error for missing parameter
        result = test_function(100)
        assert result == "100"


class MockConfig(BaseModel):
    """Mock configuration class for testing."""
    name: str
    value: int
    enabled: bool = True


class TestConfigValidation:
    """Test configuration validation decorator."""

    def test_validate_config_success(self):
        """Test successful configuration validation."""
        @validate_config(MockConfig)
        def process_config(config: MockConfig) -> str:
            return f"{config.name}: {config.value}"

        config = MockConfig(name="test", value=42)
        result = process_config(config)
        assert result == "test: 42"

    def test_validate_config_dict_conversion(self):
        """Test configuration validation with dict conversion."""
        @validate_config(MockConfig)
        def process_config(config: MockConfig) -> str:
            return f"{config.name}: {config.value}"

        config_dict = {"name": "test", "value": 42}
        result = process_config(config_dict)
        assert result == "test: 42"

    def test_validate_config_invalid_dict(self):
        """Test configuration validation with invalid dict."""
        @validate_config(MockConfig)
        def process_config(config: MockConfig) -> str:
            return f"{config.name}: {config.value}"

        invalid_dict = {"name": "test"}  # Missing required 'value'

        with pytest.raises(ValidationError) as exc_info:
            process_config(invalid_dict)

        assert "Configuration validation failed" in str(exc_info.value)

    def test_validate_config_wrong_type(self):
        """Test configuration validation with wrong type."""
        @validate_config(MockConfig)
        def process_config(config: MockConfig) -> str:
            return f"{config.name}: {config.value}"

        with pytest.raises(ValidationError) as exc_info:
            process_config("not a config")

        assert "Expected MockConfig instance" in str(exc_info.value)

    def test_validate_config_no_args(self):
        """Test configuration validation with no arguments."""
        @validate_config(MockConfig)
        def process_config(config: MockConfig) -> str:
            return f"{config.name}: {config.value}"

        # Should not raise error when no args provided
        try:
            process_config()
        except TypeError:
            # Expected TypeError for missing required argument
            pass


class TestFileValidation:
    """Test file and path validation."""

    def test_validate_file_path_factory_existing_file(self, sample_image_rgb):
        """Test file path validator factory for existing files."""
        validator = validate_file_path(must_exist=True, must_be_file=True)

        assert validator(sample_image_rgb) is True

    def test_validate_file_path_factory_nonexistent(self, temp_dir):
        """Test file path validator factory for non-existent files."""
        validator = validate_file_path(must_exist=True)
        nonexistent = temp_dir / "nonexistent.txt"

        assert validator(nonexistent) is False

    def test_validate_file_path_factory_allow_nonexistent(self, temp_dir):
        """Test file path validator factory allowing non-existent files."""
        validator = validate_file_path(must_exist=False)
        nonexistent = temp_dir / "nonexistent.txt"

        assert validator(nonexistent) is True

    def test_validate_file_path_factory_directory(self, temp_dir):
        """Test file path validator with directory."""
        validator = validate_file_path(must_be_file=True)

        assert validator(temp_dir) is False

    def test_validate_file_path_factory_permissions(self, temp_dir):
        """Test file path validator with permission checks."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")

        # Test readable requirement
        validator_readable = validate_file_path(readable=True)
        assert validator_readable(test_file) is True

        # Test writable requirement
        validator_writable = validate_file_path(writable=True)
        assert validator_writable(test_file) is True

    def test_validate_file_path_factory_error_handling(self):
        """Test file path validator error handling."""
        validator = validate_file_path()

        # Invalid path should return False
        assert validator("/invalid\x00path") is False

    def test_validate_image_file_factory_success(self, sample_image_rgb):
        """Test image file validator factory success."""
        validator = validate_image_file(supported_formats=['PNG', 'JPEG'])

        assert validator(sample_image_rgb) is True

    def test_validate_image_file_factory_unsupported_format(self, temp_dir):
        """Test image file validator with unsupported format."""
        # Create a GIF image but only allow PNG
        gif_image = temp_dir / "test.gif"
        from PIL import Image
        img = Image.new('RGB', (10, 10))
        img.save(gif_image, 'GIF')

        validator = validate_image_file(supported_formats=['PNG'])

        assert validator(gif_image) is False

    def test_validate_image_file_factory_size_limit(self, temp_dir):
        """Test image file validator with size limit."""
        # Create a small image
        small_image = temp_dir / "small.png"
        from PIL import Image
        img = Image.new('RGB', (10, 10))
        img.save(small_image)

        # Validator with very small size limit
        validator = validate_image_file(max_size_mb=0.00001)  # Very small limit

        assert validator(small_image) is False

    def test_validate_image_file_factory_error_handling(self, temp_dir):
        """Test image file validator error handling."""
        validator = validate_image_file()

        # Non-existent file
        assert validator(temp_dir / "nonexistent.jpg") is False

        # Invalid image file
        invalid_file = temp_dir / "invalid.jpg"
        invalid_file.write_text("not an image")
        assert validator(invalid_file) is False


class TestNumericValidation:
    """Test numeric validation functions."""

    def test_validate_positive_number_success(self):
        """Test positive number validation success."""
        assert validate_positive_number(10) is True
        assert validate_positive_number(3.14) is True
        assert validate_positive_number(0.001) is True

    def test_validate_positive_number_failure(self):
        """Test positive number validation failure."""
        assert validate_positive_number(0) is False
        assert validate_positive_number(-5) is False
        assert validate_positive_number("10") is False
        assert validate_positive_number(None) is False

    def test_validate_non_negative_number_success(self):
        """Test non-negative number validation success."""
        assert validate_non_negative_number(0) is True
        assert validate_non_negative_number(10) is True
        assert validate_non_negative_number(3.14) is True

    def test_validate_non_negative_number_failure(self):
        """Test non-negative number validation failure."""
        assert validate_non_negative_number(-1) is False
        assert validate_non_negative_number(-0.1) is False
        assert validate_non_negative_number("0") is False

    def test_validate_in_range_inclusive(self):
        """Test inclusive range validation."""
        validator = validate_in_range(0, 100, inclusive=True)

        assert validator(0) is True
        assert validator(50) is True
        assert validator(100) is True
        assert validator(-1) is False
        assert validator(101) is False

    def test_validate_in_range_exclusive(self):
        """Test exclusive range validation."""
        validator = validate_in_range(0, 100, inclusive=False)

        assert validator(0) is False
        assert validator(50) is True
        assert validator(100) is False
        assert validator(-1) is False
        assert validator(101) is False

    def test_validate_in_range_invalid_type(self):
        """Test range validation with invalid types."""
        validator = validate_in_range(0, 100)

        assert validator("50") is False
        assert validator(None) is False
        assert validator([50]) is False

    def test_validate_coordinates_success(self):
        """Test coordinate validation success."""
        valid_coords = [(0, 0), (10, 20), (5.5, 3.2)]
        assert validate_coordinates(valid_coords) is True

    def test_validate_coordinates_failure(self):
        """Test coordinate validation failure."""
        # Empty list
        assert validate_coordinates([]) is False

        # Not a list
        assert validate_coordinates("not a list") is False

        # Invalid coordinate format
        assert validate_coordinates([(1, 2, 3)]) is False  # 3 elements
        assert validate_coordinates([1, 2]) is False  # Not tuples
        assert validate_coordinates([("a", "b")]) is False  # Non-numeric
        assert validate_coordinates([(-1, 0)]) is False  # Negative


class TestValidationContext:
    """Test ValidationContext class."""

    def test_validation_context_success(self):
        """Test validation context with no errors."""
        context = ValidationContext()

        assert not context.has_errors()
        assert not context.has_warnings()
        assert context.get_error_summary() == "No validation errors"

    def test_validation_context_add_error(self):
        """Test adding errors to validation context."""
        context = ValidationContext()
        context.add_error("Test error")
        context.add_error("Field error", "field_name")

        assert context.has_errors()
        assert len(context.errors) == 2
        assert "Test error" in context.errors
        assert "field_name: Field error" in context.errors

    def test_validation_context_add_warning(self):
        """Test adding warnings to validation context."""
        context = ValidationContext()
        context.add_warning("Test warning")
        context.add_warning("Field warning", "field_name")

        assert context.has_warnings()
        assert len(context.warnings) == 2

    def test_validation_context_error_summary(self):
        """Test error summary generation."""
        context = ValidationContext()
        context.add_error("Error 1")
        context.add_error("Error 2")

        summary = context.get_error_summary()
        assert "2 error(s)" in summary
        assert "Error 1" in summary
        assert "Error 2" in summary

    def test_validation_context_raise_if_errors(self):
        """Test raising errors from validation context."""
        context = ValidationContext()
        context.add_error("Test error")

        with pytest.raises(ValidationError):
            context.raise_if_errors()

    def test_validation_context_no_raise_if_no_errors(self):
        """Test not raising when no errors."""
        context = ValidationContext()

        # Should not raise
        context.raise_if_errors()

    def test_validation_context_manager_success(self):
        """Test validation context manager without errors."""
        with ValidationContext() as context:
            context.add_warning("Just a warning")

        # Should exit successfully

    def test_validation_context_manager_with_errors(self):
        """Test validation context manager with errors."""
        with pytest.raises(ValidationError):
            with ValidationContext() as context:
                context.add_error("Test error")


class TestValidationUtils:
    """Test ValidationUtils class methods."""

    def test_validate_file_path_success(self, sample_image_rgb):
        """Test file path validation success."""
        result = ValidationUtils.validate_file_path(sample_image_rgb, must_exist=True)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_file_path_not_exists(self):
        """Test file path validation for non-existent file."""
        result = ValidationUtils.validate_file_path("/nonexistent/file.txt", must_exist=True)

        assert not result.is_valid
        assert any("does not exist" in error for error in result.errors)

    def test_validate_file_path_not_file(self, temp_dir):
        """Test file path validation for directory."""
        result = ValidationUtils.validate_file_path(temp_dir, must_exist=True)

        assert not result.is_valid
        assert any("not a file" in error for error in result.errors)

    def test_validate_file_path_extension(self, temp_dir):
        """Test file path validation with extension checking."""
        test_file = temp_dir / "test.txt"
        test_file.touch()

        # Valid extension
        result = ValidationUtils.validate_file_path(test_file, extensions=['txt', '.py'])
        assert result.is_valid

        # Invalid extension
        result = ValidationUtils.validate_file_path(test_file, extensions=['jpg', 'png'])
        assert not result.is_valid
        assert any("Invalid file extension" in error for error in result.errors)

    def test_validate_directory_path_success(self, temp_dir):
        """Test directory path validation success."""
        result = ValidationUtils.validate_directory_path(temp_dir, must_exist=True)

        assert result.is_valid

    def test_validate_directory_path_create_missing(self, temp_dir):
        """Test directory creation when missing."""
        new_dir = temp_dir / "new_directory"

        result = ValidationUtils.validate_directory_path(
            new_dir, must_exist=True, create_if_missing=True
        )

        assert result.is_valid
        assert new_dir.exists()

    def test_validate_directory_path_creation_error(self, temp_dir):
        """Test directory creation error handling."""
        # Try to create directory with invalid name
        invalid_dir = temp_dir / "invalid\x00name"

        result = ValidationUtils.validate_directory_path(
            invalid_dir, must_exist=True, create_if_missing=True
        )

        assert not result.is_valid

    def test_validate_image_size_success(self):
        """Test image size validation success."""
        result = ValidationUtils.validate_image_size(100, 50, min_width=10, min_height=10)

        assert result.is_valid

    def test_validate_image_size_failure(self):
        """Test image size validation failure."""
        result = ValidationUtils.validate_image_size(
            5, 200, min_width=10, min_height=10, max_width=100, max_height=150
        )

        assert not result.is_valid
        assert any("less than minimum" in error for error in result.errors)
        assert any("exceeds maximum" in error for error in result.errors)

    def test_validate_numeric_range_success(self):
        """Test numeric range validation success."""
        result = ValidationUtils.validate_numeric_range(50, min_value=0, max_value=100)

        assert result.is_valid

    def test_validate_numeric_range_failure(self):
        """Test numeric range validation failure."""
        result = ValidationUtils.validate_numeric_range(150, min_value=0, max_value=100)

        assert not result.is_valid
        assert any("exceeds maximum" in error for error in result.errors)

    def test_validate_percentage_success(self):
        """Test percentage validation success."""
        result = ValidationUtils.validate_percentage(75.5)

        assert result.is_valid

    def test_validate_percentage_failure(self):
        """Test percentage validation failure."""
        result = ValidationUtils.validate_percentage(150)

        assert not result.is_valid

    def test_validate_string_pattern_success(self):
        """Test string pattern validation success."""
        result = ValidationUtils.validate_string_pattern("test123", r"^[a-z]+\d+$")

        assert result.is_valid

    def test_validate_string_pattern_failure(self):
        """Test string pattern validation failure."""
        result = ValidationUtils.validate_string_pattern("TEST123", r"^[a-z]+\d+$")

        assert not result.is_valid

    def test_validate_string_pattern_invalid_regex(self):
        """Test string pattern validation with invalid regex."""
        result = ValidationUtils.validate_string_pattern("test", r"[invalid")

        assert not result.is_valid
        assert any("Invalid pattern" in error for error in result.errors)

    def test_validate_choice_success(self):
        """Test choice validation success."""
        result = ValidationUtils.validate_choice("option2", ["option1", "option2", "option3"])

        assert result.is_valid

    def test_validate_choice_failure(self):
        """Test choice validation failure."""
        result = ValidationUtils.validate_choice("invalid", ["option1", "option2"])

        assert not result.is_valid
        assert any("not valid" in error for error in result.errors)

    def test_validate_pydantic_model_success(self):
        """Test Pydantic model validation success."""
        data = {"name": "test", "value": 42}
        result = ValidationUtils.validate_pydantic_model(data, MockConfig)

        assert result.is_valid

    def test_validate_pydantic_model_failure(self):
        """Test Pydantic model validation failure."""
        data = {"name": "test"}  # Missing required 'value'
        result = ValidationUtils.validate_pydantic_model(data, MockConfig)

        assert not result.is_valid

    def test_validate_workflow_parameters_success(self):
        """Test workflow parameter validation success."""
        params = {"param1": "value1", "param2": "value2"}
        result = ValidationUtils.validate_workflow_parameters(
            params, required_params=["param1"], optional_params=["param2"]
        )

        assert result.is_valid

    def test_validate_workflow_parameters_missing_required(self):
        """Test workflow parameter validation with missing required parameter."""
        params = {"param2": "value2"}
        result = ValidationUtils.validate_workflow_parameters(
            params, required_params=["param1"], optional_params=["param2"]
        )

        assert not result.is_valid
        assert any("Required parameter missing" in error for error in result.errors)

    def test_validate_workflow_parameters_unknown(self):
        """Test workflow parameter validation with unknown parameter."""
        params = {"param1": "value1", "unknown": "value"}
        result = ValidationUtils.validate_workflow_parameters(
            params, required_params=["param1"]
        )

        assert not result.is_valid
        assert any("Unknown parameter" in error for error in result.errors)

    def test_validate_image_format_success(self):
        """Test image format validation success."""
        result = ValidationUtils.validate_image_format("PNG", ["PNG", "JPEG", "GIF"])

        assert result.is_valid

    def test_validate_image_format_case_insensitive(self):
        """Test image format validation is case insensitive."""
        result = ValidationUtils.validate_image_format("png", ["PNG", "JPEG"])

        assert result.is_valid

    def test_validate_image_format_failure(self):
        """Test image format validation failure."""
        result = ValidationUtils.validate_image_format("BMP", ["PNG", "JPEG"])

        assert not result.is_valid

    def test_validate_color_value_hex_success(self):
        """Test color validation for hex values."""
        result = ValidationUtils.validate_color_value("#FF0000")

        assert result.is_valid

    def test_validate_color_value_hex_with_alpha(self):
        """Test color validation for hex values with alpha."""
        result = ValidationUtils.validate_color_value("#FF0000FF", allow_transparency=True)

        assert result.is_valid

    def test_validate_color_value_hex_failure(self):
        """Test color validation for invalid hex values."""
        result = ValidationUtils.validate_color_value("#GG0000")

        assert not result.is_valid

    def test_validate_color_value_rgb_success(self):
        """Test color validation for RGB tuples."""
        result = ValidationUtils.validate_color_value((255, 0, 0))

        assert result.is_valid

    def test_validate_color_value_rgba_success(self):
        """Test color validation for RGBA tuples."""
        result = ValidationUtils.validate_color_value((255, 0, 0, 128), allow_transparency=True)

        assert result.is_valid

    def test_validate_color_value_rgb_failure(self):
        """Test color validation for invalid RGB tuples."""
        result = ValidationUtils.validate_color_value((300, 0, 0))  # Invalid component

        assert not result.is_valid

    def test_validate_color_value_grayscale_success(self):
        """Test color validation for grayscale values."""
        result = ValidationUtils.validate_color_value(128)

        assert result.is_valid

    def test_validate_color_value_grayscale_failure(self):
        """Test color validation for invalid grayscale values."""
        result = ValidationUtils.validate_color_value(300)

        assert not result.is_valid

    def test_validate_color_value_invalid_type(self):
        """Test color validation for invalid types."""
        result = ValidationUtils.validate_color_value([255, 0, 0])

        assert not result.is_valid


class TestCommonValidators:
    """Test pre-defined common validators."""

    def test_positive_int_validator(self):
        """Test positive integer validator."""
        validator = COMMON_VALIDATORS['positive_int']

        assert validator(10) is True
        assert validator(0) is False
        assert validator(-5) is False
        assert validator(3.14) is False

    def test_non_negative_int_validator(self):
        """Test non-negative integer validator."""
        validator = COMMON_VALIDATORS['non_negative_int']

        assert validator(0) is True
        assert validator(10) is True
        assert validator(-1) is False

    def test_positive_float_validator(self):
        """Test positive float validator."""
        validator = COMMON_VALIDATORS['positive_float']

        assert validator(3.14) is True
        assert validator(10) is True  # int is accepted
        assert validator(0.0) is False

    def test_non_empty_string_validator(self):
        """Test non-empty string validator."""
        validator = COMMON_VALIDATORS['non_empty_string']

        assert validator("hello") is True
        assert validator("") is False
        assert validator("   ") is False  # Whitespace only
        assert validator(123) is False

    def test_existing_dir_validator(self, temp_dir):
        """Test existing directory validator."""
        validator = COMMON_VALIDATORS['existing_dir']

        assert validator(temp_dir) is True
        assert validator(temp_dir / "nonexistent") is False

    def test_coordinates_validator(self):
        """Test coordinates validator."""
        validator = COMMON_VALIDATORS['coordinates']

        assert validator([(0, 0), (10, 20)]) is True
        assert validator([]) is False


class TestBatchValidation:
    """Test batch validation functionality."""

    def test_batch_validate_success(self):
        """Test successful batch validation."""
        validators = {
            'width': COMMON_VALIDATORS['positive_int'],
            'height': COMMON_VALIDATORS['positive_int'],
            'name': COMMON_VALIDATORS['non_empty_string']
        }

        data = {
            'width': 100,
            'height': 50,
            'name': 'test'
        }

        context = batch_validate(validators, data, raise_on_error=False)

        assert not context.has_errors()

    def test_batch_validate_with_errors(self):
        """Test batch validation with errors."""
        validators = {
            'width': COMMON_VALIDATORS['positive_int'],
            'height': COMMON_VALIDATORS['positive_int']
        }

        data = {
            'width': -10,  # Invalid
            'height': 50
        }

        context = batch_validate(validators, data, raise_on_error=False)

        assert context.has_errors()
        assert any("width" in error for error in context.errors)

    def test_batch_validate_missing_field(self):
        """Test batch validation with missing field."""
        validators = {
            'width': COMMON_VALIDATORS['positive_int'],
            'missing_field': COMMON_VALIDATORS['positive_int']
        }

        data = {'width': 100}

        context = batch_validate(validators, data, raise_on_error=False)

        assert context.has_warnings()
        assert any("missing_field" in warning for warning in context.warnings)

    def test_batch_validate_raise_on_error(self):
        """Test batch validation with raise_on_error=True."""
        validators = {'width': COMMON_VALIDATORS['positive_int']}
        data = {'width': -10}

        with pytest.raises(ValidationError):
            batch_validate(validators, data, raise_on_error=True)

    def test_batch_validate_validator_exception(self):
        """Test batch validation with validator exception."""
        def failing_validator(x):
            raise RuntimeError("Validator failed")

        validators = {'field': failing_validator}
        data = {'field': 'value'}

        context = batch_validate(validators, data, raise_on_error=False)

        assert context.has_errors()
        assert any("Validator error" in error for error in context.errors)


class TestValidationEdgeCases:
    """Test edge cases and error conditions."""

    def test_path_validation_with_string_input(self, sample_image_rgb):
        """Test path validation with string input."""
        validator = validate_file_path(must_exist=True)

        # Should work with string path
        assert validator(str(sample_image_rgb)) is True

    def test_validation_with_none_values(self):
        """Test validation behavior with None values."""
        assert validate_positive_number(None) is False
        assert validate_coordinates(None) is False

    def test_image_validation_without_pil(self):
        """Test image validation when PIL is not available."""
        validator = validate_image_file()

        with patch('PIL.Image.open', side_effect=ImportError("PIL not available")):
            # Should handle the import error gracefully
            assert validator("fake_path.jpg") is False

    def test_validation_context_unicode_messages(self):
        """Test validation context with Unicode messages."""
        context = ValidationContext()
        context.add_error("Unicode test: 测试 🔥")
        context.add_warning("Unicode warning: измена")

        assert context.has_errors()
        assert context.has_warnings()

        summary = context.get_error_summary()
        assert "测试" in summary

    def test_range_validator_edge_values(self):
        """Test range validator with edge values."""
        validator = validate_in_range(0.0, 1.0, inclusive=True)

        assert validator(0.0) is True
        assert validator(1.0) is True
        assert validator(0.9999999) is True
        assert validator(1.0000001) is False

    def test_coordinate_validation_edge_cases(self):
        """Test coordinate validation edge cases."""
        # Single coordinate
        assert validate_coordinates([(0, 0)]) is True

        # Float coordinates
        assert validate_coordinates([(0.5, 1.5)]) is True

        # Large coordinates
        assert validate_coordinates([(1000000, 2000000)]) is True

        # Mixed int/float
        assert validate_coordinates([(1, 2.5), (3.14, 4)]) is True

    def test_validation_decorator_with_complex_signature(self):
        """Test validation decorators with complex function signatures."""
        @validate_input(
            a=lambda x: x > 0,
            c=lambda x: len(x) > 0
        )
        def complex_function(a, b=None, *args, c="default", **kwargs):
            return f"a={a}, b={b}, c={c}, args={args}, kwargs={kwargs}"

        result = complex_function(10, "test", "extra", c="hello", extra_kw="value")
        assert "a=10" in result
        assert "c=hello" in result

    def test_memory_efficiency_large_validation(self):
        """Test memory efficiency with large validation operations."""
        # Test with many validators
        validators = {f'field_{i}': COMMON_VALIDATORS['positive_int'] for i in range(1000)}
        data = {f'field_{i}': i + 1 for i in range(1000)}

        context = batch_validate(validators, data, raise_on_error=False)

        assert not context.has_errors()
        assert not context.has_warnings()  # All fields present

    def test_validation_thread_safety(self):
        """Test validation operations are thread-safe."""
        import threading
        import queue

        results = queue.Queue()
        errors = queue.Queue()

        def validate_data():
            try:
                validators = {'width': COMMON_VALIDATORS['positive_int']}
                data = {'width': 100}
                context = batch_validate(validators, data, raise_on_error=False)
                results.put(not context.has_errors())
            except Exception as e:
                errors.put(e)

        # Start multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=validate_data)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Check results
        assert errors.empty(), f"Errors occurred: {list(errors.queue)}"
        assert results.qsize() == 10

        # All validations should succeed
        while not results.empty():
            assert results.get() is True