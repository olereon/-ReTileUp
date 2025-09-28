"""Comprehensive unit tests for exception hierarchy.

This module tests the custom exception system including:
- Exception hierarchy and inheritance
- Error codes and structured error handling
- Context information and cause chaining
- Serialization and string representations
- Convenience functions for common errors
"""

import json
from typing import Any, Dict, Optional

import pytest

from retileup.core.exceptions import (
    ErrorCode,
    RetileupError,
    ValidationError,
    ProcessingError,
    ConfigurationError,
    WorkflowError,
    RegistryError,
    SecurityError,
    ResourceError,
    validation_error,
    processing_error,
    configuration_error,
    workflow_error,
    registry_error,
)


class TestErrorCode:
    """Test ErrorCode enumeration."""

    def test_error_code_values(self):
        """Test that error codes have expected values."""
        assert ErrorCode.UNKNOWN_ERROR == "0000"
        assert ErrorCode.INTERNAL_ERROR == "0001"
        assert ErrorCode.VALIDATION_ERROR == "1000"
        assert ErrorCode.INVALID_INPUT == "1001"
        assert ErrorCode.PROCESSING_ERROR == "2000"
        assert ErrorCode.TOOL_EXECUTION_ERROR == "2002"
        assert ErrorCode.REGISTRY_ERROR == "3000"
        assert ErrorCode.TOOL_NOT_FOUND == "3001"
        assert ErrorCode.SECURITY_ERROR == "4000"
        assert ErrorCode.RESOURCE_ERROR == "5000"

    def test_error_code_string_comparison(self):
        """Test error code string comparison."""
        assert ErrorCode.VALIDATION_ERROR == "1000"
        assert str(ErrorCode.VALIDATION_ERROR) == "1000"

    def test_error_code_categories(self):
        """Test error code categories by range."""
        # General errors (0xxx)
        assert ErrorCode.UNKNOWN_ERROR.startswith("0")
        assert ErrorCode.INTERNAL_ERROR.startswith("0")

        # Validation errors (1xxx)
        assert ErrorCode.VALIDATION_ERROR.startswith("1")
        assert ErrorCode.INVALID_INPUT.startswith("1")

        # Processing errors (2xxx)
        assert ErrorCode.PROCESSING_ERROR.startswith("2")
        assert ErrorCode.TOOL_EXECUTION_ERROR.startswith("2")

        # Registry errors (3xxx)
        assert ErrorCode.REGISTRY_ERROR.startswith("3")
        assert ErrorCode.TOOL_NOT_FOUND.startswith("3")

        # Security errors (4xxx)
        assert ErrorCode.SECURITY_ERROR.startswith("4")

        # Resource errors (5xxx)
        assert ErrorCode.RESOURCE_ERROR.startswith("5")


class TestRetileupError:
    """Test base RetileupError class."""

    def test_retileup_error_minimal(self):
        """Test creating RetileupError with minimal parameters."""
        error = RetileupError("Test error message")

        assert str(error) == "0000: Test error message"
        assert error.message == "Test error message"
        assert error.error_code == ErrorCode.UNKNOWN_ERROR
        assert error.context == {}
        assert error.cause is None

    def test_retileup_error_complete(self):
        """Test creating RetileupError with all parameters."""
        context = {"file": "test.py", "line": 42}
        cause = ValueError("Original error")

        error = RetileupError(
            message="Test error with context",
            error_code=ErrorCode.INTERNAL_ERROR,
            context=context,
            cause=cause
        )

        assert error.message == "Test error with context"
        assert error.error_code == ErrorCode.INTERNAL_ERROR
        assert error.context == context
        assert error.cause == cause

    def test_retileup_error_to_dict(self):
        """Test converting RetileupError to dictionary."""
        context = {"component": "test", "value": 123}
        cause = RuntimeError("Original cause")

        error = RetileupError(
            message="Conversion test",
            error_code=ErrorCode.VALIDATION_ERROR,
            context=context,
            cause=cause
        )

        error_dict = error.to_dict()

        assert error_dict["error_type"] == "RetileupError"
        assert error_dict["message"] == "Conversion test"
        assert error_dict["error_code"] == "1000"
        assert error_dict["context"] == context
        assert error_dict["cause"]["type"] == "RuntimeError"
        assert error_dict["cause"]["message"] == "Original cause"

    def test_retileup_error_to_dict_no_cause(self):
        """Test converting RetileupError to dictionary without cause."""
        error = RetileupError("No cause error")
        error_dict = error.to_dict()

        assert "cause" not in error_dict

    def test_retileup_error_string_representation(self):
        """Test string representation of RetileupError."""
        # Basic error
        error = RetileupError("Basic error")
        assert str(error) == "0000: Basic error"

        # Error with context
        error = RetileupError(
            "Error with context",
            context={"key": "value", "number": 42}
        )
        assert "key=value" in str(error)
        assert "number=42" in str(error)

        # Error with cause
        cause = ValueError("Root cause")
        error = RetileupError("Error with cause", cause=cause)
        assert "Caused by: Root cause" in str(error)

    def test_retileup_error_repr(self):
        """Test detailed representation of RetileupError."""
        context = {"test": True}
        error = RetileupError(
            "Repr test",
            error_code=ErrorCode.PROCESSING_ERROR,
            context=context
        )

        repr_str = repr(error)
        assert "RetileupError" in repr_str
        assert "error_code='2000'" in repr_str
        assert "message='Repr test'" in repr_str
        assert str(context) in repr_str

    def test_retileup_error_inheritance(self):
        """Test that RetileupError inherits from Exception properly."""
        error = RetileupError("Inheritance test")

        assert isinstance(error, Exception)
        assert isinstance(error, RetileupError)

        # Should work with exception handling
        try:
            raise error
        except RetileupError as e:
            assert e.message == "Inheritance test"
        except Exception:
            pytest.fail("Should have caught as RetileupError")


class TestValidationError:
    """Test ValidationError specialized exception."""

    def test_validation_error_minimal(self):
        """Test creating ValidationError with minimal parameters."""
        error = ValidationError("Validation failed")

        assert isinstance(error, RetileupError)
        assert error.message == "Validation failed"
        assert error.error_code == ErrorCode.VALIDATION_ERROR
        assert error.field_name is None
        assert error.invalid_value is None

    def test_validation_error_with_field_info(self):
        """Test ValidationError with field information."""
        error = ValidationError(
            "Invalid field value",
            field_name="width",
            invalid_value=-10
        )

        assert error.field_name == "width"
        assert error.invalid_value == -10
        assert error.context["field_name"] == "width"
        assert error.context["invalid_value"] == "-10"

    def test_validation_error_custom_error_code(self):
        """Test ValidationError with custom error code."""
        error = ValidationError(
            "Missing required field",
            error_code=ErrorCode.MISSING_REQUIRED_FIELD,
            field_name="required_field"
        )

        assert error.error_code == ErrorCode.MISSING_REQUIRED_FIELD


class TestProcessingError:
    """Test ProcessingError specialized exception."""

    def test_processing_error_minimal(self):
        """Test creating ProcessingError with minimal parameters."""
        error = ProcessingError("Processing failed")

        assert isinstance(error, RetileupError)
        assert error.message == "Processing failed"
        assert error.error_code == ErrorCode.PROCESSING_ERROR
        assert error.tool_name is None
        assert error.stage is None

    def test_processing_error_with_tool_info(self):
        """Test ProcessingError with tool information."""
        error = ProcessingError(
            "Tool execution failed",
            tool_name="image-resize",
            stage="validation"
        )

        assert error.tool_name == "image-resize"
        assert error.stage == "validation"
        assert error.context["tool_name"] == "image-resize"
        assert error.context["stage"] == "validation"

    def test_processing_error_custom_error_code(self):
        """Test ProcessingError with custom error code."""
        error = ProcessingError(
            "Image processing error",
            error_code=ErrorCode.IMAGE_PROCESSING_ERROR,
            tool_name="tiling-tool"
        )

        assert error.error_code == ErrorCode.IMAGE_PROCESSING_ERROR


class TestConfigurationError:
    """Test ConfigurationError specialized exception."""

    def test_configuration_error_minimal(self):
        """Test creating ConfigurationError with minimal parameters."""
        error = ConfigurationError("Configuration error")

        assert isinstance(error, RetileupError)
        assert error.message == "Configuration error"
        assert error.error_code == ErrorCode.CONFIGURATION_ERROR
        assert error.config_path is None
        assert error.config_section is None

    def test_configuration_error_with_path_info(self):
        """Test ConfigurationError with path information."""
        error = ConfigurationError(
            "Invalid configuration file",
            config_path="/path/to/config.yaml",
            config_section="logging"
        )

        assert error.config_path == "/path/to/config.yaml"
        assert error.config_section == "logging"
        assert error.context["config_path"] == "/path/to/config.yaml"
        assert error.context["config_section"] == "logging"


class TestWorkflowError:
    """Test WorkflowError specialized exception."""

    def test_workflow_error_minimal(self):
        """Test creating WorkflowError with minimal parameters."""
        error = WorkflowError("Workflow failed")

        assert isinstance(error, RetileupError)
        assert error.message == "Workflow failed"
        assert error.error_code == ErrorCode.WORKFLOW_ERROR
        assert error.workflow_name is None
        assert error.step_name is None
        assert error.step_index is None

    def test_workflow_error_with_workflow_info(self):
        """Test WorkflowError with workflow information."""
        error = WorkflowError(
            "Step failed",
            workflow_name="image-processing",
            step_name="resize",
            step_index=2
        )

        assert error.workflow_name == "image-processing"
        assert error.step_name == "resize"
        assert error.step_index == 2
        assert error.context["workflow_name"] == "image-processing"
        assert error.context["step_name"] == "resize"
        assert error.context["step_index"] == 2


class TestRegistryError:
    """Test RegistryError specialized exception."""

    def test_registry_error_minimal(self):
        """Test creating RegistryError with minimal parameters."""
        error = RegistryError("Registry error")

        assert isinstance(error, RetileupError)
        assert error.message == "Registry error"
        assert error.error_code == ErrorCode.REGISTRY_ERROR
        assert error.tool_name is None
        assert error.registry_operation is None

    def test_registry_error_with_tool_info(self):
        """Test RegistryError with tool information."""
        error = RegistryError(
            "Tool registration failed",
            tool_name="custom-tool",
            registry_operation="register"
        )

        assert error.tool_name == "custom-tool"
        assert error.registry_operation == "register"
        assert error.context["tool_name"] == "custom-tool"
        assert error.context["registry_operation"] == "register"


class TestSecurityError:
    """Test SecurityError specialized exception."""

    def test_security_error_minimal(self):
        """Test creating SecurityError with minimal parameters."""
        error = SecurityError("Security violation")

        assert isinstance(error, RetileupError)
        assert error.message == "Security violation"
        assert error.error_code == ErrorCode.SECURITY_ERROR
        assert error.security_policy is None
        assert error.attempted_action is None

    def test_security_error_with_security_info(self):
        """Test SecurityError with security information."""
        error = SecurityError(
            "Path traversal attempt",
            security_policy="path_validation",
            attempted_action="access_parent_directory"
        )

        assert error.security_policy == "path_validation"
        assert error.attempted_action == "access_parent_directory"
        assert error.context["security_policy"] == "path_validation"
        assert error.context["attempted_action"] == "access_parent_directory"


class TestResourceError:
    """Test ResourceError specialized exception."""

    def test_resource_error_minimal(self):
        """Test creating ResourceError with minimal parameters."""
        error = ResourceError("Resource exhausted")

        assert isinstance(error, RetileupError)
        assert error.message == "Resource exhausted"
        assert error.error_code == ErrorCode.RESOURCE_ERROR
        assert error.resource_type is None
        assert error.resource_limit is None
        assert error.current_usage is None

    def test_resource_error_with_resource_info(self):
        """Test ResourceError with resource information."""
        error = ResourceError(
            "Memory limit exceeded",
            resource_type="memory",
            resource_limit="1GB",
            current_usage="1.2GB"
        )

        assert error.resource_type == "memory"
        assert error.resource_limit == "1GB"
        assert error.current_usage == "1.2GB"
        assert error.context["resource_type"] == "memory"
        assert error.context["resource_limit"] == "1GB"
        assert error.context["current_usage"] == "1.2GB"


class TestConvenienceFunctions:
    """Test convenience functions for creating common errors."""

    def test_validation_error_function(self):
        """Test validation_error convenience function."""
        error = validation_error(
            "Invalid input",
            field_name="age",
            invalid_value=-5
        )

        assert isinstance(error, ValidationError)
        assert error.message == "Invalid input"
        assert error.error_code == ErrorCode.INVALID_INPUT
        assert error.field_name == "age"
        assert error.invalid_value == -5

    def test_validation_error_function_with_cause(self):
        """Test validation_error function with cause."""
        cause = ValueError("Original validation error")
        error = validation_error(
            "Validation wrapper",
            field_name="width",
            cause=cause
        )

        assert error.cause == cause

    def test_processing_error_function(self):
        """Test processing_error convenience function."""
        error = processing_error(
            "Processing failed",
            tool_name="image-tool",
            stage="execution"
        )

        assert isinstance(error, ProcessingError)
        assert error.message == "Processing failed"
        assert error.error_code == ErrorCode.TOOL_EXECUTION_ERROR
        assert error.tool_name == "image-tool"
        assert error.stage == "execution"

    def test_configuration_error_function(self):
        """Test configuration_error convenience function."""
        error = configuration_error(
            "Config invalid",
            config_path="/etc/config.yaml",
            config_section="database"
        )

        assert isinstance(error, ConfigurationError)
        assert error.message == "Config invalid"
        assert error.error_code == ErrorCode.INVALID_CONFIG
        assert error.config_path == "/etc/config.yaml"
        assert error.config_section == "database"

    def test_workflow_error_function(self):
        """Test workflow_error convenience function."""
        error = workflow_error(
            "Workflow step failed",
            workflow_name="main-workflow",
            step_name="processing",
            step_index=3
        )

        assert isinstance(error, WorkflowError)
        assert error.message == "Workflow step failed"
        assert error.error_code == ErrorCode.WORKFLOW_ERROR
        assert error.workflow_name == "main-workflow"
        assert error.step_name == "processing"
        assert error.step_index == 3

    def test_registry_error_function(self):
        """Test registry_error convenience function."""
        error = registry_error(
            "Registration failed",
            tool_name="test-tool",
            operation="validate"
        )

        assert isinstance(error, RegistryError)
        assert error.message == "Registration failed"
        assert error.error_code == ErrorCode.TOOL_REGISTRATION_ERROR
        assert error.tool_name == "test-tool"
        assert error.registry_operation == "validate"


class TestErrorChaining:
    """Test error chaining and cause tracking."""

    def test_simple_error_chain(self):
        """Test simple error chaining."""
        root_cause = ValueError("Root cause error")
        wrapper_error = RetileupError(
            "Wrapper error",
            cause=root_cause
        )

        assert wrapper_error.cause == root_cause
        assert "Caused by: Root cause error" in str(wrapper_error)

        error_dict = wrapper_error.to_dict()
        assert error_dict["cause"]["type"] == "ValueError"
        assert error_dict["cause"]["message"] == "Root cause error"

    def test_nested_error_chain(self):
        """Test nested error chaining."""
        # Create a chain: ValueError -> ProcessingError -> ValidationError
        root_cause = ValueError("Original error")
        processing_error = ProcessingError(
            "Processing wrapper",
            cause=root_cause
        )
        validation_error = ValidationError(
            "Validation wrapper",
            cause=processing_error
        )

        assert validation_error.cause == processing_error
        assert processing_error.cause == root_cause

        # Check string representation includes cause
        validation_str = str(validation_error)
        assert "Caused by: Processing wrapper" in validation_str

    def test_error_serialization_with_cause(self):
        """Test error serialization with cause chain."""
        root_cause = KeyError("Missing key")
        wrapped_error = ConfigurationError(
            "Config error",
            cause=root_cause
        )

        error_dict = wrapped_error.to_dict()

        assert error_dict["error_type"] == "ConfigurationError"
        assert error_dict["message"] == "Config error"
        assert error_dict["cause"]["type"] == "KeyError"
        assert error_dict["cause"]["message"] == "Missing key"

        # Should be JSON serializable
        json_str = json.dumps(error_dict)
        assert "Config error" in json_str
        assert "Missing key" in json_str


class TestErrorContextHandling:
    """Test context information handling in errors."""

    def test_context_merging(self):
        """Test context merging in specialized errors."""
        # ValidationError should merge its own context with provided context
        custom_context = {"user_id": 123, "operation": "create"}
        error = ValidationError(
            "Field validation failed",
            context=custom_context,
            field_name="email",
            invalid_value="invalid-email"
        )

        # Should have both custom context and validation-specific context
        assert error.context["user_id"] == 123
        assert error.context["operation"] == "create"
        assert error.context["field_name"] == "email"
        assert error.context["invalid_value"] == "invalid-email"

    def test_context_override_protection(self):
        """Test that specialized context doesn't override existing keys."""
        # If custom context has same key as specialized context, custom wins
        custom_context = {"field_name": "custom_field"}
        error = ValidationError(
            "Test",
            context=custom_context,
            field_name="validation_field"
        )

        # Specialized field_name should override custom context
        assert error.context["field_name"] == "validation_field"

    def test_complex_context_types(self):
        """Test context with complex data types."""
        complex_context = {
            "list_data": [1, 2, 3],
            "dict_data": {"nested": "value"},
            "none_data": None,
            "bool_data": True
        }

        error = RetileupError(
            "Complex context test",
            context=complex_context
        )

        assert error.context["list_data"] == [1, 2, 3]
        assert error.context["dict_data"]["nested"] == "value"
        assert error.context["none_data"] is None
        assert error.context["bool_data"] is True

        # Should serialize properly
        error_dict = error.to_dict()
        assert error_dict["context"] == complex_context


class TestErrorUsagePatterns:
    """Test common error usage patterns."""

    def test_exception_handling_by_type(self):
        """Test catching specific error types."""
        def raise_validation_error():
            raise ValidationError("Validation failed")

        def raise_processing_error():
            raise ProcessingError("Processing failed")

        # Should catch ValidationError specifically
        try:
            raise_validation_error()
        except ValidationError as e:
            assert e.error_code == ErrorCode.VALIDATION_ERROR
        except RetileupError:
            pytest.fail("Should have caught ValidationError specifically")

        # Should catch ProcessingError specifically
        try:
            raise_processing_error()
        except ProcessingError as e:
            assert e.error_code == ErrorCode.PROCESSING_ERROR
        except RetileupError:
            pytest.fail("Should have caught ProcessingError specifically")

    def test_exception_handling_by_base_class(self):
        """Test catching all errors by base class."""
        errors = [
            ValidationError("Validation error"),
            ProcessingError("Processing error"),
            ConfigurationError("Configuration error"),
        ]

        caught_errors = []
        for error in errors:
            try:
                raise error
            except RetileupError as e:
                caught_errors.append(e)

        assert len(caught_errors) == 3
        assert all(isinstance(e, RetileupError) for e in caught_errors)

    def test_error_code_based_handling(self):
        """Test handling errors based on error codes."""
        errors = [
            ValidationError("Validation", error_code=ErrorCode.INVALID_INPUT),
            ProcessingError("Processing", error_code=ErrorCode.TOOL_EXECUTION_ERROR),
            RegistryError("Registry", error_code=ErrorCode.TOOL_NOT_FOUND),
        ]

        for error in errors:
            try:
                raise error
            except RetileupError as e:
                if e.error_code.startswith("1"):  # Validation errors
                    assert isinstance(e, ValidationError)
                elif e.error_code.startswith("2"):  # Processing errors
                    assert isinstance(e, ProcessingError)
                elif e.error_code.startswith("3"):  # Registry errors
                    assert isinstance(e, RegistryError)

    def test_error_logging_format(self):
        """Test error formatting for logging."""
        error = ProcessingError(
            "Tool execution failed",
            error_code=ErrorCode.TOOL_EXECUTION_ERROR,
            context={"tool": "image-resize", "step": 3},
            tool_name="resize-tool",
            stage="processing"
        )

        # String representation should be suitable for logging
        error_str = str(error)
        assert "2002:" in error_str  # Error code
        assert "Tool execution failed" in error_str  # Message
        assert "tool=image-resize" in error_str  # Context
        assert "step=3" in error_str  # Context

        # Dict representation should be suitable for structured logging
        error_dict = error.to_dict()
        assert error_dict["error_code"] == "2002"
        assert error_dict["message"] == "Tool execution failed"
        assert error_dict["context"]["tool"] == "image-resize"