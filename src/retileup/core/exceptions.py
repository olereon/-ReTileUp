"""Custom exception hierarchy for ReTileUp.

This module provides a comprehensive exception hierarchy for structured error
handling throughout the ReTileUp framework. All exceptions include error codes
for programmatic handling and structured error responses.
"""

from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(str, Enum):
    """Enumeration of error codes for structured error handling."""

    # General errors (0xxx)
    UNKNOWN_ERROR = "0000"
    INTERNAL_ERROR = "0001"
    NOT_IMPLEMENTED = "0002"
    CONFIGURATION_ERROR = "0003"

    # Validation errors (1xxx)
    VALIDATION_ERROR = "1000"
    INVALID_INPUT = "1001"
    INVALID_CONFIG = "1002"
    INVALID_PARAMETER = "1003"
    MISSING_REQUIRED_FIELD = "1004"
    INVALID_FILE_FORMAT = "1005"
    FILE_NOT_FOUND = "1006"
    INVALID_PATH = "1007"

    # Processing errors (2xxx)
    PROCESSING_ERROR = "2000"
    IMAGE_PROCESSING_ERROR = "2001"
    TOOL_EXECUTION_ERROR = "2002"
    WORKFLOW_ERROR = "2003"
    TIMEOUT_ERROR = "2004"
    MEMORY_ERROR = "2005"
    IO_ERROR = "2006"

    # Registry errors (3xxx)
    REGISTRY_ERROR = "3000"
    TOOL_NOT_FOUND = "3001"
    TOOL_REGISTRATION_ERROR = "3002"
    PLUGIN_LOAD_ERROR = "3003"
    VERSION_COMPATIBILITY_ERROR = "3004"

    # Security errors (4xxx)
    SECURITY_ERROR = "4000"
    ACCESS_DENIED = "4001"
    PATH_TRAVERSAL = "4002"
    UNSAFE_OPERATION = "4003"

    # Resource errors (5xxx)
    RESOURCE_ERROR = "5000"
    INSUFFICIENT_MEMORY = "5001"
    DISK_SPACE_ERROR = "5002"
    NETWORK_ERROR = "5003"


class RetileupError(Exception):
    """Base exception for all ReTileUp errors.

    This is the root exception class that all other ReTileUp exceptions
    inherit from. It provides structured error handling with error codes,
    context information, and optional cause chaining.

    Attributes:
        message: Human-readable error message
        error_code: Structured error code for programmatic handling
        context: Additional context information about the error
        cause: Optional underlying exception that caused this error
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message
            error_code: Structured error code
            context: Additional context information
            cause: Optional underlying exception
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.cause = cause

    def to_dict(self) -> Dict[str, Any]:
        """Convert the exception to a dictionary for serialization.

        Returns:
            Dictionary representation of the exception
        """
        result = {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code.value,
            "context": self.context,
        }

        if self.cause:
            result["cause"] = {
                "type": type(self.cause).__name__,
                "message": str(self.cause),
            }

        return result

    def __str__(self) -> str:
        """String representation of the exception."""
        parts = [f"{self.error_code.value}: {self.message}"]

        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"Context: {context_str}")

        if self.cause:
            parts.append(f"Caused by: {self.cause}")

        return " | ".join(parts)

    def __repr__(self) -> str:
        """Detailed string representation of the exception."""
        return (
            f"<{self.__class__.__name__}("
            f"error_code='{self.error_code.value}', "
            f"message='{self.message}', "
            f"context={self.context}"
            f")>"
        )


class ValidationError(RetileupError):
    """Exception raised when input validation fails.

    This exception is raised when user input, configuration, or parameters
    fail validation checks. It includes specific information about what
    validation failed and why.

    Examples:
        - Invalid file paths
        - Missing required parameters
        - Invalid parameter values
        - Unsupported file formats
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.VALIDATION_ERROR,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        field_name: Optional[str] = None,
        invalid_value: Optional[Any] = None,
    ) -> None:
        """Initialize the validation error.

        Args:
            message: Human-readable error message
            error_code: Specific validation error code
            context: Additional context information
            cause: Optional underlying exception
            field_name: Name of the field that failed validation
            invalid_value: The invalid value that caused the error
        """
        # Add validation-specific context
        validation_context = context or {}
        if field_name:
            validation_context["field_name"] = field_name
        if invalid_value is not None:
            validation_context["invalid_value"] = str(invalid_value)

        super().__init__(message, error_code, validation_context, cause)
        self.field_name = field_name
        self.invalid_value = invalid_value


class ProcessingError(RetileupError):
    """Exception raised when image processing fails.

    This exception is raised when the actual image processing operations
    encounter errors. It includes information about the processing stage
    and operation that failed.

    Examples:
        - Image corruption during processing
        - Unsupported image operations
        - Memory exhaustion during processing
        - Tool execution failures
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.PROCESSING_ERROR,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        tool_name: Optional[str] = None,
        stage: Optional[str] = None,
    ) -> None:
        """Initialize the processing error.

        Args:
            message: Human-readable error message
            error_code: Specific processing error code
            context: Additional context information
            cause: Optional underlying exception
            tool_name: Name of the tool that failed
            stage: Processing stage where the error occurred
        """
        # Add processing-specific context
        processing_context = context or {}
        if tool_name:
            processing_context["tool_name"] = tool_name
        if stage:
            processing_context["stage"] = stage

        super().__init__(message, error_code, processing_context, cause)
        self.tool_name = tool_name
        self.stage = stage


class ConfigurationError(RetileupError):
    """Exception raised when configuration is invalid or missing.

    This exception is raised when there are issues with application
    configuration, tool configuration, or workflow configuration.

    Examples:
        - Missing configuration files
        - Invalid configuration format
        - Conflicting configuration options
        - Invalid default settings
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.CONFIGURATION_ERROR,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        config_path: Optional[str] = None,
        config_section: Optional[str] = None,
    ) -> None:
        """Initialize the configuration error.

        Args:
            message: Human-readable error message
            error_code: Specific configuration error code
            context: Additional context information
            cause: Optional underlying exception
            config_path: Path to the configuration file
            config_section: Section of configuration that failed
        """
        # Add configuration-specific context
        config_context = context or {}
        if config_path:
            config_context["config_path"] = config_path
        if config_section:
            config_context["config_section"] = config_section

        super().__init__(message, error_code, config_context, cause)
        self.config_path = config_path
        self.config_section = config_section


class WorkflowError(RetileupError):
    """Exception raised when workflow execution fails.

    This exception is raised when there are issues with workflow
    definition, execution, or coordination between multiple tools.

    Examples:
        - Invalid workflow definition
        - Tool dependency failures
        - Workflow step timeout
        - Inter-tool communication errors
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.WORKFLOW_ERROR,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        workflow_name: Optional[str] = None,
        step_name: Optional[str] = None,
        step_index: Optional[int] = None,
    ) -> None:
        """Initialize the workflow error.

        Args:
            message: Human-readable error message
            error_code: Specific workflow error code
            context: Additional context information
            cause: Optional underlying exception
            workflow_name: Name of the workflow that failed
            step_name: Name of the workflow step that failed
            step_index: Index of the workflow step that failed
        """
        # Add workflow-specific context
        workflow_context = context or {}
        if workflow_name:
            workflow_context["workflow_name"] = workflow_name
        if step_name:
            workflow_context["step_name"] = step_name
        if step_index is not None:
            workflow_context["step_index"] = step_index

        super().__init__(message, error_code, workflow_context, cause)
        self.workflow_name = workflow_name
        self.step_name = step_name
        self.step_index = step_index


class RegistryError(RetileupError):
    """Exception raised when tool registry operations fail.

    This exception is raised when there are issues with tool registration,
    discovery, or management within the tool registry.

    Examples:
        - Tool registration failures
        - Plugin loading errors
        - Tool not found errors
        - Version compatibility issues
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.REGISTRY_ERROR,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        tool_name: Optional[str] = None,
        registry_operation: Optional[str] = None,
    ) -> None:
        """Initialize the registry error.

        Args:
            message: Human-readable error message
            error_code: Specific registry error code
            context: Additional context information
            cause: Optional underlying exception
            tool_name: Name of the tool involved in the error
            registry_operation: Registry operation that failed
        """
        # Add registry-specific context
        registry_context = context or {}
        if tool_name:
            registry_context["tool_name"] = tool_name
        if registry_operation:
            registry_context["registry_operation"] = registry_operation

        super().__init__(message, error_code, registry_context, cause)
        self.tool_name = tool_name
        self.registry_operation = registry_operation


class SecurityError(RetileupError):
    """Exception raised when security violations are detected.

    This exception is raised when operations violate security policies
    or when potentially unsafe operations are attempted.

    Examples:
        - Path traversal attempts
        - Access to forbidden directories
        - Unsafe file operations
        - Permission violations
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.SECURITY_ERROR,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        security_policy: Optional[str] = None,
        attempted_action: Optional[str] = None,
    ) -> None:
        """Initialize the security error.

        Args:
            message: Human-readable error message
            error_code: Specific security error code
            context: Additional context information
            cause: Optional underlying exception
            security_policy: Security policy that was violated
            attempted_action: Action that was attempted and blocked
        """
        # Add security-specific context
        security_context = context or {}
        if security_policy:
            security_context["security_policy"] = security_policy
        if attempted_action:
            security_context["attempted_action"] = attempted_action

        super().__init__(message, error_code, security_context, cause)
        self.security_policy = security_policy
        self.attempted_action = attempted_action


class ResourceError(RetileupError):
    """Exception raised when resource constraints are exceeded.

    This exception is raised when operations cannot complete due to
    resource limitations such as memory, disk space, or network issues.

    Examples:
        - Insufficient memory for processing
        - Disk space exhaustion
        - Network connectivity issues
        - Resource pool exhaustion
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.RESOURCE_ERROR,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        resource_type: Optional[str] = None,
        resource_limit: Optional[str] = None,
        current_usage: Optional[str] = None,
    ) -> None:
        """Initialize the resource error.

        Args:
            message: Human-readable error message
            error_code: Specific resource error code
            context: Additional context information
            cause: Optional underlying exception
            resource_type: Type of resource that was exhausted
            resource_limit: The resource limit that was exceeded
            current_usage: Current resource usage when error occurred
        """
        # Add resource-specific context
        resource_context = context or {}
        if resource_type:
            resource_context["resource_type"] = resource_type
        if resource_limit:
            resource_context["resource_limit"] = resource_limit
        if current_usage:
            resource_context["current_usage"] = current_usage

        super().__init__(message, error_code, resource_context, cause)
        self.resource_type = resource_type
        self.resource_limit = resource_limit
        self.current_usage = current_usage


# Convenience functions for common error scenarios

def validation_error(
    message: str,
    field_name: Optional[str] = None,
    invalid_value: Optional[Any] = None,
    cause: Optional[Exception] = None,
) -> ValidationError:
    """Create a validation error with common parameters.

    Args:
        message: Error message
        field_name: Name of the field that failed validation
        invalid_value: The invalid value
        cause: Optional underlying exception

    Returns:
        ValidationError instance
    """
    return ValidationError(
        message=message,
        error_code=ErrorCode.INVALID_INPUT,
        field_name=field_name,
        invalid_value=invalid_value,
        cause=cause,
    )


def processing_error(
    message: str,
    tool_name: Optional[str] = None,
    stage: Optional[str] = None,
    cause: Optional[Exception] = None,
) -> ProcessingError:
    """Create a processing error with common parameters.

    Args:
        message: Error message
        tool_name: Name of the tool that failed
        stage: Processing stage where error occurred
        cause: Optional underlying exception

    Returns:
        ProcessingError instance
    """
    return ProcessingError(
        message=message,
        error_code=ErrorCode.TOOL_EXECUTION_ERROR,
        tool_name=tool_name,
        stage=stage,
        cause=cause,
    )


def configuration_error(
    message: str,
    config_path: Optional[str] = None,
    config_section: Optional[str] = None,
    cause: Optional[Exception] = None,
) -> ConfigurationError:
    """Create a configuration error with common parameters.

    Args:
        message: Error message
        config_path: Path to configuration file
        config_section: Configuration section that failed
        cause: Optional underlying exception

    Returns:
        ConfigurationError instance
    """
    return ConfigurationError(
        message=message,
        error_code=ErrorCode.INVALID_CONFIG,
        config_path=config_path,
        config_section=config_section,
        cause=cause,
    )


def workflow_error(
    message: str,
    workflow_name: Optional[str] = None,
    step_name: Optional[str] = None,
    step_index: Optional[int] = None,
    cause: Optional[Exception] = None,
) -> WorkflowError:
    """Create a workflow error with common parameters.

    Args:
        message: Error message
        workflow_name: Name of the workflow
        step_name: Name of the workflow step
        step_index: Index of the workflow step
        cause: Optional underlying exception

    Returns:
        WorkflowError instance
    """
    return WorkflowError(
        message=message,
        error_code=ErrorCode.WORKFLOW_ERROR,
        workflow_name=workflow_name,
        step_name=step_name,
        step_index=step_index,
        cause=cause,
    )


def registry_error(
    message: str,
    tool_name: Optional[str] = None,
    operation: Optional[str] = None,
    cause: Optional[Exception] = None,
) -> RegistryError:
    """Create a registry error with common parameters.

    Args:
        message: Error message
        tool_name: Name of the tool
        operation: Registry operation that failed
        cause: Optional underlying exception

    Returns:
        RegistryError instance
    """
    return RegistryError(
        message=message,
        error_code=ErrorCode.TOOL_REGISTRATION_ERROR,
        tool_name=tool_name,
        registry_operation=operation,
        cause=cause,
    )