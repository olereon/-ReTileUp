"""Workflow schema definitions for ReTileUp."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StepStatusSchema(str, Enum):
    """Schema for workflow step status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ConditionalOperator(str, Enum):
    """Operators for step conditions."""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    GREATER_EQUAL = "ge"
    LESS_THAN = "lt"
    LESS_EQUAL = "le"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


class StepConditionSchema(BaseModel):
    """Schema for step execution conditions."""

    field: str = Field(..., description="Field to check")
    operator: ConditionalOperator = Field(..., description="Comparison operator")
    value: Optional[Any] = Field(None, description="Value to compare against")
    negate: bool = Field(False, description="Negate the condition result")

    model_config = ConfigDict(use_enum_values=True)


class ParameterDefinitionSchema(BaseModel):
    """Schema for parameter definitions."""

    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type")
    description: Optional[str] = Field(None, description="Parameter description")
    default: Optional[Any] = Field(None, description="Default value")
    required: bool = Field(True, description="Whether parameter is required")
    choices: Optional[List[Any]] = Field(None, description="Valid choices for parameter")
    min_value: Optional[Union[int, float]] = Field(None, description="Minimum value")
    max_value: Optional[Union[int, float]] = Field(None, description="Maximum value")
    pattern: Optional[str] = Field(None, description="Regex pattern for string validation")

    @classmethod
    @field_validator("type")
    def validate_type(cls, v: str) -> str:
        """Validate parameter type."""
        valid_types = [
            "str", "int", "float", "bool", "list", "dict",
            "path", "color", "image_format", "percentage"
        ]
        if v not in valid_types:
            raise ValueError(f"Invalid parameter type. Must be one of: {valid_types}")
        return v


class StepInputSchema(BaseModel):
    """Schema for step input configuration."""

    source: str = Field(..., description="Input source (previous_step, global, file, etc.)")
    name: Optional[str] = Field(None, description="Input name/identifier")
    transform: Optional[str] = Field(None, description="Input transformation function")
    validation: Optional[Dict[str, Any]] = Field(None, description="Input validation rules")


class StepOutputSchema(BaseModel):
    """Schema for step output configuration."""

    name: str = Field(..., description="Output name/identifier")
    type: str = Field("image", description="Output type")
    save_to_file: bool = Field(False, description="Whether to save output to file")
    filename_pattern: Optional[str] = Field(None, description="Filename pattern for saved output")
    format: Optional[str] = Field(None, description="Output format")


class WorkflowStepSchema(BaseModel):
    """Schema for workflow steps."""

    # Step identification
    name: str = Field(..., description="Step name")
    tool_name: str = Field(..., description="Name of the tool to use")
    description: Optional[str] = Field(None, description="Step description")

    # Step configuration
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    conditions: List[StepConditionSchema] = Field(
        default_factory=list,
        description="Conditions for step execution"
    )
    enabled: bool = Field(True, description="Whether the step is enabled")

    # Input/Output configuration
    inputs: List[StepInputSchema] = Field(
        default_factory=list,
        description="Step input configuration"
    )
    outputs: List[StepOutputSchema] = Field(
        default_factory=list,
        description="Step output configuration"
    )

    # Step metadata
    tags: List[str] = Field(default_factory=list, description="Step tags")
    timeout: Optional[float] = Field(None, description="Step timeout in seconds", ge=0)
    retry_count: int = Field(0, description="Number of retries for failed step", ge=0, le=10)
    priority: int = Field(0, description="Step priority for execution ordering")

    # Dependencies
    depends_on: List[str] = Field(
        default_factory=list,
        description="Names of steps this step depends on"
    )

    # Runtime state (typically not set in schema, but included for completeness)
    status: StepStatusSchema = Field(StepStatusSchema.PENDING, description="Current step status")
    error_message: Optional[str] = Field(None, description="Error message if step failed")
    execution_time: Optional[float] = Field(None, description="Step execution time in seconds")
    started_at: Optional[datetime] = Field(None, description="Step start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Step completion timestamp")

    model_config = ConfigDict(use_enum_values=True)

    @classmethod
    @field_validator("name")
    def validate_name(cls, v: str) -> str:
        """Validate step name."""
        if not v.strip():
            raise ValueError("Step name cannot be empty")
        # Check for valid identifier (no spaces, special chars)
        import re
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v):
            raise ValueError("Step name must be a valid identifier")
        return v.strip()

    @classmethod
    @field_validator("depends_on")
    def validate_dependencies(cls, v: List[str], values: Dict[str, Any]) -> List[str]:
        """Validate step dependencies."""
        step_name = values.get("name")
        if step_name and step_name in v:
            raise ValueError("Step cannot depend on itself")
        return v


class WorkflowVariableSchema(BaseModel):
    """Schema for workflow variables."""

    name: str = Field(..., description="Variable name")
    value: Any = Field(..., description="Variable value")
    type: str = Field("auto", description="Variable type")
    description: Optional[str] = Field(None, description="Variable description")
    scope: str = Field("workflow", description="Variable scope")

    @classmethod
    @field_validator("scope")
    def validate_scope(cls, v: str) -> str:
        """Validate variable scope."""
        valid_scopes = ["workflow", "global", "step", "temporary"]
        if v not in valid_scopes:
            raise ValueError(f"Invalid scope. Must be one of: {valid_scopes}")
        return v


class WorkflowTriggerSchema(BaseModel):
    """Schema for workflow triggers."""

    type: str = Field(..., description="Trigger type")
    condition: Dict[str, Any] = Field(..., description="Trigger condition")
    enabled: bool = Field(True, description="Whether trigger is enabled")

    @classmethod
    @field_validator("type")
    def validate_type(cls, v: str) -> str:
        """Validate trigger type."""
        valid_types = ["manual", "file_change", "schedule", "webhook", "condition"]
        if v not in valid_types:
            raise ValueError(f"Invalid trigger type. Must be one of: {valid_types}")
        return v


class WorkflowSchema(BaseModel):
    """Schema for complete workflows."""

    # Workflow identification
    name: str = Field(..., description="Workflow name")
    version: str = Field("1.0.0", description="Workflow version")
    description: Optional[str] = Field(None, description="Workflow description")

    # Workflow configuration
    steps: List[WorkflowStepSchema] = Field(..., description="Workflow steps", min_items=1)
    variables: List[WorkflowVariableSchema] = Field(
        default_factory=list,
        description="Workflow variables"
    )

    # Execution settings
    parallel_execution: bool = Field(False, description="Enable parallel step execution")
    stop_on_error: bool = Field(True, description="Stop workflow on first error")
    max_concurrent_steps: int = Field(1, description="Maximum concurrent steps", ge=1, le=10)

    # Workflow metadata
    author: Optional[str] = Field(None, description="Workflow author")
    tags: List[str] = Field(default_factory=list, description="Workflow tags")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    modified_at: Optional[datetime] = Field(None, description="Last modification timestamp")

    # Global parameters (can be referenced in step parameters)
    global_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Global parameters available to all steps"
    )

    # Triggers
    triggers: List[WorkflowTriggerSchema] = Field(
        default_factory=list,
        description="Workflow triggers"
    )

    # Validation settings
    validation: Dict[str, Any] = Field(
        default_factory=dict,
        description="Workflow validation settings"
    )

    model_config = ConfigDict(extra="allow")  # Allow additional fields for extensibility

    @classmethod
    @field_validator("name")
    def validate_name(cls, v: str) -> str:
        """Validate workflow name."""
        if not v.strip():
            raise ValueError("Workflow name cannot be empty")
        return v.strip()

    @classmethod
    @field_validator("version")
    def validate_version(cls, v: str) -> str:
        """Validate version format."""
        import re
        if not re.match(r'^\d+\.\d+\.\d+$', v):
            raise ValueError("Version must be in format 'x.y.z'")
        return v

    @classmethod
    @field_validator("steps")
    def validate_steps(cls, v: List[WorkflowStepSchema]) -> List[WorkflowStepSchema]:
        """Validate workflow steps."""
        if not v:
            raise ValueError("Workflow must have at least one step")

        # Check for duplicate step names
        step_names = [step.name for step in v]
        if len(step_names) != len(set(step_names)):
            raise ValueError("Workflow steps must have unique names")

        # Validate step dependencies
        for step in v:
            for dependency in step.depends_on:
                if dependency not in step_names:
                    raise ValueError(f"Step '{step.name}' depends on unknown step '{dependency}'")

        # Check for circular dependencies (simple check)
        cls._check_circular_dependencies(v)

        return v

    @staticmethod
    def _check_circular_dependencies(steps: List[WorkflowStepSchema]) -> None:
        """Check for circular dependencies in workflow steps."""
        step_deps = {step.name: set(step.depends_on) for step in steps}

        def has_cycle(node: str, visited: set, rec_stack: set) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in step_deps.get(node, set()):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        visited = set()
        rec_stack = set()

        for step_name in step_deps:
            if step_name not in visited:
                if has_cycle(step_name, visited, rec_stack):
                    raise ValueError("Circular dependency detected in workflow steps")


class WorkflowTemplateSchema(BaseModel):
    """Schema for workflow templates."""

    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    category: str = Field("general", description="Template category")

    # Template metadata
    parameters: List[ParameterDefinitionSchema] = Field(
        default_factory=list,
        description="Template parameters"
    )

    # Template content
    workflow_template: Dict[str, Any] = Field(
        ...,
        description="Workflow template with placeholders"
    )

    # Usage information
    examples: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Usage examples"
    )

    tags: List[str] = Field(default_factory=list, description="Template tags")

    model_config = ConfigDict(extra="allow")


class WorkflowExecutionSchema(BaseModel):
    """Schema for workflow execution records."""

    workflow_name: str = Field(..., description="Name of executed workflow")
    workflow_version: str = Field(..., description="Version of executed workflow")
    execution_id: str = Field(..., description="Unique execution identifier")

    # Execution metadata
    started_at: datetime = Field(..., description="Execution start time")
    completed_at: Optional[datetime] = Field(None, description="Execution completion time")
    status: str = Field("running", description="Execution status")

    # Execution results
    total_steps: int = Field(..., description="Total number of steps")
    completed_steps: int = Field(0, description="Number of completed steps")
    failed_steps: int = Field(0, description="Number of failed steps")
    skipped_steps: int = Field(0, description="Number of skipped steps")

    # Execution context
    input_files: List[str] = Field(default_factory=list, description="Input file paths")
    output_files: List[str] = Field(default_factory=list, description="Output file paths")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Execution parameters")

    # Error information
    error_message: Optional[str] = Field(None, description="Error message if execution failed")
    error_step: Optional[str] = Field(None, description="Step that caused the error")

    model_config = ConfigDict(extra="allow")