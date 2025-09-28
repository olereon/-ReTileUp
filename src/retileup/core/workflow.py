"""Workflow management for ReTileUp."""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator
from PIL import Image

from .registry import ToolRegistry

logger = logging.getLogger(__name__)


class StepStatus(str, Enum):
    """Status of a workflow step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStep(BaseModel):
    """A single step in a workflow."""

    # Step identification
    name: str = Field(..., description="Step name")
    tool_name: str = Field(..., description="Name of the tool to use")
    description: Optional[str] = Field(None, description="Step description")

    # Step configuration
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    condition: Optional[str] = Field(None, description="Condition for step execution")
    enabled: bool = Field(True, description="Whether the step is enabled")

    # Step metadata
    tags: List[str] = Field(default_factory=list, description="Step tags")
    timeout: Optional[float] = Field(None, description="Step timeout in seconds")

    # Runtime state
    status: StepStatus = Field(StepStatus.PENDING, description="Current step status")
    error_message: Optional[str] = Field(None, description="Error message if step failed")
    execution_time: Optional[float] = Field(None, description="Step execution time in seconds")

    model_config = ConfigDict(use_enum_values=True)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate step name."""
        if not v.strip():
            raise ValueError("Step name cannot be empty")
        return v.strip()

    def reset_status(self) -> None:
        """Reset step status to pending."""
        self.status = StepStatus.PENDING
        self.error_message = None
        self.execution_time = None


class Workflow(BaseModel):
    """A workflow containing multiple processing steps."""

    # Workflow identification
    name: str = Field(..., description="Workflow name")
    version: str = Field("1.0.0", description="Workflow version")
    description: Optional[str] = Field(None, description="Workflow description")

    # Workflow configuration
    steps: List[WorkflowStep] = Field(default_factory=list, description="Workflow steps")
    parallel_execution: bool = Field(False, description="Enable parallel step execution")
    stop_on_error: bool = Field(True, description="Stop workflow on first error")

    # Workflow metadata
    author: Optional[str] = Field(None, description="Workflow author")
    tags: List[str] = Field(default_factory=list, description="Workflow tags")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    modified_at: Optional[str] = Field(None, description="Last modification timestamp")

    # Global parameters (can be referenced in step parameters)
    global_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Global parameters available to all steps"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate workflow name."""
        if not v.strip():
            raise ValueError("Workflow name cannot be empty")
        return v.strip()

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, v: List[WorkflowStep]) -> List[WorkflowStep]:
        """Validate workflow steps."""
        if not v:
            raise ValueError("Workflow must have at least one step")

        # Check for duplicate step names
        step_names = [step.name for step in v]
        if len(step_names) != len(set(step_names)):
            raise ValueError("Workflow steps must have unique names")

        return v

    def add_step(
        self,
        name: str,
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> WorkflowStep:
        """Add a step to the workflow.

        Args:
            name: Step name
            tool_name: Name of the tool to use
            parameters: Tool parameters
            **kwargs: Additional step configuration

        Returns:
            The created workflow step

        Raises:
            ValueError: If step name already exists
        """
        if any(step.name == name for step in self.steps):
            raise ValueError(f"Step with name '{name}' already exists")

        step = WorkflowStep(
            name=name,
            tool_name=tool_name,
            parameters=parameters or {},
            **kwargs
        )
        self.steps.append(step)
        return step

    def get_step(self, name: str) -> Optional[WorkflowStep]:
        """Get a step by name.

        Args:
            name: Step name

        Returns:
            WorkflowStep or None if not found
        """
        for step in self.steps:
            if step.name == name:
                return step
        return None

    def remove_step(self, name: str) -> bool:
        """Remove a step from the workflow.

        Args:
            name: Step name

        Returns:
            True if step was removed, False if not found
        """
        for i, step in enumerate(self.steps):
            if step.name == name:
                del self.steps[i]
                return True
        return False

    def get_enabled_steps(self) -> List[WorkflowStep]:
        """Get list of enabled steps."""
        return [step for step in self.steps if step.enabled]

    def get_steps_by_status(self, status: StepStatus) -> List[WorkflowStep]:
        """Get steps with a specific status.

        Args:
            status: Step status to filter by

        Returns:
            List of matching steps
        """
        return [step for step in self.steps if step.status == status]

    def get_steps_by_tag(self, tag: str) -> List[WorkflowStep]:
        """Get steps with a specific tag.

        Args:
            tag: Tag to search for

        Returns:
            List of matching steps
        """
        return [step for step in self.steps if tag in step.tags]

    def reset_workflow(self) -> None:
        """Reset all steps to pending status."""
        for step in self.steps:
            step.reset_status()

    def validate_workflow(self, registry: ToolRegistry) -> List[str]:
        """Validate the workflow against a tool registry.

        Args:
            registry: Tool registry to validate against

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check that all tools exist in registry
        for step in self.steps:
            if step.tool_name not in registry:
                errors.append(f"Step '{step.name}': Tool '{step.tool_name}' not found in registry")

        # Additional validation can be added here
        # - Check parameter schemas
        # - Validate conditions
        # - Check for circular dependencies (if we add step dependencies)

        return errors

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get a summary of workflow execution.

        Returns:
            Dictionary containing execution statistics
        """
        total_steps = len(self.steps)
        completed_steps = len(self.get_steps_by_status(StepStatus.COMPLETED))
        failed_steps = len(self.get_steps_by_status(StepStatus.FAILED))
        skipped_steps = len(self.get_steps_by_status(StepStatus.SKIPPED))

        total_time = sum(
            step.execution_time for step in self.steps
            if step.execution_time is not None
        )

        return {
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "skipped_steps": skipped_steps,
            "success_rate": completed_steps / total_steps if total_steps > 0 else 0,
            "total_execution_time": total_time,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert workflow to dictionary."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workflow":
        """Create workflow from dictionary."""
        return cls(**data)