"""
Core workflow engine for AgentFlow
"""

import asyncio
import uuid
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import structlog

from agentflow.core.agent import Agent
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


class Workflow:
    """
    Main workflow orchestration engine
    
    Manages execution of multi-step agent workflows with dependency resolution,
    parallel execution, error handling, and observability.
    """
    
    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.workflow_id = str(uuid.uuid4())
        self.steps: Dict[str, WorkflowStep] = {}
        self.status = WorkflowStatus.PENDING
        self.logger = logger.bind(workflow_id=self.workflow_id, workflow_name=config.name)
        self.execution_history: List[Dict[str, Any]] = []
        
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
    
    async def execute(self) -> Dict[str, Any]:
        """Execute the workflow"""
        self.logger.info("Starting workflow execution")
        self.status = WorkflowStatus.RUNNING
        
        try:
            # Validate workflow
            self._validate_workflow()
            
            # Execute steps in dependency order
            execution_order = self._resolve_dependencies()
            results = {}
            
            for batch in execution_order:
                if self.config.enable_parallel and len(batch) > 1:
                    batch_results = await self._execute_parallel(batch, results)
                else:
                    batch_results = await self._execute_sequential(batch, results)
                
                results.update(batch_results)
            
            self.status = WorkflowStatus.COMPLETED
            self.logger.info("Workflow completed successfully")
            
            return {
                "workflow_id": self.workflow_id,
                "status": self.status.value,
                "results": results,
                "execution_history": self.execution_history
            }
            
        except Exception as e:
            self.status = WorkflowStatus.FAILED
            self.logger.error(f"Workflow failed: {str(e)}", exc_info=True)
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
    
    async def _execute_step(
        self,
        step_id: str,
        previous_results: Dict[str, Any]
    ) -> Any:
        """Execute a single step with retry logic"""
        step = self.steps[step_id]
        step.status = WorkflowStatus.RUNNING
        
        # Merge inputs with previous results
        inputs = step.inputs.copy()
        for dep in step.dependencies:
            if dep in previous_results:
                inputs[f"{dep}_result"] = previous_results[dep]
        
        retry_count = 0
        last_error = None
        
        while retry_count <= self.config.max_retries:
            try:
                self.logger.info(
                    f"Executing step {step_id}",
                    attempt=retry_count + 1,
                    agent=step.agent.config.name
                )
                
                result = await step.agent.execute(inputs)
                
                step.status = WorkflowStatus.COMPLETED
                step.result = result
                
                self.execution_history.append({
                    "step_id": step_id,
                    "status": "success",
                    "attempt": retry_count + 1,
                    "result": result
                })
                
                self.logger.info(f"Step {step_id} completed successfully")
                return result
                
            except Exception as e:
                last_error = e
                retry_count += 1
                step.retry_count = retry_count
                
                self.logger.warning(
                    f"Step {step_id} failed",
                    attempt=retry_count,
                    error=str(e),
                    exc_info=True
                )
                
                if retry_count <= self.config.max_retries:
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff
        
        # All retries exhausted
        step.status = WorkflowStatus.FAILED
        step.error = str(last_error)
        
        self.execution_history.append({
            "step_id": step_id,
            "status": "failed",
            "attempts": retry_count,
            "error": str(last_error)
        })
        
        raise AgentExecutionError(
            f"Step {step_id} failed after {retry_count} attempts: {str(last_error)}"
        )
