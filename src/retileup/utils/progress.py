"""Progress tracking utilities for ReTileUp."""

import time
from contextlib import contextmanager
from typing import Any, Callable, Generator, Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)


class SpeedColumn(ProgressColumn):
    """Custom progress column showing processing speed."""

    def render(self, task) -> str:
        """Render the speed column."""
        if task.speed is None:
            return "-- it/s"
        return f"{task.speed:.2f} it/s"


class ProgressTracker:
    """Progress tracking utility for ReTileUp operations."""

    def __init__(self, console: Optional[Console] = None) -> None:
        """Initialize progress tracker.

        Args:
            console: Rich console instance (creates new one if None)
        """
        self.console = console or Console()
        self._progress: Optional[Progress] = None
        self._tasks: dict[str, TaskID] = {}

    @contextmanager
    def track_operation(
        self,
        description: str = "Processing",
        total: Optional[int] = None,
        show_speed: bool = True,
        show_time: bool = True
    ) -> Generator["ProgressContext", None, None]:
        """Context manager for tracking a single operation.

        Args:
            description: Description of the operation
            total: Total number of items to process (None for indeterminate)
            show_speed: Whether to show processing speed
            show_time: Whether to show time information

        Yields:
            ProgressContext for updating progress
        """
        # Build progress columns
        columns = [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
        ]

        if total is not None:
            columns.extend([
                BarColumn(),
                MofNCompleteColumn(),
            ])

        if show_speed:
            columns.append(SpeedColumn())

        if show_time:
            columns.extend([
                TimeElapsedColumn(),
            ])
            if total is not None:
                columns.append(TimeRemainingColumn())

        with Progress(*columns, console=self.console) as progress:
            task_id = progress.add_task(description, total=total)
            context = ProgressContext(progress, task_id)
            yield context

    @contextmanager
    def track_multiple_operations(
        self,
        show_overall: bool = True
    ) -> Generator["MultiProgressContext", None, None]:
        """Context manager for tracking multiple operations.

        Args:
            show_overall: Whether to show overall progress

        Yields:
            MultiProgressContext for managing multiple progress bars
        """
        columns = [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            SpeedColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        ]

        with Progress(*columns, console=self.console) as progress:
            context = MultiProgressContext(progress, show_overall)
            yield context

    def create_simple_progress(self, items, description: str = "Processing") -> Generator[Any, None, None]:
        """Create a simple progress bar for iterating over items.

        Args:
            items: Iterable to process
            description: Description of the operation

        Yields:
            Items from the iterable
        """
        with self.track_operation(description, total=len(items) if hasattr(items, '__len__') else None) as progress:
            for item in items:
                yield item
                progress.advance()


class ProgressContext:
    """Context for updating a single progress operation."""

    def __init__(self, progress: Progress, task_id: TaskID) -> None:
        """Initialize progress context.

        Args:
            progress: Rich Progress instance
            task_id: Task ID for this progress
        """
        self.progress = progress
        self.task_id = task_id
        self._start_time = time.time()

    def advance(self, amount: int = 1) -> None:
        """Advance progress by specified amount.

        Args:
            amount: Amount to advance by
        """
        self.progress.advance(self.task_id, amount)

    def update(
        self,
        completed: Optional[int] = None,
        total: Optional[int] = None,
        description: Optional[str] = None,
        **kwargs
    ) -> None:
        """Update progress information.

        Args:
            completed: Number of completed items
            total: Total number of items
            description: New description
            **kwargs: Additional progress update parameters
        """
        update_kwargs = kwargs.copy()

        if completed is not None:
            update_kwargs['completed'] = completed

        if total is not None:
            update_kwargs['total'] = total

        if description is not None:
            update_kwargs['description'] = description

        self.progress.update(self.task_id, **update_kwargs)

    def set_total(self, total: int) -> None:
        """Set the total number of items.

        Args:
            total: Total number of items
        """
        self.progress.update(self.task_id, total=total)

    def complete(self) -> None:
        """Mark the operation as complete."""
        task = self.progress.tasks[self.task_id]
        if task.total is not None:
            self.progress.update(self.task_id, completed=task.total)

    def get_elapsed_time(self) -> float:
        """Get elapsed time since progress started.

        Returns:
            Elapsed time in seconds
        """
        return time.time() - self._start_time


class MultiProgressContext:
    """Context for managing multiple progress operations."""

    def __init__(self, progress: Progress, show_overall: bool = True) -> None:
        """Initialize multi-progress context.

        Args:
            progress: Rich Progress instance
            show_overall: Whether to show overall progress
        """
        self.progress = progress
        self._tasks: dict[str, TaskID] = {}
        self._overall_task: Optional[TaskID] = None
        self._show_overall = show_overall

    def add_task(
        self,
        name: str,
        description: str,
        total: Optional[int] = None
    ) -> str:
        """Add a new progress task.

        Args:
            name: Unique name for the task
            description: Description of the task
            total: Total number of items for this task

        Returns:
            Task name (same as input)

        Raises:
            ValueError: If task name already exists
        """
        if name in self._tasks:
            raise ValueError(f"Task '{name}' already exists")

        task_id = self.progress.add_task(description, total=total)
        self._tasks[name] = task_id

        # Update overall progress if enabled
        if self._show_overall:
            self._update_overall_progress()

        return name

    def update_task(
        self,
        name: str,
        completed: Optional[int] = None,
        total: Optional[int] = None,
        description: Optional[str] = None,
        advance: Optional[int] = None,
        **kwargs
    ) -> None:
        """Update a specific task.

        Args:
            name: Name of the task to update
            completed: Number of completed items
            total: Total number of items
            description: New description
            advance: Amount to advance by
            **kwargs: Additional progress update parameters

        Raises:
            KeyError: If task name doesn't exist
        """
        if name not in self._tasks:
            raise KeyError(f"Task '{name}' not found")

        task_id = self._tasks[name]

        if advance is not None:
            self.progress.advance(task_id, advance)

        update_kwargs = kwargs.copy()
        if completed is not None:
            update_kwargs['completed'] = completed
        if total is not None:
            update_kwargs['total'] = total
        if description is not None:
            update_kwargs['description'] = description

        if update_kwargs:
            self.progress.update(task_id, **update_kwargs)

        # Update overall progress if enabled
        if self._show_overall:
            self._update_overall_progress()

    def complete_task(self, name: str) -> None:
        """Mark a task as complete.

        Args:
            name: Name of the task to complete

        Raises:
            KeyError: If task name doesn't exist
        """
        if name not in self._tasks:
            raise KeyError(f"Task '{name}' not found")

        task_id = self._tasks[name]
        task = self.progress.tasks[task_id]

        if task.total is not None:
            self.progress.update(task_id, completed=task.total)

        # Update overall progress if enabled
        if self._show_overall:
            self._update_overall_progress()

    def get_task_progress(self, name: str) -> dict:
        """Get progress information for a task.

        Args:
            name: Name of the task

        Returns:
            Dictionary with progress information

        Raises:
            KeyError: If task name doesn't exist
        """
        if name not in self._tasks:
            raise KeyError(f"Task '{name}' not found")

        task_id = self._tasks[name]
        task = self.progress.tasks[task_id]

        return {
            'description': task.description,
            'completed': task.completed,
            'total': task.total,
            'percentage': task.percentage,
            'speed': task.speed,
            'time_elapsed': task.elapsed,
            'time_remaining': task.time_remaining,
        }

    def _update_overall_progress(self) -> None:
        """Update overall progress based on all tasks."""
        if not self._tasks:
            return

        # Create overall task if it doesn't exist
        if self._overall_task is None:
            self._overall_task = self.progress.add_task(
                "[bold blue]Overall Progress",
                total=100
            )

        # Calculate overall percentage
        total_percentage = 0
        task_count = 0

        for task_id in self._tasks.values():
            task = self.progress.tasks[task_id]
            if task.total is not None:
                total_percentage += task.percentage or 0
                task_count += 1

        if task_count > 0:
            overall_percentage = total_percentage / task_count
            self.progress.update(
                self._overall_task,
                completed=overall_percentage
            )


# Convenience functions for common use cases
def track_list_processing(
    items,
    processor: Callable[[Any], Any],
    description: str = "Processing items",
    console: Optional[Console] = None
) -> list:
    """Process a list of items with progress tracking.

    Args:
        items: List of items to process
        processor: Function to process each item
        description: Description for the progress bar
        console: Rich console instance

    Returns:
        List of processed results
    """
    tracker = ProgressTracker(console)
    results = []

    with tracker.track_operation(description, total=len(items)) as progress:
        for item in items:
            result = processor(item)
            results.append(result)
            progress.advance()

    return results


@contextmanager
def simple_progress(
    description: str = "Processing",
    total: Optional[int] = None,
    console: Optional[Console] = None
) -> Generator[ProgressContext, None, None]:
    """Simple context manager for progress tracking.

    Args:
        description: Description of the operation
        total: Total number of items
        console: Rich console instance

    Yields:
        ProgressContext for updating progress
    """
    tracker = ProgressTracker(console)
    with tracker.track_operation(description, total) as progress:
        yield progress