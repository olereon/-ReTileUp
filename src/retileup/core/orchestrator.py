"""Workflow orchestrator for executing ReTileUp workflows."""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional, Union

from PIL import Image

from .config import Config
from .registry import ToolRegistry
from .workflow import Workflow, WorkflowStep, StepStatus

logger = logging.getLogger(__name__)


class WorkflowExecutionError(Exception):
    """Exception raised during workflow execution."""
    pass


class StepExecutionResult:
    """Result of executing a workflow step."""

    def __init__(
        self,
        step: WorkflowStep,
        success: bool,
        result: Optional[Union[Image.Image, List[Image.Image]]] = None,
        error: Optional[Exception] = None,
        execution_time: float = 0.0
    ) -> None:
        """Initialize execution result.

        Args:
            step: The executed step
            success: Whether the step executed successfully
            result: The processing result (if successful)
            error: The error that occurred (if unsuccessful)
            execution_time: Time taken to execute the step
        """
        self.step = step
        self.success = success
        self.result = result
        self.error = error
        self.execution_time = execution_time


class WorkflowOrchestrator:
    """Orchestrates the execution of ReTileUp workflows."""

    def __init__(
        self,
        registry: ToolRegistry,
        config: Optional[Config] = None
    ) -> None:
        """Initialize the orchestrator.

        Args:
            registry: Tool registry
            config: Configuration object
        """
        self.registry = registry
        self.config = config or Config.load_default()
        self._executor: Optional[ThreadPoolExecutor] = None

    @contextmanager
    def _get_executor(self) -> Generator[ThreadPoolExecutor, None, None]:
        """Get thread pool executor context manager."""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(
                max_workers=self.config.performance.max_workers
            )
        try:
            yield self._executor
        finally:
            # Keep the executor alive for reuse
            pass

    def execute_step(
        self,
        step: WorkflowStep,
        image: Image.Image,
        global_parameters: Optional[Dict[str, Any]] = None
    ) -> StepExecutionResult:
        """Execute a single workflow step.

        Args:
            step: The step to execute
            image: Input image
            global_parameters: Global workflow parameters

        Returns:
            Step execution result
        """
        start_time = time.time()
        step.status = StepStatus.RUNNING

        try:
            # Get the tool
            tool = self.registry.create_tool(step.tool_name)
            if tool is None:
                raise WorkflowExecutionError(f"Tool '{step.tool_name}' not found")

            # Merge global parameters with step parameters
            merged_parameters = {}
            if global_parameters:
                merged_parameters.update(global_parameters)
            merged_parameters.update(step.parameters)

            # Validate parameters
            validated_parameters = tool.validate_parameters(merged_parameters)

            # Execute the tool
            logger.info(f"Executing step '{step.name}' with tool '{step.tool_name}'")
            result = tool.process_image(image, validated_parameters)

            execution_time = time.time() - start_time
            step.status = StepStatus.COMPLETED
            step.execution_time = execution_time

            logger.info(f"Step '{step.name}' completed in {execution_time:.2f}s")

            return StepExecutionResult(
                step=step,
                success=True,
                result=result,
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            step.status = StepStatus.FAILED
            step.error_message = str(e)
            step.execution_time = execution_time

            logger.error(f"Step '{step.name}' failed after {execution_time:.2f}s: {e}")

            return StepExecutionResult(
                step=step,
                success=False,
                error=e,
                execution_time=execution_time
            )

    def execute_workflow_sequential(
        self,
        workflow: Workflow,
        image: Image.Image
    ) -> List[StepExecutionResult]:
        """Execute workflow steps sequentially.

        Args:
            workflow: The workflow to execute
            image: Input image

        Returns:
            List of step execution results
        """
        results = []
        current_image = image

        for step in workflow.get_enabled_steps():
            # Check if step should be executed (condition evaluation could go here)
            if not step.enabled:
                step.status = StepStatus.SKIPPED
                continue

            # Execute the step
            result = self.execute_step(step, current_image, workflow.global_parameters)
            results.append(result)

            # Update current image for next step
            if result.success and isinstance(result.result, Image.Image):
                current_image = result.result
            elif result.success and isinstance(result.result, list) and result.result:
                # If multiple images returned, use the first one
                current_image = result.result[0]

            # Stop on error if configured
            if not result.success and workflow.stop_on_error:
                logger.error(f"Stopping workflow due to error in step '{step.name}'")
                # Mark remaining steps as skipped
                remaining_steps = workflow.steps[workflow.steps.index(step) + 1:]
                for remaining_step in remaining_steps:
                    if remaining_step.enabled:
                        remaining_step.status = StepStatus.SKIPPED
                break

        return results

    def execute_workflow_parallel(
        self,
        workflow: Workflow,
        image: Image.Image
    ) -> List[StepExecutionResult]:
        """Execute workflow steps in parallel.

        Args:
            workflow: The workflow to execute
            image: Input image

        Returns:
            List of step execution results

        Note:
            This is a simplified parallel execution that runs all enabled steps
            concurrently with the same input image. More sophisticated parallel
            execution would require dependency graphs.
        """
        enabled_steps = workflow.get_enabled_steps()
        results = []

        with self._get_executor() as executor:
            # Submit all steps for execution
            future_to_step = {
                executor.submit(
                    self.execute_step,
                    step,
                    image.copy(),  # Each step gets a copy of the original image
                    workflow.global_parameters
                ): step
                for step in enabled_steps
            }

            # Collect results as they complete
            for future in as_completed(future_to_step):
                step = future_to_step[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    # This shouldn't happen as exceptions are caught in execute_step
                    logger.error(f"Unexpected error in step '{step.name}': {e}")
                    step.status = StepStatus.FAILED
                    step.error_message = str(e)
                    results.append(StepExecutionResult(
                        step=step,
                        success=False,
                        error=e
                    ))

        # Sort results by original step order
        step_order = {step.name: i for i, step in enumerate(enabled_steps)}
        results.sort(key=lambda r: step_order.get(r.step.name, float('inf')))

        return results

    def execute_workflow(
        self,
        workflow: Workflow,
        image: Image.Image,
        validate: bool = True
    ) -> List[StepExecutionResult]:
        """Execute a workflow.

        Args:
            workflow: The workflow to execute
            image: Input image
            validate: Whether to validate the workflow before execution

        Returns:
            List of step execution results

        Raises:
            WorkflowExecutionError: If workflow validation fails
        """
        # Validate workflow
        if validate:
            errors = workflow.validate_workflow(self.registry)
            if errors:
                raise WorkflowExecutionError(f"Workflow validation failed: {errors}")

        # Reset workflow status
        workflow.reset_workflow()

        logger.info(f"Starting execution of workflow '{workflow.name}'")
        start_time = time.time()

        try:
            # Choose execution strategy
            if workflow.parallel_execution:
                results = self.execute_workflow_parallel(workflow, image)
            else:
                results = self.execute_workflow_sequential(workflow, image)

            total_time = time.time() - start_time
            summary = workflow.get_execution_summary()

            logger.info(
                f"Workflow '{workflow.name}' completed in {total_time:.2f}s. "
                f"Success rate: {summary['success_rate']:.1%} "
                f"({summary['completed_steps']}/{summary['total_steps']} steps)"
            )

            return results

        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"Workflow '{workflow.name}' failed after {total_time:.2f}s: {e}")
            raise WorkflowExecutionError(f"Workflow execution failed: {e}") from e

    def get_final_result(
        self,
        results: List[StepExecutionResult]
    ) -> Optional[Union[Image.Image, List[Image.Image]]]:
        """Get the final result from workflow execution.

        Args:
            results: List of step execution results

        Returns:
            Final processing result or None if no successful results
        """
        # Return the result from the last successful step
        for result in reversed(results):
            if result.success and result.result is not None:
                return result.result
        return None

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None