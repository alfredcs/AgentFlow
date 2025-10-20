"""
Core workflow engine for AgentFlow using Amazon Strands SDK
"""

import asyncio
import uuid
import time
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)

from agentflow.core.agent import StrandsAgent, Agent
from agentflow.utils.logging import setup_logger
from agentflow.utils.exceptions import WorkflowError, AgentExecutionError

logger = setup_logger(__name__)


class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowConfig:
    """Configuration for workflow execution"""
    name: str
    description: str = ""
    max_retries: int = 3
    timeout_seconds: int = 300
    enable_parallel: bool = True
    log_level: str = "INFO"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowStep:
    """Individual step in workflow"""
    step_id: str
    agent: Agent
    inputs: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    retry_count: int = 0
    status: WorkflowStatus = WorkflowStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None


class StrandsWorkflow:
    """
    Main workflow orchestration engine using Amazon Strands SDK patterns
    
    Manages execution of multi-step agent workflows with:
    - Dependency resolution
    - Parallel execution
    - Fault tolerance with automatic retry
    - CloudWatch logging
    - Execution tracking and observability
    """
    
    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.workflow_id = str(uuid.uuid4())
        self.steps: Dict[str, WorkflowStep] = {}
        self.status = WorkflowStatus.PENDING
        self.logger = logger.bind(
            workflow_id=self.workflow_id,
            workflow_name=config.name,
            workflow_type="StrandsWorkflow"
        )
        self.execution_history: List[Dict[str, Any]] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.execution_metrics: Dict[str, Any] = {
            "total_steps": 0,
            "completed_steps": 0,
            "failed_steps": 0,
            "retried_steps": 0
        }
        
        # CloudWatch logging
        self.logger.info(
            "Workflow initialized",
            max_retries=config.max_retries,
            timeout_seconds=config.timeout_seconds,
            enable_parallel=config.enable_parallel
        )
        
    def add_step(
        self,
        step_id: str,
        agent: Agent,
        inputs: Dict[str, Any],
        dependencies: Optional[List[str]] = None
    ) -> "Workflow":
        """Add a step to the workflow"""
        if step_id in self.steps:
            raise WorkflowError(f"Step {step_id} already exists")
            
        step = WorkflowStep(
            step_id=step_id,
            agent=agent,
            inputs=inputs,
            dependencies=dependencies or []
        )
        
        self.steps[step_id] = step
        self.logger.info(f"Added step {step_id}", agent=agent.config.name)
        return self
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(WorkflowError),
        before_sleep=before_sleep_log(logger, "WARNING"),
        reraise=True
    )
    async def execute(self) -> Dict[str, Any]:
        """
        Execute the workflow with Strands SDK patterns
        
        Implements:
        - Automatic retry at workflow level
        - CloudWatch logging
        - Execution metrics
        - Fault tolerance
        """
        self.start_time = time.time()
        self.status = WorkflowStatus.RUNNING
        
        # CloudWatch logging
        self.logger.info(
            "Workflow execution started",
            step_count=len(self.steps),
            timestamp=datetime.utcnow().isoformat()
        )
        
        try:
            # Validate workflow
            self._validate_workflow()
            
            # Execute steps in dependency order
            execution_order = self._resolve_dependencies()
            results = {}
            
            self.logger.info(
                "Execution order resolved",
                batch_count=len(execution_order),
                execution_order=[batch for batch in execution_order]
            )
            
            for batch_idx, batch in enumerate(execution_order):
                self.logger.info(
                    f"Executing batch {batch_idx + 1}/{len(execution_order)}",
                    batch_size=len(batch),
                    steps=batch
                )
                
                if self.config.enable_parallel and len(batch) > 1:
                    batch_results = await self._execute_parallel(batch, results)
                else:
                    batch_results = await self._execute_sequential(batch, results)
                
                results.update(batch_results)
                
                self.logger.info(
                    f"Batch {batch_idx + 1} completed",
                    completed_steps=len(batch_results)
                )
            
            self.end_time = time.time()
            self.status = WorkflowStatus.COMPLETED
            
            # Update metrics
            self.execution_metrics["total_steps"] = len(self.steps)
            self.execution_metrics["completed_steps"] = len(results)
            self.execution_metrics["execution_time"] = self.end_time - self.start_time
            
            # CloudWatch logging
            self.logger.info(
                "Workflow completed successfully",
                execution_time=self.end_time - self.start_time,
                total_steps=len(self.steps),
                completed_steps=len(results),
                metrics=self.execution_metrics
            )
            
            return {
                "workflow_id": self.workflow_id,
                "status": self.status.value,
                "results": results,
                "execution_history": self.execution_history,
                "metrics": self.execution_metrics,
                "execution_time": self.end_time - self.start_time
            }
            
        except Exception as e:
            self.end_time = time.time()
            self.status = WorkflowStatus.FAILED
            
            # Update metrics
            self.execution_metrics["execution_time"] = self.end_time - self.start_time if self.start_time else 0
            
            # CloudWatch error logging
            self.logger.error(
                "Workflow execution failed",
                error=str(e),
                error_type=type(e).__name__,
                execution_time=self.end_time - self.start_time if self.start_time else 0,
                metrics=self.execution_metrics,
                exc_info=True
            )
            
            raise WorkflowError(f"Workflow execution failed: {str(e)}") from e
    
    def _validate_workflow(self) -> None:
        """Validate workflow configuration"""
        if not self.steps:
            raise WorkflowError("Workflow has no steps")
        
        # Check for circular dependencies
        for step_id, step in self.steps.items():
            visited = set()
            if self._has_circular_dependency(step_id, visited):
                raise WorkflowError(f"Circular dependency detected for step {step_id}")
        
        # Validate all dependencies exist
        for step_id, step in self.steps.items():
            for dep in step.dependencies:
                if dep not in self.steps:
                    raise WorkflowError(f"Step {step_id} depends on non-existent step {dep}")
    
    def _has_circular_dependency(self, step_id: str, visited: set) -> bool:
        """Check for circular dependencies"""
        if step_id in visited:
            return True
        
        visited.add(step_id)
        step = self.steps[step_id]
        
        for dep in step.dependencies:
            if self._has_circular_dependency(dep, visited.copy()):
                return True
        
        return False
    
    def _resolve_dependencies(self) -> List[List[str]]:
        """Resolve execution order based on dependencies"""
        execution_order = []
        completed = set()
        
        while len(completed) < len(self.steps):
            # Find steps that can be executed
            ready = []
            for step_id, step in self.steps.items():
                if step_id not in completed:
                    if all(dep in completed for dep in step.dependencies):
                        ready.append(step_id)
            
            if not ready:
                raise WorkflowError("Cannot resolve dependencies - possible circular dependency")
            
            execution_order.append(ready)
            completed.update(ready)
        
        return execution_order
    
    async def _execute_parallel(
        self,
        step_ids: List[str],
        previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute steps in parallel"""
        self.logger.info(f"Executing {len(step_ids)} steps in parallel", steps=step_ids)
        
        tasks = []
        for step_id in step_ids:
            task = self._execute_step(step_id, previous_results)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        batch_results = {}
        for step_id, result in zip(step_ids, results):
            if isinstance(result, Exception):
                raise AgentExecutionError(f"Step {step_id} failed: {str(result)}")
            batch_results[step_id] = result
        
        return batch_results
    
    async def _execute_sequential(
        self,
        step_ids: List[str],
        previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute steps sequentially"""
        self.logger.info(f"Executing {len(step_ids)} steps sequentially", steps=step_ids)
        
        results = {}
        for step_id in step_ids:
            result = await self._execute_step(step_id, previous_results)
            results[step_id] = result
            previous_results[step_id] = result
        
        return results
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((AgentExecutionError, asyncio.TimeoutError)),
        before_sleep=before_sleep_log(logger, "WARNING"),
        reraise=True
    )
    async def _execute_step(
        self,
        step_id: str,
        previous_results: Dict[str, Any]
    ) -> Any:
        """
        Execute a single step with Strands SDK fault tolerance
        
        Implements:
        - Automatic retry with exponential backoff
        - CloudWatch logging
        - Timeout handling
        - Execution tracking
        """
        step = self.steps[step_id]
        step.status = WorkflowStatus.RUNNING
        step_start_time = time.time()
        
        # Merge inputs with previous results
        inputs = step.inputs.copy()
        for dep in step.dependencies:
            if dep in previous_results:
                inputs[f"{dep}_result"] = previous_results[dep]
        
        # CloudWatch logging
        self.logger.info(
            f"Step execution started",
            step_id=step_id,
            agent=step.agent.config.name,
            dependencies=step.dependencies,
            input_keys=list(inputs.keys())
        )
        
        retry_count = 0
        last_error = None
        
        while retry_count <= self.config.max_retries:
            try:
                self.logger.debug(
                    f"Executing step {step_id}",
                    attempt=retry_count + 1,
                    max_retries=self.config.max_retries,
                    agent=step.agent.config.name
                )
                
                # Execute with timeout
                result = await asyncio.wait_for(
                    step.agent.execute(inputs),
                    timeout=self.config.timeout_seconds
                )
                
                step_end_time = time.time()
                step.status = WorkflowStatus.COMPLETED
                step.result = result
                
                # Update metrics
                self.execution_metrics["completed_steps"] += 1
                if retry_count > 0:
                    self.execution_metrics["retried_steps"] += 1
                
                # CloudWatch logging
                self.execution_history.append({
                    "step_id": step_id,
                    "status": "success",
                    "attempt": retry_count + 1,
                    "execution_time": step_end_time - step_start_time,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                self.logger.info(
                    f"Step {step_id} completed successfully",
                    execution_time=step_end_time - step_start_time,
                    attempts=retry_count + 1
                )
                
                return result
                
            except asyncio.TimeoutError as e:
                last_error = e
                retry_count += 1
                step.retry_count = retry_count
                
                self.logger.warning(
                    f"Step {step_id} timed out",
                    attempt=retry_count,
                    timeout=self.config.timeout_seconds
                )
                
                if retry_count <= self.config.max_retries:
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                    
            except Exception as e:
                last_error = e
                retry_count += 1
                step.retry_count = retry_count
                
                self.logger.warning(
                    f"Step {step_id} failed",
                    attempt=retry_count,
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True
                )
                
                if retry_count <= self.config.max_retries:
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff
        
        # All retries exhausted
        step_end_time = time.time()
        step.status = WorkflowStatus.FAILED
        step.error = str(last_error)
        
        # Update metrics
        self.execution_metrics["failed_steps"] += 1
        
        # CloudWatch error logging
        self.execution_history.append({
            "step_id": step_id,
            "status": "failed",
            "attempts": retry_count,
            "error": str(last_error),
            "error_type": type(last_error).__name__,
            "execution_time": step_end_time - step_start_time,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        self.logger.error(
            f"Step {step_id} failed after all retries",
            attempts=retry_count,
            error=str(last_error),
            execution_time=step_end_time - step_start_time
        )
        
        raise AgentExecutionError(
            f"Step {step_id} failed after {retry_count} attempts: {str(last_error)}"
        )


# Backward compatibility alias
Workflow = StrandsWorkflow
